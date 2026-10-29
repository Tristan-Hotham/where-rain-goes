"""Step 7. Compact grids and tables for the interactive page (data/page/).

Britain and Ireland (web-mercator zoom 8, every second cell of the zoom 9 model):
  uk_a.png  R = sea code (1..n, an index into page.json uk.sea, 0 = not land) + 16 if the path is 256 km or longer + 32 x region (1 GB, 2 Ireland, 3 Man); G = hill shading; B = river class
            (upstream area of the modelled flow path: 1 = 10 km2, 2 = 100 km2, 3 = 1,000 km2, 4 = 5,000 km2 or more)
  uk_b.png  R, G = name-chain number + 1 (0 = none); B = path length in km (mod 256)
World (0.1 degree, every second cell of the 0.05 degree grid, rows from 90 N):
  world_idx.png  RGB = HydroBASINS level 7 sub-basin row + 1 (0 = not land)
  world_sea.png  L = IHO sea number (1..), +128 when the cell drains straight to its nearest coast; 255 = inland basin
Plus page.json (sea names, colours, chains, sub-basin table, names) and places.json (search lists).
"""
import json, math, os, sys
import numpy as np, pandas as pd
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

PG = os.path.join(DATA, "page"); os.makedirs(PG, exist_ok=True)
G = np.load(os.path.join(WORK, "uk_grid.npz"))
lab, region, chain = G["lab"], G["region"], G["chain"]; dist = G["dist"].astype(np.float32) / 10   # stored in 0.1 km
elev = G["elev"].astype(np.float32); pix_m = G["pix_m"]
X0, Y0, W, H, Z = int(G["X0"]), int(G["Y0"]), int(G["W"]), int(G["H"]), int(G["Z"])
NP = 256 * 2 ** Z
landm = (lab > 0) & (region > 0)


rcls = np.load(os.path.join(WORK, "uk_rivers.npz"))["rcls"]

# hill shading (light from the north-west), zoom 9 then averaged to zoom 8
gy, gx = np.gradient(elev)
dzdx = gx / pix_m[:, None] * 2.5; dzdn = -gy / pix_m[:, None] * 2.5
alt = math.radians(45); lx, ly, lz = -math.cos(alt) * math.sqrt(.5), math.cos(alt) * math.sqrt(.5), math.sin(alt)
hs = np.clip((-dzdx * lx - dzdn * ly + lz) / np.sqrt(1 + dzdx ** 2 + dzdn ** 2), 0, 1)
H8, W8 = H // 2, W // 2
blk = lambda a: a[:H8 * 2, :W8 * 2].reshape(H8, 2, W8, 2)
hill = ((np.round(blk(hs).mean(axis=(1, 3)) * 31) * 255 / 31)).astype(np.uint8)   # 32 shades: smaller file
riv8 = blk(rcls).max(axis=(1, 3))
s = lambda a: a[:H8 * 2:2, :W8 * 2:2]
lab8_iho = np.where(s(region) > 0, s(lab), 0)
uk_seas = [int(v) for v in np.unique(lab8_iho[lab8_iho > 0])]          # IHO sea numbers present (1-based)
assert len(uk_seas) <= 15
lab8 = np.zeros(lab8_iho.shape, np.uint8)
for k, v in enumerate(uk_seas): lab8[lab8_iho == v] = k + 1          # compact code 1..n
d8 = np.round(s(dist)).astype(np.int32); d8[lab8 == 0] = 0
ch8 = (s(chain) + 1).astype(np.int32); ch8[lab8 == 0] = 0
A = np.dstack([lab8 + 16 * (d8 >= 256) + 32 * np.where(lab8 > 0, s(region), 0), np.where(lab8 > 0, hill, 0), np.where(lab8 > 0, riv8, 0)]).astype(np.uint8)
Bm = np.dstack([(ch8 >> 8) & 255, ch8 & 255, d8 % 256]).astype(np.uint8)
Image.fromarray(A, "RGB").save(os.path.join(PG, "uk_a.png"), optimize=True)
Image.fromarray(Bm, "RGB").save(os.path.join(PG, "uk_b.png"), optimize=True)
lat_of = lambda py: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * py / NP))))
uk_bounds = [[lat_of(Y0 + 2 * H8), X0 / NP * 360 - 180], [lat_of(Y0), (X0 + 2 * W8) / NP * 360 - 180]]
print("uk grid", W8, H8, os.path.getsize(os.path.join(PG, "uk_a.png")), os.path.getsize(os.path.join(PG, "uk_b.png")))

C = json.load(open(os.path.join(WORK, "uk_chains.json")))
used = np.unique(ch8[ch8 > 0]) - 1
# keep every chain reachable from a used one
keep = set()
for c in used:
    q = int(c)
    while q >= 0 and q not in keep: keep.add(q); q = C["ch_next"][q]
print("chains used", len(keep), "of", len(C["ch_name"]))
name_ids = sorted({C["ch_name"][q] for q in keep})
nmap = {n: i for i, n in enumerate(name_ids)}
names_used = [C["names"][n] for n in name_ids]
chains = {int(q): [nmap[C["ch_name"][q]], int(C["ch_next"][q])] for q in sorted(keep)}

# --- world ---
Wz = np.load(os.path.join(WORK, "world_grids.npz")); idx, sea, det = Wz["idx"], Wz["sea"], Wz["detached"]
Bj = json.load(open(os.path.join(WORK, "world_basins.json"))); SEAS = Bj["SEAS"]
WNJ = json.load(open(os.path.join(WORK, "world_names.json"))); wn = WNJ["bname"]
basin_sea = np.array(Bj["basin_sea"]); mainb = np.array(Bj["main"]); endo = np.array(Bj["endo"]); ppn = np.array(Bj["ppn"])
idx2 = idx[::2, ::2]; sea2 = sea[::2, ::2]; det2 = det[::2, ::2]
b2 = idx2 - 1
percell = (idx2 > 0) & ((basin_sea[mainb[np.maximum(b2, 0)]] == 0) | det2) & (sea2 > 0)
ws = np.zeros(idx2.shape, np.uint8)
ws[sea2 > 0] = sea2[sea2 > 0]; ws[percell] += 128; ws[sea2 == -1] = 255
v = idx2.astype(np.int64)
Image.fromarray(np.dstack([(v >> 16) & 255, (v >> 8) & 255, v & 255]).astype(np.uint8), "RGB").save(os.path.join(PG, "world_idx.png"), optimize=True)
Image.fromarray(ws, "L").save(os.path.join(PG, "world_sea.png"), optimize=True)
print("world", os.path.getsize(os.path.join(PG, "world_idx.png")), os.path.getsize(os.path.join(PG, "world_sea.png")))
wnames = sorted(set(n for n in wn if n)); wmap = {n: i for i, n in enumerate(wnames)}
IB = pd.read_csv(os.path.join(DATA, "world_inland_basins.csv"), keep_default_na=False)
hid = Bj["hid"]
inland_names = {}
RW = json.load(open(os.path.join(WORK, "results_world.json")))
ppx_ = np.array([np.nan if v is None else v for v in Bj["ppx"]]); ppy_ = np.array([np.nan if v is None else v for v in Bj["ppy"]])
for r in IB.itertuples():
    if r.lake == "Caspian Sea": continue
    m = int(np.nanargmin((ppx_ - r.sink_lon) ** 2 + (ppy_ - r.sink_lat) ** 2))
    inland_names[int(mainb[m])] = (f"Lake {r.lake}" if r.lake and not r.lake.startswith(("Lake", "Lago")) and "Sea" not in r.lake else (r.lake or "an inland basin")) + (f" in {r.country}" if r.country else "")
for m in np.unique(mainb[basin_sea[mainb] == 250]):
    inland_names[int(m)] = "the Caspian Sea"
ppx = np.array([np.nan if v is None else v for v in Bj["ppx"]]); ppy = np.array([np.nan if v is None else v for v in Bj["ppy"]])
for r in IB.itertuples():
    d = (ppx - r.sink_lon) ** 2 + (ppy - r.sink_lat) ** 2
    m = int(np.nanargmin(d))
    label = (r.lake if r.lake else "an inland basin") + (f" in {r.country}" if r.country else "")
    inland_names[int(mainb[m])] = label
basins = dict(nd=Bj["nd"], m=mainb.tolist(), d=[int(round(x)) for x in Bj["dist_main"]],
              x=[None if not np.isfinite(a) else round(float(a), 3) for a in ppx], y=[None if not np.isfinite(a) else round(float(a), 3) for a in ppy],
              one=[int(n == 1) for n in ppn], n=[wmap[n] if n else -1 for n in wn])
SHORT = {"Irish Sea and St. George's Channel": "Irish Sea", "Inner Seas off the West Coast of Scotland": "Inner Seas (west Scotland)",
         "North Atlantic Ocean": "Atlantic Ocean", "Mediterranean Sea - Eastern Basin": "Mediterranean (east)",
         "Mediterranean Sea - Western Basin": "Mediterranean (west)", "Balearic (Iberian Sea)": "Balearic Sea",
         "The Coastal Waters of Southeast Alaska and British Columbia": "Coastal waters of SE Alaska and BC",
         "Barentsz Sea": "Barents Sea", "Andaman or Burma Sea": "Andaman Sea", "Seto Naikai or Inland Sea": "Seto Inland Sea",
         "Eastern China Sea": "East China Sea", "Japan Sea": "Sea of Japan", "Molukka Sea": "Molucca Sea"}
page = dict(seas=SEAS, seas_short=[SHORT.get(s, s) for s in SEAS], ocean_of=[ocean_of(s) for s in SEAS],
            uk=dict(sea=[v - 1 for v in uk_seas], bounds=uk_bounds, w=int(W8), h=int(H8), names=names_used, chains=chains),
            world=dict(names=wnames, rank=[WNJ["rank"].get(n, 99) for n in wnames], basins=basins, inland=inland_names, w=int(idx2.shape[1]), h=int(idx2.shape[0])))
json.dump(page, open(os.path.join(PG, "page.json"), "w"), separators=(",", ":"), ensure_ascii=False)
print("page.json", os.path.getsize(os.path.join(PG, "page.json")))

# search lists
PL = pd.read_csv(os.path.join(DATA, "uk_places.csv"), keep_default_na=False)
tr = {"City": 3, "Town": 2, "Village": 1}
uk = [[r.name, r.county, round(r.lat, 4), round(r.lon, 4), tr[r.type]] for r in PL.itertuples()]
CT = pd.read_csv(os.path.join(DATA, "world_cities.csv"), keep_default_na=False, na_values=[""])
CT = CT[CT["pop"] >= 50000]
wc = [[r.name, r.cc, round(r.lat, 3), round(r.lon, 3), int(r.pop)] for r in CT.itertuples()]
json.dump(dict(uk=uk, world=wc), open(os.path.join(PG, "places.json"), "w"), separators=(",", ":"), ensure_ascii=False)
print("places.json", len(uk), len(wc), os.path.getsize(os.path.join(PG, "places.json")))
