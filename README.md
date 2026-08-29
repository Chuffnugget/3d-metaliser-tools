# STL Flat-Surface Metal Texturer

`stl_flat_metal_texture.py` adds **real printable battered-metal geometry** to the large flat surfaces of an existing STL while trying to preserve detailed and curved geometry.

It was designed for things such as storage boxes, armour panels, industrial scenery, sci-fi crates, vehicle panels, bulkheads, doors, and similar models where the large flat areas should look worn, dented, scratched, gouged, or corroded, while skulls, emblems, rivets, curved corners, trim, and small details should remain intact.

This README describes the project as its initial public implementation rather than as an upgrade path from earlier releases.

The program works directly on mesh geometry. It does **not** create a Blender material or shader. The output STL contains the modified surface and is intended for 3D printing.

---

## Contents

- [What the program does](#what-the-program-does)
- [What it does not do](#what-it-does-not-do)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Interactive wizard](#interactive-wizard)
- [Recommended first workflow](#recommended-first-workflow)
- [Damage presets](#damage-presets)
- [Flat-surface detection](#flat-surface-detection)
- [Build-plate bottom protection](#build-plate-bottom-protection)
- [Thin-wall protection](#thin-wall-protection)
- [Local mesh refinement and triangle count](#local-mesh-refinement-and-triangle-count)
- [Damage controls](#damage-controls)
- [Advanced damage controls](#advanced-damage-controls)
- [Random seeds](#random-seeds)
- [CLI examples](#cli-examples)
- [Output and reports](#output-and-reports)
- [Understanding the console output](#understanding-the-console-output)
- [Troubleshooting](#troubleshooting)
- [Suggested starting configurations](#suggested-starting-configurations)
- [Limitations](#limitations)
- [Complete CLI reference](#complete-cli-reference)

---

# What the program does

The program performs the following pipeline:

1. Loads an STL mesh.
2. Detects connected groups of triangles which form genuinely planar surfaces.
3. Rejects surfaces which are too small or too narrow.
4. Detects and excludes the flat bottom/build-plate surface by default.
5. Locally refines only the eligible flat surfaces so there are enough vertices to represent physical damage.
6. Generates procedural metal damage:
   - broad unevenness,
   - shallow dents,
   - impacts,
   - scratches,
   - gouges,
   - corrosion pits.
7. Optionally measures local wall thickness before deforming a point.
8. Prevents deformation where the resulting wall would become thinner than the configured minimum.
9. Moves the selected flat-surface vertices inward.
10. Fades deformation to zero near the edge of a flat patch.
11. Exports a new STL.
12. Optionally writes a JSON report containing the exact settings and statistics.

The important difference from an ordinary displacement operation is that **non-flat geometry is not globally displaced or remeshed**.

---

# What it does not do

The program does not:

- apply a Blender material;
- add colour;
- add render-only bump mapping;
- texture every triangle in the STL;
- globally voxel-remesh the model;
- intentionally deform skulls, logos, curved surfaces, rivets, embossed decorations, etc.;
- guarantee that every malformed STL can be made printable;
- repair arbitrary non-manifold geometry;
- replace a final slicer/mesh validation step.

The output should still be checked in Blender, your slicer, or a mesh-repair tool before committing to a long print.

---

# Requirements

## Python

Python 3.10 or newer is recommended.

Check your version:

```bash
python3 --version
```

or on Windows:

```powershell
python --version
```

## Python packages

Install:

```bash
pip install numpy trimesh shapely rtree
```

The packages are used as follows:

| Package | Purpose |
|---|---|
| `numpy` | Mesh and vector calculations |
| `trimesh` | STL loading/exporting and mesh operations |
| `shapely` | 2D planar patch geometry and boundary calculations |
| `rtree` | Spatial acceleration for thin-wall ray casting |

`rtree` is only required when thin-wall protection is enabled, but thin-wall protection is **enabled by default**, so installing it is strongly recommended.

If you intentionally do not want thickness protection, you can run with:

```bash
--no-thickness-protection
```

---

# Installation

Put the script somewhere convenient, for example:

```text
3dMetaliser/
├── stl_flat_metal_texture.py
└── your_model.stl
```

Install dependencies:

```bash
python3 -m pip install numpy trimesh shapely rtree
```

On Windows, depending on your Python installation:

```powershell
py -m pip install numpy trimesh shapely rtree
```

or:

```powershell
python -m pip install numpy trimesh shapely rtree
```

No Blender installation is required to run the script.

---

# Quick start

The easiest way to use the program is the wizard.

Run:

```bash
python3 stl_flat_metal_texture.py
```

Then answer the questions. Pressing **Enter** accepts the value shown in square brackets.

For example:

```text
Input STL: crate.stl

Damage preset:
  1) subtle
  2) worn [default]
  3) battered
  4) abused
  5) brutal
  6) wrecked
  7) ruined
  8) catastrophic
  9) obliterated
Choice [2]:
```

The default preset is `worn`.

---

# Interactive wizard

Running the script with no arguments launches the wizard:

```bash
python3 stl_flat_metal_texture.py
```

You can also explicitly force wizard mode:

```bash
python3 stl_flat_metal_texture.py --wizard
```

The wizard covers:

- input STL,
- damage preset,
- flat-surface detection,
- build-plate protection,
- minimum resulting wall thickness,
- local surface resolution,
- triangle budget,
- overall damage intensity,
- individual damage categories,
- random seed,
- optional advanced parameters,
- output filename,
- JSON report.

The wizard uses sensible defaults. For an initial test, it is reasonable to accept most values and only change the preset.

---

# Recommended first workflow

For a complicated model, use the program in three stages.

## 1. Analyse the model first

Run a dry run:

```bash
python3 stl_flat_metal_texture.py model.stl --dry-run
```

This detects planar patches but does not modify the STL.

Look especially for:

```text
Eligible patches:
Bottom patches skipped:
Protect bottom:
Detected bottom Z:
```

## 2. Generate an obvious test

Use a stronger preset than you expect to need, such as:

```bash
python3 stl_flat_metal_texture.py model.stl \
  --preset brutal \
  --seed 12345 \
  -o model_test.stl
```

Open that STL and confirm that:

- large flat surfaces are visibly damaged;
- curved/detail areas remain intact;
- the build-plate bottom remains flat;
- thin walls have been protected.

## 3. Tune for the final print

Once the system is clearly hitting the right surfaces, reduce or increase the damage settings to taste.

Always keep an untouched source STL.

---

# Damage presets

There are nine presets, from light wear to intentionally absurd destruction:

| Preset | Approximate character |
|---|---|
| `subtle` | Slightly used/cast metal |
| `worn` | General battered industrial/military metal |
| `battered` | Clearly damaged, more dents and impacts |
| `abused` | Heavy long-term use |
| `brutal` | Strong deformation and much more damage |
| `wrecked` | Severe impacts, gouges and dents |
| `ruined` | Heavily destroyed surface |
| `catastrophic` | Extreme, very deep and dense damage |
| `obliterated` | Deliberately excessive stress-test level |

The five strongest levels are:

```text
brutal
wrecked
ruined
catastrophic
obliterated
```

## Maximum depth by preset

| Preset | Maximum combined damage depth |
|---|---:|
| subtle | 0.45 mm |
| worn | 0.70 mm |
| battered | 1.00 mm |
| abused | 1.35 mm |
| brutal | 1.75 mm |
| wrecked | 2.20 mm |
| ruined | 2.80 mm |
| catastrophic | 3.60 mm |
| obliterated | 4.80 mm |

These values are upper limits. Thin-wall protection can reduce or completely suppress damage locally.

Be careful with `catastrophic` and `obliterated` on thin printed parts.

---

# Flat-surface detection

The program is deliberately selective about what it calls a flat surface.

Default values:

```text
Maximum normal deviation:  0.75 degrees
Plane tolerance:           0.08 mm
Minimum flat area:         200 mm²
Minimum flat span:         8 mm
Edge margin:               3 mm
```

## `--flat-angle`

Default:

```text
0.75 degrees
```

Controls how much triangle normals may differ while still belonging to the same flat patch.

Smaller values are stricter.

Use a larger value if real flat panels are being split into too many pieces:

```bash
--flat-angle 1.25
```

Do not make this unnecessarily large or shallow curved surfaces may begin to be treated as planar.

---

## `--plane-tolerance`

Default:

```text
0.08 mm
```

Even when a surface is intended to be flat, STL conversion and Boolean operations can leave tiny positional differences.

This value controls how far vertices may deviate from the reference plane.

Example:

```bash
--plane-tolerance 0.15
```

Increase it carefully if obvious large flat faces are being missed.

---

## `--min-flat-area`

Default:

```text
200 mm²
```

This is one of the most useful controls.

A planar surface must be at least this large before the program considers texturing it.

Increasing it is a good way to avoid:

- small flat details on emblems;
- tops of rivets;
- tiny decorative plates;
- small flat regions in skulls;
- incidental planar fragments.

Example:

```bash
--min-flat-area 500
```

If a large panel is 10,000 mm² and a decorative detail is 30 mm², this filter separates them very effectively.

---

## `--min-flat-span`

Default:

```text
8 mm
```

Area alone is not enough. A long, skinny strip can have a surprisingly large area.

`min-flat-span` rejects planar regions whose narrow dimension is too small.

For example:

```bash
--min-flat-span 12
```

is useful if trim strips are being damaged.

---

## `--edge-margin`

Default:

```text
3 mm
```

Damage smoothly fades to zero near the perimeter of each detected flat patch.

This is important because the flat patch may meet:

- a bevel,
- skull geometry,
- a raised frame,
- a corner,
- rivets,
- an emblem,
- curved geometry.

A larger edge margin gives more protection around these transitions.

Example:

```bash
--edge-margin 5
```

The trade-off is that narrow panels may have very little remaining textured area.

---

# Build-plate bottom protection

Build-plate protection is **enabled by default**.

The program assumes:

```text
+Z = upward
-Z = toward the build plate
```

However, bottom detection does **not** rely on the STL's face-normal direction.

Imported and non-watertight STLs can have reversed/inconsistent normals, so detects the bottom using substantial horizontal planes rather than simply looking for a `-Z` normal.

## How it detects the bottom

The program:

1. finds eligible horizontal planar patches;
2. ignores tiny horizontal fragments when choosing the reference level;
3. finds the lowest substantial horizontal plane;
4. treats that as the build-plate plane;
5. excludes horizontal flat patches which are coplanar with that plane.

This avoids a common failure mode where one stray decorative vertex sits below the actual base.

## Wizard defaults

```text
Protect bottom/build-plate surface: Yes
Bottom plane coplanar tolerance:    0.60 mm
Horizontal tilt tolerance:          20 degrees
```

## CLI controls

Protection is already on by default:

```bash
--skip-bottom
```

Explicitly allow damage on the bottom:

```bash
--texture-bottom
```

Adjust the coplanar tolerance:

```bash
--bottom-tolerance 0.6
```

Adjust what counts as horizontal:

```bash
--bottom-normal-angle 20
```

## What to check

Before generating the model, the analysis should say something similar to:

```text
Bottom patches skipped:      1
Protect bottom:            True
Detected bottom Z:         0.000 mm
```

If you expect a flat base and it says:

```text
Bottom patches skipped: 0
```

do not assume the base is protected. Run a dry analysis and adjust the detection settings.

---

# Thin-wall protection

Thin-wall protection is enabled by default.

Its purpose is to stop a dent, gouge, scratch, or unevenness field from reducing a wall below a safe final thickness.

Default values:

```text
Minimum resulting wall thickness: 1.20 mm
Extra safety margin:              0.10 mm
Probe maximum:                   20.00 mm
Thickness mode:                   skip
```

## What "minimum resulting wall thickness" means

Suppose:

```text
original wall thickness = 1.50 mm
minimum wall thickness  = 1.20 mm
safety margin           = 0.10 mm
proposed dent            = 0.40 mm
```

Required protected thickness is:

```text
1.20 + 0.10 = 1.30 mm
```

The proposed dent would leave:

```text
1.50 - 0.40 = 1.10 mm
```

That is too thin.

With the default `skip` mode, that local deformation is removed.

---

## How thickness is measured

For a vertex about to be pushed inward, the program ray-casts into the original STL in the same direction as the deformation.

It looks for the first opposing, non-source surface.

That distance is treated as the local wall thickness.

The measurement is made against the **original input geometry**, before the procedural damage is applied.

---

## `skip` versus `clamp`

### `skip` — default

```bash
--thickness-mode skip
```

If a proposed deformation would leave the wall too thin, that point is left unchanged.

This is the safest behaviour and most closely matches:

> Do not transform areas where the resulting wall would be too thin.

### `clamp`

```bash
--thickness-mode clamp
```

Instead of discarding the damage entirely, the program reduces its depth until the minimum protected thickness is reached.

This can create a smoother transition in some models.

---

## Minimum wall thickness

Wizard default:

```text
1.2 mm
```

CLI:

```bash
--min-wall-thickness 1.2
```

Examples:

For a fairly sturdy FDM part:

```bash
--min-wall-thickness 1.2
```

For a model where you want to keep at least 2 mm of material:

```bash
--min-wall-thickness 2.0
```

Disable the feature completely:

```bash
--min-wall-thickness 0
```

or:

```bash
--no-thickness-protection
```

---

## Thickness safety margin

Default:

```text
0.10 mm
```

CLI:

```bash
--thickness-safety 0.1
```

The actual protected threshold is:

```text
minimum wall thickness + safety margin
```

For example:

```text
minimum = 1.20
safety  = 0.10
actual protected minimum = 1.30 mm
```

---

## Thickness probe distance

Default:

```text
20 mm
```

CLI:

```bash
--thickness-probe-max 20
```

This controls how far inward the program searches for the opposite wall.

The program automatically raises this value if necessary so it is at least:

```text
minimum wall
+ safety margin
+ maximum dent depth
+ 0.5 mm
```

This prevents a dangerously short probe from incorrectly treating a modestly thick wall as "no opposite wall found".

---

## `rtree` dependency

Thickness protection requires:

```bash
pip install rtree
```

If it is missing, the program deliberately stops instead of silently pretending thickness protection is active.

---

# Local mesh refinement and triangle count

A raw STL may represent a giant flat panel using only two huge triangles.

A physical dent cannot be represented properly unless there are vertices available to move.

The program therefore **subdivides eligible flat surfaces locally**.

It does not globally remesh the entire object.

## `--surface-resolution`

Default:

```text
1.5 mm
```

CLI:

```bash
--surface-resolution 1.5
```

This is the desired maximum edge size for refined flat surfaces.

Smaller values:

- preserve smaller damage,
- give smoother geometry,
- create more triangles,
- use more memory,
- take longer.

Larger values:

- create fewer triangles,
- run faster,
- are suitable for broad dents,
- may lose narrow scratches/pits.

Typical values:

| Value | Use |
|---:|---|
| 0.5 mm | Fine/heavy mesh |
| 0.75 mm | Detailed |
| 1.0 mm | Good general compromise |
| 1.5 mm | Default, practical for larger models |
| 2.0–3.0 mm | Broad dents only / low polygon budget |

---

## `--max-new-triangles`

Default:

```text
450000
```

CLI:

```bash
--max-new-triangles 450000
```

The program uses this as a budget for local refinement.

If the requested `surface-resolution` would generate too much geometry, the program automatically increases the effective edge size.

The analysis prints:

```text
Actual max edge: 1.734 mm
```

and may explain that it was increased to respect the triangle budget.

This exists specifically to stop large models from unexpectedly exploding into multi-million-triangle meshes.

---

# Damage controls

The normal wizard exposes six amount multipliers.

Default values in :

```text
Broad unevenness: 1.00
Dents:            1.00
Impacts:          0.70
Scratches:        0.35
Gouges:           0.20
Pitting:          0.10
```

These values affect the amount/quantity of each damage type.

Set a category to zero to disable it.

For example, mostly dented metal without corrosion:

```bash
--uneven-amount 1.3 \
--dent-amount 1.5 \
--impact-amount 0.5 \
--scratch-amount 0.2 \
--gouge-amount 0.15 \
--pit-amount 0
```

---

## Broad unevenness

Broad unevenness gives the surface a generally beaten, imperfect sheet-metal character rather than making every surface mathematically flat between individual impacts.

Controls:

```text
--uneven-amount
--uneven-amp
--uneven-scale
--secondary-amp
--secondary-scale
```

Large-scale unevenness creates broad shallow movement.

Secondary unevenness adds a smaller-scale variation on top.

---

## Dents

Dents are broad, generally smooth depressions.

Controls include:

```text
--dent-amount
--dent-density
--dent-size-min
--dent-size-max
--dent-depth-min
--dent-depth-max
```

Density is approximately specified per `100 x 100 mm` of eligible surface.

---

## Impacts

Impacts are smaller and more concentrated than broad dents.

Controls:

```text
--impact-amount
--impact-density
--impact-size-min
--impact-size-max
--impact-depth-min
--impact-depth-max
```

These are useful for dings, knocks, tool impacts, and similar damage.

---

## Scratches

Scratches are narrow curved/straight channels.

Controls:

```text
--scratch-amount
--scratch-density
--scratch-len-min
--scratch-len-max
--scratch-width-min
--scratch-width-max
--scratch-depth-min
--scratch-depth-max
--scratch-curvature
--scratch-direction-deg
--scratch-direction-bias
```

For FDM printing, extremely narrow scratches are often pointless. Use widths that your printer can physically reproduce.

---

## Gouges

Gouges are heavier, wider versions of scratches.

Controls:

```text
--gouge-amount
--gouge-density
--gouge-len-min
--gouge-len-max
--gouge-width-min
--gouge-width-max
--gouge-depth-min
--gouge-depth-max
--gouge-curvature
```

These are intended to look more like dragged or torn damage rather than hairline scratches.

---

## Pitting

Pitting creates small local depressions similar to corrosion or surface damage.

Controls:

```text
--pit-amount
--pit-density
--pit-size-min
--pit-size-max
--pit-depth-min
--pit-depth-max
```

Pitting can quickly make a model look noisy, so the normal  default amount is deliberately only `0.10`.

---

# Advanced damage controls

## `--intensity`

Default:

```text
1.0
```

Global multiplier for damage depth.

Example:

```bash
--intensity 1.5
```

This makes damage deeper without necessarily increasing its quantity.

If you want more events rather than simply deeper events, increase the individual `*-amount` or `*-density` values instead.

---

## `--max-depth`

Absolute hard limit on combined procedural deformation.

The preset supplies this automatically, but it can be overridden.

Example:

```bash
--preset wrecked --max-depth 1.5
```

Even if the preset tries to create a deeper combined deformation, it will be capped at 1.5 mm before wall-thickness protection is applied.

---

## Clustering

Default:

```text
clustering:     0.30
cluster radius: 18 mm
```

CLI:

```bash
--clustering 0.3
--cluster-radius 18
```

Higher clustering makes damage more likely to occur in groups rather than being evenly random across the surface.

This generally looks more natural than perfectly uniform distribution.

---

## Scratch direction bias

Controls:

```text
--scratch-direction-deg
--scratch-direction-bias
```

Example:

```bash
--scratch-direction-deg 15
--scratch-direction-bias 0.8
```

This makes scratches strongly prefer an angle around 15 degrees.

A bias near zero gives mostly random orientations.

---

# Random seeds

If you omit the seed, the program generates a random pattern.

To make a pattern repeatable:

```bash
--seed 12345
```

Running the same program version with the same model and same settings/seed gives a reproducible procedural layout.

The seed is also written to the JSON report.

This is useful when:

- a pattern is good but you want to adjust only the depth;
- you want matching variants;
- you need to recreate an STL later.

---

# CLI examples

## Default worn model

```bash
python3 stl_flat_metal_texture.py box.stl \
  -o box_metal.stl
```

---

## Dry-run only

```bash
python3 stl_flat_metal_texture.py box.stl \
  --dry-run
```

---

## Safer filtering for detailed models

```bash
python3 stl_flat_metal_texture.py box.stl \
  --dry-run \
  --min-flat-area 400 \
  --min-flat-span 12 \
  --edge-margin 4
```

---

## Heavy battered metal

```bash
python3 stl_flat_metal_texture.py box.stl \
  --preset brutal \
  --seed 12345 \
  -o box_brutal.stl
```

---

## Very heavy damage but preserve at least 2 mm wall

```bash
python3 stl_flat_metal_texture.py box.stl \
  --preset wrecked \
  --min-wall-thickness 2.0 \
  --thickness-safety 0.15 \
  --thickness-mode skip \
  -o box_wrecked_safe.stl
```

---

## Deep damage but clamp rather than remove unsafe dents

```bash
python3 stl_flat_metal_texture.py box.stl \
  --preset ruined \
  --min-wall-thickness 1.5 \
  --thickness-safety 0.1 \
  --thickness-mode clamp \
  -o box_ruined_clamped.stl
```

---

## Mostly broad dents with little fine noise

```bash
python3 stl_flat_metal_texture.py box.stl \
  --preset battered \
  --uneven-amount 1.5 \
  --dent-amount 1.5 \
  --impact-amount 0.4 \
  --scratch-amount 0.1 \
  --gouge-amount 0.1 \
  --pit-amount 0 \
  -o box_dinged.stl
```

---

## Strong scratches and gouges

```bash
python3 stl_flat_metal_texture.py box.stl \
  --preset battered \
  --dent-amount 0.5 \
  --impact-amount 0.5 \
  --scratch-amount 1.5 \
  --gouge-amount 1.8 \
  --pit-amount 0.1 \
  -o box_scraped.stl
```

---

## Limit polygon growth

```bash
python3 stl_flat_metal_texture.py large_model.stl \
  --surface-resolution 1.0 \
  --max-new-triangles 300000 \
  -o large_model_metal.stl
```

The program may automatically use a coarser effective edge size if required.

---

## Disable bottom protection

Not normally recommended:

```bash
python3 stl_flat_metal_texture.py model.stl \
  --texture-bottom \
  -o model_all_faces.stl
```

---

## Disable thin-wall protection

```bash
python3 stl_flat_metal_texture.py model.stl \
  --no-thickness-protection \
  -o model_unprotected.stl
```

---

# Output and reports

If the input is:

```text
crate.stl
```

the default wizard output is based on the input filename, for example:

```text
crate_metal_textured.stl
```

You can always specify your own output:

```bash
-o crate_final.stl
```

## JSON report

A report is written by default.

It records information such as:

- program version;
- all configuration values;
- input triangle and vertex counts;
- whether the input is watertight;
- output triangle and vertex counts;
- detected planar patches;
- actual mesh resolution;
- maximum damage depth;
- mean damage depth;
- feature counts;
- thickness-protection statistics;
- random seed.

Disable it with:

```bash
--no-report
```

The report is particularly useful when you want to reproduce a successful model later.

---

# Understanding the console output

A typical analysis section may look like:

```text
PLANAR PATCH ANALYSIS

Input triangles:       150,820
Input vertices:         75,137
Input watertight:        False
Planar patches found:    87,903
Eligible patches:           34
Bottom patches skipped:      1
Eligible area:         421,000.0 mm²
Min flat area:             250 mm²
Min flat span:               8 mm
Edge fade:                   3 mm
Protect bottom:            True
Detected bottom Z:         0.000 mm
Actual max edge:           1.65 mm
Thin-wall protection:      True
Minimum final wall:         1.2 mm
Thickness safety:           0.1 mm
Thickness behavior:        skip
```

Important points:

### `Eligible patches`

How many flat regions will be textured.

If this is unexpectedly huge, increase:

```text
min-flat-area
min-flat-span
```

### `Bottom patches skipped`

Should normally be at least `1` when the model has a flat build-plate bottom.

### `Detected bottom Z`

The horizontal level selected as the base.

### `Actual max edge`

The actual refinement size after triangle-budget adjustment.

### `Thin-wall protection`

Should say `True` if you expect wall safety.

---

During damage:

```text
patch 4/12 ID=27: 8,412 tris, max depth 1.600 mm,
                  thin protected 391, clamped 0
```

This means 391 candidate vertices were prevented from moving because doing so would violate the wall-thickness requirement.

At the end:

```text
Maximum dent depth:    1.600 mm
Mean textured depth:   0.140 mm
Thin vertices skipped: 1,284
```

---

# Troubleshooting

## "It did nothing"

Check the console.

If:

```text
Eligible patches: 0
```

the flat detector rejected everything.

Try:

```bash
--min-flat-area 100
--min-flat-span 4
--flat-angle 1.0
--plane-tolerance 0.15
```

Do not loosen everything at once unless necessary.

If patches are eligible but the surface barely changes, try an obvious diagnostic:

```bash
--preset brutal --intensity 1.5
```

If that is visible, the program is working and your previous settings were simply subtle.

---

## Too much detailed geometry is being textured

Increase:

```bash
--min-flat-area
```

and/or:

```bash
--min-flat-span
```

For example:

```bash
--min-flat-area 500 --min-flat-span 15
```

Also consider increasing:

```bash
--edge-margin 5
```

---

## Large real panels are not detected

Carefully loosen:

```bash
--flat-angle 1.25
```

or:

```bash
--plane-tolerance 0.15
```

If the panel was poorly triangulated during STL creation, it may not be exactly planar.

---

## The bottom is still being textured

Run a dry run:

```bash
python3 stl_flat_metal_texture.py model.stl --dry-run
```

Check:

```text
Bottom patches skipped:
Detected bottom Z:
```

If the skipped count is zero, try a larger coplanar tolerance:

```bash
--bottom-tolerance 1.0
```

If the base is slightly tilted:

```bash
--bottom-normal-angle 30
```

Be careful: overly broad values may classify other low horizontal surfaces as part of the build-plate base.

---

## The model becomes too thin

Raise:

```bash
--min-wall-thickness
```

For example:

```bash
--min-wall-thickness 2
```

Keep:

```bash
--thickness-mode skip
```

for the safest behaviour.

You can also increase:

```bash
--thickness-safety 0.2
```

---

## Missing `rtree`

Error:

```text
Thin-wall protection is enabled, but Python package 'rtree' is missing
```

Install:

```bash
pip install rtree
```

or run without thickness protection:

```bash
--no-thickness-protection
```

---

## Triangle count is too high

Increase:

```bash
--surface-resolution
```

For example:

```bash
--surface-resolution 2.0
```

or reduce:

```bash
--max-new-triangles 250000
```

Remember that very small scratches cannot be represented accurately by a very coarse mesh.

---

## Damage looks like noisy stone instead of metal

Reduce:

```text
pit amount
scratch amount
secondary unevenness
```

and emphasize:

```text
broad unevenness
dents
```

For example:

```bash
--uneven-amount 1.5 \
--dent-amount 1.5 \
--impact-amount 0.4 \
--scratch-amount 0.1 \
--gouge-amount 0.1 \
--pit-amount 0
```

---

## Damage is too uniform

Increase clustering:

```bash
--clustering 0.6
```

and possibly:

```bash
--cluster-radius 25
```

---

## Scratches are not visible after printing

They may be too narrow or shallow for the printer.

Increase widths and depths:

```bash
--scratch-width-min 1.5 \
--scratch-width-max 3 \
--scratch-depth-min 0.2 \
--scratch-depth-max 0.45
```

Remember that STL detail still has to survive slicing, nozzle diameter/resin pixel size, layer height, and physical printing.

---

## Output is not watertight

The program is not a universal mesh repair tool.

If the input was already open/non-manifold, the output may remain open/non-manifold.

Validate the result in:

- Blender 3D Print Toolbox;
- PrusaSlicer;
- OrcaSlicer;
- Bambu Studio;
- Cura;
- Meshmixer or another mesh repair tool.

Do not assume that a successful script run means the STL is automatically printable.

---

# Suggested starting configurations

## FDM — sturdy storage box

```text
Preset:               battered
Minimum flat area:    300 mm²
Minimum flat span:     10 mm
Edge margin:            3 mm
Surface resolution:   1.5 mm
Max new triangles: 450000
Minimum wall:          1.2 mm
Thickness safety:      0.1 mm
Mode:                  skip
```

Amounts:

```text
Uneven:   1.2
Dents:    1.3
Impacts:  0.6
Scratches:0.25
Gouges:   0.2
Pits:     0.05
```

---

## FDM — strongly damaged industrial prop

```text
Preset: wrecked
Minimum wall: 1.5–2.0 mm
Thickness mode: skip
Surface resolution: 1.0–1.5 mm
```

Keep bottom protection on.

---

## Mostly hammered/dinged metal

```bash
--preset battered \
--uneven-amount 1.8 \
--dent-amount 1.6 \
--impact-amount 0.5 \
--scratch-amount 0.05 \
--gouge-amount 0.05 \
--pit-amount 0
```

---

## Old scraped crate

```bash
--preset battered \
--uneven-amount 0.8 \
--dent-amount 0.7 \
--impact-amount 0.5 \
--scratch-amount 1.4 \
--gouge-amount 1.2 \
--pit-amount 0.15
```

---

## Corroded abandoned metal

```bash
--preset abused \
--uneven-amount 1 \
--dent-amount 0.8 \
--impact-amount 0.5 \
--scratch-amount 0.4 \
--gouge-amount 0.4 \
--pit-amount 1.5
```

---

# Limitations

## Flat surfaces only

The system intentionally targets planar patches.

It does not currently wrap the same procedural texture around arbitrary curved surfaces.

That is deliberate: earlier displacement-style approaches can expose the STL's triangulation and destroy detailed curves.

---

## Thickness ray casting assumes a meaningful opposite wall

Thin-wall detection searches inward from the surface.

Very unusual geometry, internal overlapping shells, self-intersections, or badly malformed STLs can confuse the measurement.

Always inspect the result.

---

## Very thin features cannot survive printing

The program can mathematically create narrow scratches smaller than your printer can reproduce.

Geometry resolution and physical print resolution are separate limitations.

---

## Extreme presets are extreme

`catastrophic` and especially `obliterated` can produce deformation several millimetres deep.

Thin-wall protection greatly reduces the risk of punching through a wall, but those presets can still radically change silhouettes on large safe areas.

Use them intentionally.

---

## Surface-resolution trade-off

There is no way to create very fine physical geometry without triangles.

A 300 × 300 mm panel at extremely fine resolution can become enormous.

Use the triangle budget and print only detail that your printer can actually reproduce.

---

# Complete CLI reference

Get the authoritative list from the script itself:

```bash
python3 stl_flat_metal_texture.py --help
```

The available options are grouped below.

## General

```text
input
-o, --output
--wizard
--preset
--seed
--dry-run
--no-report
```

## Flat-surface detection

```text
--flat-angle
--plane-tolerance
--min-flat-area
--min-flat-span
--edge-margin
```

## Build-plate protection

```text
--skip-bottom
--texture-bottom
--bottom-tolerance
--bottom-normal-angle
```

## Thin-wall protection

```text
--min-wall-thickness
--thickness-safety
--thickness-probe-max
--thickness-ray-epsilon
--thickness-mode skip|clamp
--no-thickness-protection
```

## Mesh density

```text
--surface-resolution
--max-new-triangles
```

## Global damage

```text
--max-depth
--intensity
--uneven-amount
--dent-amount
--impact-amount
--scratch-amount
--gouge-amount
--pit-amount
--clustering
--cluster-radius
```

## Unevenness

```text
--uneven-amp
--uneven-scale
--secondary-amp
--secondary-scale
```

## Dents

```text
--dent-density
--dent-size-min
--dent-size-max
--dent-depth-min
--dent-depth-max
```

## Impacts

```text
--impact-density
--impact-size-min
--impact-size-max
--impact-depth-min
--impact-depth-max
```

## Scratches

```text
--scratch-density
--scratch-len-min
--scratch-len-max
--scratch-width-min
--scratch-width-max
--scratch-depth-min
--scratch-depth-max
--scratch-curvature
--scratch-direction-deg
--scratch-direction-bias
```

## Gouges

```text
--gouge-density
--gouge-len-min
--gouge-len-max
--gouge-width-min
--gouge-width-max
--gouge-depth-min
--gouge-depth-max
--gouge-curvature
```

## Pitting

```text
--pit-density
--pit-size-min
--pit-size-max
--pit-depth-min
--pit-depth-max
```

---

# Default values

These are the program's normal non-preset structural defaults:

| Setting | Default |
|---|---:|
| Flat angle | 0.75° |
| Plane tolerance | 0.08 mm |
| Minimum flat area | 200 mm² |
| Minimum flat span | 8 mm |
| Edge margin | 3 mm |
| Protect bottom | Yes |
| Bottom coplanar tolerance | 0.60 mm |
| Bottom horizontal tolerance | 20° |
| Minimum resulting wall thickness | 1.20 mm |
| Thickness safety | 0.10 mm |
| Thickness probe maximum | 20 mm |
| Thickness ray epsilon | 0.03 mm |
| Thickness behaviour | `skip` |
| Surface resolution | 1.50 mm |
| Maximum new triangles | 450,000 |
| Intensity | 1.0 |
| Uneven amount | 1.0 |
| Dent amount | 1.0 |
| Impact amount | 0.7 |
| Scratch amount | 0.35 |
| Gouge amount | 0.20 |
| Pit amount | 0.10 |
| Clustering | 0.30 |
| Cluster radius | 18 mm |

The selected damage preset supplies the normal feature dimensions, densities, depth ranges, and maximum damage depth.

---

# Final advice

Keep the original STL and treat the generated version as disposable output.

For a new model:

1. Run `--dry-run`.
2. Confirm the correct flat patches are eligible.
3. Confirm `Bottom patches skipped` is sensible.
4. Keep thin-wall protection enabled.
5. Generate a visibly strong test.
6. Inspect it in Blender or your slicer.
7. Tune damage amounts.
8. Slice and check wall behaviour.
9. Print a representative section before committing to a very large print.

For most practical FDM models, broad dents and unevenness survive printing much better than microscopic pitting or hairline scratches. Use the geometry budget on features that will actually be visible in plastic.
