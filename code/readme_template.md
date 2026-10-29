# Where rain goes: which sea does your rain end up in?

Every place in Britain and Ireland (at about 180 m) and on the world's land outside Antarctica (at 0.05°) coloured by the sea or ocean its rain reaches, with an interactive map: click anywhere, or search a place or UK postcode, to see the sea, roughly how far the water travels and the rivers on the way.

**Interactive version:** https://maps.tristanhotham.com/where-rain-goes/

**Paper and archived release:** https://doi.org/10.5281/zenodo.23757700

**Blog post:** https://blog.tristanhotham.com/2026/10/29/where-rain-goes/

A data study by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- {{derived.gb_ns_share|pct1}} of Great Britain drains to the North Sea, {{derived.gb_west_share|pct1}} to the western seas (Irish Sea {{uk.areas.Great Britain.Irish Sea.share|pct1}}, Inner Seas off the West Coast of Scotland {{uk.areas.Great Britain.Inner Seas (west Scotland).share|pct1}}, Bristol Channel {{uk.areas.Great Britain.Bristol Channel.share|pct1}}, North Atlantic {{uk.areas.Great Britain.Atlantic Ocean.share|pct1}}, Celtic Sea {{uk.areas.Great Britain.Celtic Sea.share|pct1}}) and {{derived.gb_channel_share|pct1}} to the English Channel.
- England: {{uk.areas.England.North Sea.share|pct}} North Sea. Wales: none to the North Sea; {{uk.areas.Wales.Bristol Channel.share|pct}} Bristol Channel, {{uk.areas.Wales.Irish Sea.share|pct}} Irish Sea. Scotland: {{uk.areas.Scotland.North Sea.share|pct}} North Sea, {{uk.areas.Scotland.Inner Seas (west Scotland).share|pct}} Inner Seas. Northern Ireland: {{uk.areas.Northern Ireland.Inner Seas (west Scotland).share|pct}} Inner Seas (the North Channel). Ireland: {{uk.areas.Ireland.Atlantic Ocean.share|pct}} Atlantic.
- The North Sea divide is about {{uk.gb_north_sea_divide_km|kms}} km long on the grid, rising to {{uk.north_sea_divide_points.highest.elev_m|int}} m by Ben Alder; only {{uk.ns_divide_share_below_100m|pct}} of it lies below 100 m. {{uk.places.towns_on_watershed|int}} of {{uk.places.n_cities_towns|int}} OS towns and cities sit on a watershed between seas (Dudley, Sedgley, Rowley Regis, Blackheath, Bedworth, Market Drayton, Cumbernauld).
- {{uk.gb_triple_points|len}} triple points on Great Britain where three seas meet, including Clyde Law (Clyde, Tweed and Annan) and Swallow Hill, Staffordshire, at {{uk.gb_triple_points.2.elev_m|int}} m (Severn, Weaver and Trent).
- Longest journeys: {{uk.longest_gb.0.km|int}} km from near Dylife down the Severn; {{uk.longest_gb.1.km|int}} km from near Birdlip down the Churn and Thames. A cell {{uk.thames_head_contrast.km_west|f1}} km west of that Thames start reaches the Bristol Channel after {{uk.thames_head_contrast.path_km|int}} km. Half of Great Britain is within {{uk.gb_dist_median_km|int}} km of the sea along its path.
- World (outside Antarctica): Atlantic {{world.ocean_share.Atlantic.share|pct1}}, Arctic {{world.ocean_share.Arctic.share|pct1}}, Pacific {{world.ocean_share.Pacific.share|pct1}}, Indian {{world.ocean_share.Indian.share|pct1}}, no outlet {{derived.world_inland_share|pct1}} (largest: the Caspian, {{world.inland_top.0.km2|int}} km²). Longest journey: {{derived.nile_km|int}} km, Burundi to the Mediterranean by the Nile. One ocean triple point on the grid, in Montana (Triple Divide Peak).
- Checks: {{derived.net_agree|pct1}} of OS watercourse length that the network connects to the sea lies in cells sent to the same sea; agreement with HydroBASINS level 12 is {{derived.hb_gb|pct1}} (Great Britain) and {{derived.hb_ie|pct1}} (Ireland).

Every number is in `data/results.json`, which the page, paper, blog and collage are built from.

## Files

| Path | What it is |
|---|---|
| `index.html` | The interactive page (built by `code/09_build_site.py`). |
| `header.png` | Social card (1200 by 630). |
| `data/page/uk_a.png`, `data/page/uk_b.png` | Britain and Ireland at web-mercator zoom 8: sea code, hill shading, river class, path length and river-name chain for each cell (see `code/07_page_data.py`). |
| `data/page/world_idx.png`, `data/page/world_sea.png` | World at 0.1°: HydroBASINS level 7 sub-basin and sea for each cell. |
| `data/page/page.json`, `data/page/places.json` | Sea names, name chains, the sub-basin table and the search lists. |
| `data/uk_seas_by_area.csv` | Land area and share draining to each IHO sea, by nation, Great Britain, the UK and the island of Ireland. |
| `data/uk_places.csv` | Every OS Open Names city, town and village with its sea, path length, rivers and whether it sits on a watershed. |
| `data/uk_river_systems.csv` | River systems in Great Britain by the last named watercourse before the sea, with area and mouth. |
| `data/uk_triple_points.csv` | Triple points with nearest hill and place and the first rivers on each side. |
| `data/world_seas.csv`, `data/world_inland_basins.csv`, `data/world_triple_points.csv`, `data/world_countries.csv`, `data/world_cities.csv` | World land by IHO sea, closed basins, ocean triple points, countries by sea and ocean, and GeoNames cities (15,000 people or more) with their sea, distance and rivers. |
| `data/results.json` | Every number used anywhere. |
| `code/` | The analysis, in order (below). |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |
| `release/` | Paper PDF and source, blog post and figures, Zenodo files. |

## Method in brief

- **Britain and Ireland.** Web-mercator zoom 9 grid (about {{uk.meta.cell_m_median|int}} m) from AWS Terrain Tiles. OS Open Rivers watercourses (not canals) burned in by 20 m plus 15 m per tenfold increase in upstream network length. Priority flood from the sea (Barnes et al. 2014): each land cell takes the IHO sea of the cell it was reached from. Path length sums the steps; river names are watercourses followed for at least about 1 km (2 km for brooks and drains). Ireland and the Isle of Man: terrain only.
- **World.** HydroBASINS v1c level 7 rasterised at 0.05°, followed downstream to the next sink. Endorheic sinks and the Caspian shore are inland; otherwise the sea nearest the sink's pour point (Flanders Marine Institute IHO Sea Areas v3). Lumped coastal sub-basins and detached islands: nearest sea cell by cell. Distance: HydroBASINS DIST_SINK plus the straight line to the sub-basin's outlet.
- **Oceans** are a grouping of IHO seas (see `code/common.py`): Mediterranean, Black, Baltic, Caribbean and Gulf of Mexico with the Atlantic; Greenland Sea, Davis Strait, Baffin Bay, Hudson Bay and the seas north of Russia and Alaska with the Arctic; Indonesian seas with the Pacific except the Timor, Arafura and Savu seas.
- **Limits.** Surface flow only: no groundwater, pumping, canals or transfers. Flat land is uncertain, especially in Ireland. World distances are approximate and many small rivers have no name. Shares are of the grid's land.

## How to rerun

Raw inputs (not in this repository) are the browser bundles described in `code/common.py` (HydroBASINS level 7 and 12 rasterised, pour points, IHO Sea Areas), OS Open Rivers (GeoPackage), OS Open Names, AWS Terrain Tiles zoom 10 for Britain and Ireland, Natural Earth and GeoNames cities15000. Then:

```
python3 code/01_world.py; python3 code/02_rivers.py; python3 code/03_britain.py; python3 code/04_validate.py
python3 code/05_uk_analyse.py; python3 code/06_world_analyse.py; python3 code/07_page_data.py; python3 code/08_results.py
python3 code/09_build_site.py; python3 code/10_figures.py; python3 code/11_paper.py; python3 code/12_release.py
```

Python 3 with numpy, scipy, numba, shapely, pyproj, pandas, matplotlib and Pillow; xelatex for the paper.

## Sources and licences

- OS Open Rivers and OS Open Names: contain OS data © Crown copyright and database right 2026 (Open Government Licence v3.0).
- AWS Terrain Tiles (Mapzen/Tilezen): https://github.com/tilezen/joerd
- HydroBASINS v1c and HydroBASINS Pour Points (Lehner and Grill 2013), https://www.hydrosheds.org. This product (Where Rain Goes) incorporates data from the HydroSHEDS version 1 database which is © World Wildlife Fund, Inc. (2006-2022) and has been used herein under license. WWF has not evaluated the data as altered and incorporated within Where Rain Goes, and therefore gives no warranty regarding its accuracy, completeness, currency or suitability for any particular purpose. Portions of the HydroSHEDS v1 database incorporate data which are the intellectual property rights of © USGS (2006-2008), NASA (2000-2005), ESRI (1992-1998), CIAT (2004-2006), UNEP-WCMC (1993), WWF (2004), Commonwealth of Australia (2007), and Her Royal Majesty and the British Crown and are used under license. The HydroSHEDS v1 database and more information are available at https://www.hydrosheds.org.
- Flanders Marine Institute (2018) IHO Sea Areas, version 3, https://www.marineregions.org (CC BY 4.0).
- Natural Earth (public domain). GeoNames (CC BY 4.0). Postcode lookups on the page: postcodes.io. Live base maps on the page: Esri.

Code: MIT. Text and figures: CC BY 4.0. Data: see `LICENSE` (Open Government Licence for the OS-derived files; HydroSHEDS licence terms for the HydroBASINS-derived files).

## Citation

Hotham, T. (2026) Where rain goes: the sea every place in Britain, Ireland and the world drains to. Zenodo. https://doi.org/10.5281/zenodo.23757700

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
