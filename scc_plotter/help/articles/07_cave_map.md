# Cave map

What each test taught us. Add a section after every test: the idea, the
result, and the lesson.

> Version 5 removed the "Test an idea" page; nondimensional analysis comes back
> later (after we find the extra parameters we need). Match 1 below was done with
> version 4 and is kept as knowledge.

## Match 1 — strength and temperature scales

**Idea.** Crack speed is set by how hard the crack is pulled compared with the
steel's strength (K/σy), and by a thermally activated rate (Arrhenius).

**Combinations.** CGR·d/D against K/(σy·√d), with Q/RT as the third.

**Result (Mainstream rows).** 🟡 No real change: 0.637 → 0.634 decades;
hidden labs 0.674 → 0.686. On all low-oxygen rows it got worse.

**Splitting the match into its two halves:**

| Plot | Scatter | Hidden labs |
|---|---|---|
| Raw CGR vs K | 0.637 | 0.674 |
| Temperature only: CGR·e^(Q/RT) vs K | **0.583** | **0.610** |
| Strength only: CGR vs K/σy | 0.695 | 0.763 |

**Lessons.**

- 🔦 **Torch:** the temperature number Q/RT helps, and the gain holds on
  hidden labs.
- 🚧 **Dead end:** dividing K by yield strength is the wrong way round. In the
  data, crack speed *rises* with yield strength, but K/σy puts strength
  underneath. So "plastic zone size" is not what controls growth; strength
  must act as a driver (for example through the crack-tip strain rate).

**Open question for Match 2.** How should strength enter: as a driver, not as
a measuring stick for K?
