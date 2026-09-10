# `grdchk_repair/` — a gradient check that can actually pass

One tag, `from180yrPk_visc2x_grdchkON`: the `baseline/from180yrPk_visc2x`
namelist plus two sibling overrides — `data.pkg` with `useGrdchk = .TRUE.`
(the committed DINO default is `.FALSE.` since 2026-08-28) and a `data.grdchk`
with the perturbation moved from (4,8,1) to the 30-day sensitivity peak
(i=2, j=127, k=26 on the cost section) and `grdchk_eps` raised to `1e-3`,
per the repair prescribed in the root `README.md` ("Verifying correctness").

Since 2026-09-09 there is a second tag, `from180yrPk_viscRef_ReMax2_adv30_grdchkON`,
the same check under the new production configuration (reference viscosity,
`viscAhReMax=2.`, scheme 30). **Run 31172 (2026-09-09) passes at all five
points**: 1 − fd/adj = −9.8e-7, −1.6e-5, −3.5e-5, +4.9e-6, +5.1e-6 (0.0001 %
to 0.0035 %), against 0.88 % and then 318 %, 78 %, 87 %, 45 % for the same
points under scheme 33 (31037). The four weaker points were never at a noise
floor of the model; they were at the flux limiter's.

Run it as

    IMPACTS_TEST_CASE=grdchk_repair/from180yrPk_visc2x_grdchkON \
    IMPACTS_DURATION_DAYS=30 ../../../tools/submit.sh scripts/submit_tapAdj.sh

Each of the 4 checked points costs two extra 30-day forward integrations.
First meaningful result (2026-08-31, run pair on the hook build and a
control build of `main`): see the hook change note in the project notes, and the run
directories' `output_tap_adj.txt` (`grad-res` tables).
