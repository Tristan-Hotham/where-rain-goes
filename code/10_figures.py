"""Step 10. header.png (1200 x 630) and the static figures for the paper (release/paper/f_*.png, white, 200 dpi) and the
blog (release/blog/b_*.png, 1520 px wide, light background). Maps are drawn from work/ grids (no web tiles); every number
comes from data/results.json.
Run: FONT_DIR=/path/to/fonts python3 code/10_figures.py
"""
import json, os, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import render as rd

FD = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts")
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf"]:
    fm.fontManager.addfont(os.path.join(FD, f))
DISP = fm.FontProperties(fname=os.path.join(FD, "FrauncesVar.ttf"), weight=900)
plt.rcParams["font.family"] = "IBM Plex Mono"
R = json.load(open(os.path.join(DATA, "results.json"))); U, Wd = R["uk"], R["world"]
PO = os.path.join(ROOT, "release", "paper"); BO = os.path.join(ROOT, "release", "blog")
os.makedirs(PO, exist_ok=True); os.makedirs(BO, exist_ok=True)
FG, MUT, RULE, RAIN = "#14202B", "#5B6670", "#D5DCDC", "#2361A8"
BLOGBG = "#F3F5F4"
SEA_ORDER = ["North Sea", "English Channel", "Celtic Sea", "Bristol Channel", "Irish Sea", "Inner Seas (west Scotland)", "Atlantic Ocean"]
FULL = {"Irish Sea": "Irish Sea and St. George's Channel", "Inner Seas (west Scotland)": "Inner Seas off the West Coast of Scotland", "Atlantic Ocean": "North Atlantic Ocean"}
seac = lambda s: rd.SEA_HEX[FULL.get(s, s)]


def style(ax, grid="x"):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(MUT); ax.spines["bottom"].set_color(MUT)
    ax.tick_params(colors=FG, length=0, labelsize=11)
    if grid: ax.grid(axis=grid, color=RULE, lw=.8); ax.set_axisbelow(True)


def save(fig, name, blog):
    if blog: fig.savefig(os.path.join(BO, f"b_{name}.png"), dpi=160, facecolor=BLOGBG)
    else: fig.savefig(os.path.join(PO, f"f_{name}.png"), dpi=200, facecolor="white")
    plt.close(fig)


def bgc(blog):
    plt.rcParams["axes.facecolor"] = BLOGBG if blog else "white"
    return BLOGBG if blog else "white"


def sea_key(ax, seas, loc="upper left", fs=10.5, ncol=1):
    ax.legend(handles=[Patch(fc=seac(s), label=s) for s in seas], loc=loc, frameon=False, fontsize=fs, ncol=ncol, handlelength=1.2)


# --- Britain and Ireland map ---
def fig_britain(blog):
    b = (243, 245, 244) if blog else (255, 255, 255)
    img, _ = rd.uk_image(step=2, hills=.5, rivers=2, bg=b)
    fig = plt.figure(figsize=(9.5, 11.5), facecolor=bgc(blog)); ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(img, interpolation="lanczos"); ax.axis("off")
    sea_key(ax, SEA_ORDER, loc="upper left", fs=12)
    save(fig, "britain", blog)


def fig_triple(blog):
    """Close-up of Clyde Law, where the Clyde, Tweed and Annan begin."""
    b = (243, 245, 244) if blog else (255, 255, 255)
    p = U["gb_triple_points"][1]
    img, _ = rd.uk_image(step=1, hills=.6, rivers=4, crop=(p["lon"] - .5, p["lat"] + .22, p["lon"] + .3, p["lat"] - .22), bg=b)
    fig = plt.figure(figsize=(9.5, 7.2), facecolor=bgc(blog)); ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(img, interpolation="lanczos"); ax.axis("off")
    h, w = img.shape[:2]; cx = w * .5 / .8; ax.plot(cx, h / 2, "o", ms=16, mfc="none", mec=FG, mew=2.2)
    ax.text(cx + 22, h / 2 - 16, "Clyde Law", fontsize=14, color=FG, weight="medium", bbox=dict(fc="white", ec="none", alpha=.75, pad=2))
    sea_key(ax, ["Inner Seas (west Scotland)", "North Sea", "Irish Sea"], loc="lower left", fs=12)
    save(fig, "clyde_law", blog)


def fig_world(blog):
    b = (243, 245, 244) if blog else (255, 255, 255)
    img, _ = rd.world_image(mode="ocean", step=2, bg=b)
    fig = plt.figure(figsize=(9.5, 4.25), facecolor=bgc(blog)); ax = fig.add_axes([0, .02, 1, .98]); ax.imshow(img, interpolation="lanczos", aspect=1.0); ax.axis("off")
    labs = {"Atlantic": "Atlantic", "Pacific": "Pacific", "Indian": "Indian", "Arctic": "Arctic", "Inland": "No outlet (inland)"}
    ax.legend(handles=[Patch(fc=rd.OCEAN_HEX[k], label=v) for k, v in labs.items()], loc="lower left", frameon=False, fontsize=10.5, ncol=1, handlelength=1.2)
    save(fig, "world", blog)


def fig_nations(blog):
    order = ["England", "Scotland", "Wales", "Northern Ireland", "Ireland", "Great Britain"]
    fig, ax = plt.subplots(figsize=(9.5, 4.2), facecolor=bgc(blog)); fig.subplots_adjust(left=.19, right=.98, top=.86, bottom=.06)
    for i, n in enumerate(order[::-1]):
        x = 0
        for s in SEA_ORDER:
            v = U["areas"][n].get(s, {}).get("share", 0)
            if not v: continue
            ax.barh(i, v, left=x, color=seac(s), height=.72, edgecolor="white", lw=.6)
            if v > .06: ax.text(x + .01, i, f"{v * 100:.0f}%", va="center", fontsize=10.5, color="white" if s not in ("Celtic Sea", "English Channel") else FG)
            x += v
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order[::-1], fontsize=12); ax.set_xlim(0, 1); ax.set_xticks([])
    for s in ("top", "right", "bottom", "left"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.legend(handles=[Patch(fc=seac(s), label=s) for s in SEA_ORDER], loc="lower center", bbox_to_anchor=(.42, 1.0), ncol=4, frameon=False, fontsize=9.5, handlelength=1.1)
    save(fig, "nations", blog)


def fig_spine(blog):
    D = np.load(os.path.join(WORK, "ns_divide.npz"))
    fig, ax = plt.subplots(figsize=(9.5, 4.0), facecolor=bgc(blog)); fig.subplots_adjust(left=.08, right=.98, top=.95, bottom=.14)
    ax.scatter(D["lat"], D["elev"], s=1.2, color=RAIN, alpha=.35, lw=0)
    hi = U["north_sea_divide_points"]["highest"]
    ax.plot(hi["lat"], hi["elev_m"], "o", mfc="none", mec=FG, ms=8)
    ax.annotate(f"{hi['hill']}, {hi['elev_m']:,.0f} m", (hi["lat"], hi["elev_m"]), xytext=(-12, 2), textcoords="offset points", ha="right", fontsize=11)
    ax.set_xlabel("latitude (south to north)", fontsize=11, color=MUT); ax.set_ylabel("height (m)", fontsize=11, color=MUT)
    ax.set_xticks(range(51, 59)); ax.set_xticklabels([f"{t}° N" for t in range(51, 59)]); ax.set_ylim(0, 1250); style(ax, "y")
    save(fig, "spine", blog)


def fig_systems(blog):
    rows = U["river_systems_top"][:12][::-1]
    fig, ax = plt.subplots(figsize=(9.5, 5.2), facecolor=bgc(blog)); fig.subplots_adjust(left=.27, right=.97, top=.97, bottom=.1)
    ax.barh(range(len(rows)), [r["km2"] for r in rows], color=[seac(r["sea"]) for r in rows], height=.72)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r["name"].split(" (")[0] for r in rows], fontsize=11.5)
    for i, r in enumerate(rows): ax.text(r["km2"] + 120, i, f"{r['km2']:,.0f}", va="center", fontsize=10.5, color=MUT)
    ax.set_xlabel("land draining through the river's mouth (km²)", fontsize=11, color=MUT); style(ax, "x")
    sea_key(ax, [x for x in SEA_ORDER if x in {r["sea"] for r in rows}], loc="lower right", fs=10)
    save(fig, "systems", blog)


def fig_oceans(blog):
    o = Wd["ocean_share"]; keys = ["Atlantic", "Arctic", "Pacific", "Indian", "Inland (no outlet to the sea)"]
    fig, ax = plt.subplots(figsize=(9.5, 3.3), facecolor=bgc(blog)); fig.subplots_adjust(left=.17, right=.97, top=.95, bottom=.08)
    vals = [o[k]["share"] for k in keys][::-1]; names = ["Atlantic", "Arctic", "Pacific", "Indian", "No outlet"][::-1]
    ax.barh(range(5), vals, color=[rd.OCEAN_HEX["Inland" if n == "No outlet" else n] for n in names], height=.7)
    for i, v in enumerate(vals): ax.text(v + .005, i, f"{v * 100:.1f}%", va="center", fontsize=11.5)
    ax.set_yticks(range(5)); ax.set_yticklabels(names, fontsize=12); ax.set_xticks([]); ax.set_xlim(0, .42)
    for s in ("top", "right", "bottom"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    save(fig, "oceans", blog)


def header():
    BG = "#F3F5F4"
    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
    img, _ = rd.uk_image(step=3, hills=.5, rivers=1, bg=(243, 245, 244), crop=(-10.6, 60.9, 1.9, 49.9))
    ax = fig.add_axes([0.56, 0.02, 0.42, 0.96]); ax.imshow(img, interpolation="lanczos"); ax.axis("off")
    fig.text(0.045, 0.86, "DATA STUDY  ·  RIVERS AND SEAS", family="IBM Plex Mono", fontsize=12, color=MUT)
    fig.text(0.04, 0.80, "Where", fontproperties=DISP, fontsize=64, color=FG, va="top")
    fig.text(0.04, 0.62, "rain goes", fontproperties=DISP, fontsize=64, color=RAIN, va="top")
    gb = U["areas"]["Great Britain"]
    fig.text(0.045, 0.40, "Which sea does your rain end up in?\nEvery place in Britain, Ireland and the world,\n"
             f"followed downhill to the sea. {gb['North Sea']['share'] * 100:.0f}% of Great Britain\ndrains to the North Sea.",
             family="Source Serif 4", fontsize=17, color=FG, va="top", linespacing=1.35)
    fig.text(0.045, 0.06, "Dr Tristan Hotham · Independent researcher", family="IBM Plex Mono", fontsize=11.5, color=MUT)
    fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG)


if __name__ == "__main__":
    header()
    for blog in (False, True):
        for f in (fig_britain, fig_triple, fig_world, fig_nations, fig_spine, fig_systems):
            f(blog)
    print("figures done")
