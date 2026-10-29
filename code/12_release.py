"""Step 12. README.md, the blog post (release/blog/post.html, meta.json) and the Zenodo folder (release/zenodo/).
All numbers are filled from data/results.json.
"""
import json, os, re, shutil, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = json.load(open(os.path.join(DATA, "results.json"))); U, Wd = R["uk"], R["world"]


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{round(v):,}"
    if f == "kms": return f"{int(round(v, -1)):,}"
    if f == "pct": return f"{round(v * 100)}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    if f == "len": return str(len(v))
    raise ValueError(f)


fill = lambda t: re.sub(r"\{\{([A-Za-z0-9_.() \-]+?)\|(\w+)\}\}", lambda m: fmt(get(m.group(1)), m.group(2)), t)
# words in the blog alt text that must match the data
A = U["areas"]
assert [round(A["England"]["North Sea"]["share"] * 100), round(A["Scotland"]["North Sea"]["share"] * 100), round(A["Scotland"]["Inner Seas (west Scotland)"]["share"] * 100),
        round(A["Wales"]["Bristol Channel"]["share"] * 100), round(A["Wales"]["Irish Sea"]["share"] * 100), round(A["Northern Ireland"]["Inner Seas (west Scotland)"]["share"] * 100),
        round(A["Ireland"]["Atlantic Ocean"]["share"] * 100)] == [58, 50, 36, 52, 43, 75, 56]

readme = fill(open(os.path.join(HERE, "readme_template.md"), encoding="utf-8").read())
assert "{{" not in readme
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)

BO = os.path.join(ROOT, "release", "blog")
post = fill(open(os.path.join(HERE, "blog_template.html"), encoding="utf-8").read())
assert "{{" not in post.replace("{{IMG|", "")
for m in re.findall(r"\{\{IMG\|([^|]+)\|", post):
    assert os.path.exists(os.path.join(BO, m)), m
open(os.path.join(BO, "post.html"), "w", encoding="utf-8").write(post)
txt = re.sub(r"<[^>]+>", " ", re.sub(r"\{\{IMG\|[^}]*\}\}", " ", post)); words = len(txt.split())
gb = A["Great Britain"]
meta = dict(title="Where rain goes: which sea does your rain end up in?", slug="where-rain-goes",
            excerpt=f"Every place in Britain, Ireland and the world, followed downhill to the sea. {gb['North Sea']['share'] * 100:.0f}% of Great Britain drains to the North Sea, Wales sends none of its rain there, and {R['derived']['world_inland_share'] * 100:.0f}% of the world's land never reaches the sea at all.",
            seo_description="Which sea does your rain reach? A map of every place in Britain, Ireland and the world by the sea its rivers drain to, with paths and distances.",
            tags=["rivers", "watersheds", "maps", "Britain", "geography", "interactive", "data", "water"],
            header_alt="Title card reading 'Where rain goes' in dark ink and rain blue on pale grey, beside a map of Britain and Ireland coloured by the sea each place drains to: blue North Sea in the east, red Inner Seas in western Scotland and Northern Ireland, green Irish Sea, purple Bristol Channel, amber English Channel, navy Atlantic and yellow Celtic Sea. Text: Which sea does your rain end up in? Every place in Britain, Ireland and the world, followed downhill to the sea. " + f"{gb['North Sea']['share'] * 100:.0f}% of Great Britain drains to the North Sea.")
assert len(meta["seo_description"]) < 160
json.dump(meta, open(os.path.join(BO, "meta.json"), "w"), indent=2, ensure_ascii=False)
print("blog words", words)

# --- Zenodo ---
ZO = os.path.join(ROOT, "release", "zenodo"); os.makedirs(ZO, exist_ok=True)
NAME = "Hotham_Where_Rain_Goes"
shutil.copy(os.path.join(ROOT, "release", NAME + ".pdf"), ZO)
for f in ["uk_seas_by_area.csv", "uk_places.csv", "uk_river_systems.csv", "uk_triple_points.csv", "world_seas.csv", "world_inland_basins.csv",
          "world_triple_points.csv", "world_countries.csv", "results.json"]:      # world_cities.csv is in the zip
    shutil.copy(os.path.join(DATA, f), ZO)
zp = os.path.join(ZO, "where-rain-goes_code_and_data.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for base in ("code", "data"):
        for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
            if "__pycache__" in dp: continue
            for f in fn:
                p = os.path.join(dp, f); z.write(p, os.path.relpath(p, ROOT))
    z.write(os.path.join(ROOT, "README.md"), "README.md"); z.write(os.path.join(ROOT, "LICENSE"), "LICENSE")
tex = open(os.path.join(ROOT, "release", "paper", NAME + ".tex"), encoding="utf-8").read()
abstract = re.search(r"\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n\\textbf\{Keywords", tex, re.S).group(1)
abstract = abstract.replace("\\%", "%").replace("\\textdegree\\", "°").replace("\\textdegree", "°").replace("~", " ")
abstract = re.sub(r"\\[a-z]+\{([^}]*)\}", r"\1", abstract)
zmeta = dict(title="Where Rain Goes: The Sea Every Place in Britain, Ireland and the World Drains To",
             description_html=f"<p>{abstract}</p><p>Interactive version: https://maps.tristanhotham.com/where-rain-goes/. Data and code: https://github.com/Tristan-Hotham/where-rain-goes. Blog post: to follow.</p>",
             keywords=["watersheds", "drainage divides", "river basins", "endorheic basins", "IHO sea areas", "priority flood", "OS Open Rivers", "HydroBASINS", "Great Britain", "open data"],
             licence="cc-by-4.0",
             licence_note="Paper, text and figures CC BY 4.0; code MIT; OS-derived data Open Government Licence v3.0; HydroBASINS-derived data under the HydroSHEDS v1 licence with its attribution (see LICENSE in the zip). The lead should confirm the Zenodo licence choice.",
             related=[dict(identifier="https://github.com/Tristan-Hotham/where-rain-goes", relation="issupplementedby", resource_type="software"),
                      dict(identifier="https://maps.tristanhotham.com/where-rain-goes/", relation="issupplementedby", resource_type="other"),
                      dict(identifier="https://www.ordnancesurvey.co.uk/products/os-open-rivers", relation="isderivedfrom", resource_type="dataset"),
                      dict(identifier="https://www.ordnancesurvey.co.uk/products/os-open-names", relation="isderivedfrom", resource_type="dataset"),
                      dict(identifier="https://www.hydrosheds.org/products/hydrobasins", relation="isderivedfrom", resource_type="dataset"),
                      dict(identifier="https://doi.org/10.1002/hyp.9740", relation="isderivedfrom", resource_type="other"),
                      dict(identifier="https://www.marineregions.org/", relation="isderivedfrom", resource_type="dataset"),
                      dict(identifier="https://github.com/tilezen/joerd", relation="isderivedfrom", resource_type="dataset"),
                      dict(identifier="https://www.naturalearthdata.com/", relation="isderivedfrom", resource_type="dataset"),
                      dict(identifier="https://www.geonames.org/", relation="isderivedfrom", resource_type="dataset")])
json.dump(zmeta, open(os.path.join(ZO, "meta.json"), "w"), indent=2, ensure_ascii=False)
for f in sorted(os.listdir(ZO)): print(f, os.path.getsize(os.path.join(ZO, f)))
