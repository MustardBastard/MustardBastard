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

The app has four areas:

| Area | Question it answers |
|---|---|
| 👀 **Look** | What does the data show? Any Y against any X, or Y against every parameter. Suggested views give ready-made starting points. |
| 🔥 **Test an idea** | Does my idea reveal a pattern? A *match* in 4 guided steps: idea → quantities and units → unit-free combinations (Buckingham π) → verdict. |
| 🗂 **Data** | Who measured what (coverage), the rows themselves, and adding quantities that are not in the workbook (constants, formulas, a value per material). |
| 📖 **Learn** | Short articles: basics, dimensional analysis from zero, reading results, what the research says, our method, traps, and the **Cave map** of what each match taught. |

Every page has a 👉 **What to do next** line, and ⓘ icons explain each term in
one sentence.

**The verdict** compares the unit-free combinations with the raw plot on the
same rows: 🟢 pattern found (≥10% tighter and it holds on labs left out of the
fit), 🟡 no real change, 🔴 worse. Constants inside a combination cannot change
the verdict.

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
