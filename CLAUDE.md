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
- Interface rebuilt around the workflow: Look / Test an idea / Data / Learn,
  guided 4-step match, "what to do next" lines, Expert-mode switch, glossary
  tooltips, first-launch interactive tutorial. Help texts are editable
  Markdown in `scc_plotter/help/`.

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
- Open question for Match 2: how should yield strength enter?

## Code map (`scc_plotter/`)

- `app.py`: loading, sidebar (which data), navigation, Expert mode.
- `ui/`: `look.py`, `match.py` (4-step match + verdict), `data.py`,
  `learn.py`, `tutorial.py`, `common.py` (Ctx, help-file readers).
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

- The user is about to try the rebuilt app and tutorial and report which
  steps are still unclear.
- Then: discuss Match 2 (how yield strength enters), one match only.
