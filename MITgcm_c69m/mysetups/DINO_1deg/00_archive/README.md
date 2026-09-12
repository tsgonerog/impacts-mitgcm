# `DINO_1deg/00_archive/`

Superseded configuration kept for reference. **Nothing here is live** — no build
or submit script reads this directory, and `genmake2` never sees it. A grep hit
in here is history, not current behaviour.

**Layout rule: the archive mirrors the live directory a file came from (or would
go back to).** `00_archive/code_tap/X` means "X, which was or would be
`code_tap/X`". `MITgcm_c69m/00_archive/` follows the same rule against the
vendored `MITgcm/` tree.

The `00_` prefix keeps this directory sorted above `build*/` and `code*/` in a
plain `ls`.

---

## `code_tap/`

| File | What it is | Why it is not live |
| --- | --- | --- |
| `autodiff_inadmode_set_ad.F_aste_90x150x60` | The **ASTE original**, before porting to checkpoint69m | Superseded by the ported copy — see lineage below |
| `the_model_main.F_ForTapProfile` | `the_model_main.F` instrumented for the Tapenade profiling tool | Profiling cannot be run here — see below |
| `adcommon.h` | Hand-mirror of Tapenade's generated adjoint common blocks (`/DYNVARS_R_b/`, `Thetab`, …) | Obsoleted by the 2026-08-31 dump-hook redesign — see below |
| `addummy_for_etan.F` | `DUMMY_FOR_ETAN_b` reading `EtaNb` from `adcommon.h`; would dump `ADJetan` | Was never called: raw Tapenade emits no `DUMMY_FOR_ETAN_B` call, so no run ever produced `ADJetan`. Cannot compile without the archived `adcommon.h`. Superseded by the live `code_tap/addummy_for_etan.F` (`TAP_DUMMY_FOR_ETAN` hook) — see below |
| `monitor_ad.F` | `MONITOR_b`, an adjoint-state monitor over the `adcommon.h` commons | Same: nothing generated ever called it, and it needs the archived `adcommon.h` |

**Lineage worth knowing.** `autodiff_inadmode_set_ad.F_aste_90x150x60` is the
direct ancestor of the live `code_tap/variants/adjointViscosity/autodiff_inadmode_set_ad.F`,
which `build_tapAdj_adjVisc.sh` compiles from its first `-mods` directory
(until 2026-09-02 that file was the staged sibling
`code_tap/autodiff_inadmode_set_ad.F_adapted_frm_aste_90x150x60`). Diffing the
two shows the c69f→c69m API port; the `TAP_INADMODE_SET_B/_D` wrapper that the
2026-08-31 mode-switch hooks added lives in `code_tap/tap_inadmode.F`, not in
this file. The port itself was:

- `DIAGNOSTICS.h` + `DIAGNOSTICS_SIZE.h` → `DIAGNOSTICS_P2SHARE.h`
- `CTRL_SIZE.h` added
- `DIAGNOSTICS_SWITCH_ONOFF` gained a leading argument

So this is the record of *what upstream changed*, not a spare copy.

**On the profiling file.** Reviving Tapenade profiling needs two pieces and only
this one survives. `the_model_main.F_ForTapProfile` would have to be copied into
`code_tap/` by hand — being in the archive, no script stages it. The matching
`patched_ForTapProfile_genmake2` and `patched_AfterTapProfile_genmake2` are *not*
in this repository at all; they exist only in `Proj_ImPACTS_old` at
`MITgcm_c69f/MITgcm/tools/`. This is why `use_TapProfile` in the build scripts
works only in its `NO` mode.

**On the 2026-08-31 dump-hook redesign files.** `adcommon.h`,
`addummy_for_etan.F` and `monitor_ad.F` date from the era when the `ADJ*` dump
call had to be hand-inserted into the generated `forward_step_b.f` and the
adjoint state reached the dump routine through hand-mirrored common blocks.
Since the redesign, the hook (`TAP_DUMMY_IN_STEPPING` in
`code_tap/forward_step.F`, declared active in `code_tap/flow_tap_local`)
receives the adjoint fields as explicit arguments, so `adcommon.h` — whose
member ordering had to silently track Tapenade's generated commons — has no
live consumer. The two `.F` files were *already dead before the redesign*
(nothing in the generated adjoint ever called their `_b` routines; `ADJetan`
was never produced by any Tapenade run). The `ADJetan` follow-up anticipated
here **landed later the same day**: the live `code_tap/addummy_for_etan.F`
(upstream file + appended `TAP_DUMMY_FOR_ETAN_B`), `tap_dummy_for_etan.F` and
the `integr_continuity.F` shadow wire the hook exactly as sketched — it is a
fresh implementation on the hook pattern, not a revival of this archived file,
which still documents the dead-end `adcommon.h` approach it replaced.

## `input_tap/`

| File | What it is | Why it is not live |
| --- | --- | --- |
| `data_aste_90x150x60` | ASTE main namelist | Reference only — DINO's grid and physics differ throughout |
| `data.autodiff_aste_90x150x60` | ASTE adjoint-mode viscosity namelist | Superseded by the DINO-tuned copy — see lineage below |

**Lineage worth knowing.** `data.autodiff_aste_90x150x60` is the direct ancestor
of `input_tap/variants/adjointViscosity/data.autodiff_adjointViscosity`, which
`submit_tapAdj_adjVisc.sh` swapped in until 2026-09-12 (git history has it);
since then the variant is `data.autodiff_additions`, the boost's lines only,
added to the staged `data.autodiff`. The diff against the full file is the
whole derivation:

- the entire `SEAICE*` block commented out (DINO has no sea ice)
- `useGMRediInAdMode` `.TRUE.` → `.FALSE.`
- viscosities retuned for DINO: `inAdviscAhGrid` 2.E-2 → 2.5E-2,
  `outAdviscArNr` 5.E-4 → 1.2E-4, `outAdviscAhGrid` 0.5E-2 → 1.8E-2

Together with the `code_tap/` file above, these two are the record of **how the
`adjVisc` configuration was derived from ASTE**. They are the most useful
thing in this archive.

## `scripts/`

Six superseded build and submit scripts (a seventh, the KPP debug run, was
deleted on 2026-09-12 with KPP; git history has it). The `tapAdj_` / `frd_` filename
prefixes carry the adjoint/forward distinction, so they are not split into
subdirectories.

| File | Why it is not live |
| --- | --- |
| `tapAdj_build_serial_patched.sh`, `tapAdj_build_serial_noTpatched.sh` | **DINO is MPI-only now.** The `code_tap/SIZE.h_serial` they staged was deleted on 2026-09-02 (git history has it); `code_tap/SIZE.h` is the 27-rank decomposition. |
| `tapAdj_submit_serial_patched_on_sverdrup.sh` | Serial counterpart of the above |
| `frd_submit_mpi_on_sv_debug_{tr5,adv30_from_start,viscAhD_2p50}.sh` | One-off forward debug runs (job names `debug_tr5`, `debug_tr6`, `debug_tr12`). Their settings now live as namelists in `input/variants/`, selected by `test_cases`. |

These predate `tools/machine_env.sh`, so they carry hardcoded sverdrup paths and
were not ported — see `PORTING.md`. Their pickup paths also point at run
directories that no longer exist on scratch.

`tapAdj_build_serial_patched.sh` still names `patched_NoTapProfile_genmake2`,
which was renamed to `genmake2_override_forward_step_b` on 2026-08-20. That is
deliberate: the archived script is a record of what it called when it was live,
and rewriting it would falsify that. If you grep for the old name, these two
lines are the only hits, and they are history.

---

## Removed on 2026-08-20

`stray_gendata_from_template/` — four MATLAB/Python `gendata` scripts
(`gendata.m`, `gendata.py`, `gendata_input_tap.m`, `gendata_input_tap.py`) that
sat in `input/` and `input_tap/` but never belonged to DINO. They generate a
**62 × 62 grid, 1800 m deep**, writing `bathy.bin`, `SST_relax.bin` and
`windx_cosy.bin`; DINO is **51 × 198 × 36, 4600 m deep** and its inputs are the
`dino_*.bin` files in `input_binaries/`, produced outside this repository.
Residue from whichever template the setup was copied from. Nothing referenced
them. Recoverable from git history.

One fact from their README is worth keeping: **`SOMA_1deg/input/gendata.py` is a
different file and is genuine** — SOMA's inputs really do regenerate from it.
