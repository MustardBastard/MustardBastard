# Glossary

One sentence per term. These sentences appear when you hover over a ⓘ in the
app. Edit freely: each term starts with "## " followed by the term's key.

## CGR
Crack growth rate: how fast the crack moves forward, in mm per second. 1e-7 mm/s is about 3 mm per year.

## K
Stress intensity factor: how hard the crack tip is being pulled open. Bigger K, faster crack.

## CW
Cold work: how much the metal was squashed or rolled at room temperature, in %. It makes the steel harder, and harder steel cracks faster.

## Temp
Water temperature during the test. Hotter water speeds up the chemistry, so cracks grow faster.

## O2
Dissolved oxygen in the water. Oxygen makes the water aggressive and can speed cracking up by 10× or more.

## H2
Dissolved hydrogen in the water. Normal PWR water has hydrogen to keep it "calm" (no oxygen).

## Cl
Chloride impurity in the water, in parts per billion. Harmful mainly when oxygen is also present.

## SO4
Sulfate impurity in the water, in parts per billion.

## B
Boron in the water (from boric acid), used in PWRs to control the reactor.

## Li
Lithium in the water (from lithium hydroxide), used to control the water's pH.

## dTime
How long the test segment lasted, in hours.

## da
How far the crack grew during the test segment, in mm.

## Score
Data quality score given by the database author: 1 is best, 5 worst. MRP-458 dropped scores 4 and 5.

## Lab
The laboratory or researcher that produced the measurement. Labs disagree more than they should.

## Material
The steel grade, such as 304, 316L or 316NG.

## Mainstream
The 265 rows MRP-458 used for its equation: good quality, no oxygen, low impurities, 10–25% cold work, 270–340 °C, no weld (HAZ) data.

## HAZ
Heat affected zone: the metal right next to a weld. Welding leaves it strained, and most plant cracks are found there.

## T_K
Temperature in kelvin (°C + 273.15). Physics formulas need kelvin.

## R
Universal gas constant, 8.314 J/(mol·K). Appears in every temperature (Arrhenius) formula.

## Q
Activation energy: how strongly the crack speed depends on temperature. Bigger Q, stronger temperature effect.

## sigma_y
Yield strength: the stress at which the metal starts to bend permanently. Estimated here from cold work with the MRP-458 formula.

## d
Grain size of the metal. Here a placeholder: one value for every row.

## D
A rate scale that grows with temperature: D = D0·exp(−Q/RT). Its units (m²/s) let crack speed be made unit-free.

## log_axis
A logarithmic axis: each step along it multiplies by 10. Needed because crack speeds span a range of 100 000×.

## decade
One step on a log axis, a factor of 10. A scatter of 0.3 decades means points sit about ×2 from the curve.

## dimensions
The basic ingredients of a unit: mass M, length L, time T, temperature Θ and amount N. Speed, for example, is L/T.

## pi_group
A unit-free combination (π group): quantities multiplied and divided so that every ingredient cancels and a pure number is left.

## measuring_sticks
Measuring sticks (repeating variables): the quantities every other quantity is compared against. Choosing them is where the physics comes in.

## buckingham
Buckingham π theorem: number of unit-free combinations = number of quantities − number of independent ingredients.

## pattern_check
Pattern check (collapse score): do the points fall onto one band more tightly than in the raw plot?

## held_out
Held-out check: the curve is fitted without one lab and tested on that lab, for every lab in turn. A real pattern predicts labs it has never seen.

## constant
A quantity with the same value in every row. Multiplying by it only moves the axes; it can never make a pattern tighter.

## match
One small idea, tested on its own. Each match either lights a torch (a pattern) or closes a dead end. Both are progress.
