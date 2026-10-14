"""Static parts of the page: what ran, why it is consistent, provenance. Numbers that come from runs are
filled in by page_text.py from the stats files.

Two campaigns share this page (campaign.CAMPAIGN, since 2026-10-13): the September one with the cost at 26 N and
its rerun with the cost at the overturning maximum, 43 N. Each block below exists in both versions and the one
for the current campaign is selected at import; the September texts are kept verbatim so that page can be rebuilt."""
import campaign as c

IS43 = c.CAMPAIGN == 'kappa_v_ensemble_gmFwd_sec43N'

SETUP_INTRO_26 = """
<p>Every run in this campaign starts from a new 170-year spin-up from rest, <b>31329</b>, integrated under
the configuration that the 2026-09-12 cleanup left on <code>main</code>: DINO's reference lateral viscosity
files with <code>viscAhReMax=2.</code>, the flux-limited DST3 tracer advection (scheme 33) with explicit
vertical advection, GM/Redi on, and neither KPP nor the C-D scheme compiled. It stands in for the production
spin-up 31203, whose scratch filesystem failed on 2026-09-12; the build and namelists are those that reproduced
31203 bit for bit. The adjoint is the approximate adjoint the setup requires: GM/Redi runs in its forward sweep
only, and the adjoint sweep linearises about the unlimited DST3 (scheme 30).</p>
"""

SETUP_INTRO_43 = """
<p>This is the September campaign rerun with the cost moved to the overturning maximum. The depth-space
streamfunction of the production spin-up 31203 peaks at grid row 148 (centre 43.21° N, southern face 42.84° N)
and the 848 m interface, 7.37 Sv over years 190–200, at that same row and interface in every decade of the spin-up,
in the reference leg and in the September adjoint's window; the September cost measured the transport across
26° N in the upper 982 m, on the cell's southern flank. <code>cost_atlantic_heat.F</code> now has <code>jsec=148</code>
and <code>kmaxdepth=24</code> (at row 148 the transport above 982 m is 3.5 % below the maximum), every adjoint build
records its section in <code>build_info.txt</code>, and the eight 5-year adjoints and the finite-difference sweeps
were rerun on 2026-10-13 from the September legs' year-180 states. The forward model, its legs and the adjoint's
approximations are those of September: DINO's reference lateral viscosity files with <code>viscAhReMax=2.</code>,
the flux-limited DST3 tracer advection (scheme 33) with explicit vertical advection, GM/Redi on (in the adjoint's
forward sweep only), the adjoint sweep linearised about the unlimited DST3 (scheme 30).</p>
"""

SETUP_DESIGN_26 = """
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

SETUP_DESIGN_43 = """
<ul class="findings">
<li><b>Forward legs (September's, runs 31366–31373).</b> Ten years from year 170 of the spin-up 31203, one per vertical
diffusivity κ<sub>v</sub> ∈ {0.25, 0.5, 2, 4, 8, 16, 32} × 1.2×10⁻⁵ m² s⁻¹
(<code>input/variants/kappa_v_ensemble/data_M&lt;k&gt;_ReMax2</code>); the reference leg at the unperturbed
κ<sub>v</sub> continues the spin-up to year 180 with the same settings. Nothing about them depends on the cost.</li>
<li><b>Five-year adjoints (runs 31553–31560).</b> From year 180 to 185, sensitivities dumped every 5 days. The reference is the
live <code>input_tap/data</code> from the reference leg's year-180 pickup; each member is the same namelist with its
κ<sub>v</sub> (<code>input_tap/variants/kappa_v_ensemble/</code>), started from its leg's year-180 pickup.</li>
<li><b>Finite-difference sweeps (runs 31561–31578).</b> Forward sweeps of the adjoint executable from the reference leg's year 180,
stopped once the cost is printed: κ<sub>v</sub> ±10 %, Theta raised and lowered in boxes of the pickup, and uniform
perturbations of the four surface controls (<code>input_tap/variants/fd_checks/</code>), with September's perturbed
pickups and forcing files. September's deep box (40–50° N below 1500 m) sits right under the new section and moves J by
the noise floor, so a box north of the section (45–60° N below 1500 m, the same ±0.016 K) was added on 2026-10-14.</li>
</ul>
"""

CONSISTENCY_26 = [
    ('Forward and adjoint namelists', 'input/ against input_tap/: data differs only in nIter0, nTimeSteps and the '
     'monitor and dump frequencies; data.pkg only by useGrdchk=.FALSE.; data.gmredi, data.diagnostics, eedata '
     'and data.exch2 are identical.'),
    ('Spin-up', "31329 runs the live input/data; 31203's staged namelists differ from it only by the now commented-out "
     "useKPP and useMNC, both .FALSE. in 31203."),
    ('Forward executable', 'build_frd, compiled once (2026-09-12, commit 290da58) and used by the spin-up, its rerun and all eight '
     'legs: one checksum in every run directory. The build without KPP and the C-D scheme reproduces the one before bit for bit '
     '(run 31280 against 31267, 61 days from rest: 58 output files and every %MON line).'),
    ('Adjoint executable', 'build_tapAdj_ckpAll, compiled once (2026-09-12, commit 290da58) and used by all eight adjoints and the '
     'sixteen finite-difference sweeps: one checksum in every run directory. The only source change between its build and the runs '
     'is a two-line comment in code_tap/gad_implicit_r.F.'),
    ('Reproduction of the production spin-up', "Byte-identical states: the new spin-up's year-170 pickup and the reference leg's "
     "year-180 pickup are bit for bit the production spin-up 31203's own (checked 2026-09-15, when /scratch2 returned), and the "
     "reference adjoint's forward sweep reproduces 31203's year-185 cost proxy to ten digits."),
    ('Adjoint-mode switches', 'Every adjoint staged data.autodiff with useGMRediInAdMode=.FALSE. and '
     'useApproxAdvectionInAdMode=.TRUE.; the submit body checked both before each run.'),
    ('Controls', 'Eight declared (Theta, Salt, κ_v in 3-D; Qnet, E−P−R, Qsw and both surface stresses in 2-D), '
     'all constant in time over the window; the six controls that no DINO build can apply stay commented out.'),
    ('Ensemble parameters', 'Each member adjoint differs from the live adjoint namelist only in diffKrT/diffKrS, '
     'which equal its forward leg\'s; nIter0 = 3162240 is the leg\'s last iteration.'),
]

CONSISTENCY_43 = [
    ('The cost section', 'cost_atlantic_heat.F: jsec=148, kmaxdepth=24, chosen by overturning_maximum.py from the spin-up 31203 '
     '(the maximum of psi north of 20 N below 300 m, the same row and interface in every decade tested, in the reference leg and '
     'in the September adjoint\'s window). The preprocessed cost_atlantic_heat.f of the build carries both values, and the build '
     'body writes them into build_info.txt as cost_section_jsec=148 and cost_kmaxdepth=24.'),
    ('Adjoint executable', 'build_tapAdj_ckpAll, rebuilt on 2026-10-13 (exe_md5 280265b2f6f538b809d0aa10589ef076) and used by all '
     'eight adjoints and the eighteen finite-difference sweeps: one checksum in every run directory, verified by the submit body '
     'against the build record before each run; submit_campaign.sh refuses a build whose record does not carry the campaign\'s jsec.'),
    ('Forward legs and executable', 'Unchanged from September (build_frd of 2026-09-12, runs 31366–31373): the cost is not compiled '
     'into the forward model, and the legs\' year-180 pickups are the states every adjoint and sweep here starts from.'),
    ('Namelists', 'The live input_tap/data, data.pkg, data.gmredi and data.autodiff of September, unchanged; the member and '
     'finite-difference variants likewise. The cost is compiled in, not a namelist setting, so the staged namelists of the two '
     'campaigns are identical and only build_info.txt tells a 43 N run from a 26 N one.'),
    ('Adjoint-mode switches', 'Every adjoint staged data.autodiff with useGMRediInAdMode=.FALSE. and '
     'useApproxAdvectionInAdMode=.TRUE.; the submit body checked both before each run.'),
    ('Cost against the forward model', 'The reference adjoint\'s forward sweep gives J = 0.4484; the cost formula applied to the '
     'reference leg\'s last-year monthly velocity gives 0.450, and the monthly index\'s internal variability in the spin-up is 8.5e-4.'),
    ('Controls', 'Eight declared (Theta, Salt, κ_v in 3-D; Qnet, E−P−R, Qsw and both surface stresses in 2-D), '
     'all constant in time over the window; the six controls that no DINO build can apply stay commented out.'),
    ('Ensemble parameters', 'Each member adjoint differs from the live adjoint namelist only in diffKrT/diffKrS, '
     'which equal its forward leg\'s; nIter0 = 3162240 is the leg\'s last iteration.'),
]

PROVENANCE_26 = """
<p>Model output: <code>/scratch2/tshahriar/DINO_1deg_outputs/runs/forward/</code> (<code>spinup_200yr_viscRef_ReMax2/</code>, whose first 170 years the campaign's own spin-up reproduced bit for bit before it was deleted on 2026-09-16, and <code>kappa_v_ensemble_gmFwd/</code>)
and <code>runs/adjoint/kappa_v_ensemble_gmFwd/</code> (adjoints and finite-difference sweeps).
Products, figures and animations: <code>analysis/kappa_v_ensemble_gmFwd/</code>, with the job map in
<code>job_map.tsv</code>. Analysis code: <code>analyses/DINO_1deg/adjoint/kappa_v_ensemble_gmFwd/</code> in
impacts-mitgcm (<code>campaign.py</code>, <code>forward_state.py</code>, <code>adjoint_products.py</code>,
<code>make_figures.py</code>, <code>build_page.py</code>; since 2026-09-16 also <code>make_films.py</code>, a film of every
ADJ* dump, and <code>build_explorer.py</code>, the
<a href="https://claude.ai/artifact/M14dASutpLo9EohDruuwwL" target="_blank" rel="noopener">sensitivity explorer</a>, whose
local copy is <code>analysis/kappa_v_ensemble_gmFwd/explorer/</code>). Earlier campaigns are compared through the numbers in <code>previous_campaigns_reference.json</code>, copied from
the tables on <code>/scratch2</code> before it failed. The campaign ran on <code>/scratch</code> while <code>/scratch2</code> was down and was moved back into the main tree on 2026-09-15.</p>
"""

PROVENANCE_43 = """
<p>Model output: <code>/scratch2/tshahriar/DINO_1deg_outputs/runs/forward/</code> (<code>spinup_200yr_viscRef_ReMax2/</code>
and the September legs under <code>kappa_v_ensemble_gmFwd/</code>) and <code>runs/adjoint/kappa_v_ensemble_gmFwd_sec43N/</code>
(the adjoints and finite-difference sweeps of 2026-10-13/14). Products, figures and animations:
<code>analysis/kappa_v_ensemble_gmFwd_sec43N/</code>, with the job map in <code>job_map.tsv</code>, the overturning maximum in
<code>stats/overturning_maximum.json</code> and the validation record in <code>validation_20261014.md</code>; the September
campaign's products stay under <code>analysis/kappa_v_ensemble_gmFwd/</code> and its page is the previous version of this one.
Analysis code: <code>analyses/DINO_1deg/adjoint/kappa_v_ensemble_gmFwd/</code> in impacts-mitgcm, which serves both campaigns
through <code>CAMPAIGN_NAME</code> (<code>campaign.py</code>, <code>overturning_maximum.py</code>, <code>forward_state.py</code>,
<code>adjoint_products.py</code>, <code>make_figures.py</code>, <code>make_films.py</code>, <code>adjoint_waves.py</code>,
<code>build_explorer.py</code>, <code>build_page.py</code>). The
<a href="https://claude.ai/artifact/M14dASutpLo9EohDruuwwL" target="_blank" rel="noopener">sensitivity explorer</a> was rebuilt
for this campaign on 2026-10-14 and opens on what the slide deck's films show. The September campaign is compared through
its own stats files; the two older ensembles through <code>previous_campaigns_reference.json</code>.</p>
"""

INCIDENTS_26 = """
<div class="note-box"><b>Two interruptions, neither of which touched the results.</b> The first submission (2026-09-12) started
from 31203 on <code>/scratch2</code>; that filesystem failed at 18:45 the same evening and every running job with it, so the
campaign was resubmitted on <code>/scratch</code> from the new spin-up 31329. That spin-up integrated all 170 years but could not
write its final pickup, because the forward submit script links a default pickup of the same name into every run directory; its
last 61 days were rerun from its own pickup two months earlier (31365), which reproduced every output file and monitor value of
31329 bit for bit and wrote the year-170 state the legs start from.</div>
"""

INCIDENTS_43 = """
<div class="note-box"><b>One check lost its signal, and was replaced.</b> September's deep North Atlantic box (40–50° N below
1500 m, ±0.016 K) sits directly under the 43° N section: the model's response to it is 4×10⁻⁵, the noise floor of the cost, and
the 43° N adjoint predicts as little, so the check is consistent but says nothing. A box north of the section, 45–60° N below
1500 m with the same amplitude, where the adjoint predicts a response six times the noise floor, was run as two more sweeps on
2026-10-14 (31577, 31578) and is the deep-box check reported here.</div>
"""

SETUP_INTRO = SETUP_INTRO_43 if IS43 else SETUP_INTRO_26
SETUP_DESIGN = SETUP_DESIGN_43 if IS43 else SETUP_DESIGN_26
CONSISTENCY = CONSISTENCY_43 if IS43 else CONSISTENCY_26
PROVENANCE = PROVENANCE_43 if IS43 else PROVENANCE_26
INCIDENTS = INCIDENTS_43 if IS43 else INCIDENTS_26
