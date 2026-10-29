"""Shared drawing helpers for the static figures, header and collage: colours (the same as the page) and RGB images of
the Britain and Ireland model and the world grid, drawn from the files in work/ (no web tiles)."""
import colorsys, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import WORK, DATA, ocean_of

SEA_HEX = {
    "North Sea": "#2F67B1", "English Channel": "#E3A23A", "Bristol Channel": "#8B56B4", "Irish Sea and St. George's Channel": "#3E9E66",
    "Inner Seas off the West Coast of Scotland": "#D2594A", "North Atlantic Ocean": "#1F3A73", "Celtic Sea": "#D9C443",
    "South Atlantic Ocean": "#4A86CF", "Gulf of Mexico": "#6FB3EA", "Mediterranean Sea - Eastern Basin": "#20508F", "Mediterranean Sea - Western Basin": "#3767AD",
    "Black Sea": "#4F4FA8", "Gulf of Guinea": "#86BCE4", "Rio de La Plata": "#5C8AD6", "Baltic Sea": "#6283BD", "Caribbean Sea": "#58A6D6",
    "Gulf of St. Lawrence": "#3D72C2", "Bay of Biscay": "#7FA3D8", "Adriatic Sea": "#2D5C9E", "Aegean Sea": "#4467A6", "Sea of Azov": "#6F67B8",
    "Kara Sea": "#B6AEE2", "Laptev Sea": "#9E93D6", "Hudson Bay": "#C9C1EE", "Beaufort Sea": "#9688CC", "East Siberian Sea": "#D4CEF3",
    "Barentsz Sea": "#8A7EC4", "White Sea": "#A69EDA", "Arctic Ocean": "#BBB4E6", "Greenland Sea": "#AFA6DE", "Baffin Bay": "#C3BBEA",
    "The Northwestern Passages": "#B0A6E0", "Hudson Strait": "#D8D2F4", "Norwegian Sea": "#5B7BC6",
    "Bay of Bengal": "#E7A03A", "Arabian Sea": "#D7812A", "Indian Ocean": "#EFBF63", "Persian Gulf": "#C4672A", "Mozambique Channel": "#E6B34F",
    "Great Australian Bight": "#DA9852", "Red Sea": "#B8542E", "Timor Sea": "#E4AA6A", "Andaman or Burma Sea": "#D9913F", "Gulf of Aden": "#C98A55",
    "South China Sea": "#2BA48B", "Eastern China Sea": "#1C8770", "Yellow Sea": "#7BC4A2", "Sea of Okhotsk": "#4DB2A7", "Bering Sea": "#6CC0C2",
    "North Pacific Ocean": "#1F8A88", "South Pacific Ocean": "#2E9E78", "Gulf of Alaska": "#55B6AE", "Gulf of California": "#9CD5BE",
    "Coral Sea": "#3CBE9A", "Japan Sea": "#48A687", "Gulf of Thailand": "#5FB78C", "Java Sea": "#3F9F7F", "Tasman Sea": "#62B39A"}
OCEAN_HEX = {"Atlantic": "#2F67B1", "Pacific": "#21A08A", "Indian": "#E39A35", "Arctic": "#AA9FE0", "Southern": "#7F9BB0", "Inland": "#6B5E55"}
FAM = {"Atlantic": (215, 55), "Pacific": (165, 50), "Indian": (33, 70), "Arctic": (252, 45), "Southern": (205, 20)}
SHORT = {"Irish Sea and St. George's Channel": "Irish Sea", "Inner Seas off the West Coast of Scotland": "Inner Seas (west Scotland)", "North Atlantic Ocean": "Atlantic Ocean"}
hexrgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def sea_rgb(seas):
    out = []
    for k, s in enumerate(seas):
        if s in SEA_HEX: out.append(hexrgb(SEA_HEX[s])); continue
        h, sat = FAM[ocean_of(s)]; h = (h + ((k * 37) % 30) - 15) % 360; l = (42 + ((k * 53) % 34)) / 100
        r, g, b = colorsys.hls_to_rgb(h / 360, l, sat / 100); out.append(np.array([r, g, b], np.float32) * 255)
    return np.array(out)


def uk_image(step=1, hills=.55, rivers=2, sheds=True, crop=None, bg=(243, 245, 244)):
    """RGB image of the Britain and Ireland model (zoom 9 grid), every `step` cells; crop = (lon0, lat1, lon1, lat0)."""
    G = np.load(os.path.join(WORK, "uk_grid.npz"))
    lab, region, elev, pix_m = G["lab"], G["region"], G["elev"].astype(np.float32), G["pix_m"]
    X0, Y0, Z = int(G["X0"]), int(G["Y0"]), int(G["Z"]); NP = 256 * 2 ** Z
    rc = np.load(os.path.join(WORK, "uk_rivers.npz"))["rcls"]
    seas = json.load(open(os.path.join(WORK, "uk_chains.json")))["seas"]
    r0, r1, c0, c1 = 0, lab.shape[0], 0, lab.shape[1]
    if crop:
        lo0, la1, lo1, la0 = crop
        f = lambda lat: (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * NP - Y0
        c0, c1 = int((lo0 + 180) / 360 * NP - X0), int((lo1 + 180) / 360 * NP - X0); r0, r1 = int(f(la1)), int(f(la0))
    sl = (slice(r0, r1, step), slice(c0, c1, step))
    L = np.where(region[sl] > 0, lab[sl], 0); E = elev[sl]; RC = rc[sl]; pm = pix_m[r0:r1:step][:, None] * step
    pal = np.vstack([np.array(bg, np.float32), sea_rgb(seas)])
    img = pal[L]
    if hills:
        gy, gx = np.gradient(E); dzdx = gx / pm * 2.5; dzdn = -gy / pm * 2.5
        alt = math.radians(45); lx, ly, lz = -math.cos(alt) * math.sqrt(.5), math.cos(alt) * math.sqrt(.5), math.sin(alt)
        hs = np.clip((-dzdx * lx - dzdn * ly + lz) / np.sqrt(1 + dzdx ** 2 + dzdn ** 2), 0, 1)
        f_ = 1 - hills * (1 - hs) * .9; img = img * f_[..., None]
    if rivers:
        m = (RC >= 5 - rivers) & (L > 0); t = (.35 + .13 * RC[m])[:, None]
        img[m] = img[m] * (1 - t) + np.array([12, 40, 80], np.float32) * t
    if sheds:
        e = np.zeros(L.shape, bool)
        e[:, :-1] |= (L[:, :-1] != L[:, 1:]) & (L[:, :-1] > 0) & (L[:, 1:] > 0)
        e[:-1, :] |= (L[:-1, :] != L[1:, :]) & (L[:-1, :] > 0) & (L[1:, :] > 0)
        img[e] = (20, 32, 43)
    img[L == 0] = bg
    return np.clip(img, 0, 255).astype(np.uint8), seas


def world_image(mode="sea", lat_top=84, lat_bot=-58, step=1, bg=(243, 245, 244), sheds=True, robinson=False):
    """RGB image of the world grid (0.05 degrees), mode 'sea' or 'ocean', equirectangular rows lat_top to lat_bot."""
    Wz = np.load(os.path.join(WORK, "world_grids.npz")); sea = Wz["sea"]
    Bj = json.load(open(os.path.join(WORK, "world_basins.json"))); SEAS = Bj["SEAS"]
    r0, r1 = int((90 - lat_top) / .05), int((90 - lat_bot) / .05)
    S = sea[r0:r1:step, ::step].astype(np.int32)
    if mode == "sea":
        pal = np.vstack([np.array(bg, np.float32), sea_rgb(SEAS)])
        img = pal[np.maximum(S, 0)]; img[S == -1] = hexrgb(OCEAN_HEX["Inland"])
        key = S
    else:
        oc = ["Atlantic", "Pacific", "Indian", "Arctic", "Southern"]
        so = np.array([oc.index(ocean_of(s)) + 1 for s in SEAS])
        O = np.zeros(S.shape, np.int32); O[S > 0] = so[S[S > 0] - 1]; O[S == -1] = 6
        pal = np.vstack([np.array(bg, np.float32)] + [hexrgb(OCEAN_HEX[o]) for o in oc + ["Inland"]])
        img = pal[O]; key = O
    if sheds:
        e = np.zeros(key.shape, bool)
        e[:, :-1] |= (key[:, :-1] != key[:, 1:]) & (key[:, :-1] != 0) & (key[:, 1:] != 0)
        e[:-1, :] |= (key[:-1, :] != key[1:, :]) & (key[:-1, :] != 0) & (key[1:, :] != 0)
        img[e] = img[e] * .55
    return img.astype(np.uint8), SEAS
