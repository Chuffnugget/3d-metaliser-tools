#!/usr/bin/env python3
"""
metal_damage_stamp.py

Generate a watertight STL negative damage stamp for Boolean subtraction from
flat model surfaces. No third-party packages required.

Convention:
  target surface = Z 0
  target solid   = negative Z
  damage cutter  = negative Z
  backing block  = positive Z
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import secrets
import struct
import sys
import time
from dataclasses import dataclass, asdict

VERSION = "1.0"

PRESETS = {
    "subtle": dict(
        max_depth=0.45,
        uneven_amp=0.07, uneven_scale=28.0,
        secondary_amp=0.025, secondary_scale=8.0,
        dent_density=3.5, dent_diam=(12.0, 28.0), dent_depth=(0.10, 0.26),
        impact_density=0.7, impact_diam=(2.5, 6.0), impact_depth=(0.15, 0.32),
        scratch_density=5.0, scratch_len=(6.0, 24.0), scratch_width=(0.45, 0.8), scratch_depth=(0.10, 0.20),
        gouge_density=0.6, gouge_len=(5.0, 16.0), gouge_width=(0.8, 1.5), gouge_depth=(0.18, 0.32),
        pit_density=4.0, pit_diam=(0.7, 1.8), pit_depth=(0.10, 0.18),
    ),
    "worn": dict(
        max_depth=0.65,
        uneven_amp=0.14, uneven_scale=24.0,
        secondary_amp=0.055, secondary_scale=7.0,
        dent_density=6.5, dent_diam=(10.0, 30.0), dent_depth=(0.14, 0.42),
        impact_density=1.8, impact_diam=(2.5, 7.0), impact_depth=(0.20, 0.50),
        scratch_density=9.0, scratch_len=(5.0, 30.0), scratch_width=(0.45, 1.0), scratch_depth=(0.12, 0.28),
        gouge_density=1.8, gouge_len=(5.0, 18.0), gouge_width=(0.9, 2.0), gouge_depth=(0.22, 0.48),
        pit_density=10.0, pit_diam=(0.7, 2.1), pit_depth=(0.10, 0.24),
    ),
    "battered": dict(
        max_depth=0.90,
        uneven_amp=0.22, uneven_scale=20.0,
        secondary_amp=0.09, secondary_scale=5.5,
        dent_density=10.0, dent_diam=(8.0, 34.0), dent_depth=(0.18, 0.62),
        impact_density=4.0, impact_diam=(2.0, 8.0), impact_depth=(0.25, 0.75),
        scratch_density=16.0, scratch_len=(4.0, 34.0), scratch_width=(0.45, 1.2), scratch_depth=(0.14, 0.38),
        gouge_density=4.0, gouge_len=(4.0, 22.0), gouge_width=(1.0, 2.6), gouge_depth=(0.28, 0.68),
        pit_density=20.0, pit_diam=(0.6, 2.5), pit_depth=(0.12, 0.32),
    ),
    "abused": dict(
        max_depth=1.20,
        uneven_amp=0.32, uneven_scale=17.0,
        secondary_amp=0.14, secondary_scale=4.5,
        dent_density=14.0, dent_diam=(7.0, 38.0), dent_depth=(0.22, 0.85),
        impact_density=7.0, impact_diam=(1.8, 9.0), impact_depth=(0.30, 1.00),
        scratch_density=24.0, scratch_len=(3.0, 40.0), scratch_width=(0.4, 1.5), scratch_depth=(0.16, 0.48),
        gouge_density=7.0, gouge_len=(4.0, 28.0), gouge_width=(1.0, 3.0), gouge_depth=(0.32, 0.90),
        pit_density=35.0, pit_diam=(0.6, 3.0), pit_depth=(0.14, 0.42),
    ),
}

@dataclass
class Config:
    width: float = 100.0
    height: float = 100.0
    resolution: float = 0.50
    carrier: float = 2.0
    edge_margin: float = 5.0
    min_feature: float = 0.40
    base_cut: float = 0.0
    max_depth: float = 0.65
    intensity: float = 1.0
    seed: int = 1
    preset: str = "worn"
    output: str = "metal_damage_stamp.stl"
    json_sidecar: bool = True
    ascii_stl: bool = False

    # category amount multipliers
    uneven_amount: float = 1.0
    dent_amount: float = 1.0
    impact_amount: float = 1.0
    scratch_amount: float = 1.0
    gouge_amount: float = 1.0
    pit_amount: float = 1.0

    # distribution
    clustering: float = 0.35
    cluster_radius: float = 18.0

    # unevenness
    uneven_amp: float = 0.14
    uneven_scale: float = 24.0
    secondary_amp: float = 0.055
    secondary_scale: float = 7.0

    # dents
    dent_density: float = 6.5
    dent_diam_min: float = 10.0
    dent_diam_max: float = 30.0
    dent_depth_min: float = 0.14
    dent_depth_max: float = 0.42
    dent_oval_min: float = 0.45
    dent_oval_max: float = 1.00
    dent_softness: float = 2.0
    dent_irregularity: float = 0.12

    # impacts
    impact_density: float = 1.8
    impact_diam_min: float = 2.5
    impact_diam_max: float = 7.0
    impact_depth_min: float = 0.20
    impact_depth_max: float = 0.50
    impact_irregularity: float = 0.28

    # scratches
    scratch_density: float = 9.0
    scratch_len_min: float = 5.0
    scratch_len_max: float = 30.0
    scratch_width_min: float = 0.45
    scratch_width_max: float = 1.0
    scratch_depth_min: float = 0.12
    scratch_depth_max: float = 0.28
    scratch_curvature: float = 0.18
    scratch_direction_deg: float = 0.0
    scratch_direction_bias: float = 0.30

    # gouges
    gouge_density: float = 1.8
    gouge_len_min: float = 5.0
    gouge_len_max: float = 18.0
    gouge_width_min: float = 0.9
    gouge_width_max: float = 2.0
    gouge_depth_min: float = 0.22
    gouge_depth_max: float = 0.48
    gouge_curvature: float = 0.12

    # pitting
    pit_density: float = 10.0
    pit_diam_min: float = 0.7
    pit_diam_max: float = 2.1
    pit_depth_min: float = 0.10
    pit_depth_max: float = 0.24
    pit_irregularity: float = 0.32


def apply_preset(cfg: Config, name: str) -> None:
    cfg.preset = name
    p = PRESETS[name]
    cfg.max_depth = p["max_depth"]
    cfg.uneven_amp, cfg.uneven_scale = p["uneven_amp"], p["uneven_scale"]
    cfg.secondary_amp, cfg.secondary_scale = p["secondary_amp"], p["secondary_scale"]
    cfg.dent_density = p["dent_density"]
    cfg.dent_diam_min, cfg.dent_diam_max = p["dent_diam"]
    cfg.dent_depth_min, cfg.dent_depth_max = p["dent_depth"]
    cfg.impact_density = p["impact_density"]
    cfg.impact_diam_min, cfg.impact_diam_max = p["impact_diam"]
    cfg.impact_depth_min, cfg.impact_depth_max = p["impact_depth"]
    cfg.scratch_density = p["scratch_density"]
    cfg.scratch_len_min, cfg.scratch_len_max = p["scratch_len"]
    cfg.scratch_width_min, cfg.scratch_width_max = p["scratch_width"]
    cfg.scratch_depth_min, cfg.scratch_depth_max = p["scratch_depth"]
    cfg.gouge_density = p["gouge_density"]
    cfg.gouge_len_min, cfg.gouge_len_max = p["gouge_len"]
    cfg.gouge_width_min, cfg.gouge_width_max = p["gouge_width"]
    cfg.gouge_depth_min, cfg.gouge_depth_max = p["gouge_depth"]
    cfg.pit_density = p["pit_density"]
    cfg.pit_diam_min, cfg.pit_diam_max = p["pit_diam"]
    cfg.pit_depth_min, cfg.pit_depth_max = p["pit_depth"]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate a watertight negative metal-damage STL stamp. Run with no arguments for the wizard.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--wizard", action="store_true", help="Force wizard mode.")
    p.add_argument("--preset", choices=PRESETS.keys(), default=None)
    p.add_argument("--width", type=float)
    p.add_argument("--height", type=float)
    p.add_argument("--resolution", type=float, help="Grid spacing in mm; lower = smoother/larger STL.")
    p.add_argument("--carrier", type=float, help="Backing thickness in +Z, mm.")
    p.add_argument("--edge-margin", type=float, help="Damage fade distance at stamp edges, mm.")
    p.add_argument("--min-feature", type=float, help="Minimum printable lateral feature width, mm.")
    p.add_argument("--base-cut", type=float, help="Uniform penetration everywhere; normally 0.")
    p.add_argument("--max-depth", type=float, help="Hard maximum combined damage depth, mm.")
    p.add_argument("--intensity", type=float, help="Global multiplier for damage depths.")
    p.add_argument("--seed", type=int)
    p.add_argument("-o", "--output")
    p.add_argument("--ascii", action="store_true")
    p.add_argument("--no-json", action="store_true")

    for name in ("uneven", "dent", "impact", "scratch", "gouge", "pit"):
        p.add_argument(f"--{name}-amount", type=float, help=f"Quantity/amount multiplier for {name} damage; 0 disables.")

    p.add_argument("--clustering", type=float, help="0..1 clustering tendency.")
    p.add_argument("--cluster-radius", type=float, help="Typical cluster radius, mm.")

    p.add_argument("--uneven-amp", type=float)
    p.add_argument("--uneven-scale", type=float)
    p.add_argument("--secondary-amp", type=float)
    p.add_argument("--secondary-scale", type=float)

    p.add_argument("--dent-density", type=float, help="Dents per 100x100 mm.")
    p.add_argument("--dent-diam-min", type=float)
    p.add_argument("--dent-diam-max", type=float)
    p.add_argument("--dent-depth-min", type=float)
    p.add_argument("--dent-depth-max", type=float)
    p.add_argument("--dent-softness", type=float)
    p.add_argument("--dent-irregularity", type=float)

    p.add_argument("--impact-density", type=float)
    p.add_argument("--impact-diam-min", type=float)
    p.add_argument("--impact-diam-max", type=float)
    p.add_argument("--impact-depth-min", type=float)
    p.add_argument("--impact-depth-max", type=float)
    p.add_argument("--impact-irregularity", type=float)

    p.add_argument("--scratch-density", type=float)
    p.add_argument("--scratch-len-min", type=float)
    p.add_argument("--scratch-len-max", type=float)
    p.add_argument("--scratch-width-min", type=float)
    p.add_argument("--scratch-width-max", type=float)
    p.add_argument("--scratch-depth-min", type=float)
    p.add_argument("--scratch-depth-max", type=float)
    p.add_argument("--scratch-curvature", type=float)
    p.add_argument("--scratch-direction-deg", type=float)
    p.add_argument("--scratch-direction-bias", type=float)

    p.add_argument("--gouge-density", type=float)
    p.add_argument("--gouge-len-min", type=float)
    p.add_argument("--gouge-len-max", type=float)
    p.add_argument("--gouge-width-min", type=float)
    p.add_argument("--gouge-width-max", type=float)
    p.add_argument("--gouge-depth-min", type=float)
    p.add_argument("--gouge-depth-max", type=float)
    p.add_argument("--gouge-curvature", type=float)

    p.add_argument("--pit-density", type=float)
    p.add_argument("--pit-diam-min", type=float)
    p.add_argument("--pit-diam-max", type=float)
    p.add_argument("--pit-depth-min", type=float)
    p.add_argument("--pit-depth-max", type=float)
    p.add_argument("--pit-irregularity", type=float)
    return p


def apply_args(cfg: Config, a: argparse.Namespace) -> None:
    direct = [
        "width", "height", "resolution", "carrier", "edge_margin", "min_feature",
        "base_cut", "max_depth", "intensity", "output",
        "uneven_amount", "dent_amount", "impact_amount", "scratch_amount", "gouge_amount", "pit_amount",
        "clustering", "cluster_radius",
        "uneven_amp", "uneven_scale", "secondary_amp", "secondary_scale",
        "dent_density", "dent_diam_min", "dent_diam_max", "dent_depth_min", "dent_depth_max", "dent_softness", "dent_irregularity",
        "impact_density", "impact_diam_min", "impact_diam_max", "impact_depth_min", "impact_depth_max", "impact_irregularity",
        "scratch_density", "scratch_len_min", "scratch_len_max", "scratch_width_min", "scratch_width_max", "scratch_depth_min", "scratch_depth_max",
        "scratch_curvature", "scratch_direction_deg", "scratch_direction_bias",
        "gouge_density", "gouge_len_min", "gouge_len_max", "gouge_width_min", "gouge_width_max", "gouge_depth_min", "gouge_depth_max", "gouge_curvature",
        "pit_density", "pit_diam_min", "pit_diam_max", "pit_depth_min", "pit_depth_max", "pit_irregularity",
    ]
    for n in direct:
        v = getattr(a, n, None)
        if v is not None:
            setattr(cfg, n, v)
    if a.seed is not None:
        cfg.seed = a.seed
    if a.ascii:
        cfg.ascii_stl = True
    if a.no_json:
        cfg.json_sidecar = False


# ---------------- Wizard ----------------

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
            print("  Enter a number or press Enter.")


def ask_yes(label, default=False):
    d = "Y/n" if default else "y/N"
    while True:
        s = input(f"{label} [{d}]: ").strip().lower()
        if not s:
            return default
        if s in ("y", "yes"):
            return True
        if s in ("n", "no"):
            return False


def ask_choice(default="worn"):
    choices = ["subtle", "worn", "battered", "abused"]
    print("Damage preset:")
    for i, c in enumerate(choices, 1):
        print(f"  {i}) {c}" + (" [default]" if c == default else ""))
    while True:
        s = input(f"Choice [{choices.index(default)+1}]: ").strip()
        if not s:
            return default
        if s.isdigit() and 1 <= int(s) <= len(choices):
            return choices[int(s)-1]
        if s in choices:
            return s


def wizard(cfg: Config) -> Config:
    print("\nMETAL DAMAGE NEGATIVE-STAMP GENERATOR")
    print("Press Enter for defaults. Units are millimetres.\n")
    cfg.width = ask_float("Stamp width", cfg.width, 1)
    cfg.height = ask_float("Stamp height", cfg.height, 1)
    chosen = ask_choice(cfg.preset)
    # Preserve general geometry while swapping damage defaults.
    keep = {k: getattr(cfg, k) for k in ("width","height","resolution","carrier","edge_margin","min_feature","base_cut","intensity","seed","output","json_sidecar","ascii_stl")}
    apply_preset(cfg, chosen)
    for k, v in keep.items():
        setattr(cfg, k, v)

    print()
    cfg.resolution = ask_float("Surface resolution / grid spacing", cfg.resolution, 0.05)
    cfg.carrier = ask_float("Backing thickness", cfg.carrier, 0.1)
    cfg.edge_margin = ask_float("Damage fade at stamp edges", cfg.edge_margin, 0)
    cfg.min_feature = ask_float("Minimum printable feature width", cfg.min_feature, 0.05)
    cfg.max_depth = ask_float("Absolute maximum damage depth", cfg.max_depth, 0.01)
    cfg.intensity = ask_float("Global depth intensity", cfg.intensity, 0)

    print("\nAmount multipliers (0 disables):")
    cfg.uneven_amount = ask_float("  General unevenness", cfg.uneven_amount, 0)
    cfg.dent_amount = ask_float("  Broad dents", cfg.dent_amount, 0)
    cfg.impact_amount = ask_float("  Impacts/dings", cfg.impact_amount, 0)
    cfg.scratch_amount = ask_float("  Scratches/cuts", cfg.scratch_amount, 0)
    cfg.gouge_amount = ask_float("  Heavy gouges", cfg.gouge_amount, 0)
    cfg.pit_amount = ask_float("  Corrosion pitting", cfg.pit_amount, 0)

    s = input("\nRandom seed [random]: ").strip()
    cfg.seed = int(s) if s else secrets.randbits(32)

    if ask_yes("Advanced settings?", False):
        print("\n-- Distribution --")
        cfg.clustering = ask_float("Clustering 0..1", cfg.clustering, 0)
        cfg.cluster_radius = ask_float("Cluster radius", cfg.cluster_radius, 0.1)
        print("\n-- Unevenness --")
        cfg.uneven_amp = ask_float("Large unevenness amplitude", cfg.uneven_amp, 0)
        cfg.uneven_scale = ask_float("Large unevenness scale", cfg.uneven_scale, 0.1)
        cfg.secondary_amp = ask_float("Secondary unevenness amplitude", cfg.secondary_amp, 0)
        cfg.secondary_scale = ask_float("Secondary unevenness scale", cfg.secondary_scale, 0.1)
        print("\n-- Broad dents --")
        cfg.dent_density = ask_float("Dents per 100x100mm", cfg.dent_density, 0)
        cfg.dent_diam_min = ask_float("Dent min diameter", cfg.dent_diam_min, 0.1)
        cfg.dent_diam_max = ask_float("Dent max diameter", cfg.dent_diam_max, 0.1)
        cfg.dent_depth_min = ask_float("Dent min depth", cfg.dent_depth_min, 0)
        cfg.dent_depth_max = ask_float("Dent max depth", cfg.dent_depth_max, 0)
        cfg.dent_softness = ask_float("Dent softness", cfg.dent_softness, 0.1)
        cfg.dent_irregularity = ask_float("Dent edge irregularity", cfg.dent_irregularity, 0)
        print("\n-- Impacts --")
        cfg.impact_density = ask_float("Impacts per 100x100mm", cfg.impact_density, 0)
        cfg.impact_diam_min = ask_float("Impact min diameter", cfg.impact_diam_min, 0.1)
        cfg.impact_diam_max = ask_float("Impact max diameter", cfg.impact_diam_max, 0.1)
        cfg.impact_depth_min = ask_float("Impact min depth", cfg.impact_depth_min, 0)
        cfg.impact_depth_max = ask_float("Impact max depth", cfg.impact_depth_max, 0)
        print("\n-- Scratches/cuts --")
        cfg.scratch_density = ask_float("Scratches per 100x100mm", cfg.scratch_density, 0)
        cfg.scratch_len_min = ask_float("Scratch min length", cfg.scratch_len_min, 0.1)
        cfg.scratch_len_max = ask_float("Scratch max length", cfg.scratch_len_max, 0.1)
        cfg.scratch_width_min = ask_float("Scratch min width", cfg.scratch_width_min, 0.05)
        cfg.scratch_width_max = ask_float("Scratch max width", cfg.scratch_width_max, 0.05)
        cfg.scratch_depth_min = ask_float("Scratch min depth", cfg.scratch_depth_min, 0)
        cfg.scratch_depth_max = ask_float("Scratch max depth", cfg.scratch_depth_max, 0)
        cfg.scratch_curvature = ask_float("Scratch curvature", cfg.scratch_curvature, 0)
        cfg.scratch_direction_bias = ask_float("Direction bias 0..1", cfg.scratch_direction_bias, 0)
        cfg.scratch_direction_deg = ask_float("Preferred direction degrees", cfg.scratch_direction_deg)
        print("\n-- Gouges --")
        cfg.gouge_density = ask_float("Gouges per 100x100mm", cfg.gouge_density, 0)
        cfg.gouge_width_min = ask_float("Gouge min width", cfg.gouge_width_min, 0.05)
        cfg.gouge_width_max = ask_float("Gouge max width", cfg.gouge_width_max, 0.05)
        cfg.gouge_depth_min = ask_float("Gouge min depth", cfg.gouge_depth_min, 0)
        cfg.gouge_depth_max = ask_float("Gouge max depth", cfg.gouge_depth_max, 0)
        print("\n-- Pitting --")
        cfg.pit_density = ask_float("Pits per 100x100mm", cfg.pit_density, 0)
        cfg.pit_diam_min = ask_float("Pit min diameter", cfg.pit_diam_min, 0.05)
        cfg.pit_diam_max = ask_float("Pit max diameter", cfg.pit_diam_max, 0.05)
        cfg.pit_depth_min = ask_float("Pit min depth", cfg.pit_depth_min, 0)
        cfg.pit_depth_max = ask_float("Pit max depth", cfg.pit_depth_max, 0)

    s = input(f"\nOutput STL [{cfg.output}]: ").strip()
    if s:
        cfg.output = s
    cfg.json_sidecar = ask_yes("Write JSON settings sidecar?", True)
    cfg.ascii_stl = ask_yes("ASCII STL? (binary recommended)", False)
    if not ask_yes("Generate now?", True):
        raise SystemExit("Cancelled")
    return cfg


# ---------------- Math/noise ----------------

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

def lerp(a,b,t): return a + (b-a)*t

def fade5(t): return t*t*t*(t*(t*6-15)+10)

def smooth01(t):
    t = clamp(t,0,1)
    return t*t*(3-2*t)


def hash_noise(ix, iy, seed):
    n = (ix*374761393 + iy*668265263 + (seed & 0xffffffff)*2246822519) & 0xffffffff
    n ^= n >> 13
    n = (n*1274126177) & 0xffffffff
    n ^= n >> 16
    return n/4294967295.0*2.0 - 1.0


def value_noise(x,y,scale,seed):
    fx, fy = x/scale, y/scale
    ix, iy = math.floor(fx), math.floor(fy)
    tx, ty = fx-ix, fy-iy
    u, v = fade5(tx), fade5(ty)
    a = hash_noise(ix,iy,seed); b = hash_noise(ix+1,iy,seed)
    c = hash_noise(ix,iy+1,seed); d = hash_noise(ix+1,iy+1,seed)
    return lerp(lerp(a,b,u), lerp(c,d,u), v)


def fbm(x,y,scale,seed,octaves=3):
    total = asum = 0.0
    amp = 1.0
    for o in range(octaves):
        total += amp*value_noise(x,y,max(scale,1e-6),seed+1013*o)
        asum += amp
        amp *= 0.5
        scale *= 0.5
    return total/asum


def point_seg_dist(px,py,ax,ay,bx,by):
    abx, aby = bx-ax, by-ay
    denom = abx*abx + aby*aby
    if denom <= 1e-18:
        return math.hypot(px-ax,py-ay)
    t = clamp(((px-ax)*abx + (py-ay)*aby)/denom,0,1)
    qx, qy = ax+t*abx, ay+t*aby
    return math.hypot(px-qx,py-qy)


# ---------------- Features ----------------

def count_for(rng,density,amount,area):
    expected = max(0,density*amount*area/10000.0)
    n = int(expected)
    return n + (1 if rng.random() < expected-n else 0)


def make_centers(rng,cfg,n=3):
    mx = min(cfg.edge_margin,cfg.width*0.25); my = min(cfg.edge_margin,cfg.height*0.25)
    return [(rng.uniform(-cfg.width/2+mx,cfg.width/2-mx), rng.uniform(-cfg.height/2+my,cfg.height/2-my)) for _ in range(n)]


def pick_point(rng,cfg,centers):
    mx = min(cfg.edge_margin,cfg.width*0.25); my = min(cfg.edge_margin,cfg.height*0.25)
    xmin,xmax = -cfg.width/2+mx,cfg.width/2-mx
    ymin,ymax = -cfg.height/2+my,cfg.height/2-my
    if rng.random() < clamp(cfg.clustering,0,1):
        cx,cy = rng.choice(centers)
        return clamp(rng.gauss(cx,cfg.cluster_radius*0.45),xmin,xmax), clamp(rng.gauss(cy,cfg.cluster_radius*0.45),ymin,ymax)
    return rng.uniform(xmin,xmax), rng.uniform(ymin,ymax)


def ellipse_event(rng,cfg,centers,dmin,dmax,zmin,zmax,oval_min,oval_max,softness,irr):
    x,y = pick_point(rng,cfg,centers)
    major = rng.uniform(dmin,dmax)
    rx = major*0.5; ry = max(cfg.min_feature*0.5, rx*rng.uniform(oval_min,oval_max))
    if rng.random() < 0.5: rx,ry = ry,rx
    bound = max(rx,ry)*(1+irr*0.5)
    return dict(x=x,y=y,rx=rx,ry=ry,a=rng.uniform(0,math.pi),depth=rng.uniform(zmin,zmax),soft=softness,irr=irr,
                p1=rng.uniform(0,math.tau),p2=rng.uniform(0,math.tau),bbox=(x-bound,x+bound,y-bound,y+bound))


def ellipse_depth(x,y,e):
    xmin,xmax,ymin,ymax = e["bbox"]
    if x<xmin or x>xmax or y<ymin or y>ymax: return 0.0
    dx,dy = x-e["x"], y-e["y"]
    ca,sa = math.cos(e["a"]),math.sin(e["a"])
    xr,yr = ca*dx+sa*dy, -sa*dx+ca*dy
    ux,uy = xr/max(e["rx"],1e-9), yr/max(e["ry"],1e-9)
    th = math.atan2(uy,ux)
    mod = 1 + e["irr"]*(0.55*math.sin(3*th+e["p1"]) + 0.30*math.sin(5*th+e["p2"]) + 0.15*math.sin(7*th+e["p1"]*0.7))
    q = math.hypot(ux,uy)/max(0.55,mod)
    if q >= 1: return 0.0
    return e["depth"] * max(0,1-q*q)**e["soft"]


def chosen_angle(rng,cfg,bias_scale=1.0):
    if rng.random() < clamp(cfg.scratch_direction_bias*bias_scale,0,1):
        return math.radians(cfg.scratch_direction_deg + rng.gauss(0,18)) % math.pi
    return rng.uniform(0,math.pi)


def line_event(rng,cfg,centers,lmin,lmax,wmin,wmax,zmin,zmax,curvature,bias_scale):
    cx,cy = pick_point(rng,cfg,centers)
    L = rng.uniform(lmin,lmax); W = max(cfg.min_feature,rng.uniform(wmin,wmax)); D = rng.uniform(zmin,zmax)
    a = chosen_angle(rng,cfg,bias_scale)
    dx,dy = math.cos(a),math.sin(a); nx,ny = -dy,dx
    x0,y0 = cx-dx*L/2,cy-dy*L/2; x2,y2 = cx+dx*L/2,cy+dy*L/2
    off = rng.uniform(-1,1)*curvature*L; x1,y1 = cx+nx*off,cy+ny*off
    pts=[]
    for i in range(8):
        t=i/7; u=1-t
        pts.append((u*u*x0+2*u*t*x1+t*t*x2, u*u*y0+2*u*t*y1+t*t*y2))
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; pad=W*0.75
    return dict(points=pts,width=W,depth=D,bbox=(min(xs)-pad,max(xs)+pad,min(ys)-pad,max(ys)+pad))


def line_depth(x,y,e):
    xmin,xmax,ymin,ymax=e["bbox"]
    if x<xmin or x>xmax or y<ymin or y>ymax: return 0.0
    best=1e30; pts=e["points"]
    for i in range(len(pts)-1):
        best=min(best,point_seg_dist(x,y,*pts[i],*pts[i+1]))
    half=e["width"]*0.5
    if best>=half:return 0.0
    return e["depth"]*(1-best/max(half,1e-9))**1.7


def build_features(cfg):
    rng=random.Random(cfg.seed); area=cfg.width*cfg.height
    dc,ic,sc,gc,pc=[make_centers(rng,cfg) for _ in range(5)]
    nd=count_for(rng,cfg.dent_density,cfg.dent_amount,area)
    ni=count_for(rng,cfg.impact_density,cfg.impact_amount,area)
    ns=count_for(rng,cfg.scratch_density,cfg.scratch_amount,area)
    ng=count_for(rng,cfg.gouge_density,cfg.gouge_amount,area)
    np=count_for(rng,cfg.pit_density,cfg.pit_amount,area)
    dents=[ellipse_event(rng,cfg,dc,cfg.dent_diam_min,cfg.dent_diam_max,cfg.dent_depth_min,cfg.dent_depth_max,cfg.dent_oval_min,cfg.dent_oval_max,cfg.dent_softness,cfg.dent_irregularity) for _ in range(nd)]
    impacts=[ellipse_event(rng,cfg,ic,max(cfg.impact_diam_min,cfg.min_feature*1.5),cfg.impact_diam_max,cfg.impact_depth_min,cfg.impact_depth_max,0.55,1.0,1.25,cfg.impact_irregularity) for _ in range(ni)]
    scratches=[line_event(rng,cfg,sc,cfg.scratch_len_min,cfg.scratch_len_max,cfg.scratch_width_min,cfg.scratch_width_max,cfg.scratch_depth_min,cfg.scratch_depth_max,cfg.scratch_curvature,1.0) for _ in range(ns)]
    gouges=[line_event(rng,cfg,gc,cfg.gouge_len_min,cfg.gouge_len_max,cfg.gouge_width_min,cfg.gouge_width_max,cfg.gouge_depth_min,cfg.gouge_depth_max,cfg.gouge_curvature,0.65) for _ in range(ng)]
    pits=[ellipse_event(rng,cfg,pc,max(cfg.pit_diam_min,cfg.min_feature),cfg.pit_diam_max,cfg.pit_depth_min,cfg.pit_depth_max,0.65,1.0,1.20,cfg.pit_irregularity) for _ in range(np)]
    return dict(dents=dents,impacts=impacts,scratches=scratches,gouges=gouges,pits=pits,counts=dict(dents=nd,impacts=ni,scratches=ns,gouges=ng,pits=np))


# ---------------- Heightfield ----------------

def edge_fade(x,y,cfg):
    if cfg.edge_margin<=0:return 1.0
    d=min(x+cfg.width/2,cfg.width/2-x,y+cfg.height/2,cfg.height/2-y)
    return smooth01(d/cfg.edge_margin)


def depth_at(x,y,cfg,f):
    d=0.0
    if cfg.uneven_amount>0:
        n=fbm(x,y,cfg.uneven_scale,cfg.seed+5001,3); p=(0.5+0.5*n)**2
        d += cfg.uneven_amp*cfg.uneven_amount*(0.12+0.88*p)
        n=fbm(x,y,cfg.secondary_scale,cfg.seed+9001,2); p=(0.5+0.5*n)**2
        d += cfg.secondary_amp*cfg.uneven_amount*(0.08+0.92*p)
    for e in f["dents"]: d+=ellipse_depth(x,y,e)
    for e in f["impacts"]: d+=ellipse_depth(x,y,e)
    for e in f["scratches"]: d+=line_depth(x,y,e)
    for e in f["gouges"]: d+=line_depth(x,y,e)
    for e in f["pits"]: d+=ellipse_depth(x,y,e)
    d=min(cfg.max_depth,max(0,d*cfg.intensity+cfg.base_cut))
    return d*edge_fade(x,y,cfg)


def make_field(cfg,f):
    nx=max(2,int(math.ceil(cfg.width/cfg.resolution))+1); ny=max(2,int(math.ceil(cfg.height/cfg.resolution))+1)
    dx=cfg.width/(nx-1); dy=cfg.height/(ny-1)
    xs=[-cfg.width/2+i*dx for i in range(nx)]; ys=[-cfg.height/2+j*dy for j in range(ny)]
    z=[]; nextp=10
    print(f"Sampling {nx} x {ny} = {nx*ny:,} surface points...")
    for j,y in enumerate(ys):
        z.append([-depth_at(x,y,cfg,f) for x in xs])
        pct=int((j+1)*100/ny)
        if pct>=nextp:
            print(f"  {pct}%"); nextp+=10
    return xs,ys,z,dx,dy


# ---------------- STL ----------------

def normal(a,b,c):
    ux,uy,uz=b[0]-a[0],b[1]-a[1],b[2]-a[2]; vx,vy,vz=c[0]-a[0],c[1]-a[1],c[2]-a[2]
    nx=uy*vz-uz*vy; ny=uz*vx-ux*vz; nz=ux*vy-uy*vx; L=math.sqrt(nx*nx+ny*ny+nz*nz)
    return (0,0,0) if L<1e-20 else (nx/L,ny/L,nz/L)


def tri_count(nx,ny): return 4*(nx-1)*(ny-1)+4*(nx-1)+4*(ny-1)


def triangles(xs,ys,z,cfg):
    nx,ny=len(xs),len(ys); top=cfg.carrier
    # bottom, outward -Z
    for j in range(ny-1):
        for i in range(nx-1):
            b00=(xs[i],ys[j],z[j][i]); b10=(xs[i+1],ys[j],z[j][i+1]); b11=(xs[i+1],ys[j+1],z[j+1][i+1]); b01=(xs[i],ys[j+1],z[j+1][i])
            yield b00,b11,b10; yield b00,b01,b11
    # top +Z
    for j in range(ny-1):
        for i in range(nx-1):
            t00=(xs[i],ys[j],top);t10=(xs[i+1],ys[j],top);t11=(xs[i+1],ys[j+1],top);t01=(xs[i],ys[j+1],top)
            yield t00,t10,t11;yield t00,t11,t01
    # south -Y
    y=ys[0]
    for i in range(nx-1):
        b0=(xs[i],y,z[0][i]);b1=(xs[i+1],y,z[0][i+1]);t0=(xs[i],y,top);t1=(xs[i+1],y,top)
        yield b0,b1,t1;yield b0,t1,t0
    # north +Y
    y=ys[-1]
    for i in range(nx-1):
        b0=(xs[i],y,z[-1][i]);b1=(xs[i+1],y,z[-1][i+1]);t0=(xs[i],y,top);t1=(xs[i+1],y,top)
        yield b0,t1,b1;yield b0,t0,t1
    # west -X
    x=xs[0]
    for j in range(ny-1):
        b0=(x,ys[j],z[j][0]);b1=(x,ys[j+1],z[j+1][0]);t0=(x,ys[j],top);t1=(x,ys[j+1],top)
        yield b0,t1,b1;yield b0,t0,t1
    # east +X
    x=xs[-1]
    for j in range(ny-1):
        b0=(x,ys[j],z[j][-1]);b1=(x,ys[j+1],z[j+1][-1]);t0=(x,ys[j],top);t1=(x,ys[j+1],top)
        yield b0,b1,t1;yield b0,t1,t0


def write_binary(path,xs,ys,z,cfg):
    count=tri_count(len(xs),len(ys)); header=f"Metal damage stamp v{VERSION} seed={cfg.seed}".encode()[:80].ljust(80,b"\0")
    with open(path,"wb") as out:
        out.write(header); out.write(struct.pack("<I",count))
        for a,b,c in triangles(xs,ys,z,cfg):
            n=normal(a,b,c)
            out.write(struct.pack("<12fH",n[0],n[1],n[2],*a,*b,*c,0))
    return count


def write_ascii(path,xs,ys,z,cfg):
    count=tri_count(len(xs),len(ys))
    with open(path,"w",encoding="ascii") as out:
        out.write("solid metal_damage_stamp\n")
        for a,b,c in triangles(xs,ys,z,cfg):
            n=normal(a,b,c); out.write(f"  facet normal {n[0]:.8g} {n[1]:.8g} {n[2]:.8g}\n    outer loop\n")
            for v in (a,b,c): out.write(f"      vertex {v[0]:.8g} {v[1]:.8g} {v[2]:.8g}\n")
            out.write("    endloop\n  endfacet\n")
        out.write("endsolid metal_damage_stamp\n")
    return count


def validate(c):
    if c.width<=0 or c.height<=0 or c.resolution<=0 or c.carrier<=0 or c.max_depth<=0 or c.min_feature<=0: raise ValueError("Dimensions/resolution/carrier/max-depth/min-feature must be positive")
    c.clustering=clamp(c.clustering,0,1); c.scratch_direction_bias=clamp(c.scratch_direction_bias,0,1)
    # Ensure min<=max and printable widths.
    pairs=[("dent_diam_min","dent_diam_max"),("dent_depth_min","dent_depth_max"),("impact_diam_min","impact_diam_max"),("impact_depth_min","impact_depth_max"),("scratch_len_min","scratch_len_max"),("scratch_width_min","scratch_width_max"),("scratch_depth_min","scratch_depth_max"),("gouge_len_min","gouge_len_max"),("gouge_width_min","gouge_width_max"),("gouge_depth_min","gouge_depth_max"),("pit_diam_min","pit_diam_max"),("pit_depth_min","pit_depth_max")]
    for a,b in pairs:
        if getattr(c,a)>getattr(c,b):
            va,vb=getattr(c,a),getattr(c,b);setattr(c,a,vb);setattr(c,b,va)
    c.scratch_width_min=max(c.scratch_width_min,c.min_feature); c.scratch_width_max=max(c.scratch_width_max,c.scratch_width_min)
    c.gouge_width_min=max(c.gouge_width_min,c.min_feature); c.gouge_width_max=max(c.gouge_width_max,c.gouge_width_min)
    c.pit_diam_min=max(c.pit_diam_min,c.min_feature); c.pit_diam_max=max(c.pit_diam_max,c.pit_diam_min)


def main():
    a=parser().parse_args(); c=Config(); apply_preset(c,a.preset or "worn"); c.seed=a.seed if a.seed is not None else secrets.randbits(32); apply_args(c,a)
    if len(sys.argv)==1 or a.wizard: c=wizard(c)
    validate(c)
    if not c.output.lower().endswith(".stl"): c.output += ".stl"
    path=os.path.abspath(c.output); os.makedirs(os.path.dirname(path) or ".",exist_ok=True)
    nx=max(2,int(math.ceil(c.width/c.resolution))+1); ny=max(2,int(math.ceil(c.height/c.resolution))+1); nt=tri_count(nx,ny)
    print(f"\nPreset: {c.preset} | Size: {c.width:g}x{c.height:g} mm | Grid: {nx}x{ny} | Triangles: {nt:,} | Seed: {c.seed}")
    if nt>2_000_000: print("WARNING: very large STL; increase --resolution if needed.")
    t=time.time(); f=build_features(c); print("Features:",", ".join(f"{k}={v}" for k,v in f["counts"].items()))
    xs,ys,z,dx,dy=make_field(c,f); print("Writing STL...")
    written=write_ascii(path,xs,ys,z,c) if c.ascii_stl else write_binary(path,xs,ys,z,c)
    side=None
    if c.json_sidecar:
        side=os.path.splitext(path)[0]+".json"
        meta=dict(program="metal_damage_stamp.py",version=VERSION,units="mm",surface_plane="Z=0",damage_direction="-Z",backing_direction="+Z",config=asdict(c),mesh=dict(nx=len(xs),ny=len(ys),dx=dx,dy=dy,triangles=written),generated_counts=f["counts"])
        with open(side,"w",encoding="utf8") as out: json.dump(meta,out,indent=2,sort_keys=True)
    print(f"DONE: {path} ({os.path.getsize(path)/1048576:.1f} MB) in {time.time()-t:.1f}s")
    if side: print("Settings:",side)
    print("Import it, put Z=0 against the panel, then Boolean Difference / Hole it from the model.")

if __name__=="__main__":
    main()
