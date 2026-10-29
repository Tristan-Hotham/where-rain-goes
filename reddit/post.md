# Reddit post

## Title

[OC] Which sea does your rain end up in? Every place in Britain and Ireland coloured by the sea its rivers drain to: 50% of Great Britain drains to the North Sea, and Wales sends none of its rain there

## Body

I followed the rain downhill from every 180 m square of Britain and Ireland, using the Ordnance Survey's open river map and a terrain model, and coloured each square by the sea it finally reaches (using the IHO's official sea areas).

- Half of Great Britain (49.8%) drains to the North Sea. Wales sends it nothing: 52% goes to the Bristol Channel, 43% to the Irish Sea.
- At Clyde Law in the Southern Uplands the Clyde, Tweed and Annan start together and head for three different seas.
- Britain's longest journey is 326 km, down the Severn from near Plynlimon. Worldwide, 24% of the land never drains to the sea at all.

Caveat: it is a surface-flow model, so groundwater, pumping and canals are ignored, and Ireland has no river names.

Click anywhere to follow your own raindrop: https://maps.tristanhotham.com/where-rain-goes/

## Source comment

Source: OS Open Rivers and OS Open Names (contain OS data © Crown copyright and database right 2026, Open Government Licence v3.0); AWS Terrain Tiles (Mapzen/Tilezen) for elevation; IHO Sea Areas v3, Flanders Marine Institute / marineregions.org (CC BY 4.0); world map from HydroBASINS v1c (Lehner and Grill 2013; incorporates data from the HydroSHEDS v1 database © WWF, used under licence); Natural Earth (public domain).

Tools: Python (numpy, scipy, numba, shapely, pyproj, pandas, matplotlib) for a priority-flood drainage model; Leaflet for the interactive map.

Interactive map: https://maps.tristanhotham.com/where-rain-goes/
Blog post: https://blog.tristanhotham.com/2026/10/29/where-rain-goes/
Paper: https://doi.org/10.5281/zenodo.23757700
