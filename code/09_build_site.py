"""Step 9. Build index.html from code/page_template.html and code/page_script.js.

Every number in the text is a {{path|format}} token filled from data/results.json, so the page cannot drift from the
analysis. Facts the template states in words are checked here with assertions.
"""
import json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = json.load(open(os.path.join(DATA, "results.json"), encoding="utf-8"))
tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
js = open(os.path.join(HERE, "page_script.js"), encoding="utf-8").read()


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(v):,}"
    if f == "kms": return f"{int(round(v, -1)):,}"
    if f == "pct": return f"{round(v * 100)}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    if f == "absf1": return f"{abs(v):.1f}"
    if f == "len": return str(len(v))
    raise ValueError(f)


U, Wd = R["uk"], R["world"]
# facts stated in words in the template
assert "North Sea" not in U["areas"]["Wales"]                                   # "Wales sends none of its rain there"
tw = sorted(x[0] for x in U["places"]["towns_on_watershed_list"])
assert tw == sorted(["Bedworth", "Blackheath", "Cumbernauld", "Dudley", "Market Drayton", "Rowley Regis", "Sedgley"]), tw
assert len(U["gb_triple_points"]) == 6                                          # "Six triple points"
tp = U["gb_triple_points"]
assert "Clyde Law" == tp[1]["nearest_hill"] and "River Annan" in tp[1]["rivers"] and "River Tweed" in tp[1]["rivers"] and "River Clyde" in tp[1]["rivers"]
assert tp[2]["nearest_hill"] == "Swallow Hill" and "River Tern" in tp[2]["rivers"] and "River Weaver" in tp[2]["rivers"] and "Meece Brook > River Sow > River Trent" in tp[2]["rivers"]
lg = U["longest_gb"]
assert lg[0]["near"] == "Dylife" and "Severn" in lg[0]["route"] and lg[1]["near"] == "Birdlip" and "River Churn > River Thames" == lg[1]["route"]
ft = U["places"]["farthest_towns"]; assert [ft[0]["name"], ft[1]["name"], ft[2]["name"]] == ["Llanidloes", "Cirencester", "Swindon"]
assert U["north_sea_divide_points"]["highest"]["hill"] == "Ben Alder" and U["north_sea_divide_points"]["lowest"]["hill"] == "Corsback Hill"
lo = [x["ocean"] for x in Wd["longest_by_ocean"]]; assert lo[:5] == ["Atlantic", "Pacific", "Indian", "Arctic", "Inland (no outlet to the sea)"], lo
lb = Wd["longest_by_ocean"]
assert "Kagera" in lb[0]["route"] and "(BI)" in lb[0]["near_city"] and "Yangtze" in lb[1]["route"] and "Irtysh" in lb[3]["route"] and "Volga" in lb[4]["route"]
assert lb[4]["route"].startswith("Oka")
it = [r["lake"] for r in Wd["inland_top"][:5]]; assert it[0] == "Caspian Sea" and "Chad" in it and "Eyre North" in it, it
assert Wd["inland_top"][0]["km2"] > 2 * Wd["inland_top"][1]["km2"]             # "by far the largest"
assert any("Okavango" in r["rivers"] for r in Wd["inland_top"][:6]) and any("Tarim" in r["rivers"] for r in Wd["inland_top"][:6])
mos = [c for c in Wd["big_city_examples"] if c["name"] == "Moscow"][0]; assert mos["ocean"] == "Inland" and "Volga" in mos["route"]
assert len(Wd["triple_points_ocean_only"]) == 1 and abs(Wd["triple_points_ocean_only"][0]["lat"] - 48.6) < 0.3   # Montana
cm = Wd["countries_most_seas"]; assert cm[0]["country"] == "Indonesia" and {cm[1]["country"], cm[2]["country"]} == {"Russia", "Canada"} and cm[1]["n_seas"] == cm[2]["n_seas"] > cm[3]["n_seas"]
assert {c["country"] for c in Wd["countries_all_inland"]} <= {"Turkmenistan", "Uzbekistan", "Kyrgyzstan", "Tajikistan", "Azerbaijan", "Armenia", "Baikonur"}
o = Wd["ocean_share"]; assert o["Atlantic"]["share"] > o["Arctic"]["share"] > o["Pacific"]["share"] > o["Indian"]["share"]
assert 0.18 < R["derived"]["world_inland_share"] < 0.26                          # "a fifth" (heading) is loose but fair
mex = [c for c in Wd["big_city_examples"] if c["name"] == "Mexico City"][0]; assert mex["ocean"] == "Inland"
bf = sorted(U["areas"]["Northern Ireland"].items(), key=lambda kv: -kv[1]["share"])[0][0]; assert bf == "Inner Seas (west Scotland)"
ie = sorted(U["areas"]["Ireland"].items(), key=lambda kv: -kv[1]["share"])[0]; assert ie[0] == "Atlantic Ocean" and ie[1]["share"] > 0.5

html = re.sub(r"\{\{([A-Za-z0-9_.() \-]+?)(\|(\w+))?\}\}", lambda m: fmt(get(m.group(1)), m.group(3)), tpl)
assert "{{" not in html, re.findall(r"\{\{.*?\}\}", html)[:3]
# the divide profile: every fourth cell, rounded
D = np.load(os.path.join(WORK, "ns_divide.npz"))
k = np.arange(0, len(D["lat"]), 4)
spine = dict(lat=[round(float(v), 3) for v in D["lat"][k]], e=[int(v) for v in D["elev"][k]])
js = js.replace("/*RESULTS*/", json.dumps(R, ensure_ascii=False, separators=(",", ":"))).replace("/*SPINE*/", json.dumps(spine, separators=(",", ":")))
html = html.replace("/*SCRIPT*/", js)
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
bad = [c for c in ("\u2014", "\u2013") if c in html]   # visible dashes; "--" occurs only in CSS variable names
print("index.html", len(html), "bytes; dash check:", bad or "clean")
