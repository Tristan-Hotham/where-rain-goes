"""Step 8. Merge the Britain and world results into data/results.json (every number used anywhere comes from here)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

U = json.load(open(os.path.join(WORK, "results_uk.json")))
Wd = json.load(open(os.path.join(WORK, "results_world.json")))
R = dict(uk=U, world=Wd)
gb = U["areas"]["Great Britain"]
R["derived"] = dict(
    gb_ns_share=gb["North Sea"]["share"],
    gb_west_share=sum(v["share"] for k, v in gb.items() if k in ("Irish Sea", "Inner Seas (west Scotland)", "Atlantic Ocean", "Bristol Channel", "Celtic Sea")),
    gb_channel_share=gb["English Channel"]["share"],
    severn_km=U["longest_gb"][0]["km"], thames_km=[x for x in U["longest_gb"] if x["sea"] == "North Sea"][0]["km"],
    world_inland_share=Wd["ocean_share"]["Inland (no outlet to the sea)"]["share"],
    world_atlantic_share=Wd["ocean_share"]["Atlantic"]["share"],
    nile_km=[x for x in Wd["longest_by_ocean"] if x["ocean"] == "Atlantic"][0]["km"],
    net_agree=U["validation"]["network"]["agree_share"],
    hb_gb=U["validation"]["hydrobasins_great_britain"]["agree_share"],
    hb_ie=U["validation"]["hydrobasins_ireland"]["agree_share"],
    moscow_km=[c for c in Wd["big_city_examples"] if c["name"] == "Moscow"][0]["dist_km"],
)
R["meta"] = dict(doi="10.5281/zenodo.23757700", url="https://maps.tristanhotham.com/where-rain-goes/",
                 repo="https://github.com/Tristan-Hotham/where-rain-goes", blog="https://blog.tristanhotham.com/2026/10/29/where-rain-goes/")
json.dump(R, open(os.path.join(DATA, "results.json"), "w"), indent=1, ensure_ascii=False, default=float)
print(json.dumps(R["derived"], indent=1))
