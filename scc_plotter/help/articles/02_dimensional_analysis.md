# Dimensional analysis from zero

## Units are made of ingredients

Every physical quantity is built from a few basic ingredients:

| Symbol | Ingredient |
|---|---|
| M | mass |
| L | length |
| T | time |
| Θ | temperature |
| N | amount of substance (mol) |

Speed is a length divided by a time, so crack growth rate has the
ingredients **L·T⁻¹**. A stress is a force per area, **M·L⁻¹·T⁻²**. The stress
intensity factor K is a stress times √length, **M·L⁻½·T⁻²**.

The app reads each column's unit (mm/s, MPa√m, °C, …) and works out its
ingredients for you.

## Unit-free numbers

If you multiply and divide quantities so that every ingredient cancels, you
get a **pure number**: no unit at all. Engineers love these, because a pure
number means the same thing at any size and in any unit system.

The best-known example is the Reynolds number in fluids: one number tells you
whether flow is calm or turbulent, whether it is water in a pipe or air around
a plane.

## How many unit-free numbers are there?

The **Buckingham π theorem** answers this:

> number of unit-free combinations = number of quantities − number of independent ingredients

Example: 8 quantities built from 5 ingredients give 3 combinations, called
π₁, π₂, π₃. Instead of studying 8 things at once, you study 3.

## Measuring sticks

To build the combinations, you choose some quantities as **measuring sticks**
(the textbook calls them *repeating variables*). Every other quantity is then
measured against them.

For example, with yield strength σy as the stick for stress, K becomes K/σy.

Different sticks give different, equally correct combinations. **Choosing the
sticks is where the physics comes in**: you are saying which scales you
believe matter.

## Worked example: Match 1

Quantities: CGR, K, σy, grain size d, a rate scale D, Q, R, T.

| Combination | Meaning |
|---|---|
| CGR · d / D | crack speed measured against a thermally activated rate |
| K / (σy · √d) | crack pull measured against the steel's strength |
| Q / (R · T) | the temperature (Arrhenius) number |

Check the first one: (L/T) · L / (L²/T) = 1. All ingredients cancel.

## Why do this?

If the combinations capture the real physics, data from different
temperatures, steels and labs **collapse** onto one band. That is how the
generalized charts in thermodynamics textbooks were found: reduced pressure
and reduced temperature put all gases on one chart.
