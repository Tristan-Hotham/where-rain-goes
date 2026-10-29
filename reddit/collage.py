"""Reddit collage for Where Rain Goes (2400 x 3000 px). Run from the project folder: python3 reddit/collage.py
Every number comes from data/results.json; maps are drawn from the work/ grids (no web tiles)."""
import json, os, sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "code"))
import render as rd

F = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts") + "/"
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf"]:
    fm.fontManager.addfont(F + f)
DISP = fm.FontProperties(fname=F + "FrauncesVar.ttf", weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
BG, FG, MUT, RAIN = "#EDF2F1", "#14202B", "#5B6670", "#2361A8"
bgt = (237, 242, 241)
R = json.load(open(os.path.join(ROOT, "data", "results.json"))); U, W = R["uk"], R["world"]; D = R["derived"]
FULL = {"Irish Sea": "Irish Sea and St. George's Channel", "Inner Seas (west Scotland)": "Inner Seas off the West Coast of Scotland", "Atlantic Ocean": "North Atlantic Ocean"}
seac = lambda s: rd.SEA_HEX[FULL.get(s, s)]
SEA_ORDER = ["North Sea", "English Channel", "Celtic Sea", "Bristol Channel", "Irish Sea", "Inner Seas (west Scotland)", "Atlantic Ocean"]

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
fig.text(0.04, 0.968, "Which sea does your rain end up in?", fontproperties=DISP, fontsize=40, color=FG, va="top")
fig.text(0.04, 0.926, "Every place in Britain and Ireland, followed downhill to the sea. I modelled the path of the rain from every\n"
         "180 m square, along the Ordnance Survey's rivers, and coloured each square by the sea it finally reaches.",
         family=SER, fontsize=14.5, color=FG, va="top", linespacing=1.35)

# hero map
img, _ = rd.uk_image(step=2, hills=.45, rivers=3, bg=bgt, crop=(-10.6, 60.9, 1.9, 49.9))
ax = fig.add_axes([0.0, 0.30, 0.6, 0.575]); ax.imshow(img, interpolation="lanczos"); ax.axis("off")
gb = U["areas"]["Great Britain"]
h = [Patch(fc=seac(s), label=f"{s}   {gb[s]['share'] * 100:.0f}%" if gb[s]["share"] >= .02 else f"{s}   {gb[s]['share'] * 100:.1f}%") for s in SEA_ORDER]
fig.legend(handles=h, loc="upper left", bbox_to_anchor=(0.62, 0.885), frameon=False, prop={"family": MONO, "size": 11}, handlelength=1.3, labelspacing=.55,
           title="Share of Great Britain", title_fontproperties={"family": MONO, "size": 10.5}, alignment="left", labelcolor=FG)
H, Wd = img.shape[:2]
def ann(lat, lon, text, dx, dy, frac=None):
    import math
    NP = 256 * 2 ** 9
    G = np.load(os.path.join(ROOT, "work", "uk_grid.npz")); X0, Y0 = int(G["X0"]), int(G["Y0"])
    f = lambda la: (1 - math.log(math.tan(math.radians(la)) + 1 / math.cos(math.radians(la))) / math.pi) / 2 * NP - Y0
    cx = (lambda lo: (lo + 180) / 360 * NP - X0)
    c0, r0 = cx(-10.6), f(60.9)
    x, y = (cx(lon) - c0) / 2, (f(lat) - r0) / 2
    kw = dict(xytext=frac, textcoords="axes fraction") if frac else dict(xytext=(x + dx, y + dy))
    ax.annotate(text, xy=(x, y), **kw, family=MONO, fontsize=10, color=FG, ha="left",
                arrowprops=dict(arrowstyle="-", color=FG, lw=.8), bbox=dict(fc=BG, ec="none", alpha=.85, pad=1.5))
tp = U["gb_triple_points"][1]
ann(tp["lat"], tp["lon"], "Clyde Law: Clyde, Tweed\nand Annan, three seas", 0, 0, frac=(0.36, 0.60))
lg = U["longest_gb"]
ann(lg[0]["lat"], lg[0]["lon"], f"{lg[0]['km']:.0f} km to the sea\ndown the Severn", 0, 0, frac=(0.05, 0.10))
ann(lg[1]["lat"], lg[1]["lon"], f"{lg[1]['km']:.0f} km down the Thames;\n{U['thames_head_contrast']['km_west']:.1f} km west, {U['thames_head_contrast']['path_km']:.0f} km\nto the Bristol Channel", 120, 260)
ann(52.51, -2.09, "Dudley: a town\non the watershed", 230, -120)

# big numbers
tx = fig.add_axes([0.62, 0.30, 0.36, 0.40]); tx.axis("off")
notes = [(f"{D['gb_ns_share'] * 100:.0f}%", "of Great Britain drains to the North Sea.\nWales sends it none of its rain at all."),
         (f"{U['gb_north_sea_divide_km']:,.0f} km".replace(f"{U['gb_north_sea_divide_km']:,.0f}", f"{round(U['gb_north_sea_divide_km'], -1):,.0f}"),
          f"of North Sea divide, from the far north\nto Kent. Highest: {U['north_sea_divide_points']['highest']['elev_m']:,.0f} m by Ben Alder."),
         (f"{len(U['gb_triple_points'])}", "triple points on Great Britain, where\nthe land of three seas meets."),
         (f"{D['world_inland_share'] * 100:.0f}%", "of the world's land never drains to the\nsea, from the Caspian to Lake Eyre.")]
for (big, small), y in zip(notes, [1.0, 0.74, 0.48, 0.22]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=30, color=RAIN, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.085, small, family=SER, fontsize=12.5, color=FG, va="top", transform=tx.transAxes, linespacing=1.25)

# bottom row: world map and Clyde Law close-up
wimg, _ = rd.world_image(mode="ocean", step=3, bg=bgt, lat_top=80, lat_bot=-56)
a = fig.add_axes([0.03, 0.115, 0.6, 0.165]); a.imshow(wimg, interpolation="lanczos", aspect="auto"); a.axis("off")
fig.text(0.04, 0.285, "THE WORLD, BY OCEAN", family=MONO, fontsize=11, color=MUT)
oc = W["ocean_share"]
labs = [("Atlantic", "Atlantic"), ("Arctic", "Arctic"), ("Pacific", "Pacific"), ("Indian", "Indian"), ("Inland", "Inland (no outlet to the sea)")]
fig.legend(handles=[Patch(fc=rd.OCEAN_HEX[k], label=f"{k if k != 'Inland' else 'No outlet'} {oc[v]['share'] * 100:.0f}%") for k, v in labs],
           loc="upper left", bbox_to_anchor=(0.035, 0.113), ncol=5, frameon=False, prop={"family": MONO, "size": 10.5}, handlelength=1.1, columnspacing=1.2, labelcolor=FG)
cimg, _ = rd.uk_image(step=1, hills=.6, rivers=4, bg=bgt, crop=(tp["lon"] - .3, tp["lat"] + .16, tp["lon"] + .18, tp["lat"] - .16))
b = fig.add_axes([0.67, 0.115, 0.3, 0.165]); b.imshow(cimg, interpolation="lanczos", aspect="auto"); b.axis("off")
hh, ww = cimg.shape[:2]; b.plot(ww * .3 / .48, hh / 2, "o", ms=11, mfc="none", mec=FG, mew=1.8)
fig.text(0.67, 0.285, "CLYDE LAW, SOUTHERN UPLANDS", family=MONO, fontsize=11, color=MUT)
fig.text(0.67, 0.108, "Clyde (red), Tweed (blue), Annan (green)", family=MONO, fontsize=10, color=FG, va="top")

fig.text(0.04, 0.026, "Data: OS Open Rivers and OS Open Names (contain OS data © Crown copyright and database right 2026, OGL v3); AWS Terrain Tiles; IHO Sea Areas v3,\n"
         "Flanders Marine Institute (CC BY 4.0); world: HydroBASINS (incorporates HydroSHEDS v1 data © WWF 2006-2022, used under licence).\n"
         "A surface-flow model: groundwater, pumping and canals are ignored. Interactive map: maps.tristanhotham.com/where-rain-goes\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib.",
         family=MONO, fontsize=8.6, color=MUT, linespacing=1.45, va="bottom")
fig.savefig(os.path.join(ROOT, "reddit", "where_rain_goes.png"), facecolor=BG, dpi=200)
print("ok")
