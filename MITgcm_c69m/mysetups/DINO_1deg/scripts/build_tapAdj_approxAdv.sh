#!/bin/bash
# Adjoint built for the APPROXIMATE-ADVECTION adjoint (scheme 33 forward, scheme 30
# in the adjoint sweep), MITgcm's stock useApproxAdvectionInAdMode made to work
# under Tapenade.
#   sources : code_tap/variants/approxAdvection/ + code_tap/ + input_tap/
#          -> build_tapAdj_approxAdv/mitgcmuv_tap_adj
#
# Same stock genmake2 and shared-hooks wiring as build_tapAdj_ckpAll.sh, and
# like it EVERY call is checkpointed, on purpose: useApproxAdvectionInAdMode is
# a run-time branch on inAdMode, which AUTODIFF_INADMODE_SET_TAP_B sets at the
# start of every backward step, so it can only act where Tapenade re-runs the
# primal inside the backward sweep (joint mode). The default build's
# -nocheckpoint list puts gad_advection, gad_calc_rhs and the DST3 flux
# routines in split mode, where the forward sweep tapes the limiter's control
# flow and the switch is inert (runs 31158/31159 vs 31140/31152, byte-identical).
#
# What differs from build_tapAdj_ckpAll.sh is a further -mods directory,
# code_tap/variants/approxAdvection/, listed ahead of code_tap/ so that its two
# files shadow the vendored pkg/generic_advdiff/: gad_advection.F with the CPP
# guard of the useApproxAdvectionInAdMode block changed from ALLOW_AUTODIFF_TAMC
# (TAF only; the block was preprocessed out of every Tapenade build) to
# ALLOW_AUTODIFF, and gad_implicit_r.F with the same replacement added for the
# implicit vertical advection, which the vendored file does not cover. The
# switch itself is set in data.autodiff (useApproxAdvectionInAdMode=.TRUE.);
# with it .FALSE. this build is the ckpAll adjoint with a taped branch.
#
# Why: the adjoint of the DST3 flux limiter (scheme 33) is what blows up the
# 5-yr adjoints here (stability_study, 2026-09-09: 31166 vs 31167). The stock
# switch keeps the limited scheme in the forward model and linearises about
# the unlimited scheme in the adjoint (Thuburn & Haine 2001); ECCO v4 avoids
# the question by running scheme 30 in its forward model outright, which is
# also the exact alternative the live input*/data take since 2026-09-09. This
# build is the Tapenade form of the switch, for keeping scheme 33 forward.
#
# Pair with submit_tapAdj_approxAdv.sh (run token tapAdj_ckpAll_approxAdv).
# This file says WHAT to build; HOW is tools/lib/build_body.sh. Run from the
# setup directory: ./scripts/build_tapAdj_approxAdv.sh

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_DIR=build_tapAdj_approxAdv
BUILD_MODE=tapAdj
PARALLEL=mpi
MODS=(../code_tap/variants/approxAdvection ../code_tap)     # the variant FIRST
TAP_EXTRA=""                                                # no -nocheckpoint, on purpose (see the header)
CKP=ckpAll;         CKP_NOTE="every call checkpointed; the switch is a run-time branch that only joint mode re-evaluates"
VARIANT=approxAdv;  VARIANT_NOTE="code_tap/variants/approxAdvection/ compiled ahead of code_tap/ (useApproxAdvectionInAdMode reachable); pair with submit_tapAdj_approxAdv.sh"
RUN_TOKEN=tapAdj_ckpAll_approxAdv

# The variant must be what was compiled, and Tapenade must have differentiated
# the branch: the switch's name occurs in neither vendored file's preprocessed
# form (gad_advection.f loses the block to the TAMC guard, gad_implicit_r.f never
# had it), so its presence in the compiled .f and in the generated _b.f is the
# evidence.
post_build_checks() {
    local f
    for f in gad_advection.f gad_implicit_r.f gad_advection_b.f gad_implicit_r_b.f; do
        if ! grep -qi 'useApproxAdvectionInAdMode' "$f"; then
            echo "ERROR: the compiled $f does not carry useApproxAdvectionInAdMode;"
            echo "       check the -mods order (code_tap/variants/approxAdvection must come first)."
            exit 1
        fi
    done
    echo "OK: gad_advection and gad_implicit_r (primal and adjoint) carry the useApproxAdvectionInAdMode branch."
}

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
