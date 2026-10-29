"""Step 4. Two independent checks of the Britain and Ireland drainage map.

(a) OS Open Rivers network: each watercourse link that the network itself leads to a sea outlet (step 2) is compared with
    the sea the terrain flood gives to the cells it runs through. Agreement is by length of watercourse.
(b) HydroBASINS level 12: the finest HydroBASINS sub-basins (about 130 km2 on average) are traced to their basin outlet
    and given the IHO sea of that outlet (lumped coastal sub-basins cell by cell), on a 0.01 degree grid, then compared
    with the flood map cell by cell. Agreement is by area, for Great Britain and for Ireland.
Writes work/validation.json (read by step 6).
"""
import json, os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import importlib.util
G = np.load(os.path.join(WORK, "uk_grid.npz"))
lab, region = G["lab"], G["region"]; X0, Y0, W, H, Z = int(G["X0"]), int(G["Y0"]), int(G["W"]), int(G["H"]), int(G["Z"])
NPIX = 256 * 2 ** Z
def pix(lon, lat):
    lat = np.radians(np.asarray(lat, dtype=np.float64))
    return (((np.asarray(lon) + 180) / 360 * NPIX) - X0).astype(int), (((1 - np.log(np.tan(lat) + 1 / np.cos(lat)) / np.pi) / 2 * NPIX) - Y0).astype(int)
SEAS = json.load(open(os.path.join(WORK, "uk_chains.json")))["seas"]
out = {}

# (a) network
Lk = np.load(os.path.join(WORK, "links.npz"), allow_pickle=True)
offs, vlon, vlat, sea, length, canal = Lk["offs"], Lk["lon"], Lk["lat"], Lk["sea"], Lk["length"], Lk["canal"]
agree = dis = 0.0; conf = {}
for k in range(len(offs) - 1):
    if canal[k] or sea[k] < 0: continue
    a, b = offs[k], offs[k + 1]
    c, r = pix(vlon[a:b], vlat[a:b]); ok = (c >= 0) & (c < W) & (r >= 0) & (r < H)
    if not ok.any(): continue
    l = lab[r[ok], c[ok]].astype(int) - 1
    l = l[l >= 0]
    if not len(l): continue
    v = np.bincount(l).argmax()
    if v == sea[k]: agree += length[k]
    else:
        dis += length[k]; key = f"{SEAS[sea[k]]} -> {SEAS[v]}"; conf[key] = conf.get(key, 0) + length[k] / 1000
n_all = (~canal).sum(); n_routed = ((~canal) & (sea >= 0)).sum()
out["network"] = dict(links=int(n_all), links_routed=int(n_routed), km_routed=float(length[(~canal) & (sea >= 0)].sum() / 1000),
                      km_all=float(length[~canal].sum() / 1000), agree_km=agree / 1000, disagree_km=dis / 1000,
                      agree_share=agree / (agree + dis), top_confusions=sorted(conf.items(), key=lambda x: -x[1])[:8])
print(out["network"])

# (b) HydroBASINS level 12
B = load_bundle(); U = B["ukie"]
idx = decode_grid(U); cols = U["basins"]; N = len(cols["HYBAS_ID"])
hid = np.array(cols["HYBAS_ID"], dtype=np.int64); pos = {int(h): i for i, h in enumerate(hid)}
mainb = np.array([pos.get(int(v), -1) for v in cols["MAIN_BAS"]]); coast = np.array(cols["COAST"]); endo = np.array(cols["ENDO"])
PP = load_bundle("wrg_pourpoints.json.gz")["data"]["lev12"]
cnt = {}; pt = {}
for h, x, y in PP["window_all"]:
    cnt[h] = cnt.get(h, 0) + 1; pt.setdefault(h, (x, y))
# IHO sea on the 0.01 degree grid
x0, y0, res, Wd, Hd = U["x0"], U["y0"], U["res"], U["W"], U["H"]
sea_g = np.zeros((Hd, Wd), np.uint8)
for k, f in enumerate(B["iho"]):
    rasterise(unwrap_dateline(f["g"]), sea_g, x0, y0, res, k + 1)
sc = (idx == 0) & (sea_g > 0)
near = ndimage.distance_transform_edt(~sc, return_distances=False, return_indices=True)
nearsea = sea_g[near[0], near[1]]
bsea = np.zeros(N, np.int64)
for i in range(N):
    m = mainb[i]
    if m < 0: continue
    h = int(hid[m])
    if endo[m] == 2: bsea[i] = -1; continue
    if cnt.get(h, 0) == 1:
        x, y = pt[h]; c = int((x - x0) / res); r = int((y0 - y) / res)
        if 0 <= r < Hd and 0 <= c < Wd: bsea[i] = nearsea[r, c]
hb = np.zeros((Hd, Wd), np.int64)
m = idx > 0
hb[m] = bsea[idx[m] - 1]
pc = m & (hb == 0)
hb[pc] = nearsea[pc]
# compare at each 0.01 degree cell centre
rr, cc = np.nonzero(m)
lon = x0 + (cc + 0.5) * res; lat = y0 - (rr + 0.5) * res
c9, r9 = pix(lon, lat); ok = (c9 >= 0) & (c9 < W) & (r9 >= 0) & (r9 < H)
rr, cc, c9, r9 = rr[ok], cc[ok], c9[ok], r9[ok]
reg = region[r9, c9]; fl = lab[r9, c9].astype(int); hv = hb[rr, cc]
area = cell_area_km2(y0 - (rr + 0.5) * res, res)
for rid, nm in ((1, "great_britain"), (2, "ireland")):
    s = (reg == rid) & (fl > 0) & (hv > 0)
    a = area[s].sum(); ag = area[s & (fl == hv)].sum()
    conf = {}
    for f_, h_, ar in zip(fl[s & (fl != hv)], hv[s & (fl != hv)], area[s & (fl != hv)]):
        key = f"{SEAS[h_ - 1]} (HydroBASINS) vs {SEAS[f_ - 1]} (this map)"; conf[key] = conf.get(key, 0) + ar
    out["hydrobasins_" + nm] = dict(km2_compared=float(a), agree_share=float(ag / a), top_differences=sorted(((k, round(v)) for k, v in conf.items()), key=lambda x: -x[1])[:6])
    print(nm, out["hydrobasins_" + nm])
np.savez_compressed(os.path.join(WORK, "hb12_ukie.npz"), hb=hb.astype(np.int16))
json.dump(out, open(os.path.join(WORK, "validation.json"), "w"), indent=1)
