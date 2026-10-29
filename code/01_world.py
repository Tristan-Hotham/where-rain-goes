"""Step 1. The world: which sea does each place drain to?

Inputs (browser bundles in RAW, see README): HydroBASINS v1c level 7 rasterised to a 0.05 degree grid with its attribute
table, HydroBASINS level 7 pour points, Marine Regions IHO Sea Areas v3 (simplified), Natural Earth rivers and lakes.

Method:
  * Every level 7 sub-basin is followed downstream (NEXT_DOWN) to its next sink (NEXT_SINK): the first endorheic
    sink below it if there is one, otherwise the most downstream polygon of its river basin.
  * If that polygon is an endorheic sink (ENDO = 2) the sub-basin drains inland.
  * Otherwise the basin reaches the sea at the pour point of that sink (a single point for a river basin). The sea is the
    IHO sea area of the nearest sea cell to that point. Lumped coastal sub-basins (many small outlets, several pour
    points) are assigned cell by cell to the IHO sea of the nearest sea cell.
  * Distance: HydroBASINS DIST_SINK (river km from the sub-basin outlet to its next sink) plus the straight line from
    the cell to the sub-basin's own pour point (a lower bound for the path inside the sub-basin).
Writes work/world_*.npy and work/world_basins.json for later steps.
"""
import json, os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

B = load_bundle()
G = B["world"]; X0, Y0, RES, W, H = G["x0"], G["y0"], G["res"], G["W"], G["H"]
idx = decode_grid(G)                         # 1-based basin row, 0 = no basin
cols = G["basins"]; N = len(cols["HYBAS_ID"])
print("basins", N, "cells", (idx > 0).sum())
hid = np.array(cols["HYBAS_ID"], dtype=np.int64)
pos = {int(h): i for i, h in enumerate(hid)}
nd = np.array([pos.get(int(v), -1) if v else -1 for v in cols["NEXT_DOWN"]])
# routing ends at the next sink: an endorheic sink (ENDO = 2) if there is one downstream, otherwise the basin outlet at
# the sea. HydroBASINS links some endorheic sinks onward with 'virtual' connections (the Caspian Sea, for example);
# rain that reaches an inland sink does not reach the sea, so I stop there.
mainb = np.array([pos[int(v)] for v in cols["NEXT_SINK"]])
endo = np.array(cols["ENDO"], dtype=np.int64); coast = np.array(cols["COAST"], dtype=np.int64)
dist_main = np.array(cols["DIST_SINK"], dtype=np.float64); sub_area = np.array(cols["SUB_AREA"], dtype=np.float64)
up_area = np.array(cols["UP_AREA"], dtype=np.float64)
nextsink = np.array([pos.get(int(v), -1) for v in cols["NEXT_SINK"]])

# --- IHO seas raster (sea cells only) ---
iho = B["iho"]; SEAS = [f["p"]["name"] for f in iho]
sea = np.zeros((H, W), np.uint8)
for k, f in enumerate(iho):
    rasterise(unwrap_dateline(f["g"]), sea, X0, Y0, RES, k + 1)
# a few sub-basin polygons (18 of 57,646) fill stray runs of cells far out at sea when rasterised; any basin cell
# lying more than 3 cells inside an IHO sea area is removed
core = ndimage.binary_erosion(sea > 0, iterations=3)
stray = (idx > 0) & core
stray[int((90 + 60) / RES):, :] |= idx[int((90 + 60) / RES):, :] > 0     # HydroBASINS has no land south of 60 S
print("stray basin cells removed", stray.sum())
idx[stray] = 0
# fill rasterisation slivers: small patches inside land that are neither basin nor sea take the nearest basin
hole = (idx == 0) & (sea == 0)
lab, nl = ndimage.label(hole)
sizes = np.bincount(lab.ravel())
small = (lab > 0) & (sizes[lab] < 400)
nb = ndimage.distance_transform_edt(idx == 0, return_distances=False, return_indices=True)
idx[small] = idx[nb[0][small], nb[1][small]]
del nb
idx[int((90 + 60) / RES):, :] = 0      # no HydroBASINS land south of 60 S (the fill above can reach Antarctica)
# thin horizontal streaks (scanline artefacts of a few polygons, e.g. across the Denmark Strait): land at most 2 cells
# (10 km) thick north to south that runs on, in one row, for 20 cells (about 100 km) or more
thin = (idx > 0) & ~ndimage.binary_opening(idx > 0, structure=np.ones((3, 1), bool))
lab_s, _n = ndimage.label(thin, structure=[[0, 0, 0], [1, 1, 1], [0, 0, 0]])
run = np.bincount(lab_s.ravel())
streak = thin & (run[lab_s] >= 20)
idx[streak] = 0
print("streak cells removed", streak.sum())
print("filled sliver cells", small.sum(), "large water bodies left", (sizes[1:] >= 400).sum())
# The Caspian Sea is neither a HydroBASINS sub-basin nor an IHO sea: HydroSHEDS treats it like the ocean, so rivers such
# as the Volga end at its shore. It is a lake with no outlet, so water reaching it counts as inland (code CASPIAN).
CASPIAN = 250
holes = (idx == 0) & (sea == 0); holes[int((90 + 60) / RES):] = False
hl, _n = ndimage.label(holes)
casp = hl == hl[int((Y0 - 41.7) / RES), int((50.7 - X0) / RES)]
print("Caspian cells", casp.sum())
seacell = ((idx == 0) & (sea > 0)) | casp
print("sea cells", seacell.sum())
# nearest sea (or Caspian) cell for every cell
near = ndimage.distance_transform_edt(~seacell, return_distances=False, return_indices=True)
nearsea = np.where(casp[near[0], near[1]], CASPIAN, sea[near[0], near[1]]).astype(np.uint8)
del near

# --- pour points ---
PP = load_bundle("wrg_pourpoints.json.gz")
pp = {int(a): (b, c, n) for a, b, c, n in PP["data"]["lev07"]["first"]}
ppx = np.full(N, np.nan); ppy = np.full(N, np.nan); ppn = np.zeros(N, np.int64)
for i, h in enumerate(hid):
    if int(h) in pp: ppx[i], ppy[i], ppn[i] = pp[int(h)]
print("pour points matched", np.isfinite(ppx).sum(), "of", N)

def cell_of(lon, lat):
    c = int((lon - X0) / RES); r = int((Y0 - lat) / RES)
    return min(max(r, 0), H - 1), min(max(c, 0), W - 1)

# sea for each main basin outlet (single pour point)
inland = endo[mainb] == 2
basin_sea = np.zeros(N, np.int64)           # IHO index + 1 for river basins with one outlet; 0 = per cell / inland
for m in np.unique(mainb):
    if endo[m] == 2:
        continue
    if ppn[m] == 1 and np.isfinite(ppx[m]):
        r, c = cell_of(ppx[m], ppy[m]); basin_sea[m] = nearsea[r, c]
inland |= basin_sea[mainb] == CASPIAN
per_cell = (~inland) & (basin_sea[mainb] == 0)
print("inland basins (sub-basins)", inland.sum(), "per-cell coastal", per_cell.sum())

# --- per-cell result grid ---
land = idx > 0
b = idx - 1
seagrid = np.zeros((H, W), np.int16)        # 1..len(SEAS) = sea; -1 = inland
bl = b[land]
s = basin_sea[mainb[bl]].astype(np.int16)
pc = per_cell[bl]
# HydroBASINS lumps some far-flung islands into a sub-basin on another coast (Hawaii with an Alaskan sub-basin,
# the Kerguelen Islands with a Madagascan one). A cell far from its own sub-basin's pour point
# (more than 150 km plus twice the square root of the sub-basin area) is treated as a detached island draining
# straight to its nearest sea.
rr_, cc_ = np.nonzero(land)
dpp = haversine_km(Y0 - (rr_ + 0.5) * RES, X0 + (cc_ + 0.5) * RES, ppy[bl], ppx[bl])
detached = dpp > 150 + 2 * np.sqrt(sub_area[bl])
print("detached island cells", detached.sum())
pc = pc | detached
s[pc] = nearsea[land][pc]
s[inland[bl] & ~detached] = -1
s[s == CASPIAN] = -1
det = np.zeros((H, W), bool); det[rr_, cc_] = detached
seagrid[land] = s

lat = Y0 - (np.arange(H) + 0.5) * RES
area_row = cell_area_km2(lat, RES)
area = np.broadcast_to(area_row[:, None], (H, W))
print("land area km2", area[land].sum())

np.savez_compressed(os.path.join(WORK, "world_grids.npz"), idx=idx, sea=seagrid, nearsea=nearsea, iho=sea, detached=det)
json.dump(dict(SEAS=SEAS, hid=hid.tolist(), nd=nd.tolist(), main=mainb.tolist(), endo=endo.tolist(), coast=coast.tolist(),
               dist_main=dist_main.tolist(), sub_area=sub_area.tolist(), up_area=up_area.tolist(), nextsink=nextsink.tolist(),
               ppx=[None if not np.isfinite(v) else float(v) for v in ppx], ppy=[None if not np.isfinite(v) else float(v) for v in ppy],
               ppn=ppn.tolist(), basin_sea=basin_sea.tolist(), region=cols["region"]),
          open(os.path.join(WORK, "world_basins.json"), "w"))
# quick summary
tot = area[land].sum()
for k in np.argsort([-area[seagrid == k + 1].sum() for k in range(len(SEAS))])[:25]:
    print(f"{SEAS[k]:45s} {area[seagrid == k + 1].sum() / 1e6:8.2f} M km2")
print("inland", area[seagrid == -1].sum() / 1e6, "M km2", area[seagrid == -1].sum() / tot)
