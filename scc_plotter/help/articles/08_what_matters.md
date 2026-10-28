# What matters: reading the 📊 page

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

## The two switches

**Remove measurement effects (quality score, test duration).** These describe
how a test was run, not the steel or the water. On: their influence is taken out
before the physical parameters are judged. Rows without a test duration drop out.

**Remove water chemistry (boron, lithium).** Many tests were run in pure water and
have no B/Li values. On: those rows drop out, and with them whole labs (most of
GE Research's data, for example). Watch the row and lab counts under the switch:
a change in the result may come from the different rows, not from the chemistry.

## Spearman check

The same calculation with Spearman's ρ instead of Kendall's τ. If both have the
same sign, the result does not depend on the method chosen.

## What this cannot tell

A link is not a cause. It says *where to look*, not *why*. Parameters that were
never varied in the data (or only in one lab) cannot show a link at all, however
important they are in reality.
