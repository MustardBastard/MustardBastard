# Traps to avoid

**A constant cannot help.**
Multiplying by a number that is the same for every row (like the placeholder
grain size d) only moves the axes. If a group with a constant scores better,
the improvement comes from the other quantities in it.

**°C does not work in ratios.**
20 °C is not "twice as hot" as 10 °C. Formulas need kelvin. The app converts
°C to kelvin automatically when building combinations; do not add 273.15 a
second time.

**Empirical formulas have hidden units.**
"Yield strength = 20.9 × %CW + 255.7 MPa" works only with %CW as a plain
number. The app cannot check its units, so tick "Skip the unit check" when
adding such a formula.

**The lab effect hides inside everything.**
Each lab tested its own corner (one temperature, one cold work level). A trend
across the whole cloud may really be a difference between labs. Colour by lab
before believing a trend.

**"Looks tighter" is not proof.**
Check it with the sidebar filters: does it still show when you leave one lab
out, or look at one lab at a time? A pattern that disappears is likely luck.

**A log axis drops zeros.**
Zero or negative values cannot be shown on a log axis. The line above every
plot says how many rows were left out and why.

**Mainstream is someone else's box.**
The 265 Mainstream rows are MRP-458's choice. Run important checks on all
rows too, and compare.
