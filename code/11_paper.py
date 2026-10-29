"""Step 11. The paper: fill code/paper_template.tex from data/results.json, write release/paper/Hotham_Where_Rain_Goes.tex
and compile it with xelatex (figures from step 10).
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = json.load(open(os.path.join(DATA, "results.json"))); U, Wd = R["uk"], R["world"]
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Where_Rain_Goes"
tex = open(os.path.join(HERE, "paper_template.tex"), encoding="utf-8").read()
esc = lambda s: str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{round(v):,}"
    if f == "kms": return f"{int(round(v, -1)):,}"
    if f == "pct": return f"{round(v * 100)}\\%"
    if f == "pct1": return f"{v * 100:.1f}\\%"
    if f == "f1": return f"{v:.1f}"
    if f == "absf1": return f"{abs(v):.1f}"
    if f == "len": return str(len(v))
    raise ValueError(f)


SEAS7 = ["North Sea", "English Channel", "Celtic Sea", "Bristol Channel", "Irish Sea", "Inner Seas (west Scotland)", "Atlantic Ocean"]
HEAD7 = ["North Sea", "English Ch.", "Celtic Sea", "Bristol Ch.", "Irish Sea", "Inner Seas", "Atlantic"]
rows = ""
for a in ["England", "Scotland", "Wales", "Northern Ireland", "Isle of Man", "Ireland", "Great Britain", "United Kingdom"]:
    d = U["areas"][a]
    rows += esc(a) + f" & {U['areas_total_km2'][a]:,}" + "".join(f" & {d[s]['share'] * 100:.1f}" if s in d else " & " for s in SEAS7) + "\\\\\n"
T_AREAS = ("\\begin{table}[H]\\centering\\small\\caption{Share of land (\\%) draining to each IHO sea area. Inner Seas: the Inner Seas off the West Coast of Scotland; Atlantic: the North Atlantic Ocean; Irish Sea: the Irish Sea and St.\\ George's Channel. Land area is the grid's (km\\textsuperscript{2}).}\\label{tab:areas}"
           "\\resizebox{\\textwidth}{!}{\\begin{tabular}{lrrrrrrrr}\\toprule Area & km\\textsuperscript{2} & " + " & ".join(HEAD7) + "\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}}\\end{table}")
tr = ""
for p in U["gb_triple_points"]:
    rv = "; ".join(esc(x) for x in p["rivers"].split(" | "))
    tr += f"{esc(p['nearest_hill'])} & {esc(p['county'].split(' - ')[0])} & {p['lat']:.3f}, {p['lon']:.3f} & {p['elev_m']:,.0f} & {rv}\\\\[2pt]\n"
T_TRIPLES = ("\\begin{table}[H]\\centering\\footnotesize\\caption{Triple points on Great Britain: 2 by 2 blocks of cells touching three seas, named by the nearest OS hill, with the first named watercourses on each side.}\\label{tab:triples}"
             "\\begin{tabular}{llrr>{\\raggedright\\arraybackslash}p{6.6cm}}\\toprule Nearest hill & Area & Lat, lon & Height (m) & Seas and first rivers\\\\\\midrule\n" + tr + "\\bottomrule\\end{tabular}\\end{table}")
lr = ""
for x in U["longest_gb"]:
    lr += f"{esc(x['sea'])} & {x['km']:,.1f} & {esc(x['near'])} & {esc(x['route'].replace(' > ', ', '))}\\\\\n"
T_LONG = ("\\begin{table}[H]\\centering\\footnotesize\\caption{The longest modelled path to each sea in Great Britain, with the nearest OS place to its start and the named watercourses on the way.}\\label{tab:long}"
          "\\begin{tabular}{lrl>{\\raggedright\\arraybackslash}p{6.8cm}}\\toprule Sea & km & Starts near & Rivers\\\\\\midrule\n" + lr + "\\bottomrule\\end{tabular}\\end{table}")
wr = ""
for k in ["Atlantic", "Arctic", "Pacific", "Indian", "Inland (no outlet to the sea)"]:
    v = Wd["ocean_share"][k]; wr += f"{esc(k)} & {v['km2'] / 1e6:.2f} & {v['share'] * 100:.1f}\\\\\n"
ir = ""
for r in Wd["inland_top"][:8]:
    nm = r["lake"] if r["lake"] else "closed basin"
    nm = nm if ("Sea" in nm or nm == "closed basin") else "Lake " + nm.replace("Lake ", "")
    ir += f"{esc(nm)} & {esc(r['country'] or 'several')} & {r['km2'] / 1e6:.2f} & {esc(', '.join(r['rivers'].split(' | ')[:3]))}\\\\\n"
T_WORLD = ("\\begin{table}[H]\\centering\\small\\caption{Top: land outside Antarctica by the ocean it drains to (million km\\textsuperscript{2} and \\%). Bottom: the largest closed basins (million km\\textsuperscript{2}), with Natural Earth rivers.}\\label{tab:world}"
           "\\begin{tabular}{lrr}\\toprule Ocean & M km\\textsuperscript{2} & \\%\\\\\\midrule\n" + wr + "\\bottomrule\\end{tabular}\\\\[1em]"
           "\\resizebox{0.58\\textwidth}{!}{\\begin{tabular}{llrl}\\toprule Ends in & Country & M km\\textsuperscript{2} & Rivers\\\\\\midrule\n" + ir + "\\bottomrule\\end{tabular}}\\end{table}")
tex = tex.replace("{{TABLE_AREAS}}", T_AREAS).replace("{{TABLE_TRIPLES}}", T_TRIPLES).replace("{{TABLE_LONG}}", T_LONG).replace("{{TABLE_WORLD}}", T_WORLD)
tex = re.sub(r"\{\{([A-Za-z0-9_.() \-]+?)\|(\w+)\}\}", lambda m: fmt(get(m.group(1)), m.group(2)), tex)
assert "{{" not in tex, re.findall(r"\{\{.*?\}\}", tex)[:3]
assert "--" not in tex.replace("\\\\", ""), "double hyphen in tex"
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(tex)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
print(r.stdout[-400:])
for ext in (".aux", ".log", ".out"):
    try: os.remove(os.path.join(OUT, NAME + ext))
    except FileNotFoundError: pass
os.replace(os.path.join(OUT, NAME + ".pdf"), os.path.join(ROOT, "release", NAME + ".pdf"))
print("pdf", os.path.getsize(os.path.join(ROOT, "release", NAME + ".pdf")))
