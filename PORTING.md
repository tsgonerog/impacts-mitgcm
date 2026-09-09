# Porting to another HPC machine

Everything that differs between clusters lives in one file, `tools/machine_env.sh`.
Build and submit scripts source it, so moving to a new machine means adding a
case block there rather than editing a dozen scripts.

Currently defined: **sverdrup** (default) and **perlmutter** (NERSC).

The machine is detected from `$NERSC_HOST`, which NERSC sets on every login and
compute node. sverdrup sets nothing reliable — its compute nodes are named
`c1-1` and similar — so it is the fallback. Force one with
`export IMPACTS_MACHINE=perlmutter`.

---

## What the profile controls

| Variable | sverdrup | perlmutter |
| --- | --- | --- |
| `SCRATCH_ROOT` | `/scratch2/$USER` | `$SCRATCH` (`/pscratch/sd/<i>/<user>`) |
| `MPI_LAUNCHER` | `mpirun -n` | `srun -n` |
| `MPI_OPTFILE` | `crios_computing/.../linux_amd64_ifort+mpi_sverdrup` | `tools/optfile_templates/linux_amd64_gnu+mpi_perlmutter` **(untested)** |
| `SERIAL_OPTFILE` | `MITgcm/tools/build_options/linux_amd64_ifort` | same as MPI (Cray wrappers) |
| `SBATCH_EXTRA` | *(empty)* | `-A $NERSC_ACCOUNT -C cpu -q $PERLMUTTER_QOS -t $PERLMUTTER_WALLTIME` |
| modules | none — loaded from `~/.bashrc` | `PrgEnv-gnu`, `cray-mpich`, `cray-hdf5`, `cray-netcdf` |

The optfiles are set **from the machine, not inherited from the environment**.
`~/.bashrc` on sverdrup exports `MPI_OPTFILE`, and letting that win would
silently build Perlmutter with the Intel sverdrup optfile. Override deliberately
with `IMPACTS_MPI_OPTFILE` / `IMPACTS_SERIAL_OPTFILE`.

---

## First time on Perlmutter

### 1. Environment

```bash
export NERSC_ACCOUNT=mXXXX          # required: sbatch rejects jobs without -A
export TAPENADE_HOME=$HOME/tapenade_3.16-v2
export PATH=$PATH:$TAPENADE_HOME/bin
```

**Tapenade is not a NERSC module and is not in this repository.** `genmake2 -tap`
shells out to a `tapenade` command on `$PATH`. Download Tapenade 3.16-v2 from
INRIA, unpack it, and make sure a JRE is available (`module load java`, or the
system one). Without it every adjoint build fails at the differentiation step.

Check before building:

```bash
source tools/machine_env.sh && impacts_check_env
```

It warns about a missing `tapenade`, a missing optfile, and an unset
`NERSC_ACCOUNT` — the three things that otherwise fail deep into a build or at
submission.

### 2. Data that git does not carry

| What | Size | How to get it |
| --- | --- | --- |
| `DINO_1deg/input_binaries/` | 179 MB, 23 files | copy from sverdrup — **produced outside this repo, nothing regenerates it**, except `dino_viscAhD*.bin` (`scripts/gen_viscAhD.py` rebuilds them from `tile001.mitgrid`); `dino_diffKr*.bin` are no longer read (since 2026-09-09) |
| `DINO_1deg/input_adj_binaries/ones_64b.bin` | 2.8 MB | copy; every `xx_*_weight` in `data.ctrl` points at it |
| `SOMA_1deg/input_binaries/` | 64 KB | regenerate with `input/gendata.py` |
| `SOMA_1deg/input_adj_binaries/` | 1.2 MB | copy |
| 180-year pickup | 20 MB | copy, if you want the main adjoint experiment |

```bash
# from sverdrup
rsync -av MITgcm_c69m/mysetups/DINO_1deg/input_binaries/ \
          MITgcm_c69m/mysetups/DINO_1deg/input_adj_binaries/ \
          perlmutter.nersc.gov:~/Proj_ImPACTS/impacts-mitgcm/MITgcm_c69m/mysetups/DINO_1deg/
```

Both directories are gitignored, so a fresh clone has neither. There is no
adjoint run until they are in place.

MITgcm reads and writes big-endian MDS files. The Perlmutter optfile keeps
`-fconvert=big-endian` for exactly this reason, so pickups and `ADJ*` output stay
readable across the two machines.

**Perlmutter `$SCRATCH` is purged on inactivity.** Pickups you care about belong
on CFS (`/global/cfs/cdirs/<repo>/`), not scratch.

### 3. Build

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
./scripts/build_tapAdj.sh        # DINO: a symlink to the default variant, build_tapAdj_nocheckpoint.sh
```

No `export MPI_OPTFILE` needed — the profile supplies it. The build scripts call
`impacts_load_modules` themselves (in the shared body, `tools/lib/build_body.sh`,
which every `scripts/build_*.sh` definition sources; a definition can be run
from anywhere, it `cd`s to its setup).

`linux_amd64_gnu+mpi_perlmutter` was written from the MITgcm gfortran and Cray
templates plus NERSC's documented wrappers. **It has not been compile-tested on
Perlmutter**, which is why it sits in `tools/optfile_templates/` rather than in
`MITgcm/tools/build_options/` alongside the 93 upstream optfiles that do work.
`machine_env.sh` still points at it, so the build runs and gives you real
compiler errors to work from; `impacts_check_env` warns for as long as the
template is what is in use.

Expect to adjust `FOPTIM` on first use. If the adjoint misbehaves, drop
`-march=znver3` and lower `-O2` before looking anywhere else: the adjoint is far
more sensitive to aggressive optimisation than the forward model. Once it
builds, copy it somewhere of your own and `export IMPACTS_MPI_OPTFILE` at it —
that silences the warning. See `tools/optfile_templates/README.md`.

### 4. Submit

```bash
./tools/submit.sh MITgcm_c69m/mysetups/DINO_1deg/scripts/submit_tapAdj.sh
```

Use the wrapper rather than `sbatch` directly. Account, QOS, constraint and
walltime cannot be written as `#SBATCH` directives without breaking the other
machine, so the wrapper passes them on the command line, where sbatch lets them
override the script. It also runs sbatch from the *setup* directory (the parent
of `scripts/`), which is what the job's `SLURM_SUBMIT_DIR`, its `-o logs/` path
and the `source` of the shared body `tools/lib/submit_body.sh` resolve against.
On sverdrup `SBATCH_EXTRA` is empty and this is exactly `sbatch --export=ALL
scripts/submit_tapAdj.sh` from that directory; plain `sbatch` still works there
if you run it the same way.

**`--export=ALL` is not decoration on a new machine.** It is sbatch's default,
but the jobs genuinely depend on it: `impacts_load_modules` is a no-op on
sverdrup because the Intel/MPI stack comes from `~/.bashrc`, so the toolchain
reaches the compute node only through the inherited environment — as do the
`IMPACTS_DURATION_DAYS` / `IMPACTS_TEST_CASE` per-run overrides. If a new site
defaults `SBATCH_EXPORT` to something narrower, jobs will fail to find their
shared libraries before any of this matters. Check that first.

---

## The one thing that is not a flag change

The 200-year spin-up carries `#SBATCH -t 240:00:00` — ten days. **No Perlmutter
QOS comes close**, so that job cannot run as configured. It needs splitting into
a pickup/restart chain: run to a pickup, resubmit from it, repeat. `PERLMUTTER_WALLTIME`
sets the per-job limit (default 24 h); the chaining itself is not automated here.

Check current QOS limits before planning — NERSC changes them.

The 5-year adjoint (`1830d`) and the 1-year viscosity runs should fit in a single
job.

Rank count is fixed by `SIZE.h`: DINO is `nPx=3, nPy=9` over `sNx=17, sNy=22`, so
`-n 27`. Perlmutter CPU nodes have 128 cores, so 27 ranks fit on one node.
Changing the decomposition means changing both `SIZE.h` and `-n`.

**Changing the decomposition also changes the cost function's value.** The
section normalisation in `code_tap/cost_atlantic_heat.F` is computed per MPI
tile (verified 2026-08-30; see the root `CLAUDE.md`), so `fc` from a run with a
different `nPx`/`nPy` is not comparable with the sverdrup runs — and neither
are the adjoint fields derived from it. Keep `3×9` when results must line up
with the existing campaigns, or fix the per-tile normalisation first.

---

## Things still tied to sverdrup

Known and deliberate, listed so they are not a surprise:

- **Notebook scratch paths** are absolute
  `/scratch2/tshahriar/<setup>_outputs/runs/{forward,adjoint}/<campaign>/...`. The analysis
  notebooks are not part of the run path, so they were left pointing at sverdrup.
  Repoint them if you move the analysis too — `./tools/pre_push_check.sh` reports
  every path that no longer resolves. Expect it to report the SOMA notebook: it
  reads a c69f-era campaign deleted on 2026-09-03 and is kept as a record.
- **`--mail-user`** is a `#SBATCH` directive in each submit script. Override per
  job with `sbatch --mail-user=...`, or edit the scripts.
- **`00_archive/` scripts** were not ported. They are history and reference dead
  run directories already.
- **No Python environment file.** The notebooks need `numpy`, `xarray`,
  `xmitgcm`, `matplotlib`; on Perlmutter start from `module load python`.

---

## Adding a third machine

1. Add a case block to `tools/machine_env.sh` setting `SCRATCH_ROOT`,
   `MPI_LAUNCHER`, `MPI_OPTFILE`, `SERIAL_OPTFILE`, `SBATCH_EXTRA` and an
   `impacts_load_modules` function.
2. Add an optfile under `tools/optfile_templates/` and point the case block at
   it — not inside the vendored `MITgcm/`, which is kept byte-for-byte upstream
   (`CLAUDE.md`, "How the vendored tree deviates"). Once it has built on the
   machine, copy it somewhere of your own and `export IMPACTS_MPI_OPTFILE` at
   it, which silences the template warning.
3. Make sure the machine is detected, or set `IMPACTS_MACHINE`.

Nothing else should need touching. An unknown machine is refused with a clear
message rather than silently falling back to sverdrup's settings.
