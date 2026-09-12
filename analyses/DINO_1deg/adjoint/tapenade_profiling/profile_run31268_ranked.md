# Tapenade checkpointing profile: `/scratch2/tshahriar/DINO_1deg_outputs/runs/adjoint/checkpointing_study/DINO_1deg_tapAdj_ckpAll_profile_31d_from180yrPk_viscRef_ReMax2_gmFwd_approxAdv_run31268/tapenade_profile.0000.txt`
- peak tape (this rank): **0.837 GB**
- 161 checkpoint locations, 118 distinct callees
- summed time gain if none were checkpointed: 411 s CPU on this rank

| rank | callee | time gain [s] | cum. gain [s] | peak-mem cost [MB] | gain/cost [s/MB] | call sites | occurrences |
|---|---|---|---|---|---|---|---|
| 1 | `timestep` | 101 | 101 | -31.1 | free | 1 | 53568 |
| 2 | `forward_step` | 75 | 176 | 0.0 | free | 1 | 1488 |
| 3 | `grad_sigma` | 35 | 211 | 0.0 | free | 1 | 52080 |
| 4 | `calc_phi_hyd` | 30 | 241 | -8.6 | free | 1 | 53568 |
| 5 | `mom_vecinv` | 30 | 271 | -0.2 | free | 1 | 53568 |
| 6 | `thermodynamics` | 20 | 291 | 0.0 | free | 1 | 1488 |
| 7 | `do_oceanic_phys` | 19 | 310 | 21.4 | 0.8895117760123206 | 1 | 1488 |
| 8 | `integrate_for_w` | 17 | 327 | -0.5 | free | 1 | 53604 |
| 9 | `dynamics` | 12 | 339 | 9.3 | 1.2871216613136707 | 1 | 1488 |
| 10 | `temp_integrate` | 9 | 348 | 1.9 | 4.628534400296226 | 1 | 1488 |
| 11 | `salt_integrate` | 8 | 356 | 0.0 | free | 1 | 1488 |
| 12 | `calc_adv_flow` | 7 | 363 | -0.9 | free | 2 | 107136 |
| 13 | `impldiff` | 5 | 368 | 0.2 | 22.431986217787667 | 2 | 2976 |
| 14 | `gad_calc_rhs` | 4 | 372 | -0.0 | free | 2 | 107136 |
| 15 | `update_surf_dr` | 4 | 376 | -1.3 | free | 2 | 2976 |
| 16 | `gad_advection` | 4 | 380 | 5.8 | 0.6864383801427105 | 2 | 2976 |
| 17 | `do_stagger_fields_exchanges` | 3 | 383 | -1.1 | free | 1 | 1488 |
| 18 | `exch2_rl1_cube` | 3 | 386 | 0.0 | free | 2 | 23836 |
| 19 | `solve_tridiagonal` | 3 | 389 | 0.0 | free | 1 | 2976 |
| 20 | `exch_xy_rl` | 2 | 391 | -0.0 | free | 5 | 5962 |
| 21 | `momentum_correction_step` | 2 | 393 | -0.0 | free | 1 | 1488 |
| 22 | `adams_bashforth2` | 2 | 395 | 0.0 | free | 2 | 107136 |
| 23 | `cg2d` | 2 | 397 | 0.0 | free | 1 | 1488 |
| 24 | `find_rho_2d` | 2 | 399 | 0.0 | free | 2 | 105648 |
| 25 | `mom_calc_visc` | 2 | 401 | 0.0 | free | 1 | 53568 |
| 26 | `solve_for_pressure` | 2 | 403 | 0.0 | 250000.0 | 1 | 1488 |
| 27 | `ctrl_map_forcing` | 1 | 404 | -0.0 | free | 1 | 1488 |
| 28 | `dummy_in_stepping_uv_xyz_rl` | 1 | 405 | -38.6 | free | 1 | 1488 |
| 29 | `load_fields_driver` | 1 | 406 | -0.1 | free | 1 | 1488 |
| 30 | `tracers_correction_step` | 1 | 407 | -0.4 | free | 1 | 1488 |
| 31 | `integr_continuity` | 1 | 408 | 7.1 | 0.14096236699495862 | 2 | 1489 |
| 32 | `calc_viscosity` | 1 | 409 | 0.0 | 6410.25641025641 | 1 | 1488 |
| 33 | `gad_dst3_adv_x` | 1 | 410 | 0.4 | 2.731315073581628 | 1 | 107136 |
| 34 | `gad_dst3_adv_r` | 1 | 411 | 0.6 | 1.5635065073140832 | 1 | 104160 |
| 35 | `autodiff_inadmode_unset_tap` | 0 | 411 | -38.6 | free | 1 | 1488 |
| 36 | `calc_3d_diffusivity` | 0 | 411 | -0.2 | free | 2 | 2976 |
| 37 | `cost_driver` | 0 | 411 | -0.0 | free | 1 | 1 |
| 38 | `dummy_for_etan_tap` | 0 | 411 | -0.0 | free | 1 | 1489 |
| 39 | `dummy_in_stepping_uv_xy_rs` | 0 | 411 | -38.6 | free | 1 | 1488 |
| 40 | `dummy_in_stepping_xy_rs` | 0 | 411 | -115.7 | free | 3 | 4464 |
| 41 | `dummy_in_stepping_xyz_rl` | 0 | 411 | -154.3 | free | 4 | 5952 |
| 42 | `initialise_varia` | 0 | 411 | -2.3 | free | 1 | 1 |
| 43 | `active_read_xy` | 0 | 411 | 0.0 | free | 4 | 36 |
| 44 | `active_read_xyz` | 0 | 411 | 0.0 | free | 1 | 3 |
| 45 | `active_write_xy` | 0 | 411 | 0.0 | free | 2 | 18 |
| 46 | `apply_forcing_t` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 47 | `apply_forcing_u` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 48 | `apply_forcing_v` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 49 | `autodiff_inadmode_set_tap` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 50 | `calc_div_ghat` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 51 | `calc_grad_phi_hyd` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 52 | `calc_grad_phi_surf` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 53 | `correction_step` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 54 | `cost_accumulate_mean` | 0 | 411 | 0.0 | free | 1 | 1440 |
| 55 | `cost_atlantic_heat` | 0 | 411 | 0.0 | free | 1 | 1 |
| 56 | `cost_final` | 0 | 411 | 0.0 | free | 1 | 1 |
| 57 | `cost_init_varia` | 0 | 411 | 0.0 | free | 1 | 1 |
| 58 | `cost_tile` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 59 | `ctrl_cost_driver` | 0 | 411 | 0.0 | free | 1 | 1 |
| 60 | `ctrl_cost_final` | 0 | 411 | 0.0 | free | 1 | 1 |
| 61 | `ctrl_get_gen` | 0 | 411 | 0.0 | free | 1 | 13392 |
| 62 | `ctrl_init_variables` | 0 | 411 | 0.0 | free | 1 | 1 |
| 63 | `ctrl_map_genarr3d` | 0 | 411 | 0.0 | free | 3 | 3 |
| 64 | `ctrl_map_gentim2d` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 65 | `ctrl_map_ini_genarr` | 0 | 411 | 0.0 | free | 1 | 1 |
| 66 | `ctrl_map_ini_gentim2d` | 0 | 411 | 0.0 | free | 1 | 1 |
| 67 | `ctrl_swapffields` | 0 | 411 | 0.0 | free | 1 | 9 |
| 68 | `cycle_tracer` | 0 | 411 | 0.0 | free | 2 | 2976 |
| 69 | `diags_phi_hyd` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 70 | `do_atmospheric_phys` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 71 | `do_fields_blocking_exchanges` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 72 | `exch2_3d_rl` | 0 | 411 | 0.0 | free | 3 | 11918 |
| 73 | `exch2_3d_rs` | 0 | 411 | 0.0 | free | 1 | 10416 |
| 74 | `exch2_rl2_cube` | 0 | 411 | 0.0 | free | 2 | 2976 |
| 75 | `exch2_rs1_cube` | 0 | 411 | 0.0 | free | 2 | 20832 |
| 76 | `exch2_rs2_cube` | 0 | 411 | 0.0 | free | 2 | 2976 |
| 77 | `exch2_uv_3d_rl` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 78 | `exch2_uv_3d_rs` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 79 | `exch_3d_rl` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 80 | `exch_uv_3d_rl` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 81 | `exch_uv_xy_rs` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 82 | `exch_xy_rs` | 0 | 411 | 0.0 | free | 7 | 10416 |
| 83 | `exch_xyz_rl` | 0 | 411 | 0.0 | free | 5 | 4468 |
| 84 | `external_fields_load` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 85 | `external_forcing_surf` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 86 | `find_bulkmod` | 0 | 411 | 0.0 | free | 1 | 105648 |
| 87 | `find_rhop0` | 0 | 411 | 0.0 | free | 1 | 105648 |
| 88 | `forcing_surf_relax` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 89 | `gad_diff_x` | 0 | 411 | 0.0 | free | 1 | 107136 |
| 90 | `gad_diff_y` | 0 | 411 | 0.0 | free | 1 | 107136 |
| 91 | `gad_implicit_r` | 0 | 411 | 0.0 | free | 2 | 2976 |
| 92 | `global_sum_tile_rl` | 0 | 411 | 0.0 | free | 1 | 1 |
| 93 | `gmredi_calc_tensor_dummy` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 94 | `mom_calc_hdiv` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 95 | `mom_calc_hfacz` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 96 | `mom_calc_ke` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 97 | `mom_calc_relvort3` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 98 | `mom_calc_strain` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 99 | `mom_calc_tension` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 100 | `mom_u_botdrag_coeff` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 101 | `mom_v_botdrag_coeff` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 102 | `mom_vi_coriolis` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 103 | `mom_vi_hdissip` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 104 | `mom_vi_u_coriolis` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 105 | `mom_vi_u_grad_ke` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 106 | `mom_vi_u_vertshear` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 107 | `mom_vi_v_coriolis` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 108 | `mom_vi_v_grad_ke` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 109 | `mom_vi_v_vertshear` | 0 | 411 | 0.0 | free | 1 | 53568 |
| 110 | `packages_init_variables` | 0 | 411 | 0.0 | free | 1 | 1 |
| 111 | `pressure_for_eos` | 0 | 411 | 0.0 | free | 1 | 105648 |
| 112 | `reset_nlfs_vars` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 113 | `rotate_uv2en_rl` | 0 | 411 | 0.0 | free | 1 | 1488 |
| 114 | `timestep_tracer` | 0 | 411 | 0.0 | free | 2 | 2976 |
| 115 | `update_etah` | 0 | 411 | 0.0 | free | 1 | 1489 |
| 116 | `apply_forcing_s` | 0 | 411 | 0.0 | 0.0 | 1 | 53568 |
| 117 | `gad_dst3_adv_y` | 0 | 411 | 0.4 | 0.0 | 1 | 107136 |
| 118 | `main_do_loop` | 0 | 411 | 10403.1 | 0.0 | 1 | 1488 |

## Proposed -nocheckpoint list (budget 2000 MB/rank, min gain 1.0 s)
- 34 callees, summed peak-memory cost bound 46.8 MB, summed time gain 411 s (100.0 % of all recorded gain)

```
adams_bashforth2 calc_adv_flow calc_phi_hyd calc_viscosity cg2d ctrl_map_forcing do_oceanic_phys do_stagger_fields_exchanges dummy_in_stepping_uv_xyz_rl dynamics exch2_rl1_cube exch_xy_rl find_rho_2d forward_step gad_advection gad_calc_rhs gad_dst3_adv_r gad_dst3_adv_x grad_sigma impldiff integr_continuity integrate_for_w load_fields_driver mom_calc_visc mom_vecinv momentum_correction_step salt_integrate solve_for_pressure solve_tridiagonal temp_integrate thermodynamics timestep tracers_correction_step update_surf_dr
```
