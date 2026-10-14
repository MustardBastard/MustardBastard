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

## Coming later: checking a pattern with numbers

When we return to nondimensional analysis, the app will also *measure*
patterns instead of only showing them:

- **Pattern check:** fit a curve and measure how far points typically sit
  from it, for the raw quantities and for the unit-free combinations.
- **Held-out check:** hide one lab, fit the curve on the others, and test it
  on the hidden lab. A real pattern predicts labs it has never seen.
- **Traffic light:** 🟢 at least 10% tighter (and holds on hidden labs),
  🟡 no real change, 🔴 at least 10% looser.

Match 1 (see the Cave map) was judged this way.
