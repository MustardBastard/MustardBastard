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

**Sidebar**
- **X / Y axis**: any numeric column, or any custom parameter. Log X / Log Y.
- **Colour by**: a category (Lab, Material, Condition, highlight flags) or a
  number (e.g. Temp). The most frequent categories get the colours; the rest are
  grouped as "Other". A category keeps its colour when you filter.
- **Filters**: "Only PWR Mainstream Data" / "Only PWR Representative HAZ Data"
  (read from the green highlights in the workbook), Lab, Material, Condition,
  and range sliders for any numeric parameter.

**Tabs**
- **Plot**: the scatter plot. "Suggested plots" contains ready-made views with a
  short reason for each (K-dependence, Arrhenius, cold work, H₂, O₂, Cl⁻, SO₄²⁻,
  data quality, and a consistency check). The line above the plot says how many
  rows were left out and why (empty cells, zero on a log axis).
- **Y vs every parameter**: one small plot per parameter against the same Y, to
  see quickly which parameters seem to matter.
- **Data coverage**: % of filled cells per lab (or material) and column, so you
  can see which researchers did not report which parameters.
- **Nondimensionalize**: dimensional analysis in three steps.
  1. *Variables and units*: pick variables; the app reads each unit (mm/s, MPa√m,
     °C, J/(mol·K), µm, m²/s …) into SI dimensions M, L, T, Θ, N. Units it cannot
     read are flagged and can be corrected in the table (saved in
     `unit_overrides.json`). Constants are marked: they only shift the axes.
  2. *π groups*: the Buckingham π theorem gives n − k groups. Choose the
     repeating variables (or let the app choose), then add the groups as
     parameters. All groups are computed in SI, so they are pure numbers. You
     can also type a group of your own and check that it is dimensionless.
  3. *Collapse score*: π plot vs the raw plot it should beat, on the same rows.
     Scatter = SD of log10(Y) around a fitted curve (0.3 decades = factor 2).
     Held-out = refit without one lab at a time and test on that lab.
     Constants in a group cannot change either number.

  **Matches**: one idea at a time. "Set up Match 1" adds the parameters it needs
  (σy from %CW per MRP-458, Q, R, T_K, and placeholder constants d and D0) and
  builds π(CGR) = CGR·d/D, π(K) = K/(σy·√d) and π(Q) = Q/(R·T).
- **Custom parameters**: add parameters that are not in the workbook, without
  touching the workbook:
  - *Formula*: e.g. `1000 / (Temp + 273.15)` or `K / E_mod`
  - *Constant*: e.g. `R = 8.314`
  - *Value per category*: e.g. elastic modulus per Material, typed in a table.
  They are saved in `custom_parameters.json` and appear in every axis menu.
  A new formula's dimensions are checked against the unit you give it
  (tick "Skip the unit check" for empirical fits with hidden-unit coefficients).
- **Data table**: the filtered rows, with CSV download.

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
