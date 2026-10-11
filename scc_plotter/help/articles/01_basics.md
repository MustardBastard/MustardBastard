# The basics

## What is stress corrosion cracking?

A metal that is under stress and sits in hot water can slowly grow cracks.
Nothing breaks suddenly: a crack creeps forward, a tiny bit at a time, for
years. In nuclear plants (PWRs, pressurized water reactors) this happens to
stainless steel pipes and parts that touch the hot primary water.

Three things must come together for it to happen:

- **Stress**: something pulls the crack open (loads, or stresses left behind by welding).
- **A susceptible material**: for example steel that was cold worked or strained by welding.
- **An environment**: hot water, made worse by oxygen or impurities.

## What is measured?

The database holds 924 laboratory measurements. In each test, a specimen
with a crack is held under a constant pull in hot water, and the crack length
is tracked over time.

The key result is the **crack growth rate (CGR)**, in mm per second.
The numbers are tiny: 1×10⁻⁷ mm/s is about 3 mm per year.

## What might change the crack speed?

| Column | Plain meaning | Expected effect |
|---|---|---|
| **K** | How hard the crack tip is pulled open | More pull, faster |
| **%CW** | How much the steel was cold worked (hardened) | Harder, faster |
| **Temp** | Water temperature | Hotter, faster |
| **O₂** | Oxygen in the water | Much faster (×10 or more) |
| **H₂** | Hydrogen in the water | Keeps the water "calm" |
| **Cl, SO₄** | Impurities | Mostly matter when oxygen is present |
| **B, Li** | Normal PWR water additives | Little effect found |
| **Lab** | Who ran the test | Should not matter, but does |

## Why so much scatter?

Points that should agree often differ by a factor of 10 or more. Reasons
include differences between labs, between heats (batches) of steel, and in how
carefully each test was run. Part of our job is to find out how much of the
scatter is physics and how much is "who measured it".
