#!/usr/bin/env python3
"""
check_nocheckpoint_switches.py -- is a -nocheckpoint routine list consistent
with the adjoint-mode switches?

An adjoint-mode switch (useGMRediInAdMode, useApproxAdvectionInAdMode,
viscFacInAd, ...) changes inAdMode, package flags and viscFacAdj for the
backward sweep of each time step. FORWARD_STEP calls AUTODIFF_INADMODE_UNSET_TAP
first and AUTODIFF_INADMODE_SET_TAP last, so in its reverse sweep
AUTODIFF_INADMODE_SET_TAP_B applies the switches before any other adjoint
statement and AUTODIFF_INADMODE_UNSET_TAP_B reverts them after the last.

A switch reaches the adjoint only through values recorded after it is applied.
FORWARD_STEP's own recording sweep runs before it, in every build. In the
checkpoint-everything build every routine FORWARD_STEP calls is checkpointed:
its primal runs again, recording, inside its own _B routine in the reverse
sweep -- after the switch -- and so does everything below it. A routine
differentiated in split mode (-nocheckpoint) records in its _FWD routine, which
runs wherever its caller records: after the switch below a checkpointed
routine, before it when called from FORWARD_STEP or from a split routine that
itself records before it.

A list build therefore gives the checkpoint-everything adjoint under a switch
only if no listed routine that records before the switch -- one reached from
FORWARD_STEP through listed routines only -- executes, itself or through
anything it calls, a statement that reads a switched variable. Such a routine
would carry the forward-mode value into its own tape and its callers' (run
31056: split DYNAMICS taped forward-mode viscosities under the adjoint-viscosity
boost; runs 31156/31157 of the DINO stability study: split DO_OCEANIC_PHYS taped
the GM branch the switch turns off). A listed routine whose every call path from
FORWARD_STEP passes a checkpointed routine records after the switch, as in the
checkpoint-everything build, whatever it reads; FORWARD_STEP itself records
before the switch in either mode, and routines outside the time step never see
one.

A package that is not compiled keeps its use<PKG> flag .FALSE. in both sweeps
(packages_check stops a run that sets it; autodiff_readparms ANDs
use<PKG>InAdMode with it), so its flags leave the switched set when the build
directory's PACKAGES_CONFIG.h does not define ALLOW_<PKG>.

This script reads the preprocessed primal sources (*.f; Tapenade's *_b.f and
*_d.f are skipped) of an adjoint build directory, builds the static call graph
(CALL statements and references to any other program unit's name), marks the
units whose executable statements read a switched variable (declarations,
COMMON blocks and quoted strings do not count), finds the units that call the
switch hooks, and reports each listed routine.

    check_nocheckpoint_switches.py BUILD_DIR LIST_FILE        check a list
    check_nocheckpoint_switches.py BUILD_DIR LIST_FILE --filter=OUT
                                                  also write LIST_FILE without the
                                                  routines that must stay
                                                  checkpointed to OUT
    check_nocheckpoint_switches.py BUILD_DIR --all            classify every unit (TSV)

Options:
    --extra=NAME[,NAME]   further switched variables (the adjoint-viscosity
                          variant's inAd*/outAd* targets, say)

What it cannot see: a switched value passed as an argument is not traced (the
argument has another name in the callee), and calls through a variable
procedure name are invisible. Both are absent from the DINO call tree as far as
the switched variables go, and the final check of any list is a run bitwise
identical to the checkpoint-everything build under the switches it will be used
with.

Exit status: 0 if no listed routine records before the switch and reaches a
switched variable, 1 if one does, 2 on a usage error or a build without the
switch hooks.
"""
import os, re, sys
from collections import defaultdict, deque

# What pkg/autodiff/autodiff_inadmode_set_ad.F changes, plus the approximate-advection
# switch that gad_advection.F and gad_calc_rhs.F read together with inAdMode.
SWITCHED = {'INADMODE', 'USEKPP', 'USEGMREDI', 'USESEAICE', 'USEGGL90', 'USESALT_PLUME',
            'SEAICEUSEFREEDRIFT', 'SEAICEUSELSR', 'SEAICEUSEDYNAMICS', 'SEAICEADJMODE',
            'SINEGFAC', 'VISCFACADJ', 'USEAPPROXADVECTIONINADMODE'}
# The switched variables a package's absence pins to their forward-mode value.
PKG_FLAGS = {'KPP': {'USEKPP'}, 'GMREDI': {'USEGMREDI'}, 'GGL90': {'USEGGL90'},
             'SALT_PLUME': {'USESALT_PLUME'},
             'SEAICE': {'USESEAICE', 'SEAICEUSEFREEDRIFT', 'SEAICEUSELSR', 'SEAICEUSEDYNAMICS',
                        'SEAICEADJMODE', 'SINEGFAC'}}
# The hooks whose _B applies and reverts the switches (mods_tapenade_hooks/dummy_tap.F).
SWITCH_HOOKS = {'AUTODIFF_INADMODE_SET_TAP', 'AUTODIFF_INADMODE_UNSET_TAP'}
DECL = ('COMMON', 'LOGICAL', 'INTEGER', 'REAL', 'DOUBLE', 'CHARACTER', 'COMPLEX', 'PARAMETER',
        'EXTERNAL', 'INTRINSIC', 'SAVE', 'DATA', 'NAMELIST', 'EQUIVALENCE', 'IMPLICIT',
        'DIMENSION', 'INCLUDE', 'BYTE')
UNIT_RE = re.compile(r'^(?:RECURSIVE\s+)?(?:(?:REAL|INTEGER|LOGICAL|DOUBLEPRECISION|CHARACTER|COMPLEX)'
                     r'[*\w()]*\s*)?(SUBROUTINE|FUNCTION|PROGRAM|BLOCKDATA)\s*([A-Z_]\w*)')


def statements(path):
    """Fixed-form statements of a preprocessed file, strings and comments removed, upper case."""
    stmts = []
    with open(path, errors='replace') as fh:
        for raw in fh:
            line = raw.rstrip('\n')
            if not line or line[0] in 'Cc*!#' or not line.strip():
                continue
            body = line[6:] if len(line) > 6 else ''
            body = re.sub(r"'[^']*'", "''", body)          # quoted strings
            body = re.sub(r'"[^"]*"', '""', body)
            body = body.split('!')[0]                      # trailing comment
            if len(line) > 5 and line[5] not in ' 0' and line[:5].strip() == '' and stmts:
                stmts[-1] += ' ' + body
            else:
                stmts.append(body)
    return [s.upper() for s in stmts]


def parse(build_dir):
    units = {}                  # name -> list of executable statements
    for f in sorted(os.listdir(build_dir)):
        if not f.endswith('.f') or f.endswith(('_b.f', '_d.f')):
            continue
        path = os.path.join(build_dir, f)
        with open(path, errors='replace') as fh:
            if 'Generated by TAPENADE' in fh.read(4000):      # adj_tap_all.f and the like
                continue
        cur = None
        for s in statements(path):
            compact = s.replace(' ', '')
            m = UNIT_RE.match(compact)
            if m and cur is None:
                # the compact form glues the argument list on; take the name from the spaced form
                name = re.match(r'[A-Z_]\w*', s.split(m.group(1), 1)[1].strip()).group(0)
                cur = units.setdefault(name, [])
                continue
            if cur is None:
                continue
            # END, END SUBROUTINE NAME ... -- but not ENDIF / ENDDO / END IF
            if re.fullmatch(r'END(\s+(SUBROUTINE|FUNCTION|PROGRAM)(\s+\w+)?)?', s.strip()):
                cur = None
                continue
            # declarations (and COMMON blocks from the expanded headers) are not reads;
            # an assignment such as DATAFILE = ... is, whatever its first letters
            if compact.startswith(DECL) and not re.match(r'[A-Z_]\w*(\([^=]*\))?=', compact):
                continue
            cur.append(s)
    return units


def compiled_packages(build_dir):
    """Packages with ALLOW_<PKG> defined in the build's PACKAGES_CONFIG.h, or None without one."""
    path = os.path.join(build_dir, 'PACKAGES_CONFIG.h')
    if not os.path.isfile(path):
        return None
    with open(path) as fh:
        return set(re.findall(r'^#define\s+ALLOW_(\w+)', fh.read(), re.M))


def analyse(units, switched):
    names = set(units)
    ident = re.compile(r'[A-Z_]\w*')
    calls, reads, roots = defaultdict(set), {}, set()
    for u, stmts in units.items():
        toks = set()
        for s in stmts:
            toks.update(ident.findall(s))
        reads[u] = sorted(toks & switched)
        calls[u] = (toks & names) - {u}
        if toks & SWITCH_HOOKS and u not in SWITCH_HOOKS:
            roots.add(u)
    return calls, reads, roots


def path_to_switch(u, calls, reads):
    """Shortest call chain from u to a unit that reads a switched variable, or None."""
    seen, q = {u: None}, deque([u])
    while q:
        v = q.popleft()
        if reads.get(v):
            chain = [v]
            while seen[chain[-1]] is not None:
                chain.append(seen[chain[-1]])
            return list(reversed(chain)), reads[v]
        for w in sorted(calls.get(v, ())):
            if w not in seen:
                seen[w] = v
                q.append(w)
    return None


def records_before_switch(roots, calls, listed, passable):
    """Listed routines reached from a switch-hook caller through listed routines only, each
    mapped to the unit it was first reached from; the search continues below a routine
    only if passable(routine)."""
    parent, q = {}, deque(sorted(roots))
    while q:
        v = q.popleft()
        for w in sorted(calls.get(v, ())):
            if w in listed and w not in roots and w not in parent:
                parent[w] = v
                if passable(w):
                    q.append(w)
    return parent


def chain(u, parent):
    c = [u]
    while c[-1] in parent:
        c.append(parent[c[-1]])
    return ' > '.join(x.lower() for x in reversed(c))


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    opts = [a for a in argv[1:] if a.startswith('--')]
    if not args or not os.path.isdir(args[0]):
        print(__doc__); return 2
    switched = set(SWITCHED)
    for o in opts:
        if o.startswith('--extra='):
            switched.update(x.strip().upper() for x in o.split('=', 1)[1].split(',') if x.strip())
    compiled = compiled_packages(args[0])
    absent = sorted(p for p in PKG_FLAGS if compiled is not None and p not in compiled)
    for p in absent:
        switched -= PKG_FLAGS[p]
    units = parse(args[0])
    calls, reads, roots = analyse(units, switched)
    reach = {}

    def reaches(u):
        if u not in reach:
            reach[u] = path_to_switch(u, calls, reads)
        return reach[u]

    if '--all' in opts:
        print('unit\tswitch_free\treads\tvia')
        for u in sorted(units):
            p = reaches(u)
            print(f"{u.lower()}\t{'yes' if p is None else 'no'}\t{','.join(reads[u]).lower()}\t"
                  f"{'' if p is None else ' > '.join(x.lower() for x in p[0])}")
        return 0
    if len(args) < 2:
        print(__doc__); return 2
    names = [re.sub(r'#.*', '', l).strip().upper() for l in open(args[1])]
    names = [n for n in names if n]
    listed = {n for n in names if n in units}
    filt = next((o.split('=', 1)[1] for o in opts if o.startswith('--filter=')), None)
    print(f'{len(units)} program units in {args[0]}; the switch hooks are called from '
          f'{", ".join(sorted(r.lower() for r in roots)) or "no unit"}')
    print(f'switched variables: {", ".join(sorted(x.lower() for x in switched))}'
          + (f' (packages not compiled, their flags dropped: {", ".join(p.lower() for p in absent)})'
             if absent else ''))
    if not roots:
        print('ERROR: no unit calls the switch hooks; not an adjoint build with mods_tapenade_hooks?')
        return 2
    before = records_before_switch(roots, calls, listed, lambda w: True)
    bad = 0
    for n in names:
        if n not in units:
            print(f'  note   {n.lower()}: no primal source in the build directory'); continue
        p = reaches(n)
        if n in roots:
            print(f'  ok     {n.lower()}: calls the switch hooks, records before the switch in either mode')
        elif p is None:
            print(f'  ok     {n.lower()}')
        elif n in before:
            bad = 1
            print(f'  SWITCH {n.lower()}: records before the switch ({chain(n, before)}) and reaches '
                  f'{", ".join(r.lower() for r in p[1])} ({" > ".join(x.lower() for x in p[0])})')
        else:
            print(f'  ok     {n.lower()}: reaches {", ".join(r.lower() for r in p[1])}, but records after '
                  f'the switch (every call path from {", ".join(sorted(r.lower() for r in roots))} '
                  f'passes a checkpointed routine)')
    if filt:
        # Search down split routines that are free of switched variables only: a routine that
        # stays checkpointed moves everything below it after the switch.
        stop = records_before_switch(roots, calls, listed, lambda w: reaches(w) is None)
        joint = {w for w in stop if reaches(w) is not None}
        kept = [n.lower() for n in names if n in units and n not in joint]
        with open(filt, 'w') as fh:
            fh.write('\n'.join(kept) + '\n')
        print(f'kept {len(kept)} of {len(names)} entries in {filt}; to stay checkpointed: '
              f'{", ".join(sorted(j.lower() for j in joint)) or "none"}')
    print('OK: no listed routine records before the switch and reaches a switched variable.' if not bad
          else 'FAIL: the SWITCH routines above must stay checkpointed; remove them from the list.')
    return bad


if __name__ == '__main__':
    sys.exit(main(sys.argv))
