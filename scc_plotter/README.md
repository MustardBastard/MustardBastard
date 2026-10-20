# SCC Plotter

Interactive plotting tool for the PWR stainless-steel SCC crack growth rate
(CGR) database (MRP-458 workbook). Part 1 of the project: look at the data,
switch parameters freely, and find patterns worth a dimensional analysis later.

## Start it (Windows)

1. Install Python 3.10 or newer from https://www.python.org/downloads/
   (tick "Add python.exe to PATH" in the installer).
2. **Extract the zip** (right-click → "Extract All..."). Running it from inside
   the zip does not work.
3. Copy the workbook into the `data` folder.
4. Double-click `run_app.bat`. The first run creates a private environment in
   `.venv` and installs the packages (a few minutes). Your browser then opens
   the app at http://localhost:8501. Close the black window to stop it.

If something fails, the window stays open with a message; send a screenshot.

Or from a terminal:

```
pip install -r requirements.txt
streamlit run app.py
```

You can also upload a workbook from the sidebar instead of using `data/`.

## What it does

On first start a **3-minute tutorial** walks you through the app. Restart it
anytime with **❓ Tutorial** in the sidebar.

The **sidebar** decides *which data* you look at ("Only PWR Mainstream Data",
Lab, Material). **Expert mode** at the bottom of the sidebar shows advanced
options (more filters, range sliders, choosing measuring sticks, curve type).

The app has three areas:

| Area | Question it answers |
|---|---|
| 👀 **Look** | What does the data show? Three views: one plot (any Y against any X), Y against every parameter, and a rotatable **3D plot** (two drivers at once, plus colour). Suggested views give ready-made starting points. |
| 🗂 **Data** | Who measured what (coverage), the rows themselves, **auto-filled properties** (see below), and adding quantities that are not in the workbook (constants, formulas, a value per material). |
| 📖 **Learn** | Short articles: basics, dimensional analysis from zero, reading results, what the research says, our method, traps, and the **Cave map** of what each match taught. |

Every page has a 👉 **What to do next** line, and ⓘ icons explain each term in
one sentence.

Version 5 removed the "Test an idea" page: nondimensional analysis comes back
later, once the extra parameters it needs have been found. The engine for it
(units, Buckingham π groups, collapse score) is still in `scc_core/` and
tested. Quantities that Match 1 created on your PC are removed on first start.

### Auto-filled properties (Data → Auto-fill properties)

Columns calculated for every test from its material grade (304, 304L, 316, 316L,
316NG, 347), temperature and water chemistry, for later nondimensional analysis.
All offline (`scc_core/enrichment.py`):

| Group | Columns | Source |
|---|---|---|
| Mechanical | E_T, YS_ann_T, UTS_ann_T, YS_cw_RT, YS_cw_T | Approximate ASME BPVC II-D (TM-1, Y-1, U) values for annealed plate; MRP-458 YS(%CW) fit |
| Water chemistry | H2_NiNiO, H2_over_NiNiO, pH_T, pH_300, ECP_H2 | Attanasio & Morton Ni/NiO line; B/Li pH model (Mesmer 1972, Marshall & Franck 1981); H2/H2O electrode with Fernández-Prini H2 solubility |
| Composition | Cr, Ni, Mo, C, Si, N, S (wt %) | ASTM A240 specification ranges (316NG: nuclear-grade spec) |

Caveats: the ASME values could not be checked against the licensed code book;
replace them with your own table (columns grade, property, temp_C, value; saved
as `data/material_properties.csv`). The pH model reads about 0.1–0.2 high
against values quoted in MRP-458. Rows with empty B/Li get no pH; ECP is only
given for hydrogenated water with ≤ 5 ppb O2.

Tests: `python tests/test_enrichment.py`.

### Editing the help texts

All texts are plain files in `help/`, editable with any text editor:

- `help/glossary.md`: the one-sentence explanations behind the ⓘ icons
- `help/articles/*.md`: the Learn articles (file name order = menu order)
- `help/tutorial.md`: the tutorial steps

## How the workbook is read

- The header row is found automatically (row 4); the notes row above it
  ("compact tension id", "tip of the crack", ...) is kept as column notes.
- `CGR\nmm/s` becomes the name `CGR` with unit `mm/s`. In formulas, use the
  variable names listed in the Custom parameters tab (`∆Time` → `dTime`,
  `∆a` → `da`, `%CW` → `CW`, `Temp.` → `Temp`).
- Text in number columns (`－`, `#N/A`) is treated as empty; the "Data notes"
  box lists how many cells this affected.
- The highlight legend at the top of the sheet ("PWR Mainstream Data in Column
  A") becomes a Yes/No column from the cell colours.

## Tests

```
python tests/test_core.py
```
