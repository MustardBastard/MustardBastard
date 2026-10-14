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

## three_d | Two drivers at once: 3D

The **3D plot** puts crack speed **up**, K **across** and cold work in
**depth**, so you see two drivers at the same time. Colour adds a fourth: the
lab.

Drag to rotate it. 3D is good for spotting a direction; confirm what you see
with a normal 2D plot, because points can hide behind each other.

## data_area | The Data page

**Data** shows who measured what (coverage), the raw table, and lets you add
quantities that are not in the Excel file: constants, formulas, or a value
per material (like elastic modulus).

## learn | The Learn page

**Learn** has short articles: the basics, dimensional analysis from zero,
reading results, what the research says, our method, traps, and the
**Cave map** of what earlier tests taught us.

You can restart this tutorial anytime with **"? Tutorial"** in the sidebar.
