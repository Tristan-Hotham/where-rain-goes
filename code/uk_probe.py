"""Helper: print the modelled path for a few places (used for checking)."""
import numpy as np, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import WORK
G = np.load(os.path.join(WORK, "uk_grid.npz")); C = json.load(open(os.path.join(WORK, "uk_chains.json")))
X0, Y0, Z = int(G["X0"]), int(G["Y0"]), 9; NP = 256 * 2 ** Z
def px(lon, lat):
    la = math.radians(lat); return int((lon + 180) / 360 * NP) - X0, int((1 - math.log(math.tan(la) + 1 / math.cos(la)) / math.pi) / 2 * NP) - Y0
def chain(c):
    out = []
    while c >= 0: out.append(C["names"][C["ch_name"][c]]); c = C["ch_next"][c]
    return out
if __name__ == "__main__":
    for nm, lon, lat in [("Leeds", -1.549, 53.797), ("Birmingham", -1.89, 52.48), ("Oxford", -1.257, 51.752), ("Kinder", -1.87, 53.385), ("Aviemore", -3.83, 57.19), ("Coventry", -1.51, 52.41), ("Cambridge", 0.12, 52.2), ("Clitheroe", -2.393, 53.871), ("Manchester", -2.24, 53.48), ("Carlisle", -2.93, 54.89)]:
        c, r = px(lon, lat); print(nm, C["seas"][G["lab"][r, c] - 1], round(float(G["dist"][r, c]) / 10, 1), chain(int(G["chain"][r, c])))
