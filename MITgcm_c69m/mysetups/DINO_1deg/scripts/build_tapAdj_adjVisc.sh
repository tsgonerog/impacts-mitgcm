#!/bin/bash
# Adjoint built for ADJOINT-MODE VISCOSITY INFLATION.
#   sources : code_tap/ + input_tap/  ->  build_tapAdj_adjVisc/mitgcmuv_tap_adj
#
# Same stock genmake2 and shared-hooks wiring as build_tapAdj_ckpAll.sh
# (see there for where the ADJ* dump calls come from), and like it EVERY call
# is checkpointed: this build deliberately does NOT carry the -nocheckpoint
# list. Tested 2026-09-02 (run 31056, this build + that day's list, vs
# 31025, without it): fc and the %MON stream byte-identical, but every ADJ*
# dump and adxx_* gradient differed at order one -- while the plain pair is
# bitwise identical under the same list. In joint mode Tapenade re-runs each
# routine's primal inside the backward sweep, after AUTODIFF_INADMODE_SET_B has
# boosted the viscosities, so the boost reaches every recomputed intermediate;
# in split mode those intermediates were taped in the forward sweep at forward
# viscosities and the boost reaches only what the _BWD code reads live. Only
# the joint-mode boost is what the ASTE/TAF-style mechanism was designed as
# and what 31025 validated. Record: analyses/DINO_1deg/adjoint/
# tapenade_profiling/compare_30d_adjViscBoost_run31025_vs_nocheckpoint_run31056.md.
#
# What differs from build_tapAdj_ckpAll.sh is a further -mods directory,
# code_tap/variants/adjointViscosity/, listed ahead of code_tap/ so that its
# four files shadow both code_tap/ and the vendored tree (the shared hooks
# directory, which the build body puts first of all, has none of them): AUTODIFF_PARAMS.h / autodiff_readparms.F
# declare and read the inAd*/outAd* parameters, autodiff_inadmode_set_ad.F /
# autodiff_inadmode_unset_ad.F apply and restore them. Those let the model run
# with larger viscosity and diffusivity during the adjoint sweep than in the
# forward - the standard trick for keeping a long adjoint from blowing up.
# Nothing is copied into code_tap/; the check after make confirms the variant
# is what got compiled. genmake2 gives a file in an earlier -mods directory
# preference over a same-named file anywhere later.
#
# The build only provides the machinery; the values come from
# input_tap/variants/adjointViscosity/data.autodiff_adjointViscosity at run
# time (viscFacInAd = 10 vs viscFacInFw = 1, inAdviscArNr = 2.E-3 against a
# forward 1.2E-4, and added inAddiffKhT/S). So this build MUST be paired with
# submit_tapAdj_adjVisc.sh, which swaps that namelist in and refuses any
# other build's run token. Pairing it with submit_tapAdj.sh silently runs the
# plain configuration.
#
# Validation history: run 31025 (30 d from rest, live input_tap/data) is the
# first working adjVisc adjoint (fc bit-identical to plain 31026, every
# sensitivity damped); 31056 is the rejected split-mode variant.
#
# Numbers were adapted from the ASTE 90x150x60 regional setup.
#
# This file says WHAT to build; HOW is tools/lib/build_body.sh. Run from the
# setup directory: ./scripts/build_tapAdj_adjVisc.sh

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_DIR=build_tapAdj_adjVisc
BUILD_MODE=tapAdj
PARALLEL=mpi
MODS=(../code_tap/variants/adjointViscosity ../code_tap)    # the variant FIRST
TAP_EXTRA=""                                                # no -nocheckpoint, on purpose (see the header)
CKP=ckpAll;           CKP_NOTE="every call checkpointed; the -nocheckpoint list is NOT equivalent under the boost (run 31056 vs 31025)"
VARIANT=adjVisc; VARIANT_NOTE="code_tap/variants/adjointViscosity/ compiled ahead of code_tap/ (inAd*/outAd*); pair with submit_tapAdj_adjVisc.sh"
RUN_TOKEN=tapAdj_ckpAll_adjVisc

# The variant must be what was compiled: genmake2 links the first match it
# finds, so a wrong -mods order would silently build the plain adjoint under
# this build's name. The inAd*/outAd* names exist only in the variant sources.
post_build_checks() {
    local f
    for f in autodiff_readparms.f autodiff_inadmode_set_ad.f autodiff_inadmode_unset_ad.f; do
        if ! grep -qE 'inAdviscAhGrid|outAdviscAhGrid' "$f"; then
            echo "ERROR: the compiled $f is not the adjointViscosity variant;"
            echo "       check the -mods order (code_tap/variants/adjointViscosity must come first)."
            exit 1
        fi
    done
    echo "OK: the compiled autodiff sources are the adjointViscosity variant."
}

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
