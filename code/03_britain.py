"""Step 3. Britain and Ireland at about 180 m: follow every raindrop downhill to the sea.

Grid: web-mercator zoom 9 pixels over 10.9 W to 2.1 E, 49.62 N to 60.93 N (about 180 m across in Britain).
Elevation: AWS Terrain Tiles (zoom 10, averaged 2 x 2 to zoom 9).
Land: cells above 0 m, plus cells down to 3 m below sea level that Natural Earth counts as land (the Fens).
River burning: every OS Open Rivers watercourse link in Great Britain except canals is lowered along its line by
20 m plus 15 m for every tenfold increase in the length of river network above it, so that paths keep to main channels.
Flooding: a priority flood starts from the sea all round the coast (each sea cell carries the IHO sea area it lies in)
and climbs inland, always taking the lowest cell next. Every land cell inherits the sea of the cell it was reached
from, and remembers that cell as the next step down its path. Following those steps from any cell leads downhill
(through any filled hollows) to the coast; this is the path a raindrop takes in the model.
Along each path I add up the length (km) and the names of the OS watercourses it runs along.
Ireland and the Isle of Man have no OS Open Rivers data here, so their paths follow the terrain alone (no names).
Writes work/uk_grid.npz and work/uk_chains.json.
"""
import json, math, os, sys
import numpy as np
from numba import njit
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, "/home/claude/hist/within-sight/code")
from dem import DEM

Z = 9; NPIX = 256 * 2 ** Z


def lonlat_to_px(lon, lat):
    lat = np.radians(np.asarray(lat, dtype=np.float64))
    return (np.asarray(lon) + 180) / 360 * NPIX, (1 - np.log(np.tan(lat) + 1 / np.cos(lat)) / math.pi) / 2 * NPIX


def px_to_lat(py):
    return np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * np.asarray(py, dtype=np.float64) / NPIX))))


LON0, LON1, LAT0, LAT1 = -10.89, 2.10, 49.62, 60.92
gx0, gy0 = lonlat_to_px(LON0, LAT1); gx1, gy1 = lonlat_to_px(LON1, LAT0)
X0, Y0 = int(gx0), int(gy0); W, H = int(gx1) - X0, int(gy1) - Y0
print("grid", W, H, W * H)

# --- elevation, zoom 10 averaged to zoom 9 ---
dem = DEM()
elev = np.zeros((H, W), np.float32)
cols10 = (np.arange(2 * W) + 2 * X0)
for r0 in range(0, H, 256):
    r1 = min(H, r0 + 256)
    rows10 = np.arange(2 * r0, 2 * r1) + 2 * Y0
    IX, IY = np.meshgrid(cols10, rows10)
    e = dem._get(IX.astype(np.int64), IY.astype(np.int64)).reshape(2 * (r1 - r0), 2 * W)
    elev[r0:r1] = e.reshape(r1 - r0, 2, W, 2).mean(axis=(1, 3))
lat_rows = px_to_lat(np.arange(H) + Y0 + 0.5)
pix_m = 2 * math.pi * 6378137 / NPIX * np.cos(np.radians(lat_rows))   # cell size in metres by row

# --- Natural Earth land, rasterised in pixel space ---
def to_pix_polys(geoms):
    out = []
    for g in geoms:
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            rr = []
            for ring in poly:
                a = np.array(ring)
                if a[:, 0].max() - a[:, 0].min() > 180:   # rings that cross the 180 degree meridian are far from Britain
                    rr = None if not rr else rr; break
                if a[:, 0].max() < LON0 - 1 or a[:, 0].min() > LON1 + 1 or a[:, 1].max() < LAT0 - 1 or a[:, 1].min() > LAT1 + 1:
                    rr = None if not rr else rr; break
                a[:, 1] = np.clip(a[:, 1], -85, 85)
                px, py = lonlat_to_px(a[:, 0], a[:, 1]); rr.append(np.c_[px - X0, -(py - Y0)])
            if rr: out.append(rr)
    return out
ne_land = np.zeros((H, W), np.uint8)
NL = json.load(open(os.path.join(NE, "ne_10m_land.geojson")))
rasterise(to_pix_polys([f["geometry"] for f in NL["features"]]), ne_land, 0.0, 0.0, 1.0, 1)
land = (elev > 0) | ((ne_land > 0) & (elev > -3))
# drop specks of land smaller than 4 cells
lab, n = ndimage.label(land, structure=np.ones((3, 3)))
sz = np.bincount(lab.ravel()); land &= sz[lab] >= 4
lab, n = ndimage.label(land, structure=np.ones((3, 3))); sz = np.bincount(lab.ravel())
def comp_at(lon, lat):
    px, py = lonlat_to_px(lon, lat); return lab[int(py) - Y0, int(px) - X0]
c_ireland = comp_at(-8.0, 53.5); c_man = comp_at(-4.5, 54.23); c_france = comp_at(1.9, 50.3)
c_gb = comp_at(-1.5, 52.5)
region = np.zeros((H, W), np.uint8)   # 1 Great Britain and its islands, 2 Ireland and its islands, 3 Isle of Man, 0 sea or outside
mainm = np.zeros((H, W), np.uint8)
mainm[lab == c_gb] = 1; mainm[lab == c_ireland] = 2; mainm[lab == c_man] = 3
# every other island goes with the nearest of the three main islands
ind = ndimage.distance_transform_edt(mainm == 0, return_distances=False, return_indices=True)
region[land] = mainm[ind[0], ind[1]][land]; del ind
region[(lab == c_france) & (c_france > 0)] = 0
# the tip of the Cotentin peninsula and the Channel Islands lie inside the window but are not part of this map
lon_c = (np.arange(W) + X0 + 0.5) / NPIX * 360 - 180
region[(lat_rows[:, None] < 49.95) & (lon_c[None, :] > -5.0)] = 0
print("cells GB", (region == 1).sum(), "Ireland", (region == 2).sum(), "Man", (region == 3).sum(), "France comp", c_france)

# --- IHO seas on the sea cells ---
B = load_bundle(); SEAS = [f["p"]["name"] for f in B["iho"]]
iho = np.zeros((H, W), np.uint8)
for k, f in enumerate(B["iho"]):
    pp = to_pix_polys([{"type": "MultiPolygon", "coordinates": f["g"]}])
    if pp: rasterise(pp, iho, 0.0, 0.0, 1.0, k + 1)
seacell = ~land & (iho > 0)
near = ndimage.distance_transform_edt(~seacell, return_distances=False, return_indices=True)
sea_lab = iho[near[0], near[1]]; del near

# --- burn OS Open Rivers (GB, no canals) ---
Lk = np.load(os.path.join(WORK, "links.npz"), allow_pickle=True)
offs, vlon, vlat = Lk["offs"], Lk["lon"], Lk["lat"]; canal = Lk["canal"]; lname = Lk["name"]
CH = json.load(open(os.path.join(WORK, "chains.json"))); NAMES = CH["names"]; nid = {n: i for i, n in enumerate(NAMES)}
river_name = np.full((H, W), -1, np.int32)   # name id of a named watercourse in the cell
river = np.zeros((H, W), bool)
vx, vy = lonlat_to_px(vlon, vlat); vx -= X0; vy -= Y0
up_km = Lk["up_km"]
burn_k = np.zeros((H, W), np.float32)
is_canal_name = np.array([str(n).endswith("Canal") or " Canal (" in str(n) for n in lname])
for k in np.argsort(up_km):     # small streams first, so the larger river wins a shared cell
    if canal[k] or is_canal_name[k]: continue
    a, b = offs[k], offs[k + 1]
    x, y = vx[a:b], vy[a:b]
    if len(x) > 1:   # densify to quarter-cell steps
        seg = np.hypot(np.diff(x), np.diff(y)); t = np.r_[0, np.cumsum(seg)]; m = max(2, int(t[-1] * 4) + 1)
        tt = np.linspace(0, t[-1], m); x = np.interp(tt, t, x); y = np.interp(tt, t, y)
    c = x.astype(int); r = y.astype(int); ok = (c >= 0) & (c < W) & (r >= 0) & (r < H)
    c, r = c[ok], r[ok]
    river[r, c] = True
    burn_k[r, c] = 20.0 + 15.0 * np.log10(1.0 + up_km[k])   # deeper for bigger rivers, so paths keep to the main channel
    river_name[r, c] = nid[str(lname[k])] if lname[k] else -1
river &= land & (region == 1)
river_name[~river] = -1
z = elev.copy(); z[river] -= burn_k[river]
print("river cells", river.sum())


@njit(cache=True)
def priority_flood(z, land, seed_lab, H, W):
    N = H * W
    lab = np.zeros(N, np.uint8); parent = np.full(N, -1, np.int64); done = np.zeros(N, np.bool_)
    order = np.empty(N, np.int64); no = 0
    hk = np.empty(N + 16, np.float64); hc = np.empty(N + 16, np.int64); hv = np.empty(N + 16, np.int64); hn = 0; cnt = 0
    zz = z.ravel().copy(); L = land.ravel(); S = seed_lab.ravel()
    # seeds: sea cells touching land
    for i in range(N):
        if L[i]: continue
        r = i // W; c = i % W; touch = False
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                rr = r + dr; cc = c + dc
                if 0 <= rr < H and 0 <= cc < W and L[rr * W + cc]: touch = True
        if touch and S[i] > 0:
            lab[i] = S[i]; done[i] = True; zz[i] = -1e9 + 0.0
            # push
            k = hn; hn += 1; hk[k] = -1e9; hc[k] = cnt; hv[k] = i; cnt += 1
            while k > 0:
                p = (k - 1) // 2
                if hk[p] > hk[k] or (hk[p] == hk[k] and hc[p] > hc[k]):
                    hk[p], hk[k] = hk[k], hk[p]; hc[p], hc[k] = hc[k], hc[p]; hv[p], hv[k] = hv[k], hv[p]; k = p
                else: break
    while hn > 0:
        ck = hk[0]; i = hv[0]
        hn -= 1; hk[0] = hk[hn]; hc[0] = hc[hn]; hv[0] = hv[hn]; k = 0
        while True:
            l = 2 * k + 1; rgt = l + 1; m = k
            if l < hn and (hk[l] < hk[m] or (hk[l] == hk[m] and hc[l] < hc[m])): m = l
            if rgt < hn and (hk[rgt] < hk[m] or (hk[rgt] == hk[m] and hc[rgt] < hc[m])): m = rgt
            if m == k: break
            hk[m], hk[k] = hk[k], hk[m]; hc[m], hc[k] = hc[k], hc[m]; hv[m], hv[k] = hv[k], hv[m]; k = m
        if L[i]:
            order[no] = i; no += 1
        r = i // W; c = i % W
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0: continue
                rr = r + dr; cc = c + dc
                if rr < 0 or rr >= H or cc < 0 or cc >= W: continue
                j = rr * W + cc
                if done[j] or not L[j]: continue
                done[j] = True; lab[j] = lab[i]; parent[j] = i
                kz = zz[j] if zz[j] > ck else ck
                k = hn; hn += 1; hk[k] = kz; hc[k] = cnt; hv[k] = j; cnt += 1
                while k > 0:
                    p = (k - 1) // 2
                    if hk[p] > hk[k] or (hk[p] == hk[k] and hc[p] > hc[k]):
                        hk[p], hk[k] = hk[k], hk[p]; hc[p], hc[k] = hc[k], hc[p]; hv[p], hv[k] = hv[k], hv[p]; k = p
                    else: break
    return lab, parent, order[:no]


land_in = land & (region > 0)
lab_f, parent, order = priority_flood(z, land_in, sea_lab, H, W)
print("flooded land cells", len(order), "of", land_in.sum())


# a watercourse joins the list of names only after the path has followed it for 5 cells (about 0.9 km), or 12 cells
# for brooks, drains, ditches and the like, which often run beside a main river for a stretch
MAIN_WORDS = ("River ", "Afon ", "Water of ", "Burn of ")
kname = np.array([5 if (n.startswith(MAIN_WORDS) or n.endswith((" Water", " Burn"))) else 12 for n in NAMES], np.int32)


@njit(cache=True)
def _node(n, base, ch_name, ch_next, nch, keys_k, keys_v):
    key = (np.int64(n) << 32) + np.int64(base + 1)
    h = (key * 2654435761) % keys_k.shape[0]
    while True:
        if keys_k[h] == -1:
            keys_k[h] = key; keys_v[h] = nch; ch_name[nch] = n; ch_next[nch] = base
            return nch, nch + 1
        if keys_k[h] == key:
            return keys_v[h], nch
        h = (h + 1) % keys_k.shape[0]


@njit(cache=True)
def propagate(order, parent, W, pix_m, rname, ch_name, ch_next, nch, keys_k, keys_v, KN):
    N = parent.shape[0]
    dist = np.zeros(N, np.float32); chain = np.full(N, -1, np.int32); mouth = np.full(N, -1, np.int64)
    base = np.full(N, -1, np.int32); run = np.zeros(N, np.int32)
    for t in range(order.shape[0]):
        i = order[t]; p = parent[i]
        r = i // W; pr = p // W
        step = pix_m[r] * (1.4142135 if (pr != r and (p % W) != (i % W)) else 1.0)
        dist[i] = dist[p] + step / 1000.0
        mouth[i] = mouth[p] if mouth[p] >= 0 else p
        n = rname[i]
        pc = chain[p]
        if n < 0:
            chain[i] = pc; continue
        if rname[p] == n:
            run[i] = run[p] + 1; base[i] = base[p]
        else:
            run[i] = 1; base[i] = pc
        # name already met further down: nothing new
        q = base[i]; found = False; depth = 0
        while q >= 0 and depth < 64:
            if ch_name[q] == n:
                found = True; break
            q = ch_next[q]; depth += 1
        if found:
            chain[i] = q; continue   # back on a river already met downstream: the names between are side-steps
        if run[i] >= KN[n]:
            c, nch = _node(n, base[i], ch_name, ch_next, nch, keys_k, keys_v)
            chain[i] = c
        else:
            chain[i] = base[i]
    return dist, chain, mouth, nch


CAP = 4_000_000
ch_name = np.full(CAP, -1, np.int32); ch_next = np.full(CAP, -1, np.int32)
keys_k = np.full(2 * CAP + 1, -1, np.int64); keys_v = np.zeros(2 * CAP + 1, np.int32)
dist, chain, mouth, nch = propagate(order, parent, W, pix_m.astype(np.float64), river_name.ravel(), ch_name, ch_next, 0, keys_k, keys_v, kname)
print("name chains", nch)
ch_name = ch_name[:nch]; ch_next = ch_next[:nch]

lab_f = lab_f.reshape(H, W); dist = dist.reshape(H, W); chain = chain.reshape(H, W); mouth = mouth.reshape(H, W)
# river classes for the maps: the area draining through each cell along the modelled paths
@njit(cache=True)
def accumulate(parent, landm, area):
    N = parent.shape[0]
    indeg = np.zeros(N, np.int32)
    for i in range(N):
        if landm[i] and parent[i] >= 0 and landm[parent[i]]: indeg[parent[i]] += 1
    acc = area.copy(); stack = np.empty(N, np.int64); n = 0
    for i in range(N):
        if landm[i] and indeg[i] == 0: stack[n] = i; n += 1
    while n > 0:
        n -= 1; i = stack[n]; p = parent[i]
        if p >= 0 and landm[p]:
            acc[p] += acc[i]; indeg[p] -= 1
            if indeg[p] == 0: stack[n] = p; n += 1
    return acc


landm = (lab_f > 0) & (region > 0)
cell_area = np.repeat((pix_m ** 2 / 1e6)[:, None], W, axis=1).astype(np.float64)
acc = accumulate(parent, landm.ravel(), np.where(landm, cell_area, 0).ravel()).reshape(H, W)
rcls = np.digitize(acc, [10, 100, 1000, 5000]).astype(np.uint8); rcls[~landm] = 0   # 1 = 10 km2 upstream ... 4 = 5,000 km2
np.savez_compressed(os.path.join(WORK, "uk_rivers.npz"), rcls=rcls)
del acc, cell_area
# path length stored in units of 0.1 km (uint16) to keep the file small
np.savez_compressed(os.path.join(WORK, "uk_grid.npz"), lab=lab_f, dist=np.round(dist * 10).astype(np.uint16), chain=chain, mouth=mouth.astype(np.int32),
                    region=region, elev=elev.astype(np.int16), land=land, X0=X0, Y0=Y0, W=W, H=H, Z=Z, pix_m=pix_m)
json.dump(dict(names=NAMES, ch_name=ch_name.tolist(), ch_next=ch_next.tolist(), seas=SEAS), open(os.path.join(WORK, "uk_chains.json"), "w"))
for k in np.unique(lab_f[region == 1]):
    print(SEAS[k - 1] if k else "none", round(float(((lab_f == k) & (region == 1)) .astype(float).__mul__(pix_m[:, None] ** 2 / 1e6).sum())), "km2 GB")
