# SCC Plotter

Interactive plotting tool for the PWR stainless-steel SCC crack growth rate
(CGR) database (MRP-458 workbook). Part 1 of the project: look at the data,
switch parameters freely, and find patterns worth a dimensional analysis later.

## Start it (Windows)

1. Install Python 3.10 or newer from python.org (tick "Add Python to PATH").
2. Copy the workbook into the `data` folder.
3. Double-click `run_app.bat`. Your browser opens the app at http://localhost:8501.

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
- **Custom parameters**: add parameters that are not in the workbook, without
  touching the workbook:
  - *Formula*: e.g. `1000 / (Temp + 273.15)` or `K / E_mod`
  - *Constant*: e.g. `R = 8.314`
  - *Value per category*: e.g. elastic modulus per Material, typed in a table.
  They are saved in `custom_parameters.json` and appear in every axis menu.
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
