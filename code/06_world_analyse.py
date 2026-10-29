"""Step 6. Numbers for the world: land by ocean and sea, inland basins, longest journeys, ocean triple points,
countries and cities. Writes data/world_*.csv, work/world_page.npz and work/results_world.json.
"""
import io, json, math, os, sys, zipfile
import numpy as np, pandas as pd
from scipy import ndimage
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

Gz = np.load(os.path.join(WORK, "world_grids.npz"))
idx, sea, iho = Gz["idx"], Gz["sea"], Gz["iho"]
Bj = json.load(open(os.path.join(WORK, "world_basins.json")))
SEAS = Bj["SEAS"]; nd = np.array(Bj["nd"]); mainb = np.array(Bj["main"]); dist_main = np.array(Bj["dist_main"])
ppx = np.array([np.nan if v is None else v for v in Bj["ppx"]]); ppy = np.array([np.nan if v is None else v for v in Bj["ppy"]]); ppn = np.array(Bj["ppn"])
endo = np.array(Bj["endo"]); NB = len(nd)
H, W = idx.shape; X0, Y0, RES = -180.0, 90.0, 0.05
lat_r = Y0 - (np.arange(H) + 0.5) * RES; lon_c = X0 + (np.arange(W) + 0.5) * RES
area_r = cell_area_km2(lat_r, RES)
land = idx > 0; b = idx - 1
OCEANS = ["Atlantic", "Pacific", "Indian", "Arctic", "Southern"]
sea_ocean = np.array([OCEANS.index(ocean_of(s)) + 1 for s in SEAS])
ocean = np.zeros((H, W), np.int8)       # 1..5 oceans, 6 inland, 0 not land
ocean[sea > 0] = sea_ocean[sea[sea > 0] - 1]; ocean[sea == -1] = 6
ONAMES = OCEANS + ["Inland (no outlet to the sea)"]
R = {}
A = np.broadcast_to(area_r[:, None], (H, W))
tot = A[land].sum()
R["land_km2"] = float(tot)
R["ocean_share"] = {ONAMES[k - 1]: dict(km2=float(A[ocean == k].sum()), share=float(A[ocean == k].sum() / tot)) for k in range(1, 7)}
print(R["ocean_share"])
srows = []
for k, s in enumerate(SEAS):
    a = A[sea == k + 1].sum()
    if a > 0: srows.append(dict(sea=s, ocean=ocean_of(s), km2=round(float(a)), share=round(float(a / tot), 5)))
SD = pd.DataFrame(srows).sort_values("km2", ascending=False); SD.to_csv(os.path.join(DATA, "world_seas.csv"), index=False)
R["seas_top"] = SD.head(15).to_dict("records"); R["n_seas_receiving"] = int(len(SD))

# --- distance to the sea or sink for every land cell ---
near = ndimage.distance_transform_edt(~((idx == 0) & (iho > 0)), return_distances=False, return_indices=True)
rr, cc = np.nonzero(land)
bb = b[rr, cc]
la, lo = lat_r[rr], lon_c[cc]
single = (ppn[bb] == 1) & ~Gz["detached"][rr, cc]
d = np.zeros(len(rr), np.float32)
d[single] = dist_main[bb[single]] + haversine_km(la[single], lo[single], ppy[bb[single]], ppx[bb[single]])
ns_ = ~single
d[ns_] = haversine_km(la[ns_], lo[ns_], lat_r[near[0][rr[ns_], cc[ns_]]], lon_c[near[1][rr[ns_], cc[ns_]]])
dist = np.zeros((H, W), np.float32); dist[rr, cc] = d
del near

# --- Natural Earth river names for each level 7 sub-basin ---
RV = json.load(open(os.path.join(NE, "ne_10m_rivers_lake_centerlines.geojson")))
RVE = json.load(open(os.path.join(NE, "ne_10m_rivers_europe.geojson")))
cnt = {}
for f in RV["features"] + RVE["features"]:
    p = f["properties"]; nm = p.get("name") or p.get("name_en")
    if not nm or p.get("featurecla", "River") != "River": continue
    g = f["geometry"]; lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
    for ln in lines:
        a = np.array(ln)
        if len(a) < 2: continue
        seg = np.hypot(*np.diff(a, axis=0).T); t = np.r_[0, np.cumsum(seg)]; m = max(2, int(t[-1] / (RES / 3)))
        tt = np.linspace(0, t[-1], m); x = np.interp(tt, t, a[:, 0]); y = np.interp(tt, t, a[:, 1])
        c_ = ((x - X0) / RES).astype(int); r_ = ((Y0 - y) / RES).astype(int); ok = (c_ >= 0) & (c_ < W) & (r_ >= 0) & (r_ < H)
        for bi in idx[r_[ok], c_[ok]]:
            if bi > 0:
                key = (int(bi) - 1, nm); cnt[key] = cnt.get(key, 0) + 1
rank = {}
for f in RV["features"] + RVE["features"]:
    p = f["properties"]; nm = p.get("name") or p.get("name_en")
    if nm: rank[nm] = min(rank.get(nm, 99), p.get("scalerank") or 99)
bname = [""] * NB
best = {}
for (bi, nm), n in cnt.items():
    if n < 3: continue      # a river that only clips the sub-basin
    key = (-n, rank.get(nm, 99))          # the river with most length inside the sub-basin
    if bi not in best or key < best[bi][0]: best[bi] = (key, nm)
coast_flag = np.array(Bj["coast"])
for bi, (_, nm) in best.items():
    if coast_flag[bi] != 1 and ppn[bi] == 1:   # lumped coastal sub-basins hold many small streams, so no single river name
        bname[bi] = " ".join(nm.split())
print("sub-basins with a Natural Earth river name", sum(1 for x in bname if x))


def route(bi):
    """Natural Earth river names met downstream. Going down, rivers only get bigger, so a name is added only when its
    Natural Earth scale rank is at least as important as the last one added (this drops tributaries that a main-stem
    sub-basin happens to be named after)."""
    out = []; j = bi; g = 0; sink = mainb[bi]; cur = 99
    while j >= 0 and g < 4000:
        nm = bname[j]
        if nm and nm not in out and (not out or rank.get(nm, 99) <= cur):
            out.append(nm); cur = rank.get(nm, 99)
        if j == sink: break
        j = nd[j]; g += 1
    return out


# --- GeoNames cities (for naming places) ---
with zipfile.ZipFile("/home/claude/hist/_data13/cities15000.zip") as z:
    CT = pd.read_csv(z.open("cities15000.txt"), sep="\t", header=None, quoting=3, keep_default_na=False, na_values=[""],
                     usecols=[1, 4, 5, 8, 14], names=["name", "lat", "lon", "cc", "pop"])
CT = CT[CT["pop"] >= 15000].reset_index(drop=True)
CT["name"] = CT.name.str.replace("\u2013", "-").str.replace("\u2014", "-")   # a few GeoNames names contain dashes
CTT = cKDTree(np.c_[CT.lon.values * np.cos(np.radians(CT.lat.values)), CT.lat.values])
def city_near(lat, lon):
    dd, j = CTT.query([lon * math.cos(math.radians(lat)), lat]); r = CT.iloc[j]
    return f"{r['name']} ({r.cc})", float(haversine_km(lat, lon, r.lat, r.lon))

# --- longest journeys by ocean ---
lj = []
for k in range(1, 7):
    m = ocean == k
    if not m.any(): continue
    i = int(np.argmax(np.where(m, dist, -1))); r_, c_ = divmod(i, W)
    nm, dk = city_near(lat_r[r_], lon_c[c_])
    lj.append(dict(ocean=ONAMES[k - 1], km=round(float(dist[r_, c_])), lat=round(float(lat_r[r_]), 3), lon=round(float(lon_c[c_]), 3),
                   sea=SEAS[sea[r_, c_] - 1] if sea[r_, c_] > 0 else "inland", route=" > ".join(route(int(b[r_, c_]))), near_city=nm, near_city_km=round(dk)))
R["longest_by_ocean"] = lj
# the longest journey to each of the top seas
R["world_dist_median_km"] = float(np.median(dist[land & (ocean <= 5)]))
w_ = A[land & (ocean <= 5)]; dd_ = dist[land & (ocean <= 5)]
R["world_share_over_1000km"] = float(w_[dd_ > 1000].sum() / w_.sum())
print(lj)

# --- inland basins ---
LK = json.load(open(os.path.join(NE, "ne_10m_lakes.geojson")))
from shapely.geometry import shape, Point
lakes = [(f["properties"].get("name_en") or f["properties"].get("name"), shape(f["geometry"])) for f in LK["features"] if (f["properties"].get("name_en") or f["properties"].get("name"))]
AD = json.load(open(os.path.join(NE, "ne_10m_admin_0_countries.geojson")))
ctry = np.zeros((H, W), np.int16); CN = []
for k, f in enumerate(AD["features"]):
    g = f["geometry"]; polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    rasterise(polys, ctry, X0, Y0, RES, k + 1); CN.append(f["properties"]["NAME"])
def country_at(lat, lon):
    r_ = int((Y0 - lat) / RES); c_ = int((lon - X0) / RES)
    v = ctry[r_, c_]
    if v == 0:
        win = ctry[max(0, r_ - 20):r_ + 20, max(0, c_ - 20):c_ + 20]; v = np.bincount(win[win > 0]).argmax() if (win > 0).any() else 0
    return CN[v - 1] if v else ""
inl = ocean == 6
bsea = np.array(Bj["basin_sea"])
key = np.where(bsea[mainb] == 250, -2, mainb)          # every river into the Caspian Sea counts as one basin
casp_rep = int(np.nonzero(bsea[mainb] == 250)[0][0]) if (bsea[mainb] == 250).any() else -1
mb = np.where(inl, np.where(key[np.maximum(b, 0)] == -2, mainb[casp_rep], mainb[np.maximum(b, 0)]), -1)
casp_main = int(mainb[casp_rep]) if casp_rep >= 0 else -1
ar = np.bincount(mb[inl], weights=A[inl], minlength=NB)
top = np.argsort(-ar)[:40]
by_basin = {}
for (bi, nm), n in cnt.items(): by_basin.setdefault(bi, []).append((nm, n))
def group_rivers(members, k=4):
    """The rivers with the most Natural Earth line length inside a group of sub-basins."""
    tot = {}
    for bi in members:
        for nm, n in by_basin.get(int(bi), []): tot[nm] = tot.get(nm, 0) + n
    return [" ".join(n.split()) for n, _ in sorted(tot.items(), key=lambda x: -x[1])[:k]]
irows = []
for m_ in top:
    if ar[m_] <= 0: continue
    x, y = (50.7, 41.7) if m_ == casp_main else (ppx[m_], ppy[m_]); pt = Point(x, y)
    lk = ["Caspian Sea"] if m_ == casp_main else [n for n, g in lakes if g.distance(pt) < 0.25]
    irows.append(dict(km2=round(float(ar[m_])), sink_lat=round(float(y), 3), sink_lon=round(float(x), 3), lake=lk[0] if lk else "",
                      country="" if m_ == casp_main else country_at(y, x), rivers=" | ".join(group_rivers(np.nonzero((key == -2) if m_ == casp_main else (mainb == m_))[0]))))
IB = pd.DataFrame(irows); IB.to_csv(os.path.join(DATA, "world_inland_basins.csv"), index=False)
R["inland_top"] = IB.head(15).to_dict("records"); R["n_inland_basins"] = int((ar > 0).sum())
print(IB.head(15))

# --- triple points between oceans (2 x 2 blocks of land touching 3 or more of the five oceans plus inland) ---
# For triple points, small closed depressions (inland sinks draining less than 10,000 km2) are given back to the ocean
# that HydroBASINS joins them to (its MAIN_BAS), so that a pothole on a divide does not hide a meeting of oceans.
Bfull = load_bundle()["world"]["basins"]
posw = {int(h): i for i, h in enumerate(Bfull["HYBAS_ID"])}
mainbas = np.array([posw[int(v)] for v in Bfull["MAIN_BAS"]])
bsea_all = np.array(Bj["basin_sea"])
ocean_tp = ocean.copy()
small = inl & (ar[np.maximum(mb, 0)] < 10000)
bm = mainbas[np.maximum(b, 0)]
ok_ = small & (bsea_all[bm] > 0) & (bsea_all[bm] < 250)
ocean_tp[ok_] = sea_ocean[bsea_all[bm][ok_] - 1]
R["triple_rule_small_inland_km2"] = 10000
a, b2, c2, d2 = ocean_tp[:-1, :-1], ocean_tp[:-1, 1:], ocean_tp[1:, :-1], ocean_tp[1:, 1:]
allland = (a > 0) & (b2 > 0) & (c2 > 0) & (d2 > 0)
st = np.stack([a, b2, c2, d2]); st.sort(axis=0)
nd3 = 1 + (st[1] != st[0]) + (st[2] != st[1]) + (st[3] != st[2])
tp = allland & (nd3 >= 3)
rr, cc = np.nonzero(tp)
tps = []; used = np.zeros(len(rr), bool)
for i in range(len(rr)):
    if used[i]: continue
    nb_ = (np.abs(rr - rr[i]) < 40) & (np.abs(cc - cc[i]) < 40); used |= nb_
    r_, c_ = rr[i], cc[i]
    oc = sorted(set(int(v) for v in (a[r_, c_], b2[r_, c_], c2[r_, c_], d2[r_, c_])))
    nm, dk = city_near(lat_r[r_] - RES / 2, lon_c[c_] + RES / 2)
    tps.append(dict(lat=round(float(lat_r[r_] - RES / 2), 3), lon=round(float(lon_c[c_] + RES / 2), 3), oceans=" | ".join(ONAMES[o - 1].split(" (")[0] for o in oc),
                    n=len(oc), inland=6 in oc, country=country_at(lat_r[r_], lon_c[c_]), near_city=nm, near_city_km=round(dk)))
TP = pd.DataFrame(tps); TP.to_csv(os.path.join(DATA, "world_triple_points.csv"), index=False)
R["triple_points_n"] = int(len(TP)); R["triple_points_ocean_only_n"] = int((~TP.inland).sum())
R["triple_points_ocean_only"] = TP[~TP.inland].to_dict("records")
print(TP[~TP.inland])

# --- countries ---
crow = []
for k, nm in enumerate(CN):
    m = (ctry == k + 1) & land
    a_ = A[m].sum()
    if a_ < 5000: continue
    ss = np.bincount(sea[m & (sea > 0)], weights=A[m & (sea > 0)], minlength=len(SEAS) + 1)
    os_ = np.bincount(ocean[m], weights=A[m], minlength=7)
    main_sea = SEAS[int(np.argmax(ss[1:]))] if ss[1:].sum() > 0 else ""
    row = dict(country=nm, km2=round(float(a_)), n_seas=int((ss[1:] / a_ > 0.005).sum()), main_sea=main_sea,
               main_sea_share=round(float(ss[1:].max() / a_), 3) if ss[1:].sum() > 0 else 0)
    for o in range(1, 7): row[ONAMES[o - 1].split(" (")[0].lower() + "_share"] = round(float(os_[o] / a_), 4)
    row["n_oceans"] = int(sum(1 for o in range(1, 6) if os_[o] / a_ > 0.005))
    crow.append(row)
CD = pd.DataFrame(crow).sort_values("km2", ascending=False); CD.to_csv(os.path.join(DATA, "world_countries.csv"), index=False)
R["countries_n"] = int(len(CD))
R["countries_most_seas"] = CD.sort_values(["n_seas", "km2"], ascending=False).head(8)[["country", "n_seas", "n_oceans"]].to_dict("records")
R["countries_all_inland"] = CD[CD.inland_share > 0.99][["country", "km2"]].to_dict("records")
R["countries_four_oceans"] = CD[CD.n_oceans >= 4][["country", "n_oceans"]].to_dict("records")
R["countries_mostly_inland"] = CD[CD.inland_share > 0.5].sort_values("inland_share", ascending=False)[["country", "inland_share"]].to_dict("records")
uk = CD[CD.country == "United Kingdom"]
print(CD.head(12)[["country", "n_seas", "n_oceans", "main_sea", "inland_share"]])

# --- cities ---
r_ = ((Y0 - CT.lat.values) / RES).astype(int); c_ = ((CT.lon.values - X0) / RES).astype(int)
lc = idx[r_, c_]
# a coastal city whose cell is sea: use the nearest land cell
if (lc == 0).any():
    ind = ndimage.distance_transform_edt(idx == 0, return_distances=False, return_indices=True)
    r2, c2_ = ind[0][r_, c_], ind[1][r_, c_]; del ind
    r_ = np.where(lc == 0, r2, r_); c_ = np.where(lc == 0, c2_, c_)
CT["ocean"] = [ONAMES[o - 1].split(" (")[0] if o > 0 else "" for o in ocean[r_, c_]]
CT["sea"] = [SEAS[s - 1] if s > 0 else ("Inland" if s == -1 else "") for s in sea[r_, c_]]
CT["dist_km"] = np.round(dist[r_, c_]).astype(int)
CT["route"] = [" > ".join(route(int(v) - 1)) if v > 0 else "" for v in idx[r_, c_]]
CT = CT[CT.ocean != ""].sort_values("pop", ascending=False)
CT.to_csv(os.path.join(DATA, "world_cities.csv"), index=False)
pop_tot = CT["pop"].sum()
R["cities_n"] = int(len(CT))
R["city_pop_share_by_ocean"] = {o: float(CT[CT.ocean == o]["pop"].sum() / pop_tot) for o in CT.ocean.unique()}
R["big_city_examples"] = CT.head(30)[["name", "cc", "pop", "ocean", "sea", "dist_km", "route"]].to_dict("records")
print(R["city_pop_share_by_ocean"])

np.savez_compressed(os.path.join(WORK, "world_page.npz"), dist=np.round(dist).astype(np.uint16), ocean=ocean, ctry=ctry)
json.dump(dict(bname=bname, rank={n: rank.get(n, 99) for n in set(bname) if n}), open(os.path.join(WORK, "world_names.json"), "w"))
json.dump(R, open(os.path.join(WORK, "results_world.json"), "w"), indent=1, default=float)
