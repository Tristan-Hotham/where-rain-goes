"""Shared helpers for the Where Rain Goes analysis: paths, the browser bundles, a polygon rasteriser and cell areas."""
import base64, gzip, json, math, os
import numpy as np
from numba import njit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(ROOT, "work")
RAW = os.environ.get("WRG_RAW", "/home/claude/hist/_data18/where-rain-goes")
NE = "/home/claude/hist/_data3/ne/geojson"
OSRIVERS = "/home/claude/hist/osrivers/Data/oprvrs_gb.gpkg"
OSNAMES = "/home/claude/hist/osnames_gb.tsv"
os.makedirs(WORK, exist_ok=True); os.makedirs(DATA, exist_ok=True)
R_EARTH_KM = 6371.0088


def load_bundle(name="wrg_hydrobasins_iho.json.gz"):
    return json.load(gzip.open(os.path.join(RAW, name)))


def decode_grid(g):
    """Grid from the browser bundle: gzip, base64, little-endian int32, row 0 at the north edge."""
    a = np.frombuffer(gzip.decompress(base64.b64decode(g["b64"])), dtype="<i4")
    return a.reshape(g["H"], g["W"]).copy()


@njit(cache=True)
def _rast_ring_edges(xs, ys, x0, y0, res, H, rows_x, rows_n, maxk):
    n = xs.shape[0]
    for i in range(n):
        x1 = xs[i]; y1 = ys[i]; j = (i + 1) % n; x2 = xs[j]; y2 = ys[j]
        if y1 == y2:
            continue
        ymin = min(y1, y2); ymax = max(y1, y2)
        r0 = int(math.ceil((y0 - ymax) / res - 0.5)); r1 = int(math.floor((y0 - ymin) / res - 0.5))
        if r0 < 0: r0 = 0
        if r1 > H - 1: r1 = H - 1
        for r in range(r0, r1 + 1):
            yc = y0 - (r + 0.5) * res
            if yc < ymin or yc >= ymax:
                continue
            k = rows_n[r]
            if k < maxk:
                rows_x[r, k] = x1 + (yc - y1) * (x2 - x1) / (y2 - y1); rows_n[r] = k + 1


@njit(cache=True)
def _fill(rows_x, rows_n, x0, res, W, arr, val, r_lo, r_hi):
    for r in range(r_lo, r_hi + 1):
        k = rows_n[r]
        if k < 2:
            continue
        xs = np.sort(rows_x[r, :k])
        for m in range(0, k - 1, 2):
            c0 = int(math.ceil((xs[m] - x0) / res - 0.5)); c1 = int(math.floor((xs[m + 1] - x0) / res - 0.5))
            if c0 < 0: c0 = 0
            if c1 > W - 1: c1 = W - 1
            for c in range(c0, c1 + 1):
                arr[r, c] = val


def rasterise(polys, arr, x0, y0, res, val, maxk=4096):
    """Even-odd scanline fill of polygons (each a list of rings of [x, y]) at cell centres, one polygon at a time."""
    H, W = arr.shape
    rows_x = np.zeros((H, maxk)); rows_n = np.zeros(H, np.int64)
    for poly in polys:
        ys = [p[1] for ring in poly for p in ring]
        if not ys:
            continue
        r_lo = max(0, int((y0 - max(ys)) / res) - 1); r_hi = min(H - 1, int((y0 - min(ys)) / res) + 1)
        if r_lo > r_hi:
            continue
        rows_n[r_lo:r_hi + 1] = 0
        for ring in poly:
            a = np.asarray(ring, dtype=np.float64)
            _rast_ring_edges(a[:, 0].copy(), a[:, 1].copy(), x0, y0, res, H, rows_x, rows_n, maxk)
        _fill(rows_x, rows_n, x0, res, W, arr, val, r_lo, r_hi)


def cell_area_km2(lat, res):
    """Area of a res x res degree cell centred at latitude lat (spherical earth)."""
    return (math.pi / 180 * R_EARTH_KM) ** 2 * res * res * np.cos(np.radians(lat))


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(np.asarray(lon2) - np.asarray(lon1)) / 2) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.sqrt(a))


# IHO seas grouped into oceans (my convention; see README). Anything not listed is matched by name below.
ARCTIC = {"Arctic Ocean", "Barentsz Sea", "White Sea", "Kara Sea", "Laptev Sea", "East Siberian Sea", "Chukchi Sea",
          "Beaufort Sea", "Lincoln Sea", "The Northwestern Passages", "Baffin Bay", "Hudson Bay", "Hudson Strait",
          "Greenland Sea", "Davis Strait"}
INDIAN = {"Indian Ocean", "Bay of Bengal", "Arabian Sea", "Laccadive Sea", "Andaman or Burma Sea", "Red Sea", "Gulf of Aden",
          "Gulf of Oman", "Persian Gulf", "Gulf of Aqaba", "Gulf of Suez", "Mozambique Channel", "Great Australian Bight",
          "Timor Sea", "Malacca Strait", "Bass Strait", "Savu Sea", "Arafura Sea"}
SOUTHERN = {"Southern Ocean"}
PACIFIC = {"North Pacific Ocean", "South Pacific Ocean", "Tasman Sea", "Coral Sea", "Solomon Sea", "Bismarck Sea", "Philippine Sea",
           "South China Sea", "Eastern China Sea", "Yellow Sea", "Japan Sea", "Sea of Okhotsk", "Bering Sea", "Gulf of Alaska",
           "Gulf of California", "The Coastal Waters of Southeast Alaska and British Columbia", "Seto Naikai or Inland Sea",
           "Gulf of Thailand", "Java Sea", "Celebes Sea", "Sulu Sea", "Makassar Strait", "Flores Sea", "Bali Sea", "Banda Sea",
           "Ceram Sea", "Halmahera Sea", "Molukka Sea", "Gulf of Tomini", "Gulf of Boni", "Singapore Strait"}


def ocean_of(sea):
    if sea in ARCTIC: return "Arctic"
    if sea in INDIAN: return "Indian"
    if sea in SOUTHERN: return "Southern"
    if sea in PACIFIC: return "Pacific"
    return "Atlantic"


def unwrap_dateline(polys):
    """Polygons whose rings jump across the 180 degree meridian are shifted into 0..360 and repeated at -360..0."""
    out = []
    for poly in polys:
        lons = [p[0] for ring in poly for p in ring]
        if max(lons) - min(lons) > 180:
            shifted = [[[x + 360 if x < 0 else x, y] for x, y in ring] for ring in poly]
            out.append(shifted); out.append([[[x - 360, y] for x, y in ring] for ring in shifted])
        else:
            out.append(poly)
    return out
