#!/bin/bash
# Adjoint built for the APPROXIMATE-ADVECTION adjoint (scheme 33 forward, scheme 30
# in the adjoint sweep), MITgcm's stock useApproxAdvectionInAdMode made to work
# under Tapenade.
#   sources : code_tap/variants/approxAdvection/ + code_tap/ + input_tap/
#          -> build_tapAdj_approxAdv/mitgcmuv_tap_adj
#
# Same stock genmake2 and shared-hooks wiring as build_tapAdj_ckpAll.sh, and
# like it EVERY call is checkpointed. useApproxAdvectionInAdMode is a run-time
# branch on inAdMode, which AUTODIFF_INADMODE_SET_TAP_B sets at the start of
# every backward step, so it acts on what Tapenade records after that: every
# checkpointed routine's re-run, and a split routine only below a checkpointed
# caller. The -nocheckpoint list of 2026-09-02 also split thermodynamics, above
# gad_advection, so the switch could not act there; the list of 2026-09-12
# keeps thermodynamics checkpointed (tools/tapenade_profiling/README.md,
# section 4). Before 2026-09-12 no plain Tapenade build compiled the switch at
# all (the guard below; runs 31158/31159 vs 31140/31152, byte-identical).
#
# What differs from build_tapAdj_ckpAll.sh is a further -mods directory,
# code_tap/variants/approxAdvection/, listed ahead of code_tap/ so that its
# gad_implicit_r.F shadows the vendored pkg/generic_advdiff/ one: the same
# replacement added for the implicit vertical advection, which the vendored file
# does not cover under any AD tool. The horizontal and explicit vertical part --
# the CPP guard of gad_advection.F's block widened from ALLOW_AUTODIFF_TAMC (TAF
# only; the block was preprocessed out of every Tapenade build) to ALLOW_AUTODIFF
# -- was in this directory too from 2026-09-09 and is in the shared
# MITgcm_c69m/mods_tapenade_hooks/ since 2026-09-12, so every adjoint build
# compiles it. With explicit vertical advection (the live input_tap/data since
# 2026-09-10) this build and build_tapAdj_ckpAll.sh therefore give the same
# adjoint. The switch itself is set in data.autodiff
# (useApproxAdvectionInAdMode=.TRUE.); with it .FALSE. this build is the ckpAll
# adjoint with taped branches.
#
# Why: the adjoint of the DST3 flux limiter (scheme 33) is what blows up the
# 5-yr adjoints here (stability_study, 2026-09-09: 31166 vs 31167). The stock
# switch keeps the limited scheme in the forward model and linearises about
# the unlimited scheme in the adjoint (Thuburn & Haine 2001); ECCO v4 avoids
# the question by running scheme 30 in its forward model outright, which is
# also the exact alternative the live input*/data take since 2026-09-09. This
# build is the Tapenade form of the switch, for keeping scheme 33 forward.
#
# THE DEFAULT adjoint build since 2026-09-10: ./scripts/build_tapAdj.sh is a
# symlink to this file (and ./scripts/submit_tapAdj.sh to
# submit_tapAdj_approxAdv.sh), because the live input_tap/data keeps scheme 33
# and the live input_tap/data.autodiff sets the switch. The ckpAll build honours
# the switch as well since 2026-09-12 (above), and so does the nocheckpoint
# build with its list of that day (31276 vs 31269, bitwise); neither has the
# swap for implicit vertical advection.
# Pair with submit_tapAdj_approxAdv.sh (run token tapAdj_ckpAll_approxAdv).
# This file says WHAT to build; HOW is tools/lib/build_body.sh. Run from the
# setup directory: ./scripts/build_tapAdj_approxAdv.sh

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_DIR=build_tapAdj_approxAdv
BUILD_MODE=tapAdj
PARALLEL=mpi
MODS=(../code_tap/variants/approxAdvection ../code_tap)     # the variant FIRST
TAP_EXTRA=""                                                # every call checkpointed; build_tapAdj_nocheckpoint.sh is the list build
CKP=ckpAll;         CKP_NOTE="every call checkpointed"
VARIANT=approxAdv;  VARIANT_NOTE="code_tap/variants/approxAdvection/ compiled ahead of code_tap/ (useApproxAdvectionInAdMode also reaches the implicit vertical advection); pair with submit_tapAdj_approxAdv.sh"
RUN_TOKEN=tapAdj_ckpAll_approxAdv

# The variant must be what was compiled, and Tapenade must have differentiated
# the branch: the switch's name occurs in neither vendored file's preprocessed
# form (gad_advection.f loses the block to the TAMC guard, gad_implicit_r.f never
# had it), so its presence in the compiled .f and in the generated _b.f is the
# evidence: for gad_advection that the shared hooks directory was compiled (since
# 2026-09-12), for gad_implicit_r that this variant was.
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
