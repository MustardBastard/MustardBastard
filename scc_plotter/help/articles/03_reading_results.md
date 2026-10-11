# Reading the results

## Log axes and decades

Crack speeds in the database range from about 10⁻¹⁰ to 10⁻⁵ mm/s, a range of
100 000×. On a normal axis almost every point would be squashed near zero, so
the app uses **logarithmic axes**: each step along the axis multiplies by 10.

One such step is called a **decade**.

| Scatter | Points typically sit… |
|---|---|
| 0.1 decades | ×1.3 from the curve |
| 0.3 decades | ×2 from the curve |
| 0.5 decades | ×3 from the curve |
| 1.0 decade | ×10 from the curve |

On log-log axes, a power law (y = a·xⁿ) is a straight line, and its slope is n.

## The pattern check

The app fits a curve through the points and measures how far they typically
sit from it. It does this twice, on exactly the same rows:

- for the **raw** plot (for example CGR against K), and
- for the **unit-free combinations** of your idea.

If the combinations make the points sit closer to the curve, your idea
explains part of the scatter.

## The held-out check

Fitting a curve to points always makes it look a bit better than it really
is. So the app also hides one lab, fits the curve on all the others, and
measures how well it predicts the hidden lab. Then it does the same for every
other lab.

A real pattern predicts labs it has never seen. A lucky one does not.

## The traffic light

| Light | Meaning |
|---|---|
| 🟢 Pattern found | At least 10% tighter, and it also holds on hidden labs. A torch. |
| 🟡 No real change | Within ±10%. The idea explains nothing new. |
| 🔴 Worse | At least 10% looser. The idea points the wrong way. A dead end, and a lesson. |

## Constants never help

Multiplying by a fixed number (the same in every row) only moves the axes.
Both checks are built so that a constant cannot change them. That is why the
app marks constants as "shifts axes only".
