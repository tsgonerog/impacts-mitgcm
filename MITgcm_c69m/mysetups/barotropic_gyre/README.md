# barotropic_gyre

The tutorial barotropic gyre of MITgcm (`verification/tutorial_barotropic_gyre`:
a 62 x 62 Cartesian domain of 20 km cells, one 5000 m layer, walls on all four
sides, a zonal wind stress of -0.1 cos(pi y/L) N m^-2, beta-plane) with
temperature stepped as a **passive tracer**, and a Tapenade adjoint of it. The
setup exists to show a temperature sensitivity on a small, fast configuration:
the sensitivity of the mean temperature over a box in the north-eastern
interior at the end of 6 months to the temperature field at every earlier day,
written by the `ADJ*` hooks and animated. Added 2026-09-07.

The gyre dynamics are the tutorial's, untouched: the thermal expansion
coefficient is zero (`tAlpha=0.`), so temperature does not feed back on the
flow, and the sensitivity is the adjoint of a linear advection-diffusion
operator (third-order upwind advection, `tempAdvScheme=3`, with
`diffKhT=100` m^2 s^-1). Because the operator is linear, the sensitivity does
not depend on the temperature field itself; the initial field, a meridional
gradient from 25 C at the southern wall to 15 C at the northern wall, only
gives the forward run something to advect.

## Layout

| Directory | Contents |
| --- | --- |
| `code/` | `SIZE.h`, the tutorial's single 62 x 62 x 1 tile; the forward model uses the default packages |
| `code_tap/` | `SIZE.h`; `packages.conf` (the default `gfd` group plus `tapenade` and the `adjoint` group); `CPP_OPTIONS.h` (upstream with `ALLOW_SRCG` undefined: the single-reduction pressure solver `CG2D_SR` has no hand-written Tapenade adjoint, so the adjoint would not link, as SOMA found); `COST_OPTIONS.h` (upstream with `ALLOW_COST_TEST` defined); `cost_test.F` (see below); `AUTODIFF_OPTIONS.h` (as in the other setups: TAMC checkpointing and the viscosity factors off); `the_main_loop.F` (upstream plus the `C$AD BINOMIAL-CKP` directive for the time loop, byte-identical to DINO's and SOMA's) |
| `input/` | `data` (spin-up: 2 years from rest; `pChkptFreq` of one model year, so the end of a whole-year run writes a permanent `pickup.<iteration>` rather than only the rolling `ckptA`), `data.pkg`, `eedata`, `gendata.py` |
| `input_tap/` | `data` (180 days from the spin-up's end, daily `ADJ*` and forward dumps), `data.pkg` (`useGrdchk=.FALSE.`), `data.cost` (`mult_test=1.`), `data.ctrl` (the control `xx_theta`, uniform weight), `data.grdchk`, `data.autodiff`, `data.optim`, `eedata` |
| `input_binaries/` | untracked; `bathy.bin`, `windx_cosy.bin`, `theta_init.bin`, written by `python3 input/gendata.py` |
| `input_adj_binaries/` | untracked; `ones_64b.bin`, the control weight, written by the same script |
| `scripts/` | `setup_params.sh`, `build_frd.sh`, `build_tapAdj.sh`, `submit_frd.sh`, `submit_tapAdj.sh`, thin definitions sourcing `tools/lib/` as in the other setups |

The Tapenade hooks are not in this setup: the build body lists
`MITgcm_c69m/mods_tapenade_hooks/` first in `-mods` for the adjoint build, as
for DINO and SOMA. Of the wrapper's eleven fields, nine reach the compiler
here and Tapenade generates the adjoint call for every one of them: `theta`,
`salt` and `wVel` (the 3-D scalar hook), the `uVel`/`vVel` pair, the `fu`/`fv`
pair, `Qnet` and `EmPmR` (the 2-D scalar hook), plus the free-surface hook and
the two mode switches; `build_tapAdj/dummy_in_stepping_tap_b.f` carries all
seven `_B` calls, and run 31118 wrote all ten fields (`ADJtheta`, `ADJsalt`,
`ADJwvel`, `ADJuvel`, `ADJvvel`, `ADJtaux`, `ADJtauy`, `ADJqnet`, `ADJempmr`,
`ADJetan`) every day. The two fields that are missing, `Qsw` and `diffKr`, are
missing at preprocessing, not by Tapenade's choice: `SHORTWAVE_HEATING` is
undefined in `code_tap/CPP_OPTIONS.h` and `ALLOW_DIFFKR_CONTROL` in the tree's
`pkg/ctrl/CTRL_OPTIONS.h`, so their calls are never compiled. Salt being
unstepped (`saltStepping=.FALSE.`) and the forcing being uncontrolled are
run-time facts that Tapenade's static activity analysis does not see, so
those hooks keep their calls and their dumps are written (all zero for salt).
`scripts/setup_params.sh` lists the seven generated calls the build asserts.
(Until 2026-09-08 this paragraph claimed that the salt and forcing calls were
dropped; the generated file says otherwise.)

## The cost function

`code_tap/cost_test.F` is the setup's version of `pkg/cost/cost_test.F`, under
the same name and with the same `objf_test` / `mult_test` plumbing: the mean of
the surface temperature over the box of global cells `i = 40..49`,
`j = 44..53` (200 km x 200 km, north-eastern interior; the ocean occupies cells
2..61), evaluated at the final time step. Upstream's version measures the
temperature at the single grid point (80, 30), which lies outside this
domain. The box is compiled in, like the section of DINO's
`cost_atlantic_heat.F`; moving it means editing the file and rebuilding.

With the uniform control weight, `adxx_theta` is the sensitivity of that box
mean to the initial temperature field, in degrees per degree, and `ADJtheta`
at each dumped iteration is the same sensitivity to the temperature at that
day. A uniform change of temperature everywhere changes the box mean by the
same amount and the tracer is conserved, so the sum of `ADJtheta` over the
ocean cells is 1 at every lead time; the analysis checks it.

## Build and run

```bash
cd MITgcm_c69m/mysetups/barotropic_gyre
python3 input/gendata.py                        # once: the input binaries
./scripts/build_frd.sh                          # -> build_frd/mitgcmuv
../../../tools/submit.sh scripts/submit_frd.sh  # 2-year spin-up from rest (default 720 d)
./scripts/build_tapAdj.sh                       # -> build_tapAdj/mitgcmuv_tap_adj
../../../tools/submit.sh scripts/submit_tapAdj.sh   # 180 d from the spin-up's end
```

Both models are serial (`-n 1`). The time step is 1200 s, 72 per day; the
spin-up's `nTimeSteps=51840` and the adjoint's `nIter0=51840` are the same 720
days at 360 days per year. `submit_tapAdj.sh` links the pickup of a named
spin-up run (`SPINUP_RUN`), under the per-tile names this setup writes
(`pickup.0000051840.001.001.*`); a new spin-up means pointing that variable at
its run directory. Durations and frequencies are patched into the staged
namelist from the `*_days` values at the top of each submit definition, or
from the `IMPACTS_*` environment overrides.

Output lands under `$SCRATCH_ROOT/barotropic_gyre_outputs/runs/{forward,adjoint}/`,
named `barotropic_gyre_<run_token>_<duration>_run<jobid>`. The spin-up takes
about three minutes; the 6-month adjoint (every call checkpointed, the time
loop binomially checkpointed) a few tens of minutes.

## Runs (2026-09-07)

| Run | What | Result |
| --- | --- | --- |
| `barotropic_gyre_frd_2yr_run31115` (forward) | the 2-year spin-up from rest, 2 min; permanent pickups at 1 and 2 years | the spin-up whose `pickup.0000051840` starts the adjoint |
| `barotropic_gyre_tapAdj_ckpAll_180d_run31118` (adjoint) | 180 d from the spin-up's end, daily `ADJ*` and forward snapshots, 4.5 min | the box on the western boundary current (the committed `cost_test.F`); `fc` = box-mean temperature at day 180; sum of `ADJtheta` over the ocean = 1.000000 at all 180 days; day-0 `ADJtheta` equals `adxx_theta` |
| `barotropic_gyre_tapAdj_ckpAll_180d_run31117` (adjoint) | the same run with the first version of the box, `i = 40..49, j = 44..53` in the north-eastern interior | kept as a record; diffusion-dominated because the interior flow is a few millimetres per second, which is why the box was moved |

An earlier spin-up, run 31114, wrote only the rolling `ckptA` pickup (no
`pChkptFreq` yet) and was superseded by 31115.

## Analysis

`analyses/barotropic_gyre/temperature_sensitivity_6months.ipynb` reads one
adjoint run and writes into it `figures/` (the gyre and the box at day 180,
`adxx_theta`, the sensitivity at selected lead times, the amplitude against
time) and `animations/` (`sensitivity_ADJtheta_6months.gif`, the sensitivity
from the cost time back to day 0, one frame per day, and the forward
temperature over the same period). The runs it reads are recorded in
`analyses/README.md`.
