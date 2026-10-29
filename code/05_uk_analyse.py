"""Step 5. Numbers for Britain and Ireland: areas by sea and nation, towns, river systems, watersheds, triple points.
Writes data/uk_*.csv and work/results_uk.json (merged into data/results.json in step 7).
"""
import json, math, os, sys
import numpy as np, pandas as pd
from scipy import ndimage
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

G = np.load(os.path.join(WORK, "uk_grid.npz"))
lab, region, chain, mouth = G["lab"], G["region"], G["chain"], G["mouth"]; dist = G["dist"].astype(np.float32) / 10
elev = G["elev"].astype(np.float32); pix_m = G["pix_m"]; land = G["land"]
X0, Y0, W, H, Z = int(G["X0"]), int(G["Y0"]), int(G["W"]), int(G["H"]), int(G["Z"])
NP = 256 * 2 ** Z
C = json.load(open(os.path.join(WORK, "uk_chains.json"))); NAMES, CHN, CHX, SEAS = C["names"], C["ch_name"], C["ch_next"], C["seas"]
V = json.load(open(os.path.join(WORK, "validation.json")))
cell_km2 = (pix_m ** 2 / 1e6)[:, None] * np.ones((1, W), np.float32)
lat_rows = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * (np.arange(H) + Y0 + 0.5) / NP))))
lon_cols = (np.arange(W) + X0 + 0.5) / NP * 360 - 180


def px(lon, lat):
    lat = np.radians(np.asarray(lat, dtype=np.float64))
    return (((np.asarray(lon) + 180) / 360 * NP) - X0).astype(int), (((1 - np.log(np.tan(lat) + 1 / np.cos(lat)) / np.pi) / 2 * NP) - Y0).astype(int)


def chain_names(c):
    out = []
    while c >= 0: out.append(NAMES[CHN[c]]); c = CHX[c]
    return out


SHORT = {"Irish Sea and St. George's Channel": "Irish Sea", "Inner Seas off the West Coast of Scotland": "Inner Seas (west Scotland)",
         "North Atlantic Ocean": "Atlantic Ocean"}
short = lambda s: SHORT.get(s, s)
R = {}

# --- nations: OS Open Names country for GB cells (nearest named place), Natural Earth for Northern Ireland ---
OSN = pd.read_csv(OSNAMES, sep="\t", dtype=str, keep_default_na=False)
OSN["lat"] = OSN.lat.astype(float); OSN["lon"] = OSN.lon.astype(float)
pp = OSN[OSN.type == "populatedPlace"]
ox, oy = px(pp.lon.values, pp.lat.values)
T = cKDTree(np.c_[ox, oy])
nation = np.zeros((H, W), np.uint8)   # 1 England 2 Scotland 3 Wales 4 Northern Ireland 5 Ireland (state) 6 Isle of Man
gb = region == 1
rr, cc = np.nonzero(gb)
_, ii = T.query(np.c_[cc, rr], workers=2)
cmap = {"England": 1, "Scotland": 2, "Wales": 3}
nation[rr, cc] = np.array([cmap.get(c, 1) for c in pp.country.values])[ii]
del rr, cc, ii
AD = json.load(open(os.path.join(NE, "ne_10m_admin_0_countries.geojson")))
uk_poly = [f for f in AD["features"] if f["properties"]["ADM0_A3"] == "GBR"][0]["geometry"]
ukm = np.zeros((H, W), np.uint8)
polys = []
for poly in (uk_poly["coordinates"] if uk_poly["type"] == "MultiPolygon" else [uk_poly["coordinates"]]):
    rr_ = []
    for ring in poly:
        a = np.array(ring); x, y = px(a[:, 0], a[:, 1])
        rr_.append(np.c_[(((a[:, 0] + 180) / 360 * NP) - X0), -((1 - np.log(np.tan(np.radians(a[:, 1])) + 1 / np.cos(np.radians(a[:, 1]))) / np.pi) / 2 * NP - Y0)])
    polys.append(rr_)
rasterise(polys, ukm, 0.0, 0.0, 1.0, 1)
isl = region == 2
nation[isl & (ukm > 0)] = 4; nation[isl & (ukm == 0)] = 5; nation[region == 3] = 6
NATIONS = {1: "England", 2: "Scotland", 3: "Wales", 4: "Northern Ireland", 5: "Ireland", 6: "Isle of Man"}

rows = []
for nk, nn in NATIONS.items():
    m = nation == nk; tot = cell_km2[m].sum()
    for k in np.unique(lab[m]):
        if k == 0: continue
        a = cell_km2[m & (lab == k)].sum()
        rows.append(dict(area=nn, sea=SEAS[k - 1], sea_short=short(SEAS[k - 1]), km2=round(float(a)), share=round(float(a / tot), 4)))
for nm_, m in (("Great Britain", gb), ("United Kingdom", (nation >= 1) & (nation <= 4)), ("Island of Ireland", isl)):
    tot = cell_km2[m].sum()
    for k in np.unique(lab[m]):
        if k == 0: continue
        a = cell_km2[m & (lab == k)].sum()
        rows.append(dict(area=nm_, sea=SEAS[k - 1], sea_short=short(SEAS[k - 1]), km2=round(float(a)), share=round(float(a / tot), 4)))
AS = pd.DataFrame(rows); AS.to_csv(os.path.join(DATA, "uk_seas_by_area.csv"), index=False)
R["areas"] = {a: {r.sea_short: dict(km2=r.km2, share=r.share) for r in g.itertuples()} for a, g in AS.groupby("area")}
R["areas_total_km2"] = {a: int(g.km2.sum()) for a, g in AS.groupby("area")}
print(AS[AS.area.isin(["Great Britain", "United Kingdom"])])

# --- towns and villages ---
PL = OSN[(OSN.type == "populatedPlace") & OSN.local_type.isin(["City", "Town", "Village"])].copy()
x, y = px(PL.lon.values, PL.lat.values)
ok = (x >= 0) & (x < W) & (y >= 0) & (y < H); PL = PL[ok]; x, y = x[ok], y[ok]
# a place's cell, or the nearest land cell within 2 cells if the point sits on the coast
lk = lab[y, x]
if (lk == 0).any():
    landc = lab > 0
    ind = ndimage.distance_transform_edt(~landc, return_distances=False, return_indices=True)
    y2, x2 = ind[0][y, x], ind[1][y, x]; del ind
    y = np.where(lk == 0, y2, y); x = np.where(lk == 0, x2, x)
PL["sea"] = [SEAS[k - 1] if k else "" for k in lab[y, x]]
PL["sea_short"] = [short(s) for s in PL.sea]
PL["dist_km"] = np.round(dist[y, x].astype(float), 1)
PL["route"] = [" > ".join(chain_names(int(c))) for c in chain[y, x]]
PL["nation"] = [NATIONS.get(int(n), "") for n in nation[y, x]]
# on a watershed: a neighbouring cell (8 directions) drains to a different sea
def on_divide(yy, xx):
    out = np.zeros(len(yy), bool); lv = lab[yy, xx]
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            y2 = np.clip(yy + dy, 0, H - 1); x2 = np.clip(xx + dx, 0, W - 1); l2 = lab[y2, x2]
            out |= (l2 > 0) & (l2 != lv)
    return out
PL["on_watershed"] = on_divide(y, x)
PL = PL[PL.sea != ""]
PLo = PL[["name1", "local_type", "county", "district", "nation", "lat", "lon", "sea_short", "sea", "dist_km", "route", "on_watershed"]].rename(
    columns={"name1": "name", "local_type": "type"})
PLo["county"] = np.where(PLo.county == "", OSN.loc[PLo.index, "district"], PLo.county)
PLo.drop(columns=["district"]).sort_values(["type", "name"]).to_csv(os.path.join(DATA, "uk_places.csv"), index=False)
tw = PLo[PLo.type.isin(["City", "Town"])]
R["places"] = dict(n_cities_towns=int(len(tw)), n_villages=int((PLo.type == "Village").sum()),
                   towns_by_sea={k: int(v) for k, v in tw.sea_short.value_counts().items()},
                   villages_by_sea={k: int(v) for k, v in PLo[PLo.type == "Village"].sea_short.value_counts().items()},
                   towns_on_watershed=int(tw.on_watershed.sum()), villages_on_watershed=int((PLo[PLo.type == "Village"].on_watershed).sum()),
                   towns_on_watershed_list=tw[tw.on_watershed].sort_values("name")[["name", "county", "sea_short"]].values.tolist(),
                   median_town_dist_km=float(tw.dist_km.median()))
far = tw.sort_values("dist_km", ascending=False).head(12)
R["places"]["farthest_towns"] = [dict(name=r.name, county=r.county, sea=r.sea_short, km=r.dist_km, route=r.route) for r in far.itertuples()]
cities = tw[tw.type == "City"].sort_values("name")
R["places"]["cities"] = [dict(name=r.name, sea=r.sea_short, km=r.dist_km, route=r.route) for r in cities.itertuples()]
print(R["places"]["towns_by_sea"], R["places"]["towns_on_watershed"])

# --- longest journeys (GB, with the river route) ---
lj = []
for k in np.unique(lab[gb]):
    if k == 0: continue
    m = gb & (lab == k)
    i = np.argmax(np.where(m, dist, -1)); r_, c_ = divmod(int(i), W)
    lat, lon = float(lat_rows[r_]), float(lon_cols[c_])
    _, j = T.query([c_, r_])
    lj.append(dict(sea=short(SEAS[k - 1]), km=round(float(dist[r_, c_]), 1), lat=round(lat, 4), lon=round(lon, 4),
                   near=pp.name1.values[j], route=" > ".join(chain_names(int(chain[r_, c_])))))
R["longest_gb"] = sorted(lj, key=lambda d: -d["km"])
# the start of the longest North Sea journey: the nearest cell to the west that drains to another sea
ns0 = [x for x in R["longest_gb"] if x["sea"] == "North Sea"][0]
c0, r0 = px(ns0["lon"], ns0["lat"]); k0 = lab[r0, c0]
for dc in range(1, 200):
    if lab[r0, c0 - dc] and lab[r0, c0 - dc] != k0:
        R["thames_head_contrast"] = dict(km_west=round(float(dc * pix_m[r0] / 1000), 1), sea=short(SEAS[lab[r0, c0 - dc] - 1]),
                                         path_km=round(float(dist[r0, c0 - dc]), 1), route=" > ".join(chain_names(int(chain[r0, c0 - dc]))))
        break
R["severn_thames_start_km"] = float(haversine_km(R["longest_gb"][0]["lat"], R["longest_gb"][0]["lon"], ns0["lat"], ns0["lon"]))
R["gb_dist_median_km"] = float(np.median(dist[gb])); R["gb_dist_mean_km"] = float(dist[gb].mean())
w = cell_km2[gb]; dd = dist[gb]
R["gb_share_within_10km"] = float(w[dd <= 10].sum() / w.sum()); R["gb_share_over_100km"] = float(w[dd > 100].sum() / w.sum())
print(R["longest_gb"][:3])

# --- river systems: group cells by the last named watercourse and their mouth ---
mf = mouth.ravel()
last = np.full(H * W, -1, np.int32)
cu = np.unique(chain[chain >= 0])
lastname = {}
for c in cu:
    q = int(c)
    while CHX[q] >= 0: q = CHX[q]
    lastname[int(c)] = CHN[q]
ch_flat = chain.ravel()
sel = np.nonzero((ch_flat >= 0) & (lab.ravel() > 0) & (region.ravel() == 1))[0]
ln_ = np.array([lastname[int(c)] for c in ch_flat[sel]])
mr, mc = np.divmod(mf[sel], W)
df = pd.DataFrame(dict(name=ln_, sea=lab.ravel()[sel], mx=mc // 110, my=mr // 110, a=cell_km2.ravel()[sel], mr=mr, mc=mc))   # mouths grouped in ~20 km blocks
gsys = df.groupby(["name", "sea", "mx", "my"]).agg(km2=("a", "sum"), mr=("mr", "median"), mc=("mc", "median")).reset_index().sort_values("km2", ascending=False)
gsys["name"] = [NAMES[n] for n in gsys.name]
gsys["sea"] = [short(SEAS[s - 1]) for s in gsys.sea]
gsys["mouth_lat"] = [round(float(lat_rows[int(r)]), 4) for r in gsys.mr]; gsys["mouth_lon"] = [round(float(lon_cols[int(c)]), 4) for c in gsys.mc]
gsys["km2"] = gsys.km2.round(0)
gsys[["name", "sea", "km2", "mouth_lat", "mouth_lon"]].head(200).to_csv(os.path.join(DATA, "uk_river_systems.csv"), index=False)
R["river_systems_top"] = gsys[["name", "sea", "km2"]].head(15).to_dict("records")
print(gsys.head(12))

# --- watersheds: length of the line between seas, the North Sea divide, triple points ---
def edges(a, b, ok):
    return (a != b) & ok
labg = np.where(gb, lab, 0)
h_e = (labg[:, 1:] != labg[:, :-1]) & (labg[:, 1:] > 0) & (labg[:, :-1] > 0)
v_e = (labg[1:, :] != labg[:-1, :]) & (labg[1:, :] > 0) & (labg[:-1, :] > 0)
# cell edges trace a staircase; for lines of all orientations the staircase is on average 4/pi times longer than
# the line, so lengths are multiplied by pi/4
STAIR = math.pi / 4
R["gb_divide_km_all"] = STAIR * float((h_e * pix_m[:, None]).sum() / 1000 + (v_e * pix_m[:-1, None]).sum() / 1000)
NS = SEAS.index("North Sea") + 1
ns = labg == NS
h_ns = h_e & (ns[:, 1:] ^ ns[:, :-1]); v_ns = v_e & (ns[1:, :] ^ ns[:-1, :])
R["gb_north_sea_divide_km"] = STAIR * float((h_ns * pix_m[:, None]).sum() / 1000 + (v_ns * pix_m[:-1, None]).sum() / 1000)
# lowest and highest points on the North Sea divide (mainland only: largest GB component)
labc, n = ndimage.label(gb, structure=np.ones((3, 3))); main = labc == np.bincount(labc.ravel())[1:].argmax() + 1
dv = np.zeros((H, W), bool); dv[:, 1:] |= h_ns; dv[:, :-1] |= h_ns; dv[1:, :] |= v_ns; dv[:-1, :] |= v_ns
dv &= main
coast_km = ndimage.distance_transform_edt(lab > 0) * np.median(pix_m) / 1000
ev = np.where(dv & (coast_km > 3), elev, np.nan)   # ignore the last 3 km where the divide meets the coast
def place_at(r_, c_, kinds=("Hill Or Mountain",)):
    sub = OSN[OSN.local_type.isin(kinds)]
    sx, sy = px(sub.lon.values, sub.lat.values); TT = cKDTree(np.c_[sx, sy]); d_, j = TT.query([c_, r_])
    return sub.name1.values[j], float(d_ * pix_m[r_] / 1000)
lo = np.nanargmin(ev); hi = np.nanargmax(ev)
out = {}
for nm_, i in (("lowest", lo), ("highest", hi)):
    r_, c_ = divmod(int(i), W)
    _, j = T.query([c_, r_])
    out[nm_] = dict(elev_m=float(elev[r_, c_]), lat=round(float(lat_rows[r_]), 4), lon=round(float(lon_cols[c_]), 4), near=pp.name1.values[j],
                    county=pp.county.values[j] or pp.district.values[j], hill=place_at(r_, c_)[0], hill_km=round(place_at(r_, c_)[1], 1))
R["north_sea_divide_points"] = out
# divide line points for the paper figure and the page (sampled)
rr, cc = np.nonzero(dv)
np.savez_compressed(os.path.join(WORK, "ns_divide.npz"), lat=lat_rows[rr], lon=lon_cols[cc], elev=elev[rr, cc])
# share of the divide below 100 m and the length of the mainland divide
R["ns_divide_cells"] = int(dv.sum()); R["ns_divide_share_below_100m"] = float((elev[dv] < 100).mean())
print(R["gb_north_sea_divide_km"], out)

# triple points: 2 x 2 blocks on Great Britain land touching three or more seas
a, b, c, d = labg[:-1, :-1], labg[:-1, 1:], labg[1:, :-1], labg[1:, 1:]
allland = (a > 0) & (b > 0) & (c > 0) & (d > 0)
st = np.stack([a, b, c, d]); st.sort(axis=0)
nd_ = 1 + (st[1] != st[0]) + (st[2] != st[1]) + (st[3] != st[2])
tp = allland & (nd_ >= 3)
rr, cc = np.nonzero(tp)
tps = []
used = np.zeros(len(rr), bool)
for i in range(len(rr)):
    if used[i]: continue
    near_ = (np.abs(rr - rr[i]) < 15) & (np.abs(cc - cc[i]) < 15); used |= near_
    r_, c_ = rr[i], cc[i]
    seas = sorted(set(int(v) for v in (a[r_, c_], b[r_, c_], c[r_, c_], d[r_, c_])))
    hill, hd = place_at(r_, c_)
    _, j = T.query([c_, r_])
    # the first named watercourse on each side, looking a little way out from the point
    firsts = {}
    for dy in range(-6, 8):
        for dx in range(-6, 8):
            y2, x2 = r_ + dy, c_ + dx
            if 0 <= y2 < H and 0 <= x2 < W and lab[y2, x2] > 0 and chain[y2, x2] >= 0:
                k_ = int(lab[y2, x2]); nm_ = chain_names(int(chain[y2, x2]))
                if k_ not in firsts or len(nm_) > len(firsts[k_]): firsts[k_] = nm_
    rivers = " | ".join(f"{short(SEAS[k_ - 1])}: {' > '.join(firsts[k_][:3])}" for k_ in seas if k_ in firsts)
    tps.append(dict(rivers=rivers, lat=round(float(lat_rows[r_]), 4), lon=round(float(lon_cols[c_]), 4), elev_m=float(elev[r_, c_]),
                    seas=" | ".join(short(SEAS[s - 1]) for s in seas), nearest_hill=hill, hill_km=round(hd, 1),
                    nearest_place=pp.name1.values[j], county=pp.county.values[j] or pp.district.values[j], nation=NATIONS.get(int(nation[r_, c_]), "")))
TP = pd.DataFrame(tps); TP.to_csv(os.path.join(DATA, "uk_triple_points.csv"), index=False)
R["gb_triple_points"] = tps
print(TP)

# --- the either-way cases from the river network ---
BF = pd.read_csv(os.path.join(WORK, "bifurcations.csv"))
R["network_bifurcations_to_different_seas"] = int(len(BF))
R["validation"] = V
R["meta"] = dict(grid_cells_gb=int(gb.sum()), grid_cells_ireland=int(isl.sum()), cell_m_median=float(np.median(pix_m)),
                 os_links=int(V["network"]["links"]), name_chains=len(CHN))
json.dump(R, open(os.path.join(WORK, "results_uk.json"), "w"), indent=1, default=float)
np.savez_compressed(os.path.join(WORK, "uk_nation.npz"), nation=nation)
