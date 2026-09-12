# `viscosity_study/` — how lateral viscosity is specified

Viscosity is the axis most DINO experiments vary, and there are two different
ways to set it. These variants explore both, all from rest.

| Tag | Setting |
| --- | --- |
| `from_rest_viscD2x_Zref` | `viscAhDfile` at 2× but `viscAhZfile` left at the reference field — a **mixed** setting. This is the configuration whose 200-year spin-up crashed at 126.3 years |
| `from_rest_viscGrid1p8e-2_A4Grid1p0e-2` | the scalar `viscAhGrid=1.8E-2` in `PARM01` with biharmonic `viscA4Grid=1.0E-2`, `PARM05` files commented out |
| `..._C4Leith1p5` | as above plus Leith |

A fourth tag, `..._CDscheme` (as above plus the C-D scheme for the Coriolis
terms, `useCDscheme=.TRUE.`, `tauCD=321428.`; forward only), was deleted on
2026-09-12, when `cd_code` stopped being compiled into `code/`; git history has
it. Its 200-year spin-up from May 2026, run 28489, was never analysed and was
deleted on 2026-09-03.

Read `p` as the decimal point: `1p8e-2` is `1.8E-2`. `analyses/README.md`
carries the token vocabulary.

**The analysis side is thinner than it was.** The three notebooks that compared
`viscAhGrid` against the `PARM05` files were retired on 2026-09-03 with the
1-year runs they read (28402, 28447, 28448, 28451); their result — that
`viscAhGrid = 1.135E-2` matches the reference field's *domain mean* to 0.01 %
but overshoots it by 30 % at mid-domain, which is why production uses the files
— now lives in
`analyses/DINO_1deg/forward/viscosity_binaries_construction.ipynb`, together
with the recipe for `dino_viscAhD*.bin` itself. The retired notebooks are in
`~/trash/Proj_ImPACTS/analyses/DINO_1deg/02_forward/01_viscosity_study/`.
