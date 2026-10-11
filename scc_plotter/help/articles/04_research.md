# What the research says

A summary, in our own words, of four EPRI reports that frame this work.

## MRP-458 (2022): where the database comes from

The author collected 924 crack growth measurements from about 20 labs and
gave each one a quality score. Using filters, he narrowed them down to 265
**Mainstream** rows:

- quality score 1–3
- no oxygen
- low impurities
- 10–25% cold work
- 270–340 °C
- no weld (HAZ) data

He then fitted one equation:

> CGR = 1.50×10⁻¹⁸ · K^2.5 · HV^6 · exp(−85 000 / RT)

HV is hardness, calculated from cold work. Oxygen adds a factor of 7.

## Inside the box: assumptions in that method

- The **form** of the equation (power laws and Arrhenius) was chosen
  beforehand, because earlier EPRI work used it.
- The final exponents are **expert choices**, not the best fit. The plain
  regression gave K^2.15, HV^7.6 and Q = 88 750 J/mol.
- **Hardness was never measured**; it is calculated from cold work with one
  curve.
- Odd regions (above 340 °C, below 270 °C, outside 10–25% cold work) were
  **cut out** rather than explained.
- Tests with **no crack growth were removed**.
- One person **scored** all the data, including data from his own lab.
- Differences between labs were noted but **not resolved**.

## Outside the box: what the other reports add

- **MRP-236 and MRP-352:** most real plant cracks happen in **stagnant or
  occluded spots** with oxygen and impurities, often below normal
  temperature. The database is mostly clean, flowing water at full
  temperature.
- **MRP-352** calls **steel composition**, especially **sulfur content**,
  the biggest knowledge gap. Sulfur is not in our data.
- In hydrogenated water, **sensitized steel cracks more slowly**, the
  opposite of experience with oxygenated water.
- The database covers only **crack growth**, not how cracks **start**.
- **The testing guidelines** say growth rates are rarely reproducible within
  a factor of 2, and data from many labs often scatters by a factor of
  100–1000.

## What our own quick checks showed (Mainstream rows)

- Which **lab** ran the test explains about as much of the scatter (45%) as
  K, hardness and temperature together (50%).
- Between labs, results differ by about **8×** under supposedly the same
  conditions.
- One lab supplies 40% of the rows.

So "which lab" is not noise to ignore: it is a variable to understand.
