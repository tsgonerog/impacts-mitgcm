# mods_tapenade_hooks: the Tapenade output hooks, in the shape of an upstream contribution

This directory holds the source changes that give a Tapenade-generated MITgcm
adjoint the `ADJ*` sensitivity dumps, the `ADJetan` dump, the tangent-linear
`G_J*` dumps and the adjoint-mode parameter switches that the TAF build gets
from `pkg/autodiff`, and, since 2026-09-12, the one CPP guard that lets MITgcm's
approximate-advection switch act once those switches exist. It is used as a
`-mods` directory by every adjoint build of
every setup under `mysetups/`, and it is, file for file, the proposal for
including the same mechanism in MITgcm itself. Each file is either new to the
tree or a copy of a tree file, under the tree file's own name, with lines
added (two of them also remove stubs that nothing can call, and one widens a
CPP guard), and
`check_against_tree.sh` verifies that shape and derives the patch series in
`patches/` from it.

Until 2026-09-07 the same mechanism lived in each setup's `code_tap/` as ten
shadow files (DINO) or seven (SOMA), in a design that widened the argument
lists of the existing hooks. That design worked here but could not be
submitted: Tapenade omits the derivative of an argument that is passive at the
call site, so a hand-written adjoint with a fixed argument list matches only
the configurations in which every field is active. The files here use one
external call per field instead; a passive field loses its call, an active one
is always passed with its derivative. The design was developed and tested in
a copy of checkpoint69m outside this repository (`~/MITgcm_c69m_tapenade_hooks/`,
branch `tapenade-hooks`, written up in `README.md` there and in the project
notes under `references/tapenade_hooks/`), and this directory is that branch
exported flat.

## How the directory is used

`genmake2` reads the files of a `-mods` directory by base name and does not
recurse, so the directory is flat and every file carries the name it has, or
would have, in the tree. Two things reach the build from here:

- **the Fortran sources and the differentiation list**, through `-mods`. The
  shared build body (`tools/lib/build_body.sh`) lists this directory first in
  the `-mods` list of every adjoint build, ahead of the setup's `code_tap/` and
  any variant directory, and afterwards asserts that the compiled hook sources
  link into it. `genmake2` picks up `tapenade_ad_diff.list` like any package's
  differentiation list, so the wrapper is differentiated without any change to
  the tree.
- **the Tapenade external declarations**, through `-tap_extra "-ext <this
  directory>/flow_tap"`. The file is a complete copy of the tree's
  `tools/TAP_support/flow_tap` with the seven hook stanzas inserted; Tapenade
  reads it beside the stock file that the stock options file passes, and the
  duplicated stanzas are identical, so the order is immaterial (tested
  2026-09-07 on a stock verification experiment). No setup-local `-adof` file
  is needed any more.

A stock verification experiment of the tree can use the directory the same
way, without touching `testreport`: `genmake2` reads a `genmake_local` in the
experiment's `build/` directory after the command line, so

```
MODS="../code_tap /path/to/mods_tapenade_hooks"
TAP_EXTRA="-ext /path/to/mods_tapenade_hooks/flow_tap"
```

in `verification/<experiment>/build/genmake_local` is enough. Upstream
un-ignores that file (`build/.gitignore` lists `!/genmake_local`), so remove it
afterwards rather than leaving it in the vendored tree. The stock experiments
set no `adjDumpFreq` in their `data` namelist, so the hooks run but write no
`ADJ*` files unless that parameter is added.

## The files and where each one goes in the tree

| File here | Destination in MITgcm | Kind of change | Lines |
| --- | --- | --- | --- |
| `forward_step.F` | `model/src/forward_step.F` | modify an existing file: additions only | +18 |
| `integr_continuity.F` | `model/src/integr_continuity.F` | modify an existing file: additions only | +5 |
| `stubs_tap_adj.F` | `pkg/tapenade/stubs_tap_adj.F` | modify an existing file: five stubs replaced by implementations | +172, −19 |
| `flow_tap` | `tools/TAP_support/flow_tap` | modify an existing file: additions only | +68 |
| `dummy_tap.F` | `pkg/tapenade/dummy_tap.F` | modify an existing file: the four unreachable stubs removed, the hook bodies added | +1034, −35 |
| `dummy_in_stepping_tap.F` | `pkg/tapenade/dummy_in_stepping_tap.F` | new file | 113 |
| `tapenade_ad_diff.list` | `pkg/tapenade/tapenade_ad_diff.list` | new file | 1 |
| `gad_advection.F` | `pkg/generic_advdiff/gad_advection.F` | modify an existing file: one CPP guard widened, `ALLOW_AUTODIFF_TAMC` → `ALLOW_AUTODIFF` | +2, −2 |

The same mapping, as data, is the `MAP` array in `check_against_tree.sh`.
`patches/` holds it as three unified diffs against the vendored tree, generated
by that script: `0001` carries `stubs_tap_adj.F` alone, `0002` the six hook
files, `0003` `gad_advection.F`.
Every file that modifies a tree file carries that file's name, so a reader
can diff it against the tree directly; the new files carry the names they
would have in `pkg/tapenade`.
They are meant to be applied in that order, and each is a pull request on its
own (see "Toward a pull request" below).

### `forward_step.F`: modify, additions only

Three blocks under `#ifdef ALLOW_TAPENADE`, each directly after the TAF hook
call it mirrors: a call to `AUTODIFF_INADMODE_UNSET_TAP` at the start of the
step, a `C$AD NOCHECKPOINT` directive and a call to `DUMMY_IN_STEPPING_TAP` in
the `ALLOW_AUTODIFF_MONITOR` block, and a call to `AUTODIFF_INADMODE_SET_TAP`
at the end of the step. The stock three-argument calls to `DUMMY_IN_STEPPING`,
`AUTODIFF_INADMODE_UNSET` and `AUTODIFF_INADMODE_SET` stay as they are, so TAF
and OpenAD builds see no change. The mode switches carry `etaN` as an argument
only so that Tapenade generates their reverse-sweep calls; its adjoint is not
touched.

### `integr_continuity.F`: modify, additions only

One block under `#ifdef ALLOW_TAPENADE` after the stock `DUMMY_FOR_ETAN` call:
a call to `DUMMY_FOR_ETAN_TAP` with `etaN` as its first argument. The free
surface has its own hook because its adjoint is half a time step out of phase
with the rest of the state.

### `stubs_tap_adj.F`: modify, stubs replaced

The tree ships the five `ADEXCH_*` adjoint halo exchanges as stubs that print
"Called not yet defined". Here they are implemented by composing, in reverse
order, the `*_AD` twins of the exchanges their forward counterparts call
(`EXCH2_*_CUBE_AD` with `pkg/exch2`, the `EXCH1_*_AD` family otherwise),
mirroring `eesupp/src/exch_3d_rl.F` and its siblings. This is one of the two
files in the directory that remove lines from their tree counterpart (the
other is `dummy_tap.F`, below).
The `pkg/autodiff` routines that call `ADEXCH_*` from TAF-named adjoint code
(`addummy_in_stepping.F`, `monitor_ad.F`, `ptracers_ad_dump.F`, ...) benefit
as well, which is why it is a pull request of its own. Without it the `ADJ*`
dumps of a multi-tile run carry partial sums on every tile seam (DINO runs
before job 31022).

### `flow_tap`: modify, additions only

Seven stanzas, inserted after the stanzas of the stock hooks, declaring the
externals of `dummy_tap.F` to Tapenade: the field argument(s) read then
written, the names, times and thread number read only. Because Tapenade keeps
the last declaration of an external, new names were chosen for the hooks
rather than re-declaring the stock ones. Upstream this is a block appended to
the file; here the whole file is carried so that it can be passed as a second
`-ext` and checked by a plain diff.

### `dummy_in_stepping_tap.F`: new file

The wrapper that Tapenade differentiates: called beside `DUMMY_IN_STEPPING`
from `FORWARD_STEP`, a no-op in the forward model, consisting of one call per
output field to the externals of `dummy_tap.F`. Its field set and guards
mirror `ADDUMMY_IN_STEPPING`: `theta`, `salt`, `wVel`, the `uVel`/`vVel` pair;
`fu`/`fv`, `Qnet`, `EmPmR` and, under `SHORTWAVE_HEATING`, `Qsw`, all only
without `pkg/seaice` and `pkg/exf`; `diffKr` under `ALLOW_DIFFKR_CONTROL`. The
package-specific dumps of the TAF routine (sea ice, passive tracers, shelf ice,
GGL90, ...) are not carried yet. The `C$AD NOCHECKPOINT` directive before its
call makes Tapenade differentiate it in split mode, so each field is stored
once per time step instead of twice.

### `dummy_tap.F`: modify, stubs removed and bodies added

The tree ships this file as four empty routines, `DUMMY_IN_STEPPING_B`/`_D`
and `DUMMY_FOR_ETAN_B`/`_D`, after one `#include "CPP_EEOPTIONS.h"`. The
include is kept; the four routines are removed. They are unreachable:
`flow_tap` declares `dummy_in_stepping` and `dummy_for_etan` as externals
whose arguments are all read only, and Tapenade generates no call to a
derivative of such an external, in either mode. Checked on 2026-09-07 before
removing them: no generated `_b.f` or `_d.f` of the seven adjoint builds of
the setups or of the eighteen adjoint and tangent-linear verification builds
of the study names them, and no object file has an undefined reference to
them (TAF builds never compile `pkg/tapenade`; forward builds never compile
this file). Tapenade run on a toy caller shows where they came from: for a
hook with no `flow_tap` stanza at all and an active `myTime` it emits
`DUMMY_FOR_ETAN_B(myTime, myTimeb, myIter, myThid)`, the stub's exact
argument list, so the stubs record development before the stanzas existed;
the three-argument `DUMMY_IN_STEPPING_B` matches no call Tapenade produces
under any declaration, so as a safety net it would have misaligned silently.
Kept, they suggest that the stock hooks have Tapenade derivatives, which
they do not. (From the move of 2026-09-07 until later that day the shared
copy kept them verbatim ahead of the bodies; the rebuild after their removal
left every Tapenade-generated file byte-identical and removed the four
symbols from every executable.)

In their place are the hand-written derivatives, 37 routines: two helpers,
and for each of the seven externals (four field-shape hooks, the `etaN`
hook, the two mode switches) the forward no-op and its `_B` (reverse sweep:
fold the halo with `ADEXCH_*`, then `DUMP_ADJ_*`, or call
`ADAUTODIFF_INADMODE_SET`/`UNSET`), `_D` (tangent-linear: `WRITE_FLD_*` of
the `G_J*` file) and `_FWD`/`_BWD` (the pair a caller differentiated in
split mode uses). The option headers and `AD_CONFIG.h` the bodies need
follow the tree's opening include. The adjoint arrays arrive as
arguments generated by Tapenade, so no hand-written code needs to know the
layout of any adjoint common block; there is no Tapenade counterpart of
`adcommon.h` to keep in step. The `etaN` hook keeps its own record counter
`dumpAdRecEt`, and the diagnostics route (`useDiag4AdjOutp`) works as with
TAF. Keeping the bodies in this file follows the tree's own placement of the
hook stubs; the maintainers may prefer the split the tree uses for the
exchange derivatives (`eesupp/src/exch_tap_b.F` / `exch_tap_d.F`), in which
case any new file must not be named `dummy_in_stepping_tap_b.F`, the name
Tapenade uses for the wrapper's generated adjoint.

### `tapenade_ad_diff.list`: new file

One line, `dummy_in_stepping_tap.f`, adding the wrapper to the set of files
Tapenade differentiates. `genmake2` reads every `*_ad_diff.list` of every
source directory, packages and `-mods` alike.

### `gad_advection.F`: modify, one CPP guard widened

Not a hook: the change that makes an existing `pkg/autodiff` parameter work
once the mode switches above exist. `useApproxAdvectionInAdMode` (MITgcm pull
request 404) replaces the flux-limited DST3 scheme (33) by the unlimited one
(30) while `inAdMode` is true, so that the adjoint is linearised about a scheme
whose adjoint is a well-behaved transport operator. `gad_advection.F`, which
selects the horizontal fluxes and, with multi-dimensional advection, the
explicit vertical ones, guards that block with `ALLOW_AUTODIFF_TAMC`, which
every Tapenade experiment undefines in its `AUTODIFF_OPTIONS.h`; the switch
therefore did nothing under Tapenade. `gad_calc_rhs.F` and
`seaice/seaice_advection.F` already guard the same switch with
`ALLOW_AUTODIFF`, and this file now does too. A TAF build defines both macros
and a forward build neither, so both preprocess the file to exactly the text
they did before.

What the change does under Tapenade is what pull request 611 made it do under
TAF: the routine is recomputed inside its adjoint with `inAdMode` true, so the
tape and the adjoint are those of scheme 30 about the scheme-33 trajectory.
Tapenade does that in joint mode, its default, after
`AUTODIFF_INADMODE_SET_TAP_B` has set `inAdMode`. A routine differentiated in
split mode (`-nocheckpoint`) replays the control flow taped in the forward
sweep instead, so an adjoint built with a routine list must keep
`gad_advection` and every routine above it in joint mode for the switch to
act consistently. Without patch `0002`, `inAdMode` is never set under Tapenade
and this patch changes nothing, which is why it comes last.

## What stays in the setups

Everything in a setup's `code_tap/` is now configuration of that setup, not
proposal material: the option headers, `SIZE.h`, `packages.conf`, the cost
function with its compiled-in section, the `-nocheckpoint` routine list, the
variant directories, and `the_main_loop.F` with the `C$AD BINOMIAL-CKP`
directive for the time loop. That directive is additive as well, but it is a
separate matter from the hooks: the tree has no such directive anywhere, its
verification experiments run with every step stored, and the snapshot count
is a decision about the memory of the machine. It could become a proposal of
its own later.

The four `pkg/autodiff` hook files (`dummy_in_stepping.F`, `dummy_for_etan.F`,
`autodiff_inadmode_set.F`, `autodiff_inadmode_unset.F`) and their TAF adjoints
(`addummy_in_stepping.F`, `addummy_for_etan.F`) compile untouched from the
vendored tree in every build; under Tapenade the TAF adjoints are dead code,
as in the tree's own Tapenade verification builds.

## Checking, and the patch series

```
./check_against_tree.sh            # verify the shape, rewrite patches/
./check_against_tree.sh --check    # verify, fail if patches/ is stale
./check_against_tree.sh --tree=DIR # against another tree, before a rebase
```

The check fails if a file here is not in the mapping, if a "new" file exists
in the tree, if an "additions only" file removes a line, if a shadow has become
identical to its tree file (the change landed upstream: delete it here), if the
tree's `flow_tap` already declares the hook externals, or if `patches/` does not
apply to the vendored tree (`git apply --check`). `tools/pre_push_check.sh`
runs the `--check` form.

## Validation

- **In the tree** (2026-09-05, the study): eight adjoint and six tangent-linear
  verification experiments identical between the pristine and the modified
  tree; DINO run 31107, built against the modified tree, bitwise identical to
  run 31101 (default build) in `fc`, all `adxx_*` and `ADJ*` files and the
  `%MON` stream; the diagnostics route reproduces the `ADJ*` dumps bitwise.
- **As a `-mods` directory on the pristine tree** (2026-09-07):
  `tutorial_tracer_adjsens` through `genmake_local`, twice (declarations as a
  68-line file, then as this full `flow_tap`): same testreport verdict, output
  and gradients identical to the study's runs, all hook calls generated.
- **In the setups** (2026-09-07, after the conversion, every adjoint build
  rebuilt from this directory; `tools/compare_adj_runs.sh`, all EQUIVALENT):
  DINO default build, 30 d from the 180-yr pickup, run 31108 against 31101
  (218 files, `fc`, 441 `%MON` lines); DINO adjoint-viscosity build, 30 d
  from rest, 31109 against 31090 (210 fields, `fc`, 441 `%MON`; the mode
  switches engage under the boost as before); SOMA 5 d, 31110 against 31076
  (186 fields, `fc`, 390 `%MON`). Details in `mysetups/DINO_1deg/TODO.md`,
  entry of 2026-09-07.
- **The checked-in directory on a stock experiment** (2026-09-07):
  `tutorial_tracer_adjsens` through `genmake_local` pointing here: same
  verdict, output and gradients identical to the study, all hook calls
  generated.
- **MITgcm's seven Tapenade verification experiments with `adjDumpFreq`
  set** (2026-09-07, `~/MITgcm_c69m_tapenade_hooks/results/adjdump_20260907/`):
  every testreport verdict as in the study, every dump finite, the day-0
  `ADJ*` dump equal to the `adxx_*` gradient in every cell wherever an
  initial-condition control exists (the one exception, the surface layer of
  `global_oce_biogeo_bling`, is the ECCO sea-surface-temperature cost being
  accumulated before the hook), dumps identical to the study's where the
  study archived them, and `G_J*` files from three tangent-linear builds.
- **A demonstration setup**, `mysetups/barotropic_gyre` (2026-09-07): daily
  `ADJtheta` snapshots over six months whose domain sum is 1.000000 at every
  day, as conservation requires, and whose day-0 snapshot equals `adxx_theta`.
- **Stub removal** (2026-09-07, evening): after the four stock stubs were
  removed from `dummy_tap.F`, all seven adjoint builds were rebuilt; every
  Tapenade-generated `_b.f` byte-identical to the previous build (188 in
  each DINO build, 212 in SOMA's, 165 in the gyre's), the four symbols gone
  from every executable, every build-body check passed. No run: the
  generated code is unchanged and the removed routines were never reached.
- **The approximate-advection guard, `gad_advection.F`** (2026-09-12, patch
  `0003`). Preprocessed with a TAF build's macros (`ALLOW_AUTODIFF`,
  `ALLOW_AUTODIFF_TAMC`) and with a forward build's (neither), the file gives
  exactly the text the tree's does; with Tapenade's or OpenAD's it gains the
  eleven-line block. Every adjoint build that compiles this directory was
  rebuilt and run once, `tools/compare_adj_runs.sh`, all EQUIVALENT: DINO's
  `approxAdv` build, which had taken the same change from its variant
  directory, 5 d from the production spin-up's year-180 pickup, run 31262
  against 31259 (186 sensitivity fields, `fc`, 390 `%MON` lines); DINO's
  `ckpAll` build, which now honours the switch, the same run, 31263 against
  31259, identical as expected with explicit vertical advection; SOMA 5 d,
  31265 against 31097; the barotropic gyre 180 d, 31266 against 31118 (3 604
  fields). DINO's adjoint-viscosity build compiles against the ASTE headers.
  The stock Tapenade verification experiments on the in-tree branch are in
  `~/MITgcm_c69m_tapenade_hooks/results/approx_guard_20260912/`.

## Toward a pull request

Three pull requests, in order: `0001` (implement the `ADEXCH_*` exchanges),
`0002` (the hooks) and `0003` (the approximate-advection guard, which acts only
once `0002` sets `inAdMode` under Tapenade). Both were prepared against checkpoint69m; the review of
checkpoint69q on 2026-09-05 found the Tapenade infrastructure unchanged, and
the OpenAD removal in MITgcm pull request 1029 will touch the same files, so
rebase after it has landed and regenerate the patches with
`--tree=<checkout of master>`. Open points for the maintainers: whether the
bodies stay in `dummy_tap.F` or are split as `exch_tap_b.F`/`exch_tap_d.F`
are; whether the four unreachable stubs of `dummy_tap.F` are removed, as
here, or kept; the `_TAP` suffix of the new routine names; and whether the
package-specific dumps of `ADDUMMY_IN_STEPPING` should follow in the same
change or a later one.
