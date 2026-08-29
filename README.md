# 3D Metaliser Tools

3D Metaliser Tools is a pair of Python command-line/wizard utilities for adding **physical, printable battered-metal damage** to STL models.

The repository currently contains:

```text
3dMetaliser.py
3dMetaliserBlock.py
README.md
```

The two programs solve different jobs:

| Program | Purpose |
|---|---|
| `3dMetaliser.py` | Detect large flat surfaces on an existing STL and physically deform those surfaces with dents, impacts, scratches, gouges, pitting and broad metal unevenness. |
| `3dMetaliserBlock.py` | Generate a separate watertight negative damage-stamp STL which can be Boolean-subtracted from another model. |

Both tools assume STL dimensions are in **millimetres**. STL itself does not store units, so make sure the source model is already at the intended mm scale.

---

## Requirements

Python 3.10+ is recommended.

### `3dMetaliser.py`

Install:

```bash
python -m pip install numpy trimesh shapely rtree
```

or on systems where Python 3 is invoked as `python3`:

```bash
python3 -m pip install numpy trimesh shapely rtree
```

Packages used:

- `numpy` — mesh/vector calculations
- `trimesh` — STL loading, mesh handling and export
- `shapely` — planar patch outlines and edge margins
- `rtree` — ray acceleration used by thin-wall protection

`rtree` is required when thin-wall protection is enabled. Thin-wall protection is enabled by default.

### `3dMetaliserBlock.py`

No third-party packages are required. It uses only the Python standard library.

---

# 1. `3dMetaliser.py`

`3dMetaliser.py` modifies an existing STL.

It is intended for models where large sheet-metal / armour / box surfaces should become battered while small detailed geometry such as skulls, emblems, rivets, trim and curved surfaces should remain largely untouched.

The program does **not** globally voxel-remesh the model and does **not** use a global Boolean operation. Instead it:

1. loads the STL;
2. detects connected planar patches;
3. rejects patches which are too small or narrow;
4. excludes the build-plate bottom by default;
5. locally subdivides eligible flat patches;
6. procedurally generates metal damage;
7. optionally checks local wall thickness;
8. moves only the eligible patch vertices inward;
9. exports a new STL;
10. optionally writes a JSON report.

## Quick start

Launch the interactive wizard:

```bash
python 3dMetaliser.py
```

or:

```bash
python3 3dMetaliser.py
```

You can also force wizard mode:

```bash
python 3dMetaliser.py --wizard
```

The wizard asks for the input STL and then walks through the available settings.

Press **Enter** to accept the displayed default.

---

## Basic command-line use

```bash
python 3dMetaliser.py model.stl
```

If `-o` is not supplied, the current program creates:

```text
model_metal_textured_v2.stl
```

Example with an explicit output filename:

```bash
python 3dMetaliser.py model.stl \
  --preset battered \
  -o model_metal.stl
```

Windows PowerShell can use the same command on one line:

```powershell
python 3dMetaliser.py model.stl --preset battered -o model_metal.stl
```

---

## Damage presets

`3dMetaliser.py` includes these presets:

```text
subtle
worn
battered
abused
brutal
wrecked
ruined
catastrophic
obliterated
```

The default preset is:

```text
worn
```

The preset supplies the normal feature densities, sizes and depths. You can then override individual settings from the wizard or command line.

For example:

```bash
python 3dMetaliser.py model.stl \
  --preset wrecked \
  --intensity 1.2 \
  --max-depth 1.8 \
  -o model_wrecked.stl
```

---

## Damage types

The procedural field can contain:

- broad unevenness;
- broad dents;
- smaller impacts/dings;
- scratches;
- gouges;
- pitting/corrosion.

The normal amount controls are:

```text
--uneven-amount
--dent-amount
--impact-amount
--scratch-amount
--gouge-amount
--pit-amount
```

Set an amount to `0` to disable that category.

Example focused on broad denting rather than noisy surface damage:

```bash
python 3dMetaliser.py model.stl \
  --preset battered \
  --uneven-amount 1.5 \
  --dent-amount 1.5 \
  --impact-amount 0.5 \
  --scratch-amount 0.1 \
  --gouge-amount 0.1 \
  --pit-amount 0 \
  -o model_dinged.stl
```

---

## Flat-surface detection

Default detection settings:

| Setting | Default |
|---|---:|
| Maximum normal deviation | `0.75°` |
| Plane tolerance | `0.08 mm` |
| Minimum flat patch area | `200 mm²` |
| Minimum flat span | `8 mm` |
| Edge fade margin | `3 mm` |

### Minimum flat area

```text
--min-flat-area 200
```

Raise this when small decorative flat regions are being affected.

Example:

```bash
--min-flat-area 500
```

### Minimum flat span

```text
--min-flat-span 8
```

This rejects long narrow strips which may have enough total area but are not really large panels.

### Flat angle

```text
--flat-angle 0.75
```

Increase slightly if a genuinely flat panel has tiny normal inconsistencies.

### Plane tolerance

```text
--plane-tolerance 0.08
```

Increase carefully if STL conversion has made a nominally flat panel slightly uneven.

### Edge margin

```text
--edge-margin 3
```

Damage fades to zero over this distance around the perimeter of each eligible patch.

Increasing it gives more clearance around trim, bevels and detailed geometry.

---

## Build-plate bottom protection

Bottom protection is enabled by default.

The detector finds substantial horizontal planar patches and identifies the lowest substantial horizontal plane as the build-plate surface.

Default settings:

```text
Protect bottom:          yes
Bottom tolerance:        0.6 mm
Horizontal angle limit:  20 degrees
```

Explicitly enable protection:

```bash
--skip-bottom
```

Allow the bottom to be textured:

```bash
--texture-bottom
```

Adjust detection:

```bash
--bottom-tolerance 0.8
--bottom-normal-angle 20
```

During analysis, check the console output:

```text
Bottom patches skipped:
Protect bottom:
Detected bottom Z:
```

If you expect a flat base and `Bottom patches skipped` is `0`, do not assume the base has been protected.

---

## Thin-wall protection

Thin-wall protection is enabled by default.

Defaults:

| Setting | Default |
|---|---:|
| Minimum resulting wall thickness | `1.2 mm` |
| Additional safety margin | `0.1 mm` |
| Maximum probe distance | `20 mm` |
| Ray epsilon | `0.03 mm` |
| Behaviour | `skip` |

The configured protected threshold is therefore normally:

```text
1.2 mm + 0.1 mm = 1.3 mm
```

CLI example:

```bash
python 3dMetaliser.py model.stl \
  --min-wall-thickness 1.5 \
  --thickness-safety 0.1 \
  --thickness-mode skip \
  -o model_safe.stl
```

Modes:

```text
skip
```

leaves a proposed unsafe vertex unchanged.

```text
clamp
```

reduces the deformation to the calculated safe depth.

Disable the feature:

```bash
--no-thickness-protection
```

or:

```bash
--min-wall-thickness 0
```

### Important limitation

The thickness system in the current `3dMetaliser.py` is a **best-effort pre-deformation ray test, not a guarantee that the final STL cannot contain a hole**.

It casts inward from candidate vertices and uses the first non-source triangle hit as the local wall thickness. If the opposite wall is also an eligible textured patch, the available deformation budget is split between the two sides.

However, if no valid opposing hit is found within the probe distance, the current implementation does not treat that ray miss as an automatic failure. Open, non-manifold, intersecting or unusual STL topology can therefore defeat the check.

For thin or critical parts, inspect the generated STL in your slicer/mesh checker before printing.

---

## Local subdivision and triangle budget

A large flat STL panel may consist of only two triangles. It needs additional vertices before dents can physically exist.

The program therefore performs conforming local refinement.

Defaults:

```text
Desired maximum triangle edge: 1.5 mm
Approx maximum new triangles: 450000
```

Controls:

```text
--surface-resolution
--max-new-triangles
```

Smaller `--surface-resolution` values produce finer geometry but many more triangles.

Example:

```bash
--surface-resolution 1.0 --max-new-triangles 600000
```

If the requested resolution would exceed the approximate triangle budget, the program automatically uses a larger effective edge size.

The analysis reports:

```text
Actual max edge:
```

---

## Dry run

Use a dry run to inspect which surfaces will be selected without modifying the mesh:

```bash
python 3dMetaliser.py model.stl --dry-run
```

This is useful when tuning:

```text
--flat-angle
--plane-tolerance
--min-flat-area
--min-flat-span
--edge-margin
--bottom-tolerance
--bottom-normal-angle
```

A JSON report is still written unless `--no-report` is supplied.

---

## Random seeds

The wizard generates a random seed unless you enter one.

For repeatable damage:

```bash
--seed 12345
```

Using the same input, settings and seed makes it possible to reproduce the same procedural layout.

---

## JSON report

Reports are enabled by default.

For an output such as:

```text
model_metal.stl
```

the report filename is:

```text
model_metal_report.json
```

Disable reports with:

```bash
--no-report
```

The report includes configuration, mesh statistics, patch statistics, actual surface resolution and procedural damage information.

---

## Useful examples

### Normal battered-metal pass

```bash
python 3dMetaliser.py model.stl \
  --preset battered \
  --min-flat-area 250 \
  --min-flat-span 8 \
  --edge-margin 3 \
  --surface-resolution 1.5 \
  --max-new-triangles 450000 \
  -o model_battered.stl
```

### Strong damage with thicker-wall protection

```bash
python 3dMetaliser.py model.stl \
  --preset brutal \
  --min-wall-thickness 2.0 \
  --thickness-safety 0.15 \
  --thickness-mode skip \
  -o model_brutal.stl
```

### Mostly dents, almost no pitting

```bash
python 3dMetaliser.py model.stl \
  --preset battered \
  --uneven-amount 1.4 \
  --dent-amount 1.5 \
  --impact-amount 0.5 \
  --scratch-amount 0.15 \
  --gouge-amount 0.10 \
  --pit-amount 0 \
  -o model_dented.stl
```

### Diagnostic heavy pass

```bash
python 3dMetaliser.py model.stl \
  --preset brutal \
  --intensity 1.5 \
  --max-depth 1.2 \
  --seed 12345 \
  -o model_test.stl
```

---

## Full `3dMetaliser.py` options

The authoritative option list is always available from:

```bash
python 3dMetaliser.py --help
```

Main groups include:

### General

```text
input
-o / --output
--wizard
--preset
--seed
--dry-run
--no-report
```

### Flat detection

```text
--flat-angle
--plane-tolerance
--min-flat-area
--min-flat-span
--edge-margin
```

### Bottom protection

```text
--skip-bottom
--texture-bottom
--bottom-tolerance
--bottom-normal-angle
```

### Thin-wall protection

```text
--min-wall-thickness
--thickness-safety
--thickness-probe-max
--thickness-ray-epsilon
--thickness-mode skip|clamp
--no-thickness-protection
```

### Mesh refinement

```text
--surface-resolution
--max-new-triangles
```

### Global damage

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

### Detailed damage parameters

The program also exposes individual density, size, width, length, depth, curvature and directional controls for dents, impacts, scratches, gouges and pits. Use:

```bash
python 3dMetaliser.py --help
```

for the exact current names.

---

# 2. `3dMetaliserBlock.py`

`3dMetaliserBlock.py` creates a **standalone watertight negative damage stamp**.

Instead of modifying an existing STL automatically, it generates a rectangular cutter which can be positioned against a panel and Boolean-subtracted manually in Blender, CAD software or another mesh editor.

The coordinate convention is:

```text
Target surface plane: Z = 0
Damage/cutter depth:  -Z
Backing block:        +Z
```

---

## Quick start

Run the wizard:

```bash
python 3dMetaliserBlock.py
```

or:

```bash
python3 3dMetaliserBlock.py
```

The wizard asks for:

- stamp width and height;
- preset;
- surface resolution;
- backing thickness;
- edge fade;
- minimum printable feature width;
- maximum damage depth;
- global intensity;
- damage-category amounts;
- random seed;
- optional advanced controls;
- output filename;
- JSON sidecar;
- binary or ASCII STL.

Default output:

```text
metal_damage_stamp.stl
```

---

## Block presets

`3dMetaliserBlock.py` currently includes:

```text
subtle
worn
battered
abused
```

Default:

```text
worn
```

These presets are independent of the larger preset list in `3dMetaliser.py`.

---

## Block defaults

| Setting | Default |
|---|---:|
| Width | `100 mm` |
| Height | `100 mm` |
| Grid spacing | `0.5 mm` |
| Backing thickness | `2 mm` |
| Edge fade | `5 mm` |
| Minimum printable feature | `0.4 mm` |
| Base cut | `0 mm` |
| Maximum depth (`worn`) | `0.65 mm` |
| Intensity | `1.0` |
| Clustering | `0.35` |
| Cluster radius | `18 mm` |

The default damage-category amount multipliers are all `1.0`.

---

## Basic block command

```bash
python 3dMetaliserBlock.py \
  --width 100 \
  --height 100 \
  --preset worn \
  -o metal_damage_stamp.stl
```

Example larger stamp:

```bash
python 3dMetaliserBlock.py \
  --width 300 \
  --height 300 \
  --preset battered \
  --resolution 1.0 \
  -o battered_300mm.stl
```

---

## Resolution and triangle count

The stamp is generated from a regular grid.

Lower resolution values mean smaller grid spacing and therefore:

- smoother detail;
- more triangles;
- larger STL files;
- longer generation time.

Higher values mean:

- fewer triangles;
- smaller files;
- coarser damage.

For large stamps, `0.5 mm` can produce a very large mesh.

Typical examples:

```text
0.5 mm  = fine/heavy mesh
1.0 mm  = much lighter
1.5 mm  = broad damage / lower triangle count
```

The script prints the calculated grid dimensions and triangle count before writing the STL.

It also warns if the estimated STL exceeds 2,000,000 triangles.

---

## Minimum printable feature

```text
--min-feature 0.4
```

The script enforces this minimum on scratch widths, gouge widths and pit diameters during validation.

This is useful for preventing settings which are obviously too fine to reproduce physically.

---

## Binary vs ASCII STL

Binary STL is the default and is recommended.

Generate ASCII instead:

```bash
--ascii
```

ASCII STLs are substantially larger.

---

## JSON settings sidecar

A JSON file is written by default beside the stamp.

For:

```text
battered_stamp.stl
```

the sidecar is:

```text
battered_stamp.json
```

It contains the configuration, mesh dimensions, triangle count, seed and generated feature counts.

Disable it with:

```bash
--no-json
```

---

## Using the generated stamp

Typical Boolean workflow:

1. Generate the stamp.
2. Import both your model and stamp into the 3D editor.
3. Place the stamp so its `Z=0` surface sits against the panel.
4. Make sure the negative damage extends into the model.
5. Boolean **Difference** / subtract the stamp from the target.
6. Inspect the resulting mesh.
7. Export the finished model.

The backing extends in `+Z`; the damage cutter extends in `-Z`.

---

## Block examples

### Worn 100 × 100 mm stamp

```bash
python 3dMetaliserBlock.py \
  --width 100 \
  --height 100 \
  --preset worn \
  -o worn_stamp.stl
```

### Broad dents, reduced scratches and pitting

```bash
python 3dMetaliserBlock.py \
  --width 150 \
  --height 100 \
  --preset battered \
  --dent-amount 1.5 \
  --impact-amount 0.7 \
  --scratch-amount 0.2 \
  --gouge-amount 0.2 \
  --pit-amount 0.05 \
  -o dented_stamp.stl
```

### Lower-poly large stamp

```bash
python 3dMetaliserBlock.py \
  --width 300 \
  --height 300 \
  --resolution 1.5 \
  --preset worn \
  -o large_stamp.stl
```

### Repeatable seed

```bash
python 3dMetaliserBlock.py \
  --preset battered \
  --seed 12345 \
  -o repeatable_stamp.stl
```

---

## Full `3dMetaliserBlock.py` options

Use:

```bash
python 3dMetaliserBlock.py --help
```

Main option groups include:

### General geometry

```text
--width
--height
--resolution
--carrier
--edge-margin
--min-feature
--base-cut
--max-depth
--intensity
--seed
-o / --output
--ascii
--no-json
```

### Damage amounts

```text
--uneven-amount
--dent-amount
--impact-amount
--scratch-amount
--gouge-amount
--pit-amount
```

### Distribution

```text
--clustering
--cluster-radius
```

### Detailed controls

The script exposes individual parameters for:

- broad unevenness;
- dents;
- impacts;
- scratches;
- gouges;
- pitting.

Run `--help` for the exact current parameter names.

---

# Choosing which tool to use

Use **`3dMetaliser.py`** when:

- you want the program to find the flat panels automatically;
- you want to process many panels in one run;
- you want curved/detail geometry left alone;
- you want build-plate bottom exclusion;
- you want the available thin-wall safety check.

Use **`3dMetaliserBlock.py`** when:

- you want full manual control over exactly where damage goes;
- you want to position or rotate a cutter by hand;
- you want to Boolean the same damage pattern into multiple models;
- automatic planar-patch selection is not appropriate.

---

# Troubleshooting

## `ModuleNotFoundError`

For `3dMetaliser.py`:

```bash
python -m pip install numpy trimesh shapely rtree
```

`3dMetaliserBlock.py` does not require these third-party packages.

---

## No eligible flat patches

If `3dMetaliser.py` reports:

```text
No eligible flat patches
```

try a dry run and carefully lower:

```text
--min-flat-area
--min-flat-span
```

or slightly loosen:

```text
--flat-angle
--plane-tolerance
```

Do not loosen them more than necessary or detailed/curved regions may become eligible.

---

## Too many small details are being metalised

Increase:

```text
--min-flat-area
--min-flat-span
--edge-margin
```

---

## Build-plate base is being affected

Run:

```bash
python 3dMetaliser.py model.stl --dry-run
```

Check:

```text
Bottom patches skipped:
Detected bottom Z:
```

Then adjust:

```text
--bottom-tolerance
--bottom-normal-angle
```

if necessary.

---

## Damage is barely visible

Try an intentionally obvious diagnostic:

```bash
python 3dMetaliser.py model.stl \
  --preset brutal \
  --intensity 1.5 \
  --seed 12345 \
  -o obvious_test.stl
```

If that is visible, reduce the settings afterward.

---

## Output has too many triangles

For `3dMetaliser.py`, raise:

```text
--surface-resolution
```

or lower:

```text
--max-new-triangles
```

For `3dMetaliserBlock.py`, raise:

```text
--resolution
```

---

## Thin wall still gets damaged

The current `3dMetaliser.py` thickness protection is a ray-based pre-check and is not a full final-mesh wall-thickness validator.

Possible problem cases include:

- open/non-watertight STL shells;
- missing/internal faces;
- self intersections;
- unusual normals/topology;
- rays which do not find the intended opposite wall;
- very aggressive damage on both sides of complex geometry.

Use conservative wall settings and inspect the final STL before printing.

---

# Notes for 3D printing

- Both programs assume millimetres.
- STL contains geometry only; there is no render material involved.
- Very small pits or scratches may exist mathematically but still disappear during slicing/printing.
- Physical detail should be chosen with nozzle diameter, resin XY resolution and layer height in mind.
- Keep the original STL.
- Check the resulting STL in your slicer before committing to a long print.
