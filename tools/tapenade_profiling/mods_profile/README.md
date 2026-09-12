# `mods_profile/` — the two files a Tapenade `-profile` build needs

A `genmake2 -mods` directory, listed **before** a setup's `code_tap/` by
`build_tapAdj_profile.sh` so that both files shadow their counterparts:

| File | Shadows | Why it is here |
| --- | --- | --- |
| `adProfile.c`, `adProfile.h` | nothing (an addition) | The runtime behind the `ADPROFILEADJ_*` calls Tapenade emits under `-profile`. Copied **verbatim** from the installed Tapenade's `ADFirstAidKit/adProfile.c` (3.16 develop, 2025-12-05 build, header dated 2024). c69m vendors a 2021 `tools/TAP_support/ADFirstAidKit/adProfile.c` with a different API (`profileline_`/`printprofile_` event list) and does not compile it — `pkg/tapenade/` symlinks only `adStack.c`, `adBinomial.c`, `adFixedPoint.c`. The generated code calls the new API, so the new runtime is what must link. It needs only `adStack_getCurrentStackSize()` from `adStack.c`, which the vendored copy provides (the two `adStack.c` differ in one typedef spelling). |
| `the_model_main.F` | `model/src/the_model_main.F` (the setups' `code_tap/` carry no copy of their own) | Upstream byte-for-byte plus two additive blocks under `#ifdef ALLOW_TAPENADE`: declarations, and after `CALL THE_MAIN_LOOP_B` the calls `ADSTACK_SHOWPEAKSIZE`, `ADSTACK_SHOWTOTALTRAFFIC` (stdout) and `ADPROFILEADJ_SHOWPROFILESFILE` writing `tapenade_profile.NNNN.txt` per MPI process (`NNNN` = `myProcId`). Tapenade instruments the checkpoints but never emits the final report call itself, so the main program has to. |

Nothing here is setup-specific: the same directory serves SOMA (drop `-mpi`
and use `$SERIAL_OPTFILE`, as its build scripts do). It must contain only
these sources plus this README and `TREE_BASE.txt` — genmake2 treats every
`*.[hcF]`/`*.F90` file in a `-mods` directory as a source to compile.
`TREE_BASE.txt` records the tree blob `the_model_main.F` was derived from;
`tools/check_variant_shadows.sh` fails when that tree file changes.

Keep `adProfile.c` in step with the installed Tapenade: if `tapenade -version`
changes, re-diff against `$TAPENADE_HOME/ADFirstAidKit/adProfile.c`.

How to read the table it produces, and what was done with it for DINO, is in
`../README.md`.
