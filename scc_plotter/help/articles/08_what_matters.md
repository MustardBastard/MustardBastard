# What matters: reading the results

Find it on **🗂 Data → What matters for CGR**. The same result appears above
every plot of CGR in 👀 Look.

## The question

When CGR changes from test to test, **which parameters is that change linked
to?** The plain plots cannot answer this alone, because the parameters are mixed
up: each lab tested its own corner (one temperature, one cold-work level, with or
without oxygen…). A parameter can look important only because it travels together
with another one.

The answer feeds the nondimensional analysis later: it tells us which quantities
deserve a place in the unit-free combinations.

## Kendall's τ in one sentence

Pick two tests at random and ask: *is the one with the higher K also the one with
the higher CGR?* τ is the chance of "yes" minus the chance of "no".

| τ | Meaning |
|---|---|
| +0.30 | 65 % of pairs agree: higher value → usually faster cracking |
| 0 | no link: half agree, half disagree |
| −0.30 | 65 % of pairs disagree: higher value → usually slower cracking |

Rough wording used in the app: below 0.10 *negligible*, 0.10–0.20 *weak*,
0.20–0.30 *moderate*, above 0.30 *strong*. (τ runs lower than the more familiar
Pearson or Spearman coefficients for the same data.)

## "After removing other effects"

This is Kendall's **partial τ** (Kendall, 1942). It is the link that remains when
the other parameters are held fixed.

A classic example: ice-cream sales and drownings rise together, but only because
both rise in hot weather. Hold the temperature fixed and the link disappears.

In our data, dissolved **hydrogen** looks linked to CGR, but once oxygen is
taken into account the link is close to zero: hydrogenated tests simply had no
oxygen. On the page this shows as a ○ far from the ●.

## The bar: how sure are we?

The data are recalculated on 1000 resampled versions (**bootstrap**, Efron 1979).
Whole specimens are resampled, because tests on the same specimen are not
independent. The bar spans the middle 95 % of the results.

- Bar **does not cross 0** → *clear*: the direction of the link is reliable.
- Bar **crosses 0** → *uncertain*: with these rows we cannot tell.

More rows give narrower bars (4× the rows ≈ half the width). But *which* rows
remain matters even more than how many.

## What is held fixed (⚙ box at the top)

The ⚙ box lists every parameter that can be **held fixed** while the others are
judged, in groups. Tick or untick each one separately. The grey text under a box
says how many tests (and labs) holding it fixed costs, because a test needs a
value for every ticked parameter.

- **Physics** (K, %CW, temperature, O₂, H₂): ticked by default.
- **Measurement** (quality score, test duration): ticked by default. They describe
  how a test was run, not the steel or the water; holding them fixed keeps that
  influence out of the physical parameters. Tests without a duration drop out.
- **Water chemistry** (boron, lithium): not ticked by default. Many tests were run
  in pure water and have no B/Li values, so ticking them drops whole labs (most of
  GE Research's data, for example). A change in the result may then come from the
  different rows, not from the chemistry.
- **Added quantities**: the quantities you made yourself (🗂 Data → Add a quantity
  or Auto-fill properties). Not ticked by default. Some are not offered, with the
  reason shown:
  - made from CGR itself (e.g. CGR from crack length): that would be circular;
  - in exactly the same (or reverse) order as a parameter already there, such as
    temperature in kelvin or 1000/T against temperature: for a rank method they
    carry nothing new;
  - only one value in the data.

**Unticking does not remove a parameter from the results.** Its own row stays and
still shows its own link with CGR; unticking only stops it being taken out of the
*others*. **Reset to recommended** brings back the default ticks. When the choice
differs from the recommended one, the summary sentence and the table say so.

SO₄ and Cl are shown in the results but never held fixed: most tests have no value
for them.

## Spearman check

The same calculation with Spearman's ρ instead of Kendall's τ. If both have the
same sign, the result does not depend on the method chosen.

## What this cannot tell

A link is not a cause. It says *where to look*, not *why*. Parameters that were
never varied in the data (or only in one lab) cannot show a link at all, however
important they are in reality.
