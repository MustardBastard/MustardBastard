# Project context: SCC Plotter (handoff for new sessions)

Read this first. It summarizes a long earlier conversation so it does not have
to be repeated.

## The project

- Student project (supervised by tutor Özgür Ertunç) on **stress corrosion
  crack growth rates (CGR) of stainless steel in PWR primary water**.
- Data: EPRI MRP-458 database, 924 rows, one xlsx (sheet `PWR_SCC_CGR_DB`;
  `Sheet1` is a useless excerpt). The xlsx is **not** in the repo (not public);
  the user keeps it in `scc_plotter/data/`.
- Three parts, in order: (1) a plotting tool to see patterns, (2) dimensional
  (nondimensional) analysis to find patterns, (3) clear statements about them.
- The user and tutor suspect the published researchers think "inside a box"
  (too technical, fixed equation forms); the goal is to look at the data both
  inside and outside that box.

## Working preferences

- Explain from zero, plainly; the user is rusty on dimensional analysis.
- Discuss options and let the user decide before building big changes.
- UI language: English. Platform: Python on the user's Windows PC.
- **One match per gist**: test one small idea at a time ("matches find
  torches, torches light the cave"). Do not set up the next match before the
  user has looked at the current one.

## Decisions made

- Nondimensionalization = Buckingham π groups (B) and physically scaled
  variables (C). No plain "divide by a reference number" normalization.
- Collapse score included from the start: SD of log10(Y) around a fitted
  curve (decades), plus leave-one-lab-out ("held-out") check. Verdict:
  ≥10% tighter on both → 🟢, ≥10% worse → 🔴, else 🟡. Constants cannot change
  the score (by design).
- Interface built around the workflow: "what to do next" lines, Expert-mode
  switch, glossary tooltips, first-launch interactive tutorial. Help texts are
  editable Markdown in `scc_plotter/help/`.
- **Version 5 (current):** areas Look / Data / Learn. Look has three views:
  One plot, Y against every parameter, 3D plot. The "Test an idea" (match)
  page was **removed on the tutor's advice**: nondimensionalizing comes later,
  after upgrading the plotting tool and finding extra parameters. The engine
  (`units.py`, `dimensional.py`, `collapse.py`, `matches.py`) stays in
  `scc_core/`, tested but unused by the UI. On start, v5 deletes the exact
  quantities Match 1 created (sigma_y, Q, d, D0, D, π groups) from the user's
  `custom_parameters.json`; R, T_K, invT_1000, CGR_from_da and user-made ones stay.

- **Version 6:** adds a hidden "old map" plot style (easter egg, user's request):
  parchment, IM Fell English font, ink palette, map symbols, compass rose,
  double border, "Hic sunt dracones". Toggled by clicking the plain-looking
  "version N" text at the bottom of the sidebar 3 times within 4 s
  (`ui/theme.py`, `knock()`); state kept in `scc_plotter/.old_map`. Keep it
  hidden: do not mention it in the README or in-app help.
- Open proposal (not yet built): when ≤8 groups are on screen, give each its
  own colour instead of folding small labs into "Other"; also add the
  Expert-mode colour options to the 3D plot.

## Research findings so far (details: `scc_plotter/help/articles/04_research.md`)

- MRP-458 equation (median): CGR = 1.50e-18 · K^2.5 · HV^6 · exp(−85000/RT),
  fitted on 265 "Mainstream" rows (the green highlight in column A). Exponents
  are expert choices (the raw regression gave K^2.15, HV^7.6, Q = 88 750).
  HV is computed from %CW, not measured.
- Our check: the lab alone explains ~45% of the variance in log CGR on
  Mainstream rows, versus ~50% for K + HV + T together; lab offsets reach ~8×.
- MRP-352: steel composition (sulfur) is the biggest gap and is not in the data.
  Most plant cracks happen in occluded/stagnant spots, unlike the lab data.

## Match results (details: `scc_plotter/help/articles/07_cave_map.md`)

- **Match 1** (π: CGR·d/D vs K/(σy·√d), Q/RT): 🟡 no change on Mainstream
  (0.637 → 0.634 decades). Split: the temperature part (Arrhenius, Q = 85 kJ/mol)
  helps (0.583, holds on held-out labs); K/σy hurts (CGR rises with σy, so
  strength must act as a driver, not as a measuring stick for K).
- Open question for Match 2 (later): how should yield strength enter?

## Code map (`scc_plotter/`)

- `app.py`: loading, sidebar (which data), navigation, Expert mode, VERSION.
- `ui/`: `look.py` (2D, every-parameter, 3D), `data.py`, `learn.py`,
  `tutorial.py`, `common.py` (Ctx, help-file readers). The old 4-step match
  page (`ui/match.py`) is in git history (commit 0b89b3a) if it is needed again.
- `scc_core/`: `loader.py` (header detection, units, highlight flags),
  `custom_params.py` (constants/formulas/lookups → `custom_parameters.json`),
  `units.py` (unit parser → SI scale + M,L,T,Θ,N), `dimensional.py`
  (Buckingham, formula dimensions, SI rewrite), `collapse.py` (score),
  `matches.py` (Match 1 definition), `plotdata.py`, `suggestions.py`.
- `help/`: `glossary.md`, `articles/*.md`, `tutorial.md`.
- Tests: `python scc_plotter/tests/test_core.py` (no xlsx needed).
- Run: `run_app.bat` (creates `.venv`, installs requirements, starts Streamlit).

## Environment notes

- In the cloud sessions, PyPI was blocked, so Streamlit/Plotly could not be
  installed; the UI was verified with stub modules only. The real app has
  not yet been seen running by Claude, so ask the user for screenshots if
  anything looks off.
- Development branch: `claude/custom-plotting-mechanism-2gtt83`.

## Status / next steps

- Version 5 delivered (3D view added, match page removed). Version 6 adds the hidden old-map style.
- Next, per the tutor: keep upgrading the plotting tool, then find the extra
  parameters (material properties etc.) needed before returning to
  nondimensional analysis. Match 2 (how yield strength enters) waits until then.
