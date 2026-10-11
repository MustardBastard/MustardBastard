# Tutorial

Each step starts with "## step-id | Title". The step ids are linked to actions
in ui/tutorial.py (for example "open the Look page"). The text can be edited
freely.

## welcome | Welcome

This app helps you look for patterns in **924 crack growth measurements** of
stainless steel in hot reactor water, from 22 labs.

The tutorial takes about 3 minutes. Each step changes the screen to show you
something. Press **Next** to start.

## which_data | Which data?

The **sidebar on the left** decides *which rows* you look at.

The box **"Only PWR Mainstream Data"** keeps the 265 rows that the official
report (MRP-458) used. We have ticked it for you, so the rest of the tour uses
those rows. Everything on screen follows the sidebar.

## first_plot | Your first plot

This is the most famous relationship: **crack speed (CGR)** against **how hard
the crack is pulled (K)**.

Both axes are **logarithmic**: each step multiplies by 10, because crack
speeds span a range of 100 000×. Hover over a point to see where it came from.

## lab_effect | The lab effect

Now each colour is a **lab**. Notice the clumps: labs sit in different places,
even for similar K.

Keep this in mind. A lot of the scatter is "who measured it", not physics.

## every_param | Quick screening

This view plots crack speed against **every parameter at once**. It is the
fastest way to get a first gist of what might matter.

## match_idea | Testing an idea: a match

A **match** is one small idea, tested on its own.

Match 1's idea: crack speed depends on the pull K *compared with the steel's
strength*, and on temperature. We have set it up for you.

## match_vars | Step 2: quantities and their units

Here are the quantities in the idea. For each one, the app reads its unit and
breaks it into **ingredients**: mass M, length L, time T, temperature Θ and
amount N.

Rows marked "constant" are the same for every measurement. They only move the
axes and can never make a pattern tighter.

## match_groups | Step 3: unit-free combinations

The app combines the quantities so that every ingredient cancels, leaving
**pure numbers** (π groups).

8 quantities − 5 ingredients = **3 combinations**. The **measuring sticks**
are the quantities everything else is compared against.

Press **Next** and the app will create the combinations and run the check.

## match_verdict | Step 4: the verdict

The traffic light compares the combinations with the raw plot, on the same
rows:

- 🟢 **Pattern found**: tighter, and holds on labs it never saw
- 🟡 **No real change**
- 🔴 **Worse**: the idea points the wrong way

Match 1 gives 🟡. The Cave map (Learn page) explains why. Half of the idea
helps and half hurts.

## data_area | The Data page

**Data** shows who measured what (coverage), the raw table, and lets you add
quantities that are not in the Excel file: constants, formulas, or a value
per material (like elastic modulus).

## learn | The Learn page

**Learn** has short articles: the basics, dimensional analysis from zero,
reading results, what the research says, our method, traps, and the
**Cave map** of what each match taught us.

You can restart this tutorial anytime with **"? Tutorial"** in the sidebar.
