"""Step 2. The river network of Great Britain (OS Open Rivers) traced to the sea.

For every watercourse link I follow the flow downstream, node by node, until the water reaches a node with no link
leaving it. If that last node is an OS 'outlet' (where a watercourse meets the sea) the link reaches the sea there.
Canals are left out of the routing: they are made by people and some cross watersheds. Where a river splits
(a bifurcation) I follow the branch that is not a canal and, of those, the one that reaches the sea soonest, and I
record every split whose branches end in different seas.
The sea at each outlet is the IHO sea area nearest to the outlet point (Marine Regions IHO Sea Areas v3).
Writes work/links.npz, work/chains.json, work/outlets.csv, work/bifurcations.csv.
"""
import json, os, sqlite3, struct, sys
import numpy as np, pandas as pd
from pyproj import Transformer
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

con = sqlite3.connect(OSRIVERS)


def gpkg_xy(blob):
    """Coordinates of a GeoPackage LINESTRING or POINT blob (British National Grid metres)."""
    flags = blob[3]; env = (flags >> 1) & 7
    off = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[env]
    le = blob[off] == 1; typ = struct.unpack_from("<I" if le else ">I", blob, off + 1)[0] % 1000
    if typ == 1:
        return np.frombuffer(blob, "<f8" if le else ">f8", 2, off + 5).reshape(1, 2)
    n = struct.unpack_from("<I" if le else ">I", blob, off + 5)[0]
    return np.frombuffer(blob, "<f8" if le else ">f8", 2 * n, off + 9).reshape(n, 2)


rows = con.execute("select geometry, id, flow_direction, length, form, watercourse_name, start_node, end_node, watercourse_name_alternative from watercourse_link").fetchall()
nodes = {r[1]: (gpkg_xy(r[0])[0], r[2]) for r in con.execute("select geometry, id, hydro_node_category from hydro_node")}
L = len(rows); print("links", L, "nodes", len(nodes))
geom = []; start = []; end = []; length = np.zeros(L); form = []; name = []
def display_name(nm, alt):
    """OS gives Welsh and English names for some Welsh rivers; show both, the English-style 'River ...' first."""
    if not nm: return alt or ""
    # the alternative name is often just the name of a reach or pool; keep it only when it is the river's other name
    welsh = lambda t: t.split(" ")[0] in ("Afon", "Nant")
    if alt and alt != nm and (welsh(alt) or welsh(nm)) and (alt.startswith("River ") or nm.startswith("River ")):
        return f"{alt} ({nm})" if alt.startswith("River ") else f"{nm} ({alt})"
    if alt and alt.startswith("River ") and not nm.startswith("River "):
        return alt      # name1 is the name of a reach or pool; the alternative is the river
    return nm
for k, (g, i, fd, ln, fm, nm, s, e, alt) in enumerate(rows):
    nm = display_name(nm, alt)
    xy = gpkg_xy(g)
    if fd == "in opposite direction":
        xy = xy[::-1]; s, e = e, s
    geom.append(xy); start.append(s); end.append(e); length[k] = ln; form.append(fm); name.append(nm or "")
form = np.array(form); canal = form == "canal"
out_of = {}
for k in range(L):
    out_of.setdefault(start[k], []).append(k)

# --- IHO seas near Britain, in BNG ---
B = load_bundle()
SEAS = [f["p"]["name"] for f in B["iho"]]
to_bng = Transformer.from_crs(4326, 27700, always_xy=True)
to_ll = Transformer.from_crs(27700, 4326, always_xy=True)
polys, pid = [], []
for k, f in enumerate(B["iho"]):
    for poly in f["g"]:
        ring = np.array(poly[0])
        if ring[:, 0].max() < -25 or ring[:, 0].min() > 15 or ring[:, 1].max() < 40 or ring[:, 1].min() > 70:
            continue
        rr = []
        for ring in poly:
            a = np.array(ring); a = a[(a[:, 1] > 35) & (a[:, 1] < 75) & (a[:, 0] > -40) & (a[:, 0] < 30)]
            if len(a) < 4: rr.append(None); continue
            x, y = to_bng.transform(a[:, 0], a[:, 1]); rr.append(np.c_[x, y])
        if rr[0] is None: continue
        p = Polygon(rr[0], [r for r in rr[1:] if r is not None]).buffer(0)
        polys.append(p); pid.append(k)
tree = STRtree(polys)
print("IHO polygons near GB", len(polys), sorted(set(SEAS[k] for k in pid)))


def sea_at(x, y):
    i = tree.nearest(Point(x, y)); return pid[i]



SEAU = None
from shapely.ops import unary_union
SEAU = unary_union(polys)
from shapely import prepared
SEAP = prepared.prep(SEAU.buffer(4000))
coastal = {}
for t, ((x, y), cat) in nodes.items():
    if cat == "outlet":
        coastal[t] = SEAP.contains(Point(x, y))
tidal_end = set(end[k] for k in range(L) if form[k] == "tidalRiver")
for t in coastal:
    coastal[t] = coastal[t] or t in tidal_end
print("outlet nodes", len(coastal), "treated as sea ends (within 4 km of the IHO sea or at the end of a tidal river)", sum(coastal.values()))
def is_sea_end(t):
    return coastal.get(t, False)

# --- close small gaps in the network ---
# OS Open Rivers has places where a watercourse stops a few metres short of the next one (for example the Thames at
# Oxford ends at an inland 'outlet' node 36 m from the next Thames link). Every dead end that is not a sea outlet is
# joined to the nearest point on another link within GAP_M metres, preferring a link with the same name.
from scipy.spatial import cKDTree
GAP_M = 300.0
vx = np.concatenate(geom); vlink = np.repeat(np.arange(L), [len(g) for g in geom])
VT = cKDTree(vx)
into = {}
for k in range(L):
    into.setdefault(end[k], []).append(k)
n_join = 0; join_rows = []
for t, ins in into.items():
    if t in out_of or is_sea_end(t):
        continue
    (x, y), cat = nodes.get(t, ((geom[ins[0]][-1]), None))
    d, ii = VT.query([x, y], k=40, distance_upper_bound=GAP_M)
    cands = {}
    for dd, i in zip(d, ii):
        if not np.isfinite(dd): continue
        j = int(vlink[i])
        if j in ins or j in cands: continue
        cands[j] = dd
    if not cands: continue
    nm_in = set(name[k] for k in ins if name[k])
    j = min(cands, key=lambda j: (0 if name[j] in nm_in else 1, 1 if canal[j] else 0, cands[j]))
    out_of[t] = [j]; n_join += 1
    join_rows.append((t, j, round(float(cands[j]), 1), name[j]))
print("dead ends joined across a gap of up to", GAP_M, "m:", n_join)

# --- route every link to the sea: shortest path over the network (Dijkstra from the sea ends, upstream) ---
# Cost is length, with canals counted 25 times their length so that water only follows a canal when no natural
# channel leads on (some canal sections carry rivers through towns). Each link then follows the next link that lies
# on its cheapest route to the sea.
import heapq
CANAL_W = 25.0
wlen = np.where(canal, length * CANAL_W, length)
rev = {}
for t, js in out_of.items():
    for j in js:
        rev.setdefault(end[j], []).append((t, j))
Cn = {}
hq = [(0.0, t) for t in coastal if coastal[t]]
for c, t in hq: Cn[t] = 0.0
heapq.heapify(hq)
while hq:
    c, u = heapq.heappop(hq)
    if c > Cn.get(u, 1e30): continue
    for t, j in rev.get(u, []):
        nc = c + wlen[j]
        if nc < Cn.get(t, 1e30):
            Cn[t] = nc; heapq.heappush(hq, (nc, t))
nxt = np.full(L, -1)
for k in range(L):
    u = end[k]
    if is_sea_end(u) or u not in Cn: continue
    best = min((j for j in out_of.get(u, []) if end[j] in Cn and j != k), key=lambda j: wlen[j] + Cn[end[j]], default=-1)
    nxt[k] = best
# real distance (metres) from the downstream end of each link to its sea end, and the terminal node
dist_end = np.full(L, np.nan); term = [None] * L
order = sorted(range(L), key=lambda k: Cn.get(end[k], 1e30))
for k in order:
    u = end[k]
    if is_sea_end(u):
        dist_end[k] = 0.0; term[k] = u
    elif nxt[k] >= 0 and term[nxt[k]] is not None:
        dist_end[k] = dist_end[nxt[k]] + length[nxt[k]]; term[k] = term[nxt[k]]
    else:
        dist_end[k] = 0.0; term[k] = None
is_outlet = np.array([term[k] is not None and is_sea_end(term[k]) for k in range(L)])
print("links reaching an outlet", (is_outlet & ~canal).sum(), "of", (~canal).sum())

# outlets and their seas
term_ids = sorted(set(term[k] for k in range(L) if is_outlet[k] and not canal[k]))
osea = {}
orows = []
for t in term_ids:
    (x, y), cat = nodes[t]
    s = sea_at(x, y); osea[t] = s
    lon, lat = to_ll.transform(x, y)
    orows.append(dict(node=t, x=round(x, 1), y=round(y, 1), lon=round(lon, 5), lat=round(lat, 5), sea=SEAS[s]))
link_sea = np.full(L, -1)
for k in range(L):
    if is_outlet[k] and not canal[k]:
        link_sea[k] = osea[term[k]]

# name chain per link: distinct watercourse names met on the way down (in order)
chain_of = np.full(L, -1); chains = {}; chain_list = []
names_all = sorted(set(n for n in name if n)); nid = {n: i for i, n in enumerate(names_all)}
memo = {}
def chain(k):
    seq = []; j = k; guard = 0
    while j >= 0 and guard < 20000:
        if name[j] and (not seq or seq[-1] != nid[name[j]]):
            seq.append(nid[name[j]])
        j = nxt[j]; guard += 1
    out = []
    for s in seq:
        if s not in out: out.append(s)
    return tuple(out)
for k in range(L):
    if canal[k] or not is_outlet[k]: continue
    c = chain(k)
    if c not in chains: chains[c] = len(chain_list); chain_list.append(list(c))
    chain_of[k] = chains[c]
print("distinct name chains", len(chain_list))

# terminal (mouth) name per outlet: the last named watercourse above it
mouth_name = {}
for k in range(L):
    if is_outlet[k] and not canal[k] and nxt[k] < 0 and name[k]:
        mouth_name.setdefault(term[k], name[k])
for r in orows:
    r["last_name"] = mouth_name.get(r["node"], "")
pd.DataFrame(orows).to_csv(os.path.join(WORK, "outlets.csv"), index=False)

# bifurcations whose branches reach different seas
bif = []
for nd_, outs in out_of.items():
    outs = [j for j in outs if is_outlet[j] and link_sea[j] >= 0]
    if len(outs) > 1:
        ss = sorted(set(int(link_sea[j]) for j in outs))
        if len(ss) > 1:
            (x, y), cat = nodes[nd_]; lon, lat = to_ll.transform(x, y)
            bif.append(dict(node=nd_, lon=round(lon, 5), lat=round(lat, 5), seas="|".join(SEAS[s] for s in ss),
                            names="|".join(sorted(set(name[j] for j in outs if name[j]))),
                            forms="|".join(sorted(set(form[j] for j in outs)))))
pd.DataFrame(bif).to_csv(os.path.join(WORK, "bifurcations.csv"), index=False)
print("bifurcations to different seas", len(bif))

# upstream length of watercourse above (and including) each link, along the routing tree (km)
ordr = [k for k in sorted(range(L), key=lambda k: Cn.get(end[k], 1e30) + wlen[k], reverse=True)]
up = length.copy() / 1000.0
for k in ordr:
    j = nxt[k]
    if j >= 0: up[j] += up[k]
up_km = up

# flatten geometry for rasterising (lon/lat), with distance-to-mouth at every vertex
offs = np.zeros(L + 1, np.int64)
for k in range(L): offs[k + 1] = offs[k] + len(geom[k])
xy = np.concatenate(geom)
lon, lat = to_ll.transform(xy[:, 0], xy[:, 1])
dv = np.zeros(len(xy))
for k in range(L):
    g = geom[k]; seg = np.r_[0, np.cumsum(np.hypot(*np.diff(g, axis=0).T))]
    tot = seg[-1] if seg[-1] > 0 else 1
    rem = (seg[-1] - seg) * (length[k] / tot)
    dv[offs[k]:offs[k + 1]] = (dist_end[k] if np.isfinite(dist_end[k]) else 0) + rem
np.savez_compressed(os.path.join(WORK, "links.npz"), offs=offs, lon=lon.astype(np.float32), lat=lat.astype(np.float32),
                    sea=link_sea, chain=chain_of, up_km=up_km, canal=canal, outlet=is_outlet, length=length, nxt=nxt,
                    dist_end=dist_end, form=form, name=np.array(name))
json.dump(dict(names=names_all, chains=chain_list, seas=SEAS), open(os.path.join(WORK, "chains.json"), "w"))
s = pd.Series([SEAS[x] for x in link_sea if x >= 0]).value_counts(); print(s)
