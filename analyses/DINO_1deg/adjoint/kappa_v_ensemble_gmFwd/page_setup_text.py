"""Static parts of the page: what ran, why it is consistent, provenance. Numbers that come from runs are
filled in by page_text.py from the stats files."""

SETUP_INTRO = """
<p>Every run in this campaign starts from a new 170-year spin-up from rest, <b>31329</b>, integrated under
the configuration that the 2026-09-12 cleanup left on <code>main</code>: DINO's reference lateral viscosity
files with <code>viscAhReMax=2.</code>, the flux-limited DST3 tracer advection (scheme 33) with explicit
vertical advection, GM/Redi on, and neither KPP nor the C-D scheme compiled. It stands in for the production
spin-up 31203, whose scratch filesystem failed on 2026-09-12; the build and namelists are those that reproduced
31203 bit for bit. The adjoint is the approximate adjoint the setup requires: GM/Redi runs in its forward sweep
only, and the adjoint sweep linearises about the unlimited DST3 (scheme 30).</p>
"""

SETUP_DESIGN = """
<ul class="findings">
<li><b>Forward legs.</b> Ten years, from the spin-up's year-170 pickup, one per vertical diffusivity
κ<sub>v</sub> ∈ {0.25, 0.5, 2, 4, 8, 16, 32} × 1.2×10⁻⁵ m² s⁻¹
(<code>input/variants/kappa_v_ensemble/data_M&lt;k&gt;_ReMax2</code>). The reference leg at the unperturbed
κ<sub>v</sub> continues the spin-up to year 180 with the same settings.</li>
<li><b>Five-year adjoints.</b> From year 180 to 185, sensitivities dumped every 5 days. The reference is the
live <code>input_tap/data</code> from the reference leg's year-180 pickup; each member is the same namelist with its
κ<sub>v</sub> (<code>input_tap/variants/kappa_v_ensemble/</code>), started from its leg's year-180 pickup.</li>
<li><b>Finite-difference sweeps.</b> Forward sweeps of the adjoint executable from the reference leg's year 180, stopped once
the cost is printed: κ<sub>v</sub> ±10 %, Theta raised and lowered in three boxes of the pickup, and uniform
perturbations of the four surface controls whose gradients looked least trustworthy
(<code>input_tap/variants/fd_checks/</code>).</li>
</ul>
"""

CONSISTENCY = [
    ('Forward and adjoint namelists', 'input/ against input_tap/: data differs only in nIter0, nTimeSteps and the '
     'monitor and dump frequencies; data.pkg only by useGrdchk=.FALSE.; data.gmredi, data.diagnostics, eedata '
     'and data.exch2 are identical.'),
    ('Spin-up', "31329 runs the live input/data; 31203's staged namelists differ from it only by the now commented-out "
     "useKPP and useMNC, both .FALSE. in 31203."),
    ('Forward executable', 'build_frd (after KPP and the C-D scheme left the package list) reproduces 31203 bit for '
     'bit over 61 days: run 31280, 50 output files and all %MON values.'),
    ('Adjoint executable', 'build_tapAdj_ckpAll, the default pair; the only source change after its build is a '
     'two-line comment in code_tap/gad_implicit_r.F (its preprocessed text is otherwise identical).'),
    ('Adjoint-mode switches', 'Every adjoint staged data.autodiff with useGMRediInAdMode=.FALSE. and '
     'useApproxAdvectionInAdMode=.TRUE.; the submit body checked both before each run.'),
    ('Controls', 'Eight declared (Theta, Salt, κ_v in 3-D; Qnet, E−P−R, Qsw and both surface stresses in 2-D), '
     'all constant in time over the window; the six controls that no DINO build can apply stay commented out.'),
    ('Ensemble parameters', 'Each member adjoint differs from the live adjoint namelist only in diffKrT/diffKrS, '
     'which equal its forward leg\'s; nIter0 = 3162240 is the leg\'s last iteration.'),
]

PROVENANCE = """
<p>Model output: <code>/scratch/tshahriar/DINO_1deg_outputs/runs/forward/kappa_v_ensemble_gmFwd/</code> (spin-up and legs)
and <code>runs/adjoint/kappa_v_ensemble_gmFwd/</code> (adjoints and finite-difference sweeps).
Products, figures and animations: <code>analysis/kappa_v_ensemble_gmFwd/</code>, with the job map in
<code>job_map.tsv</code>. Analysis code: <code>analyses/DINO_1deg/adjoint/kappa_v_ensemble_gmFwd/</code> in
impacts-mitgcm (<code>campaign.py</code>, <code>forward_state.py</code>, <code>adjoint_products.py</code>,
<code>make_figures.py</code>, <code>build_page.py</code>). Earlier campaigns are compared through the numbers in <code>previous_campaigns_reference.json</code>, copied from
the tables on <code>/scratch2</code> before it failed.</p>
"""

INCIDENTS = """
<div class="note-box"><b>Two interruptions, neither of which touched the results.</b> The first submission (2026-09-12) started
from 31203 on <code>/scratch2</code>; that filesystem failed at 18:45 the same evening and every running job with it, so the
campaign was resubmitted on <code>/scratch</code> from the new spin-up 31329. That spin-up integrated all 170 years but could not
write its final pickup, because the forward submit script links a default pickup of the same name into every run directory; its
last 61 days were rerun from its own pickup two months earlier (31365), which reproduced every output file and monitor value of
31329 bit for bit and wrote the year-170 state the legs start from.</div>
"""
