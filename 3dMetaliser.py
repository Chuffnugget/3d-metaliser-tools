#!/usr/bin/env python3
"""
stl_flat_metal_texture_v2.py

V2: directly re-meshes and displaces ONLY eligible flat/planar surface patches.
No global Boolean. No manifold repair. No remeshing of curves/skulls/emblems.

This is specifically meant for STL models where the original mesh may be
non-watertight/open and where a Boolean engine would otherwise rebuild/repair
the entire object.

Dependencies:
    pip install numpy trimesh shapely

Python 3.10+ recommended.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import secrets
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import trimesh
import shapely
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union

VERSION = "2.5"

PRESETS = {
    "subtle": dict(
        max_depth=0.45,
        uneven_amp=0.08, uneven_scale=28.0,
        secondary_amp=0.03, secondary_scale=8.0,
        dent_density=3.0, dent_size_min=12.0, dent_size_max=28.0, dent_depth_min=0.10, dent_depth_max=0.28,
        impact_density=0.6, impact_size_min=3.0, impact_size_max=7.0, impact_depth_min=0.14, impact_depth_max=0.30,
        scratch_density=3.0, scratch_len_min=8.0, scratch_len_max=25.0, scratch_width_min=1.2, scratch_width_max=2.0, scratch_depth_min=0.10, scratch_depth_max=0.20,
        gouge_density=0.5, gouge_len_min=6.0, gouge_len_max=18.0, gouge_width_min=1.6, gouge_width_max=2.8, gouge_depth_min=0.16, gouge_depth_max=0.30,
        pit_density=1.5, pit_size_min=1.5, pit_size_max=3.0, pit_depth_min=0.10, pit_depth_max=0.18,
    ),
    "worn": dict(
        max_depth=0.70,
        uneven_amp=0.16, uneven_scale=24.0,
        secondary_amp=0.06, secondary_scale=7.0,
        dent_density=6.0, dent_size_min=10.0, dent_size_max=32.0, dent_depth_min=0.14, dent_depth_max=0.46,
        impact_density=1.5, impact_size_min=3.0, impact_size_max=8.0, impact_depth_min=0.18, impact_depth_max=0.50,
        scratch_density=5.0, scratch_len_min=7.0, scratch_len_max=30.0, scratch_width_min=1.2, scratch_width_max=2.2, scratch_depth_min=0.12, scratch_depth_max=0.26,
        gouge_density=1.2, gouge_len_min=6.0, gouge_len_max=22.0, gouge_width_min=1.6, gouge_width_max=3.0, gouge_depth_min=0.20, gouge_depth_max=0.46,
        pit_density=3.5, pit_size_min=1.5, pit_size_max=3.5, pit_depth_min=0.10, pit_depth_max=0.24,
    ),
    "battered": dict(
        max_depth=1.00,
        uneven_amp=0.25, uneven_scale=20.0,
        secondary_amp=0.10, secondary_scale=5.5,
        dent_density=9.0, dent_size_min=8.0, dent_size_max=36.0, dent_depth_min=0.18, dent_depth_max=0.68,
        impact_density=3.0, impact_size_min=2.5, impact_size_max=9.0, impact_depth_min=0.22, impact_depth_max=0.78,
        scratch_density=8.0, scratch_len_min=6.0, scratch_len_max=36.0, scratch_width_min=1.1, scratch_width_max=2.5, scratch_depth_min=0.14, scratch_depth_max=0.36,
        gouge_density=2.5, gouge_len_min=5.0, gouge_len_max=26.0, gouge_width_min=1.6, gouge_width_max=3.5, gouge_depth_min=0.26, gouge_depth_max=0.70,
        pit_density=7.0, pit_size_min=1.3, pit_size_max=4.0, pit_depth_min=0.12, pit_depth_max=0.32,
    ),
    "abused": dict(
        max_depth=1.35,
        uneven_amp=0.36, uneven_scale=17.0,
        secondary_amp=0.15, secondary_scale=4.5,
        dent_density=13.0, dent_size_min=7.0, dent_size_max=42.0, dent_depth_min=0.22, dent_depth_max=0.95,
        impact_density=5.5, impact_size_min=2.5, impact_size_max=10.0, impact_depth_min=0.28, impact_depth_max=1.05,
        scratch_density=12.0, scratch_len_min=5.0, scratch_len_max=42.0, scratch_width_min=1.0, scratch_width_max=3.0, scratch_depth_min=0.16, scratch_depth_max=0.48,
        gouge_density=4.5, gouge_len_min=5.0, gouge_len_max=32.0, gouge_width_min=1.8, gouge_width_max=4.0, gouge_depth_min=0.30, gouge_depth_max=0.95,
        pit_density=12.0, pit_size_min=1.2, pit_size_max=4.5, pit_depth_min=0.14, pit_depth_max=0.42,
    ),
    "brutal": dict(
        max_depth=1.75,
        uneven_amp=0.48, uneven_scale=15.0,
        secondary_amp=0.20, secondary_scale=4.0,
        dent_density=17.0, dent_size_min=6.0, dent_size_max=48.0, dent_depth_min=0.28, dent_depth_max=1.25,
        impact_density=8.0, impact_size_min=2.2, impact_size_max=11.0, impact_depth_min=0.34, impact_depth_max=1.35,
        scratch_density=17.0, scratch_len_min=4.0, scratch_len_max=48.0, scratch_width_min=1.0, scratch_width_max=3.5, scratch_depth_min=0.18, scratch_depth_max=0.60,
        gouge_density=7.0, gouge_len_min=4.0, gouge_len_max=38.0, gouge_width_min=2.0, gouge_width_max=4.8, gouge_depth_min=0.36, gouge_depth_max=1.25,
        pit_density=18.0, pit_size_min=1.2, pit_size_max=5.0, pit_depth_min=0.16, pit_depth_max=0.50,
    ),
    "wrecked": dict(
        max_depth=2.20,
        uneven_amp=0.62, uneven_scale=13.0,
        secondary_amp=0.27, secondary_scale=3.6,
        dent_density=22.0, dent_size_min=5.5, dent_size_max=54.0, dent_depth_min=0.34, dent_depth_max=1.60,
        impact_density=11.0, impact_size_min=2.0, impact_size_max=12.0, impact_depth_min=0.40, impact_depth_max=1.75,
        scratch_density=23.0, scratch_len_min=4.0, scratch_len_max=54.0, scratch_width_min=1.0, scratch_width_max=4.0, scratch_depth_min=0.20, scratch_depth_max=0.75,
        gouge_density=10.0, gouge_len_min=4.0, gouge_len_max=44.0, gouge_width_min=2.2, gouge_width_max=5.5, gouge_depth_min=0.42, gouge_depth_max=1.60,
        pit_density=26.0, pit_size_min=1.1, pit_size_max=5.5, pit_depth_min=0.18, pit_depth_max=0.62,
    ),
    "ruined": dict(
        max_depth=2.80,
        uneven_amp=0.80, uneven_scale=11.0,
        secondary_amp=0.36, secondary_scale=3.2,
        dent_density=28.0, dent_size_min=5.0, dent_size_max=60.0, dent_depth_min=0.42, dent_depth_max=2.10,
        impact_density=15.0, impact_size_min=1.8, impact_size_max=14.0, impact_depth_min=0.48, impact_depth_max=2.25,
        scratch_density=30.0, scratch_len_min=3.5, scratch_len_max=60.0, scratch_width_min=1.0, scratch_width_max=4.5, scratch_depth_min=0.22, scratch_depth_max=0.95,
        gouge_density=14.0, gouge_len_min=3.5, gouge_len_max=50.0, gouge_width_min=2.4, gouge_width_max=6.5, gouge_depth_min=0.50, gouge_depth_max=2.10,
        pit_density=36.0, pit_size_min=1.0, pit_size_max=6.5, pit_depth_min=0.20, pit_depth_max=0.78,
    ),
    "catastrophic": dict(
        max_depth=3.60,
        uneven_amp=1.00, uneven_scale=9.5,
        secondary_amp=0.48, secondary_scale=2.8,
        dent_density=36.0, dent_size_min=4.5, dent_size_max=68.0, dent_depth_min=0.52, dent_depth_max=2.75,
        impact_density=20.0, impact_size_min=1.8, impact_size_max=16.0, impact_depth_min=0.58, impact_depth_max=3.00,
        scratch_density=40.0, scratch_len_min=3.0, scratch_len_max=68.0, scratch_width_min=1.0, scratch_width_max=5.5, scratch_depth_min=0.25, scratch_depth_max=1.20,
        gouge_density=19.0, gouge_len_min=3.0, gouge_len_max=58.0, gouge_width_min=2.5, gouge_width_max=8.0, gouge_depth_min=0.62, gouge_depth_max=2.75,
        pit_density=48.0, pit_size_min=1.0, pit_size_max=8.0, pit_depth_min=0.22, pit_depth_max=1.00,
    ),
    "obliterated": dict(
        max_depth=4.80,
        uneven_amp=1.30, uneven_scale=8.0,
        secondary_amp=0.65, secondary_scale=2.5,
        dent_density=46.0, dent_size_min=4.0, dent_size_max=78.0, dent_depth_min=0.65, dent_depth_max=3.60,
        impact_density=28.0, impact_size_min=1.6, impact_size_max=20.0, impact_depth_min=0.70, impact_depth_max=4.00,
        scratch_density=52.0, scratch_len_min=2.5, scratch_len_max=78.0, scratch_width_min=1.0, scratch_width_max=7.0, scratch_depth_min=0.28, scratch_depth_max=1.60,
        gouge_density=26.0, gouge_len_min=2.5, gouge_len_max=70.0, gouge_width_min=2.8, gouge_width_max=10.0, gouge_depth_min=0.75, gouge_depth_max=3.60,
        pit_density=65.0, pit_size_min=0.9, pit_size_max=10.0, pit_depth_min=0.25, pit_depth_max=1.35,
    ),
}


@dataclass
class Config:
    input: str = ""
    output: str = ""
    preset: str = "worn"
    seed: int = 1

    # Flat patch detection
    flat_angle_deg: float = 0.75
    plane_tolerance: float = 0.08
    min_flat_area: float = 200.0
    min_flat_span: float = 8.0
    edge_margin: float = 3.0

    # Build-plate protection
    skip_bottom: bool = True
    bottom_tolerance: float = 0.60
    bottom_normal_angle_deg: float = 20.0

    # Thin-wall protection
    min_wall_thickness: float = 1.20
    thickness_safety: float = 0.10
    thickness_probe_max: float = 20.0
    thickness_ray_epsilon: float = 0.03
    thickness_mode: str = "skip"  # skip | clamp

    # Local remeshing
    surface_resolution: float = 1.5
    max_new_triangles: int = 450000
    max_subdivide_iter: int = 9

    # Damage
    max_depth: float = 0.70
    intensity: float = 1.0
    uneven_amount: float = 1.0
    dent_amount: float = 1.0
    impact_amount: float = 0.7
    scratch_amount: float = 0.35
    gouge_amount: float = 0.20
    pit_amount: float = 0.10
    clustering: float = 0.30
    cluster_radius: float = 18.0

    uneven_amp: float = 0.16
    uneven_scale: float = 24.0
    secondary_amp: float = 0.06
    secondary_scale: float = 7.0

    dent_density: float = 6.0
    dent_size_min: float = 10.0
    dent_size_max: float = 32.0
    dent_depth_min: float = 0.14
    dent_depth_max: float = 0.46

    impact_density: float = 1.5
    impact_size_min: float = 3.0
    impact_size_max: float = 8.0
    impact_depth_min: float = 0.18
    impact_depth_max: float = 0.50

    scratch_density: float = 5.0
    scratch_len_min: float = 7.0
    scratch_len_max: float = 30.0
    scratch_width_min: float = 1.2
    scratch_width_max: float = 2.2
    scratch_depth_min: float = 0.12
    scratch_depth_max: float = 0.26
    scratch_curvature: float = 0.16
    scratch_direction_deg: float = 0.0
    scratch_direction_bias: float = 0.25

    gouge_density: float = 1.2
    gouge_len_min: float = 6.0
    gouge_len_max: float = 22.0
    gouge_width_min: float = 1.6
    gouge_width_max: float = 3.0
    gouge_depth_min: float = 0.20
    gouge_depth_max: float = 0.46
    gouge_curvature: float = 0.12

    pit_density: float = 3.5
    pit_size_min: float = 1.5
    pit_size_max: float = 3.5
    pit_depth_min: float = 0.10
    pit_depth_max: float = 0.24

    dry_run: bool = False
    write_report: bool = True


def apply_preset(cfg, name):
    cfg.preset = name
    for k, v in PRESETS[name].items():
        setattr(cfg, k, v)


def ask_float(label, default, minimum=None):
    while True:
        s = input(f"{label} [{default:g}]: ").strip()
        if not s:
            return default
        try:
            v = float(s)
            if minimum is not None and v < minimum:
                print(f"  Must be >= {minimum:g}")
                continue
            return v
        except ValueError:
            print("  Enter a number or press Enter for default.")


def ask_int(label, default, minimum=None):
    while True:
        s = input(f"{label} [{default}]: ").strip()
        if not s:
            return default
        try:
            v = int(s)
            if minimum is not None and v < minimum:
                print(f"  Must be >= {minimum}")
                continue
            return v
        except ValueError:
            print("  Enter an integer or press Enter for default.")


def ask_yes_no(label, default=False):
    suffix = "Y/n" if default else "y/N"
    while True:
        s = input(f"{label} [{suffix}]: ").strip().lower()
        if not s:
            return default
        if s in ("y", "yes"):
            return True
        if s in ("n", "no"):
            return False
        print("  Enter y or n.")


def ask_choice(label, choices, default):
    print(label)
    for i, c in enumerate(choices, 1):
        mark = " [default]" if c == default else ""
        print(f"  {i}) {c}{mark}")
    while True:
        s = input(f"Choice [{choices.index(default)+1}]: ").strip()
        if not s:
            return default
        if s.isdigit() and 1 <= int(s) <= len(choices):
            return choices[int(s)-1]
        if s in choices:
            return s
        print("  Pick one of the listed options.")


def wizard(cfg):
    print()
    print("="*72)
    print(" STL FLAT-SURFACE METAL TEXTURER V2.5")
    print("="*72)
    print("V2 directly deforms only selected flat patches.")
    print("It does NOT Boolean/rebuild the whole model.")
    print("Press Enter to accept defaults.")
    print()

    while True:
        p = input("Input STL: ").strip().strip('"')
        if os.path.isfile(p):
            cfg.input = p
            break
        print("  File not found.")

    cfg.output = str(Path(cfg.input).with_suffix("")) + "_metal_textured_v2.stl"

    chosen = ask_choice("Damage preset:", ["subtle","worn","battered","abused","brutal","wrecked","ruined","catastrophic","obliterated"], cfg.preset)
    apply_preset(cfg, chosen)

    print("\nFlat-surface detection:")
    cfg.flat_angle_deg = ask_float("  Maximum normal deviation (degrees)", cfg.flat_angle_deg, 0.01)
    cfg.plane_tolerance = ask_float("  Maximum distance from plane (mm)", cfg.plane_tolerance, 0.0)
    cfg.min_flat_area = ask_float("  Minimum flat patch area (mm^2)", cfg.min_flat_area, 0.0)
    cfg.min_flat_span = ask_float("  Minimum patch width/span (mm)", cfg.min_flat_span, 0.0)
    cfg.edge_margin = ask_float("  Fade damage to zero over this edge margin (mm)", cfg.edge_margin, 0.0)

    print("\nBuild-plate protection:")
    cfg.skip_bottom = ask_yes_no("  Protect bottom/build-plate surface from texturing?", cfg.skip_bottom)
    if cfg.skip_bottom:
        cfg.bottom_tolerance = ask_float(
            "  Bottom plane coplanar tolerance (mm)",
            cfg.bottom_tolerance,
            0.0,
        )
        cfg.bottom_normal_angle_deg = ask_float(
            "  Maximum tilt away from horizontal for bottom detection (degrees)",
            cfg.bottom_normal_angle_deg,
            0.0,
        )

    print("\nThin-wall protection:")
    protect_thin = ask_yes_no(
        "  Protect areas that would become too thin?",
        cfg.min_wall_thickness > 0,
    )
    if protect_thin:
        cfg.min_wall_thickness = ask_float(
            "  Minimum RESULTING wall thickness (mm)",
            cfg.min_wall_thickness,
            0.01,
        )
        cfg.thickness_safety = ask_float(
            "  Extra thickness safety margin (mm)",
            cfg.thickness_safety,
            0.0,
        )
        cfg.thickness_probe_max = ask_float(
            "  Maximum thickness probe distance (mm)",
            cfg.thickness_probe_max,
            0.1,
        )
        cfg.thickness_mode = ask_choice(
            "  If a proposed dent would breach the minimum:",
            ["skip", "clamp"],
            cfg.thickness_mode,
        )
    else:
        cfg.min_wall_thickness = 0.0

    print("\nLocal surface mesh:")
    cfg.surface_resolution = ask_float("  Desired maximum triangle edge (mm)", cfg.surface_resolution, 0.1)
    cfg.max_new_triangles = ask_int("  Approx maximum triangles for textured patches", cfg.max_new_triangles, 1000)

    print("\nDamage:")
    cfg.max_depth = ask_float("  Absolute maximum damage depth (mm)", cfg.max_depth, 0.01)
    cfg.intensity = ask_float("  Global depth intensity", cfg.intensity, 0.0)
    cfg.uneven_amount = ask_float("  Broad unevenness amount", cfg.uneven_amount, 0.0)
    cfg.dent_amount = ask_float("  Dents amount", cfg.dent_amount, 0.0)
    cfg.impact_amount = ask_float("  Impacts amount", cfg.impact_amount, 0.0)
    cfg.scratch_amount = ask_float("  Scratches amount", cfg.scratch_amount, 0.0)
    cfg.gouge_amount = ask_float("  Gouges amount", cfg.gouge_amount, 0.0)
    cfg.pit_amount = ask_float("  Pitting amount", cfg.pit_amount, 0.0)

    seed = input("Random seed [random]: ").strip()
    cfg.seed = int(seed) if seed else secrets.randbits(32)

    if ask_yes_no("\nAdvanced damage settings?", False):
        cfg.clustering = ask_float("Clustering 0..1", cfg.clustering, 0.0)
        cfg.cluster_radius = ask_float("Cluster radius (mm)", cfg.cluster_radius, 0.1)

        print("\nBroad unevenness:")
        cfg.uneven_amp = ask_float("  Large unevenness amplitude (mm)", cfg.uneven_amp, 0.0)
        cfg.uneven_scale = ask_float("  Large unevenness scale (mm)", cfg.uneven_scale, 0.1)
        cfg.secondary_amp = ask_float("  Secondary unevenness amplitude (mm)", cfg.secondary_amp, 0.0)
        cfg.secondary_scale = ask_float("  Secondary unevenness scale (mm)", cfg.secondary_scale, 0.1)

        print("\nDents:")
        cfg.dent_density = ask_float("  Dents per 100x100 mm", cfg.dent_density, 0.0)
        cfg.dent_size_min = ask_float("  Minimum diameter (mm)", cfg.dent_size_min, 0.1)
        cfg.dent_size_max = ask_float("  Maximum diameter (mm)", cfg.dent_size_max, 0.1)
        cfg.dent_depth_min = ask_float("  Minimum depth (mm)", cfg.dent_depth_min, 0.0)
        cfg.dent_depth_max = ask_float("  Maximum depth (mm)", cfg.dent_depth_max, 0.0)

        print("\nImpacts:")
        cfg.impact_density = ask_float("  Impacts per 100x100 mm", cfg.impact_density, 0.0)
        cfg.impact_size_min = ask_float("  Minimum diameter (mm)", cfg.impact_size_min, 0.1)
        cfg.impact_size_max = ask_float("  Maximum diameter (mm)", cfg.impact_size_max, 0.1)
        cfg.impact_depth_min = ask_float("  Minimum depth (mm)", cfg.impact_depth_min, 0.0)
        cfg.impact_depth_max = ask_float("  Maximum depth (mm)", cfg.impact_depth_max, 0.0)

        print("\nScratches:")
        cfg.scratch_density = ask_float("  Scratches per 100x100 mm", cfg.scratch_density, 0.0)
        cfg.scratch_width_min = ask_float("  Minimum width (mm)", cfg.scratch_width_min, 0.1)
        cfg.scratch_width_max = ask_float("  Maximum width (mm)", cfg.scratch_width_max, 0.1)
        cfg.scratch_depth_min = ask_float("  Minimum depth (mm)", cfg.scratch_depth_min, 0.0)
        cfg.scratch_depth_max = ask_float("  Maximum depth (mm)", cfg.scratch_depth_max, 0.0)

        print("\nGouges:")
        cfg.gouge_density = ask_float("  Gouges per 100x100 mm", cfg.gouge_density, 0.0)
        cfg.gouge_width_min = ask_float("  Minimum width (mm)", cfg.gouge_width_min, 0.1)
        cfg.gouge_width_max = ask_float("  Maximum width (mm)", cfg.gouge_width_max, 0.1)
        cfg.gouge_depth_min = ask_float("  Minimum depth (mm)", cfg.gouge_depth_min, 0.0)
        cfg.gouge_depth_max = ask_float("  Maximum depth (mm)", cfg.gouge_depth_max, 0.0)

        print("\nPitting:")
        cfg.pit_density = ask_float("  Pits per 100x100 mm", cfg.pit_density, 0.0)
        cfg.pit_size_min = ask_float("  Minimum diameter (mm)", cfg.pit_size_min, 0.1)
        cfg.pit_size_max = ask_float("  Maximum diameter (mm)", cfg.pit_size_max, 0.1)
        cfg.pit_depth_min = ask_float("  Minimum depth (mm)", cfg.pit_depth_min, 0.0)
        cfg.pit_depth_max = ask_float("  Maximum depth (mm)", cfg.pit_depth_max, 0.0)

    cfg.output = input(f"\nOutput STL [{cfg.output}]: ").strip().strip('"') or cfg.output
    cfg.write_report = ask_yes_no("Write JSON report?", True)

    return cfg


def build_parser():
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Directly texture only large flat regions of an STL; no global Boolean."
    )
    p.add_argument("input", nargs="?")
    p.add_argument("-o","--output")
    p.add_argument("--wizard", action="store_true")
    p.add_argument("--preset", choices=sorted(PRESETS))
    p.add_argument("--seed", type=int)

    p.add_argument("--flat-angle", dest="flat_angle_deg", type=float)
    p.add_argument("--plane-tolerance", type=float)
    p.add_argument("--min-flat-area", type=float)
    p.add_argument("--min-flat-span", type=float)
    p.add_argument("--edge-margin", type=float)

    bottom_group = p.add_mutually_exclusive_group()
    bottom_group.add_argument(
        "--skip-bottom",
        dest="skip_bottom",
        action="store_true",
        default=None,
        help="Protect build-plate bottom surfaces from texturing (default).",
    )
    bottom_group.add_argument(
        "--texture-bottom",
        dest="skip_bottom",
        action="store_false",
        default=None,
        help="Allow texturing on bottom/build-plate surfaces.",
    )
    p.add_argument(
        "--bottom-tolerance",
        type=float,
        help="Coplanar tolerance around the detected lowest substantial horizontal plane.",
    )
    p.add_argument(
        "--bottom-normal-angle",
        dest="bottom_normal_angle_deg",
        type=float,
        help="Maximum tilt away from horizontal for a lowest-Z patch to count as bottom.",
    )

    p.add_argument(
        "--min-wall-thickness",
        type=float,
        help="Minimum allowed RESULTING wall thickness in mm. 0 disables thin-wall protection.",
    )
    p.add_argument(
        "--thickness-safety",
        type=float,
        help="Extra safety margin added to the minimum wall thickness.",
    )
    p.add_argument(
        "--thickness-probe-max",
        type=float,
        help="Maximum inward ray distance used to search for the opposite wall.",
    )
    p.add_argument(
        "--thickness-ray-epsilon",
        type=float,
        help="Small inward ray offset in mm to avoid self-hits.",
    )
    p.add_argument(
        "--thickness-mode",
        choices=["skip", "clamp"],
        help="skip = leave unsafe vertices unchanged; clamp = reduce dent depth to stay above minimum.",
    )
    p.add_argument(
        "--no-thickness-protection",
        action="store_true",
        help="Disable minimum-wall-thickness protection.",
    )

    p.add_argument("--surface-resolution", type=float)
    p.add_argument("--max-new-triangles", type=int)
    p.add_argument("--max-depth", type=float)
    p.add_argument("--intensity", type=float)

    p.add_argument("--uneven-amount", type=float)
    p.add_argument("--dent-amount", type=float)
    p.add_argument("--impact-amount", type=float)
    p.add_argument("--scratch-amount", type=float)
    p.add_argument("--gouge-amount", type=float)
    p.add_argument("--pit-amount", type=float)

    p.add_argument("--clustering", type=float)
    p.add_argument("--cluster-radius", type=float)

    for name in (
        "uneven_amp","uneven_scale","secondary_amp","secondary_scale",
        "dent_density","dent_size_min","dent_size_max","dent_depth_min","dent_depth_max",
        "impact_density","impact_size_min","impact_size_max","impact_depth_min","impact_depth_max",
        "scratch_density","scratch_len_min","scratch_len_max","scratch_width_min","scratch_width_max",
        "scratch_depth_min","scratch_depth_max","scratch_curvature","scratch_direction_deg","scratch_direction_bias",
        "gouge_density","gouge_len_min","gouge_len_max","gouge_width_min","gouge_width_max",
        "gouge_depth_min","gouge_depth_max","gouge_curvature",
        "pit_density","pit_size_min","pit_size_max","pit_depth_min","pit_depth_max",
    ):
        p.add_argument("--"+name.replace("_","-"), dest=name, type=float)

    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-report", action="store_true")
    return p


def apply_args(cfg,args):
    if args.preset:
        apply_preset(cfg,args.preset)

    if args.input:
        cfg.input = args.input
    if args.output:
        cfg.output = args.output
    if args.seed is not None:
        cfg.seed = args.seed

    for name in cfg.__dataclass_fields__:
        if hasattr(args,name):
            v = getattr(args,name)
            if v is not None and name not in ("input","output","seed"):
                setattr(cfg,name,v)

    if getattr(args, "no_thickness_protection", False):
        cfg.min_wall_thickness = 0.0

    if args.no_report:
        cfg.write_report=False


def load_mesh(path):
    loaded=trimesh.load(path,force=None,process=True)
    if isinstance(loaded,trimesh.Scene):
        parts=[g for g in loaded.geometry.values() if isinstance(g,trimesh.Trimesh)]
        if not parts:
            raise RuntimeError("No mesh geometry found.")
        mesh=trimesh.util.concatenate(parts)
    elif isinstance(loaded,trimesh.Trimesh):
        mesh=loaded
    else:
        raise RuntimeError("Could not load input as mesh.")
    mesh.remove_unreferenced_vertices()
    return mesh


def make_basis(normal):
    n=np.asarray(normal,dtype=float)
    n/=max(np.linalg.norm(n),1e-15)
    axis=np.array([1.,0.,0.])
    if abs(np.dot(axis,n))>0.85:
        axis=np.array([0.,1.,0.])
    u=np.cross(n,axis); u/=np.linalg.norm(u)
    v=np.cross(n,u); v/=np.linalg.norm(v)
    return u,v,n


def detect_planar_patches(mesh,cfg):
    normals=np.asarray(mesh.face_normals)
    centroids=np.asarray(mesh.triangles_center)
    vertices=np.asarray(mesh.vertices)
    faces=np.asarray(mesh.faces)
    areas=np.asarray(mesh.area_faces)

    adjacency=[[] for _ in range(len(faces))]
    for a,b in np.asarray(mesh.face_adjacency):
        adjacency[int(a)].append(int(b))
        adjacency[int(b)].append(int(a))

    assigned=np.full(len(faces),-1,dtype=np.int64)
    cos_tol=math.cos(math.radians(cfg.flat_angle_deg))
    patches=[]

    for seed in range(len(faces)):
        if assigned[seed]!=-1:
            continue
        if areas[seed]<=1e-12:
            assigned[seed]=-2
            continue

        ref_n=normals[seed].copy()
        ln=np.linalg.norm(ref_n)
        if ln<=1e-12:
            assigned[seed]=-2
            continue
        ref_n/=ln
        origin=centroids[seed].copy()

        pid=len(patches)
        assigned[seed]=pid
        stack=[seed]
        group=[]

        while stack:
            f=stack.pop()
            group.append(f)
            for nb in adjacency[f]:
                if assigned[nb]!=-1:
                    continue
                nn=normals[nb]
                l=np.linalg.norm(nn)
                if l<=1e-12:
                    continue
                nn=nn/l
                if np.dot(nn,ref_n)<cos_tol:
                    continue
                pts=vertices[faces[nb]]
                max_dist=float(np.max(np.abs((pts-origin)@ref_n)))
                if max_dist>cfg.plane_tolerance:
                    continue
                assigned[nb]=pid
                stack.append(nb)

        ids=np.asarray(group,dtype=np.int64)
        patches.append({
            "id":pid,
            "faces":ids,
            "normal":ref_n,
            "origin":origin,
            "area":float(np.sum(areas[ids])),
        })

    return patches


def boundary_loops(mesh,face_ids):
    faces=np.asarray(mesh.faces)[face_ids]
    counts={}
    for tri in faces:
        for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            key=(int(a),int(b)) if a<b else (int(b),int(a))
            counts[key]=counts.get(key,0)+1
    boundary=[e for e,c in counts.items() if c==1]
    if not boundary:
        return []

    nbs={}
    for a,b in boundary:
        nbs.setdefault(a,[]).append(b)
        nbs.setdefault(b,[]).append(a)
    if any(len(v)!=2 for v in nbs.values()):
        return []

    unused={tuple(sorted(e)) for e in boundary}
    loops=[]
    while unused:
        start=next(iter(unused))[0]
        curr=start
        prev=None
        loop=[start]
        for _ in range(len(boundary)+5):
            options=nbs[curr]
            nxt=options[0] if options[0]!=prev else options[1]
            key=tuple(sorted((curr,nxt)))
            if key not in unused:
                alt=options[1] if nxt==options[0] else options[0]
                key2=tuple(sorted((curr,alt)))
                if key2 in unused:
                    nxt=alt; key=key2
                elif nxt==start:
                    break
                else:
                    return []
            unused.discard(key)
            prev,curr=curr,nxt
            if curr==start:
                break
            loop.append(curr)
        if len(loop)>=3:
            loops.append(loop)
    return loops


def patch_polygon(mesh,patch):
    u,v,n=make_basis(patch["normal"])
    origin=patch["origin"]

    def proj_idx(idx):
        d=np.asarray(mesh.vertices[idx])-origin
        return (float(np.dot(d,u)),float(np.dot(d,v)))

    loops=boundary_loops(mesh,patch["faces"])
    if loops:
        polys=[]
        for loop in loops:
            p=Polygon([proj_idx(i) for i in loop])
            if p.is_valid and p.area>1e-8:
                polys.append(p)
        if polys:
            geom=polys[0]
            for p in polys[1:]:
                geom=geom.symmetric_difference(p)
            if not geom.is_empty:
                return geom,u,v,n,origin

    # robust fallback: union the actual projected triangles
    pieces=[]
    for fid in patch["faces"]:
        p=Polygon([proj_idx(i) for i in mesh.faces[fid]])
        if p.area>1e-10:
            pieces.append(p)
    if not pieces:
        return None,u,v,n,origin
    return unary_union(pieces),u,v,n,origin


def min_rotated_span(geom):
    if geom.is_empty:
        return 0.0
    r=geom.minimum_rotated_rectangle
    coords=list(r.exterior.coords)
    if len(coords)<4:
        return 0.0
    lens=[]
    for i in range(4):
        x0,y0=coords[i]; x1,y1=coords[i+1]
        lens.append(math.hypot(x1-x0,y1-y0))
    return min(lens)



def analyze(mesh,cfg):
    """
    Detect planar patches, apply size/span filtering, then robustly identify the
    build-plate plane.

    Bottom detection in V2.3 does NOT depend on:
      - mesh watertightness
      - face winding
      - the absolute lowest stray vertex

    Instead it:
      1. finds substantial horizontal planar patches;
      2. takes the LOWEST such plane as the build-plate level;
      3. excludes all substantial horizontal patches coplanar with that level
         within bottom_tolerance.

    This catches a genuinely flat base even if a stray decorative/non-manifold
    vertex sticks slightly lower than it.
    """
    patches=detect_planar_patches(mesh,cfg)
    candidates=[]

    # First pass: normal geometric eligibility, but don't decide bottom yet.
    for p in patches:
        if p["area"]<cfg.min_flat_area:
            p["eligible"]=False; p["reason"]="area"; continue

        geom,u,v,n,origin=patch_polygon(mesh,p)
        if geom is None or geom.is_empty:
            p["eligible"]=False; p["reason"]="polygon"; continue

        span=min_rotated_span(geom)
        if span<cfg.min_flat_span:
            p["eligible"]=False; p["reason"]="span"; continue

        safe=geom.buffer(-cfg.edge_margin) if cfg.edge_margin>0 else geom
        if safe.is_empty:
            p["eligible"]=False; p["reason"]="edge_margin"; continue

        if safe.area<max(20.0,cfg.min_flat_area*0.20):
            p["eligible"]=False; p["reason"]="safe_area"; continue

        # Plane height. For a horizontal patch all vertices should be at almost
        # the same Z, so median is robust to tiny floating-point noise.
        patch_vertex_ids=np.unique(np.asarray(mesh.faces)[p["faces"]].ravel())
        patch_z=np.asarray(mesh.vertices)[patch_vertex_ids,2]

        p.update({
            "eligible":True,
            "reason":"",
            "geom":geom,
            "safe_geom":safe,
            "u":u,"v":v,"n":n,"origin":origin,
            "span":float(span),
            "safe_area":float(safe.area),
            "plane_z":float(np.median(patch_z)),
            "z_min":float(np.min(patch_z)),
            "z_max":float(np.max(patch_z)),
        })
        candidates.append(p)

    if cfg.skip_bottom and candidates:
        cos_tol=math.cos(math.radians(cfg.bottom_normal_angle_deg))

        # Horizontal regardless of normal sign/winding.
        horizontal=[
            p for p in candidates
            if abs(float(np.asarray(p["normal"])[2])) >= cos_tol
        ]

        if horizontal:
            # Prefer a substantial horizontal patch for the reference floor.
            # Requiring a decent area prevents a tiny flat ornament below the
            # chassis from becoming the build-plate reference.
            largest_h=max(p["area"] for p in horizontal)
            substantial_threshold=max(
                cfg.min_flat_area,
                min(largest_h*0.05, 1000.0)
            )
            substantial=[p for p in horizontal if p["area"]>=substantial_threshold]
            reference_pool=substantial if substantial else horizontal

            bottom_z=min(p["plane_z"] for p in reference_pool)

            for p in candidates:
                if abs(float(np.asarray(p["normal"])[2])) < cos_tol:
                    continue
                # Protect patches on the same lowest substantial horizontal plane.
                if abs(p["plane_z"]-bottom_z) <= cfg.bottom_tolerance:
                    p["eligible"]=False
                    p["reason"]="build_plate_bottom"

    eligible=[p for p in candidates if p.get("eligible",False)]
    return patches,eligible


# ---------------------------- procedural field ----------------------------

def clamp(x,a,b):
    return a if x<a else b if x>b else x

def fade5(t):
    return t*t*t*(t*(t*6-15)+10)

def hash_noise(ix,iy,seed):
    n=((ix*374761393)+(iy*668265263)+((seed&0xffffffff)*2246822519))&0xffffffff
    n^=(n>>13); n=(n*1274126177)&0xffffffff; n^=(n>>16)
    return (n/4294967295.0)*2.0-1.0

def value_noise(x,y,scale,seed):
    scale=max(scale,1e-9)
    fx=x/scale; fy=y/scale
    ix=math.floor(fx); iy=math.floor(fy)
    tx=fx-ix; ty=fy-iy
    u=fade5(tx); v=fade5(ty)
    a=hash_noise(ix,iy,seed); b=hash_noise(ix+1,iy,seed)
    c=hash_noise(ix,iy+1,seed); d=hash_noise(ix+1,iy+1,seed)
    return (a+(b-a)*u)*(1-v)+(c+(d-c)*u)*v

def fbm(x,y,scale,seed,octaves=3):
    total=0.; amp=1.; asum=0.; s=scale
    for o in range(octaves):
        total+=amp*value_noise(x,y,s,seed+1013*o)
        asum+=amp
        amp*=0.5; s*=0.5
    return total/asum if asum else 0.

def count_for_area(rng,density,amount,area):
    expected=max(0.,density*amount*area/10000.)
    whole=int(expected)
    return whole+(1 if rng.random()<expected-whole else 0)

def random_point_in(geom,rng):
    minx,miny,maxx,maxy=geom.bounds
    for _ in range(500):
        x=rng.uniform(minx,maxx); y=rng.uniform(miny,maxy)
        if geom.contains(Point(x,y)):
            return x,y
    p=geom.representative_point()
    return p.x,p.y

def choose_point(geom,rng,clusters,cfg):
    for _ in range(300):
        if clusters and rng.random()<clamp(cfg.clustering,0,1):
            cx,cy=rng.choice(clusters)
            x=rng.gauss(cx,cfg.cluster_radius*0.45)
            y=rng.gauss(cy,cfg.cluster_radius*0.45)
            if geom.contains(Point(x,y)):
                return x,y
        else:
            return random_point_in(geom,rng)
    return random_point_in(geom,rng)

def make_ellipse(rng,geom,clusters,cfg,size_min,size_max,depth_min,depth_max,oval_min,oval_max,softness,irregularity):
    x,y=choose_point(geom,rng,clusters,cfg)
    major=rng.uniform(size_min,size_max)
    ratio=rng.uniform(oval_min,oval_max)
    rx=major*0.5; ry=rx*ratio
    if rng.random()<0.5: rx,ry=ry,rx
    return dict(
        x=x,y=y,rx=rx,ry=ry,angle=rng.uniform(0,math.pi),
        depth=rng.uniform(depth_min,depth_max),
        softness=softness,irr=irregularity,
        p1=rng.uniform(0,math.tau),p2=rng.uniform(0,math.tau),
    )

def ellipse_depth(x,y,e):
    dx=x-e["x"]; dy=y-e["y"]
    ca=math.cos(e["angle"]); sa=math.sin(e["angle"])
    xr=ca*dx+sa*dy; yr=-sa*dx+ca*dy
    ux=xr/max(e["rx"],1e-9); uy=yr/max(e["ry"],1e-9)
    th=math.atan2(uy,ux)
    mod=1.0+e["irr"]*(0.55*math.sin(3*th+e["p1"])+0.30*math.sin(5*th+e["p2"])+0.15*math.sin(7*th+e["p1"]*.7))
    mod=max(.6,mod)
    q=math.hypot(ux,uy)/mod
    if q>=1: return 0.
    return e["depth"]*(max(0.,1-q*q)**e["softness"])

def biased_angle(rng,deg,bias):
    if rng.random()<clamp(bias,0,1):
        return math.radians(deg+rng.gauss(0,18))%math.pi
    return rng.uniform(0,math.pi)

def make_path(rng,geom,clusters,cfg,lmin,lmax,wmin,wmax,dmin,dmax,curvature,bias):
    cx,cy=choose_point(geom,rng,clusters,cfg)
    length=rng.uniform(lmin,lmax)
    width=rng.uniform(wmin,wmax)
    depth=rng.uniform(dmin,dmax)
    ang=biased_angle(rng,cfg.scratch_direction_deg,bias)
    dx,dy=math.cos(ang),math.sin(ang); nx,ny=-dy,dx
    p0=np.array([cx-dx*length*.5,cy-dy*length*.5])
    p2=np.array([cx+dx*length*.5,cy+dy*length*.5])
    bend=rng.uniform(-1,1)*curvature*length
    p1=np.array([cx+nx*bend,cy+ny*bend])
    pts=[]
    for i in range(9):
        t=i/8.; u=1-t
        pts.append(u*u*p0+2*u*t*p1+t*t*p2)
    return dict(points=np.asarray(pts),width=width,depth=depth)

def point_segment_distance(px,py,a,b):
    ab=b-a; ap=np.array([px,py])-a
    den=float(np.dot(ab,ab))
    if den<1e-15: return float(np.linalg.norm(ap))
    t=clamp(float(np.dot(ap,ab))/den,0,1)
    q=a+t*ab
    return math.hypot(px-q[0],py-q[1])

def path_depth(x,y,e):
    best=1e99
    pts=e["points"]
    for i in range(len(pts)-1):
        best=min(best,point_segment_distance(x,y,pts[i],pts[i+1]))
    hw=e["width"]*.5
    if best>=hw: return 0.
    return e["depth"]*((1-best/max(hw,1e-9))**1.7)


def make_events(p,cfg,rng):
    geom=p["safe_geom"]
    area=float(geom.area)
    clusters=[random_point_in(geom,rng) for _ in range(3)]
    ev={"dents":[],"impacts":[],"scratches":[],"gouges":[],"pits":[]}

    for _ in range(count_for_area(rng,cfg.dent_density,cfg.dent_amount,area)):
        ev["dents"].append(make_ellipse(rng,geom,clusters,cfg,cfg.dent_size_min,cfg.dent_size_max,cfg.dent_depth_min,cfg.dent_depth_max,.45,1.0,2.0,.14))
    for _ in range(count_for_area(rng,cfg.impact_density,cfg.impact_amount,area)):
        ev["impacts"].append(make_ellipse(rng,geom,clusters,cfg,cfg.impact_size_min,cfg.impact_size_max,cfg.impact_depth_min,cfg.impact_depth_max,.55,1.0,1.25,.24))
    for _ in range(count_for_area(rng,cfg.pit_density,cfg.pit_amount,area)):
        ev["pits"].append(make_ellipse(rng,geom,clusters,cfg,cfg.pit_size_min,cfg.pit_size_max,cfg.pit_depth_min,cfg.pit_depth_max,.65,1.0,1.15,.25))

    for _ in range(count_for_area(rng,cfg.scratch_density,cfg.scratch_amount,area)):
        ev["scratches"].append(make_path(rng,geom,clusters,cfg,cfg.scratch_len_min,cfg.scratch_len_max,cfg.scratch_width_min,cfg.scratch_width_max,cfg.scratch_depth_min,cfg.scratch_depth_max,cfg.scratch_curvature,cfg.scratch_direction_bias))
    for _ in range(count_for_area(rng,cfg.gouge_density,cfg.gouge_amount,area)):
        ev["gouges"].append(make_path(rng,geom,clusters,cfg,cfg.gouge_len_min,cfg.gouge_len_max,cfg.gouge_width_min,cfg.gouge_width_max,cfg.gouge_depth_min,cfg.gouge_depth_max,cfg.gouge_curvature,cfg.scratch_direction_bias*.7))
    return ev


def local_depth(x,y,p,cfg,ev,fade):
    # broad rolling unevenness: positive-only so it always dents inward
    d=0.
    if cfg.uneven_amount>0:
        n1=.5+.5*fbm(x,y,cfg.uneven_scale,cfg.seed+5001+p["id"]*37,3)
        n2=.5+.5*fbm(x,y,cfg.secondary_scale,cfg.seed+9001+p["id"]*53,2)
        d+=cfg.uneven_amount*(cfg.uneven_amp*(n1*n1)+cfg.secondary_amp*(n2*n2))

    for e in ev["dents"]: d+=ellipse_depth(x,y,e)
    for e in ev["impacts"]: d+=ellipse_depth(x,y,e)
    for e in ev["pits"]: d+=ellipse_depth(x,y,e)
    for e in ev["scratches"]: d+=path_depth(x,y,e)
    for e in ev["gouges"]: d+=path_depth(x,y,e)

    d=min(cfg.max_depth,max(0.,d*cfg.intensity))
    return d*fade


def auto_resolution(cfg,eligible):
    area=sum(p["area"] for p in eligible)
    if area<=0 or cfg.max_new_triangles<=0:
        return cfg.surface_resolution
    # Equilateral-ish estimate. Conservative factor accounts for real STL triangles.
    budget_edge=math.sqrt(max(area,1e-9)/(0.38*cfg.max_new_triangles))
    return max(cfg.surface_resolution,budget_edge)



def build_thickness_intersector(mesh, cfg):
    """
    Build a trimesh ray intersector when thin-wall protection is enabled.

    trimesh's pure-Python triangle ray intersector uses the `rtree` package
    for spatial indexing. We fail loudly rather than silently disabling wall
    protection.
    """
    if cfg.min_wall_thickness <= 0:
        return None

    try:
        import rtree  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "Thin-wall protection is enabled, but Python package 'rtree' is missing.\\n"
            "Install it with:\\n"
            "    pip install rtree\\n"
            "Then run the program again.\\n"
            "Or use --no-thickness-protection to run without this safety check."
        )

    from trimesh.ray.ray_triangle import RayMeshIntersector
    return RayMeshIntersector(mesh)


def measure_wall_thickness(points, direction, source_face_ids, mesh, intersector, cfg):
    """
    Measure local wall thickness in the deformation direction.

    Returns both the thickness and the original-mesh face which was hit.
    Knowing the opposing face lets us detect when BOTH sides of the same thin
    wall are eligible for texturing.
    """
    count = len(points)
    if count == 0:
        return np.empty(0, dtype=float), np.empty(0, dtype=np.int64)

    direction = np.asarray(direction, dtype=float)
    dl = np.linalg.norm(direction)
    if dl <= 1e-12:
        return (
            np.full(count, np.inf, dtype=float),
            np.full(count, -1, dtype=np.int64),
        )
    direction = direction / dl

    eps = max(1e-6, cfg.thickness_ray_epsilon)
    origins = np.asarray(points, dtype=float) + direction[None, :] * eps
    directions = np.repeat(direction[None, :], count, axis=0)

    try:
        locations, ray_ids, tri_ids = intersector.intersects_location(
            origins,
            directions,
            multiple_hits=True,
        )
    except ModuleNotFoundError as e:
        if e.name == "rtree":
            raise RuntimeError(
                "Thin-wall protection needs Python package 'rtree'.\n"
                "Install it with: pip install rtree"
            ) from e
        raise

    result = np.full(count, np.inf, dtype=float)
    hit_face = np.full(count, -1, dtype=np.int64)
    if len(ray_ids) == 0:
        return result, hit_face

    ray_ids = np.asarray(ray_ids, dtype=np.int64)
    tri_ids = np.asarray(tri_ids, dtype=np.int64)
    locations = np.asarray(locations, dtype=float)

    source_mask = np.zeros(len(mesh.faces), dtype=bool)
    source_mask[np.asarray(source_face_ids, dtype=np.int64)] = True

    vec = locations - origins[ray_ids]
    distances = np.einsum("ij,j->i", vec, direction) + eps

    valid = (
        (distances > eps * 0.5)
        & (distances <= cfg.thickness_probe_max)
        & (~source_mask[tri_ids])
    )
    if not np.any(valid):
        return result, hit_face

    vr = ray_ids[valid]
    vd = distances[valid]
    vt = tri_ids[valid]

    # Sort by ray then distance; first item for a ray is its nearest hit.
    order = np.lexsort((vd, vr))
    vr = vr[order]
    vd = vd[order]
    vt = vt[order]

    first = np.ones(len(vr), dtype=bool)
    if len(vr) > 1:
        first[1:] = vr[1:] != vr[:-1]

    chosen_r = vr[first]
    result[chosen_r] = vd[first]
    hit_face[chosen_r] = vt[first]
    return result, hit_face


def apply_thickness_protection(depths, points, direction, source_face_ids,
                               mesh, intersector, cfg, source_face_labels):
    """
    Enforce minimum RESULTING wall thickness.

    Important safety case:
    if the opposing wall face is ALSO an eligible textured flat patch, both
    sides may be pushed inward independently.

    Example:
        original wall = 1.5 mm
        protected min = 1.3 mm
        available     = 0.2 mm

    It is NOT safe to let each side independently use 0.2 mm. That could remove
    0.4 mm in total and create a hole.

    For an opposing textured face, each side therefore receives HALF of the
    available budget. For a non-textured opposing face, the current side may
    use the full budget.

    skip:
        unsafe deformation is set to zero.

    clamp:
        unsafe deformation is reduced to the safe limit.
    """
    stats = {
        "rays": 0,
        "hits": 0,
        "opposing_textured_hits": 0,
        "protected_vertices": 0,
        "clamped_vertices": 0,
        "min_measured_thickness": None,
        "min_resulting_thickness": None,
    }

    if cfg.min_wall_thickness <= 0 or intersector is None:
        return depths, stats

    active = np.flatnonzero(depths > 1e-8)
    if len(active) == 0:
        return depths, stats

    thickness, hit_face = measure_wall_thickness(
        np.asarray(points)[active],
        direction,
        source_face_ids,
        mesh,
        intersector,
        cfg,
    )

    finite = np.isfinite(thickness)
    stats["rays"] = int(len(active))
    stats["hits"] = int(np.count_nonzero(finite))

    if np.any(finite):
        stats["min_measured_thickness"] = float(np.min(thickness[finite]))

    labels = np.asarray(source_face_labels, dtype=np.int64)
    opposing_textured = np.zeros(len(active), dtype=bool)
    valid_face = finite & (hit_face >= 0) & (hit_face < len(labels))
    if np.any(valid_face):
        opposing_textured[valid_face] = labels[hit_face[valid_face]] >= 0

    stats["opposing_textured_hits"] = int(np.count_nonzero(opposing_textured))

    required = cfg.min_wall_thickness + cfg.thickness_safety
    proposed = depths[active].copy()
    result_depth = proposed.copy()

    available_total = np.maximum(0.0, thickness - required)
    safe_limit = available_total.copy()

    # Reserve the other half of the material budget for damage coming from the
    # opposite textured surface.
    safe_limit[opposing_textured] *= 0.5

    unsafe = finite & (proposed > safe_limit + 1e-12)

    if cfg.thickness_mode == "clamp":
        changed = unsafe & (safe_limit < result_depth)
        result_depth[changed] = safe_limit[changed]
        stats["clamped_vertices"] = int(np.count_nonzero(changed))
        stats["protected_vertices"] = int(
            np.count_nonzero(changed & (safe_limit <= 1e-8))
        )
    else:
        result_depth[unsafe] = 0.0
        stats["protected_vertices"] = int(np.count_nonzero(unsafe))

    depths = depths.copy()
    depths[active] = result_depth

    if np.any(finite):
        remaining = thickness.copy()
        remaining[finite] -= result_depth[finite]
        two_sided = finite & opposing_textured
        remaining[two_sided] -= result_depth[two_sided]
        stats["min_resulting_thickness"] = float(np.min(remaining[finite]))

    return depths, stats


def _edge_key(a,b):
    a=int(a); b=int(b)
    return (a,b) if a<b else (b,a)


def conforming_refine(vertices,faces,labels,max_edge,max_iter,max_total_faces):
    """
    Adaptively subdivide long edges on eligible planar faces while also
    splitting any neighbour which shares a split edge.

    This is the key V2 behavior: no T-junction cracks are introduced at the
    boundary between a textured flat patch and untouched geometry.
    """
    vertices=np.asarray(vertices,dtype=float).copy()
    faces=np.asarray(faces,dtype=np.int64).copy()
    labels=np.asarray(labels,dtype=np.int64).copy()

    for iteration in range(max_iter):
        eligible_idx=np.flatnonzero(labels>=0)
        if len(eligible_idx)==0:
            break

        ef=faces[eligible_idx]
        edges=np.vstack((ef[:,[0,1]],ef[:,[1,2]],ef[:,[2,0]]))
        edge_pts=vertices[edges]
        lengths=np.linalg.norm(edge_pts[:,0]-edge_pts[:,1],axis=1)
        long_edges=edges[lengths>max_edge]

        if len(long_edges)==0:
            print(f"  Refinement complete after {iteration} iteration(s).")
            break

        long_edges=np.sort(long_edges,axis=1)
        long_edges=np.unique(long_edges,axis=0)

        # If the model is already over the requested budget, don't make another
        # enormous jump. The output is still valid; it just has a coarser patch.
        if len(faces)>=max_total_faces:
            print("  Triangle budget reached; stopping refinement.")
            break

        midpoint={}
        new_vertices=[]
        base=len(vertices)
        for i,(a,b) in enumerate(long_edges):
            key=(int(a),int(b))
            midpoint[key]=base+i
            new_vertices.append((vertices[a]+vertices[b])*0.5)

        vertices=np.vstack((vertices,np.asarray(new_vertices,dtype=float)))

        new_faces=[]
        new_labels=[]

        for tri,label in zip(faces,labels):
            a,b,c=map(int,tri)
            k0=_edge_key(a,b)
            k1=_edge_key(b,c)
            k2=_edge_key(c,a)
            m0=midpoint.get(k0)
            m1=midpoint.get(k1)
            m2=midpoint.get(k2)

            mask=(1 if m0 is not None else 0)|(2 if m1 is not None else 0)|(4 if m2 is not None else 0)

            if mask==0:
                kids=[(a,b,c)]
            elif mask==1:  # AB
                kids=[(a,m0,c),(m0,b,c)]
            elif mask==2:  # BC
                kids=[(b,m1,a),(m1,c,a)]
            elif mask==4:  # CA
                kids=[(c,m2,b),(m2,a,b)]
            elif mask==3:  # AB + BC
                kids=[(b,m1,m0),(a,m0,c),(m0,m1,c)]
            elif mask==6:  # BC + CA
                kids=[(c,m2,m1),(b,m1,a),(m1,m2,a)]
            elif mask==5:  # CA + AB
                kids=[(a,m0,m2),(c,m2,b),(m2,m0,b)]
            else:  # all 3
                kids=[(a,m0,m2),(m0,b,m1),(m2,m1,c),(m0,m1,m2)]

            new_faces.extend(kids)
            new_labels.extend([label]*len(kids))

        faces=np.asarray(new_faces,dtype=np.int64)
        labels=np.asarray(new_labels,dtype=np.int64)

        print(
            f"  refine {iteration+1}: "
            f"{len(long_edges):,} edges split -> {len(faces):,} triangles"
        )

    return vertices,faces,labels


def texture_refined_mesh(vertices,faces,labels,patch_by_id,cfg,rng,source_mesh,thickness_intersector,source_face_labels):
    """
    Move vertices inward only on eligible planar faces.
    Patch boundary vertices stay exactly fixed because the procedural field
    fades to zero at the original planar-patch boundary.
    """
    out=vertices.copy()
    patch_stats=[]

    # Find vertices shared between different face labels. These are hard
    # boundaries and are forced to remain unmoved as an extra safety measure.
    vertex_label_sets={}
    for tri,label in zip(faces,labels):
        for vi in tri:
            s=vertex_label_sets.get(int(vi))
            if s is None:
                vertex_label_sets[int(vi)]={int(label)}
            else:
                s.add(int(label))
    hard_boundary={vi for vi,s in vertex_label_sets.items() if len(s)>1}

    for seq,(pid,p) in enumerate(patch_by_id.items(),1):
        face_idx=np.flatnonzero(labels==pid)
        if len(face_idx)==0:
            continue
        vids=np.unique(faces[face_idx].ravel())

        delta=out[vids]-p["origin"][None,:]
        xs=delta@p["u"]
        ys=delta@p["v"]

        pts=shapely.points(xs,ys)
        dist=np.asarray(shapely.distance(pts,p["geom"].boundary),dtype=float)
        inside=np.asarray(shapely.covers(p["geom"],pts),dtype=bool)

        if cfg.edge_margin>0:
            t=np.clip(dist/cfg.edge_margin,0.,1.)
            fade=t*t*(3.-2.*t)
        else:
            fade=np.ones(len(vids),dtype=float)
        fade[~inside]=0.

        # Never move a vertex which is shared with another patch/non-flat face.
        for i,vi in enumerate(vids):
            if int(vi) in hard_boundary:
                fade[i]=0.

        ev=make_events(p,cfg,rng)
        depths=np.zeros(len(vids),dtype=float)

        for i,(x,y) in enumerate(zip(xs,ys)):
            if fade[i]<=0:
                continue
            depths[i]=local_depth(float(x),float(y),p,cfg,ev,float(fade[i]))

        deform_direction = -p["n"]
        depths, thickness_stats = apply_thickness_protection(
            depths,
            out[vids],
            deform_direction,
            p["faces"],
            source_mesh,
            thickness_intersector,
            cfg,
            source_face_labels,
        )

        out[vids]+=depths[:,None]*deform_direction[None,:]

        patch_stats.append({
            "id":int(pid),
            "area":float(p["area"]),
            "span":float(p["span"]),
            "faces_out":int(len(face_idx)),
            "vertices_touched":int(np.count_nonzero(depths>1e-7)),
            "max_depth_actual":float(depths.max()) if len(depths) else 0.,
            "mean_depth":float(depths.mean()) if len(depths) else 0.,
            "features":{k:len(v) for k,v in ev.items()},
            "thickness_protection":thickness_stats,
        })

        tmsg=""
        if (
            thickness_stats["protected_vertices"]
            or thickness_stats["clamped_vertices"]
            or thickness_stats.get("opposing_textured_hits", 0)
        ):
            tmsg=(
                f", thin protected {thickness_stats['protected_vertices']:,}"
                f", clamped {thickness_stats['clamped_vertices']:,}"
                f", two-sided checks {thickness_stats.get('opposing_textured_hits', 0):,}"
            )
        print(
            f"  patch {seq}/{len(patch_by_id)} ID={pid}: "
            f"{len(face_idx):,} tris, max depth {patch_stats[-1]['max_depth_actual']:.3f} mm"
            f"{tmsg}"
        )

    return out,patch_stats



def validate(cfg):
    if not cfg.input or not os.path.isfile(cfg.input):
        raise ValueError("Input STL does not exist.")
    if cfg.flat_angle_deg<=0 or cfg.flat_angle_deg>=45:
        raise ValueError("Flat angle must be >0 and <45 degrees.")
    if cfg.surface_resolution<=0:
        raise ValueError("Surface resolution must be >0.")
    if cfg.max_depth<=0:
        raise ValueError("Max depth must be >0.")
    if cfg.bottom_tolerance < 0:
        raise ValueError("Bottom tolerance cannot be negative.")
    if cfg.bottom_normal_angle_deg < 0 or cfg.bottom_normal_angle_deg > 90:
        raise ValueError("Bottom normal angle must be between 0 and 90 degrees.")
    cfg.clustering=clamp(cfg.clustering,0,1)
    cfg.scratch_direction_bias=clamp(cfg.scratch_direction_bias,0,1)


def print_analysis(mesh,patches,eligible,cfg,max_edge):
    print()
    print("="*72)
    print("PLANAR PATCH ANALYSIS")
    print("="*72)
    print(f"Input triangles:       {len(mesh.faces):,}")
    print(f"Input vertices:        {len(mesh.vertices):,}")
    print(f"Input watertight:      {mesh.is_watertight}")
    print(f"Planar patches found:  {len(patches):,}")
    bottom_skipped = sum(1 for p in patches if p.get("reason") == "build_plate_bottom")
    print(f"Eligible patches:      {len(eligible):,}")
    print(f"Bottom patches skipped:{bottom_skipped:>7,}")
    print(f"Eligible area:         {sum(p['area'] for p in eligible):,.1f} mm^2")
    print(f"Min flat area:         {cfg.min_flat_area:g} mm^2")
    print(f"Min flat span:         {cfg.min_flat_span:g} mm")
    print(f"Edge fade:             {cfg.edge_margin:g} mm")
    print(f"Protect bottom:        {cfg.skip_bottom}")
    if cfg.skip_bottom:
        print(f"Bottom plane tolerance:{cfg.bottom_tolerance:>7g} mm")
        print(f"Bottom horizontal tol: {cfg.bottom_normal_angle_deg:g} deg")
        skipped=[p for p in patches if p.get("reason")=="build_plate_bottom"]
        if skipped:
            print(f"Detected bottom Z:     {min(p.get('plane_z',0.0) for p in skipped):.3f} mm")
    print(f"Actual max edge:       {max_edge:.3f} mm")
    print(f"Thin-wall protection:  {cfg.min_wall_thickness > 0}")
    if cfg.min_wall_thickness > 0:
        print(f"Minimum final wall:    {cfg.min_wall_thickness:g} mm")
        print(f"Thickness safety:      {cfg.thickness_safety:g} mm")
        print(f"Thickness behavior:    {cfg.thickness_mode}")
        print(f"Thickness probe max:   {cfg.thickness_probe_max:g} mm")
    if max_edge>cfg.surface_resolution+1e-6:
        print(f"  (raised from requested {cfg.surface_resolution:g} mm to respect triangle budget)")
    print()

    top=sorted(eligible,key=lambda p:p["area"],reverse=True)[:15]
    if top:
        print("Largest eligible patches:")
        print("  ID       area       span      normal")
        for p in top:
            n=p["normal"]
            print(f"  {p['id']:>4}  {p['area']:>10.1f}  {p['span']:>8.1f}   ({n[0]: .2f},{n[1]: .2f},{n[2]: .2f})")


def main():
    parser=build_parser()
    args=parser.parse_args()

    cfg=Config()
    apply_preset(cfg,"worn")
    cfg.seed=secrets.randbits(32)

    if len(sys.argv)==1 or args.wizard:
        cfg=wizard(cfg)
    else:
        apply_args(cfg,args)
        if not cfg.output and cfg.input:
            cfg.output=str(Path(cfg.input).with_suffix(""))+"_metal_textured_v2.stl"

    validate(cfg)

    print(f"Loading: {cfg.input}")
    mesh=load_mesh(cfg.input)
    patches,eligible=analyze(mesh,cfg)
    max_edge=auto_resolution(cfg,eligible)
    print_analysis(mesh,patches,eligible,cfg,max_edge)

    report_path=str(Path(cfg.output).with_suffix(""))+"_report.json"

    if cfg.dry_run:
        if cfg.write_report:
            report={
                "program":"stl_flat_metal_texture_v2.py",
                "version":VERSION,
                "config":asdict(cfg),
                "input":{"triangles":len(mesh.faces),"vertices":len(mesh.vertices),"watertight":bool(mesh.is_watertight)},
                "eligible_patches":[{"id":p["id"],"area":p["area"],"span":p["span"],"normal":[float(x) for x in p["normal"]]} for p in eligible],
                "actual_surface_resolution":max_edge,
            }
            with open(report_path,"w") as f: json.dump(report,f,indent=2)
            print(f"Report: {report_path}")
        return

    if not eligible:
        raise RuntimeError("No eligible flat patches. Lower minimum area/span or loosen flat tolerance.")

    if len(sys.argv)==1 or args.wizard:
        if not ask_yes_no("\nTexture these flat patches now?",True):
            print("Cancelled.")
            return

    rng=random.Random(cfg.seed)

    if cfg.min_wall_thickness > 0:
        print("\nPreparing thin-wall thickness ray index...")
    thickness_intersector = build_thickness_intersector(mesh, cfg)

    # Label original faces with their eligible planar patch ID.
    labels=np.full(len(mesh.faces),-1,dtype=np.int64)
    patch_by_id={}
    for pinfo in eligible:
        pid=int(pinfo["id"])
        labels[pinfo["faces"]]=pid
        patch_by_id[pid]=pinfo

    t0=time.time()
    source_face_labels = labels.copy()
    target_total=len(mesh.faces)+cfg.max_new_triangles

    print("\nConforming local refinement...")
    rv,rf,rl=conforming_refine(
        np.asarray(mesh.vertices),
        np.asarray(mesh.faces),
        labels,
        max_edge,
        cfg.max_subdivide_iter,
        target_total,
    )

    print("\nApplying procedural damage...")
    dv,patch_stats=texture_refined_mesh(
        rv,rf,rl,patch_by_id,cfg,rng,mesh,thickness_intersector,source_face_labels
    )

    out=trimesh.Trimesh(vertices=dv,faces=rf,process=False)
    out.remove_unreferenced_vertices()

    print(f"\nExporting: {cfg.output}")
    out.export(cfg.output)

    moved_max=max((s["max_depth_actual"] for s in patch_stats),default=0.)
    weights=[max(1,s["vertices_touched"]) for s in patch_stats]
    moved_mean=np.average(
        [s["mean_depth"] for s in patch_stats],
        weights=weights
    ) if patch_stats else 0.

    print()
    print("="*72)
    print("DONE")
    print("="*72)
    print(f"Output triangles:      {len(out.faces):,}")
    print(f"Output vertices:       {len(out.vertices):,}")
    print(f"Output watertight:     {out.is_watertight}")
    total_thin_protected=sum(
        s.get("thickness_protection",{}).get("protected_vertices",0)
        for s in patch_stats
    )
    total_thin_clamped=sum(
        s.get("thickness_protection",{}).get("clamped_vertices",0)
        for s in patch_stats
    )
    total_two_sided=sum(
        s.get("thickness_protection",{}).get("opposing_textured_hits",0)
        for s in patch_stats
    )
    print(f"Maximum dent depth:    {moved_max:.3f} mm")
    print(f"Mean textured depth:   {moved_mean:.3f} mm")
    if cfg.min_wall_thickness > 0:
        print(f"Thin vertices skipped: {total_thin_protected:,}")
        if cfg.thickness_mode=="clamp":
            print(f"Thin vertices clamped: {total_thin_clamped:,}")
        print(f"Two-sided wall checks: {total_two_sided:,}")
    print(f"Seed:                  {cfg.seed}")
    print(f"Time:                  {time.time()-t0:.1f}s")

    if cfg.write_report:
        report={
            "program":"stl_flat_metal_texture_v2.py",
            "version":VERSION,
            "config":asdict(cfg),
            "input":{
                "triangles":int(len(mesh.faces)),
                "vertices":int(len(mesh.vertices)),
                "watertight":bool(mesh.is_watertight),
            },
            "output":{
                "triangles":int(len(out.faces)),
                "vertices":int(len(out.vertices)),
                "watertight":bool(out.is_watertight),
                "max_depth_actual":float(moved_max),
                "mean_textured_depth":float(moved_mean),
            },
            "actual_surface_resolution":float(max_edge),
            "patches":patch_stats,
        }
        with open(report_path,"w") as f:
            json.dump(report,f,indent=2)
        print(f"Report:                {report_path}")


if __name__=="__main__":
    main()
