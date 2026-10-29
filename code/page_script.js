const R = /*RESULTS*/;
const SPINE = /*SPINE*/;
const NS = "http://www.w3.org/2000/svg";
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const el = (t, a = {}, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
const fmt = n => n == null || isNaN(n) ? "n/a" : Math.round(n).toLocaleString("en-GB");
const pct = (v, d = 0) => (v * 100).toFixed(d) + "%";
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const tip = document.getElementById("tip");
function showTip(h, x, y) { tip.innerHTML = h; tip.style.display = "block"; const w = tip.offsetWidth; x = Math.max(w / 2 + 8, Math.min(innerWidth - w / 2 - 8, x)); tip.style.left = x + scrollX + "px"; tip.style.top = y + scrollY + "px"; }
function hideTip() { tip.style.display = "none"; }
function hover(node, h) { node.style.cursor = "pointer"; node.setAttribute("tabindex", "0"); const s = () => { const r = node.getBoundingClientRect(); showTip(h, r.left + r.width / 2, r.top); }; node.addEventListener("pointerenter", s); node.addEventListener("pointerleave", hideTip); node.addEventListener("focus", s); node.addEventListener("blur", hideTip); }
const redraws = [];
function resp(box, render) { let last = 0; const go = (force) => { const w = Math.max(280, Math.round(box.clientWidth)); if (!force && Math.abs(w - last) < 4) return; last = w; box.innerHTML = ""; render(w, w < 560); }; new ResizeObserver(() => go()).observe(box); go(); redraws.push(() => go(true)); }
const lbl = (svg, x, y, s, cls = "lab", anchor = "start") => { const t = el("text", { x, y, class: cls, "text-anchor": anchor }, svg); t.textContent = s; return t; };
const isDark = () => { const r = document.documentElement; return r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches; };
document.getElementById("theme").onclick = () => { const r = document.documentElement; r.dataset.theme = isDark() ? "light" : "dark"; redraws.forEach(f => f()); };
const hex = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const hav = (la1, lo1, la2, lo2) => { const r = Math.PI / 180, a = Math.sin((la2 - la1) * r / 2) ** 2 + Math.cos(la1 * r) * Math.cos(la2 * r) * Math.sin((lo2 - lo1) * r / 2) ** 2; return 2 * 6371 * Math.asin(Math.sqrt(a)); };

/* ===== colours ===== */
const SEA_HEX = {
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
  "Coral Sea": "#3CBE9A", "Japan Sea": "#48A687", "Gulf of Thailand": "#5FB78C", "Java Sea": "#3F9F7F", "Tasman Sea": "#62B39A"
};
const OCEAN_HEX = { Atlantic: "#2F67B1", Pacific: "#21A08A", Indian: "#E39A35", Arctic: "#AA9FE0", Southern: "#7F9BB0", Inland: "#6B5E55" };
const OCEANS = ["Atlantic", "Pacific", "Indian", "Arctic", "Southern"];
const FAM = { Atlantic: [215, 55], Pacific: [165, 50], Indian: [33, 70], Arctic: [252, 45], Southern: [205, 20] };
function hsl(h, s, l) { s /= 100; l /= 100; const k = n => (n + h / 30) % 12, a = s * Math.min(l, 1 - l), f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1))); return [Math.round(255 * f(0)), Math.round(255 * f(8)), Math.round(255 * f(4))]; }
let P = null, SEA_RGB = [], OCEAN_RGB = {}, INLAND_RGB = hex(OCEAN_HEX.Inland);
function buildColours() {
  SEA_RGB = P.seas.map((s, k) => { if (SEA_HEX[s]) return hex(SEA_HEX[s]); const [h, sat] = FAM[P.ocean_of[k]]; return hsl(h + ((k * 37) % 30) - 15, sat, 42 + ((k * 53) % 34)); });
  for (const o in OCEAN_HEX) OCEAN_RGB[o] = hex(OCEAN_HEX[o]);
}
const DBRK = [10, 30, 100, 300, 1000, 3000];
const DCOL = ["#E7F0F6", "#BCD6EA", "#86B5DA", "#5290C6", "#2A6AAC", "#164987", "#0B2A55"].map(hex);
const dcls = d => { let i = 0; while (i < DBRK.length && d >= DBRK[i]) i++; return i; };

/* ===== state and data ===== */
const S = { view: "uk", mode: "sea", place: null };
const LY = { base: "plain", hills: true, hillK: 55, rivers: true, riverLvl: 2, sheds: true, names: true, nameLvl: 1, colour: 90 };
const LYDEF = { ...LY };
try { Object.assign(LY, JSON.parse(localStorage.getItem("wrg_layers") || "{}")); } catch (e) {}
const saveLY = () => { try { localStorage.setItem("wrg_layers", JSON.stringify(LY)); } catch (e) {} };
let UK = null, WD = null, PLACES = null;
async function pixels(url) {
  const bl = await (await fetch(url)).blob();
  const bm = await createImageBitmap(bl, { colorSpaceConversion: "none", premultiplyAlpha: "none" });
  const c = document.createElement("canvas"); c.width = bm.width; c.height = bm.height;
  const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(bm, 0, 0);
  return { w: bm.width, h: bm.height, d: x.getImageData(0, 0, bm.width, bm.height).data };
}
async function loadAll() {
  const [pj, a, b, wi, ws, pl] = await Promise.all([fetch("data/page/page.json").then(r => r.json()), pixels("data/page/uk_a.png"), pixels("data/page/uk_b.png"),
    pixels("data/page/world_idx.png"), pixels("data/page/world_sea.png"), fetch("data/page/places.json").then(r => r.json())]);
  P = pj; PLACES = pl; buildColours();
  const n = a.w * a.h, region = new Uint8Array(n), lab = new Uint8Array(n), hill = new Uint8Array(n), riv = new Uint8Array(n), chain = new Int32Array(n), dist = new Uint16Array(n);
  for (let i = 0; i < n; i++) { const q = 4 * i; lab[i] = a.d[q] & 15; region[i] = (a.d[q] >> 5) & 3; hill[i] = a.d[q + 1]; riv[i] = a.d[q + 2]; chain[i] = (b.d[q] << 8 | b.d[q + 1]) - 1; dist[i] = b.d[q + 2] + ((a.d[q] >> 4) & 1) * 256; }
  UK = { w: a.w, h: a.h, region, lab, hill, riv, chain, dist, bounds: P.uk.bounds };
  const m = wi.w * wi.h, idx = new Int32Array(m), sea = new Uint8Array(m);
  for (let i = 0; i < m; i++) { const q = 4 * i; idx[i] = (wi.d[q] << 16 | wi.d[q + 1] << 8 | wi.d[q + 2]) - 1; sea[i] = ws.d[q]; }
  WD = { w: wi.w, h: wi.h, idx, sea, B: P.world.basins };
}

/* ===== projection helpers ===== */
const mercY = lat => Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360));
function ukCell(lat, lon) {
  const [[s, w], [n, e]] = UK.bounds; if (lat <= s || lat >= n || lon <= w || lon >= e) return -1;
  const x = Math.floor((lon - w) / (e - w) * UK.w), y = Math.floor((mercY(n) - mercY(lat)) / (mercY(n) - mercY(s)) * UK.h);
  return y * UK.w + x;
}
function worldCell(lat, lon) { const x = Math.floor((lon + 180) / 0.1), y = Math.floor((90 - lat) / 0.1); if (x < 0 || y < 0 || x >= WD.w || y >= WD.h) return -1; return y * WD.w + x; }
const shortSea = k => P.seas_short[k];

/* ===== rendering ===== */
const ukCv = document.createElement("canvas"), wSrc = document.createElement("canvas"), wMerc = document.createElement("canvas");
const W_TOP = 84, W_BOT = -60;
let wRows = null;
function inkRGB() { return isDark() ? [235, 240, 244] : [20, 32, 43]; }
function colourUK(i) {
  const l = UK.lab[i]; if (!l) return null;
  const k = P.uk.sea[l - 1];
  if (S.mode === "sea") return SEA_RGB[k];
  if (S.mode === "ocean") return OCEAN_RGB[P.ocean_of[k]];
  return DCOL[dcls(UK.dist[i])];
}
function keyUK(i) { const l = UK.lab[i]; return S.mode === "ocean" ? (l ? P.ocean_of[P.uk.sea[l - 1]] : "") : l; }
function renderUK() {
  if (!UK) return;
  const W = UK.w, H = UK.h; ukCv.width = W; ukCv.height = H;
  const ctx = ukCv.getContext("2d"), img = ctx.createImageData(W, H), d = img.data, ink = inkRGB(), dark = isDark();
  const hk = LY.hills ? Math.min(1, .15 + LY.hillK / 100) : 0, rv = LY.rivers ? 5 - LY.riverLvl : 9;
  const rivInk = dark ? [170, 210, 245] : [12, 40, 80];
  for (let i = 0; i < W * H; i++) {
    const c = colourUK(i); if (!c) continue;
    let r = c[0], g = c[1], b = c[2];
    if (hk) { const v = UK.hill[i] / 255, f = dark ? 1 + hk * (v - .78) * .9 : 1 - hk * (1 - v) * .9; r *= f; g *= f; b *= f; }
    if (UK.riv[i] >= rv) { const t = .35 + .13 * UK.riv[i]; r = r * (1 - t) + rivInk[0] * t; g = g * (1 - t) + rivInk[1] * t; b = b * (1 - t) + rivInk[2] * t; }
    if (LY.sheds && S.mode !== "dist") { const k = keyUK(i), x = i % W; if ((x < W - 1 && UK.lab[i + 1] && keyUK(i + 1) !== k) || (i + W < W * H && UK.lab[i + W] && keyUK(i + W) !== k)) { r = ink[0]; g = ink[1]; b = ink[2]; } }
    const q = 4 * i; d[q] = r; d[q + 1] = g; d[q + 2] = b; d[q + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
}
let WDIST = null;
function worldDist() {
  if (WDIST) return WDIST;
  const B = WD.B, n = WD.w * WD.h; WDIST = new Float32Array(n).fill(-1);
  for (let i = 0; i < n; i++) {
    const b = WD.idx[i]; if (b < 0) continue; const s = WD.sea[i];
    if (s !== 255 && (s & 128)) { WDIST[i] = 20; continue; }
    const lat = 90 - (Math.floor(i / WD.w) + .5) * .1, lon = -180 + (i % WD.w + .5) * .1;
    WDIST[i] = B.d[b] + (B.x[b] == null ? 0 : hav(lat, lon, B.y[b], B.x[b]));
  }
  return WDIST;
}
function wKey(i) { const s = WD.sea[i]; if (s === 255) return S.mode === "ocean" ? "Inland" : 255; const k = (s & 127) - 1; return S.mode === "ocean" ? P.ocean_of[k] : k; }
let UKMASK = null;   // world cells inside the Britain and Ireland grid are left to that finer grid
function ukMask() {
  if (UKMASK) return UKMASK; UKMASK = new Uint8Array(WD.w * WD.h); const [[s, w], [n, e]] = UK.bounds;
  for (let y = 0; y < WD.h; y++) { const lat = 90 - (y + .5) * .1; if (lat <= s || lat >= n) continue;
    for (let x = 0; x < WD.w; x++) { const lon = -180 + (x + .5) * .1; if (lon <= w || lon >= e) continue;
      const france = (lat < 51.1 && lon > 1.0) || (lat < 49.95 && lon > -5.0); if (!france) UKMASK[y * WD.w + x] = 1; } }
  return UKMASK;
}
function colourW(i) {
  if (WD.idx[i] < 0 || ukMask()[i]) return null; const s = WD.sea[i];
  if (S.mode === "dist") { const d = worldDist()[i]; return d < 0 ? null : DCOL[dcls(d)]; }
  if (s === 255) return INLAND_RGB; if (!s) return null;
  const k = (s & 127) - 1; return S.mode === "sea" ? SEA_RGB[k] : OCEAN_RGB[P.ocean_of[k]];
}
function renderWorld() {
  if (!WD) return;
  const W = WD.w, H = WD.h; wSrc.width = W; wSrc.height = H;
  const ctx = wSrc.getContext("2d"), img = ctx.createImageData(W, H), d = img.data, ink = inkRGB();
  for (let i = 0; i < W * H; i++) {
    const c = colourW(i); if (!c) continue; let r = c[0], g = c[1], b = c[2];
    if (LY.sheds && S.mode !== "dist") { const k = wKey(i), x = i % W; if ((x < W - 1 && WD.idx[i + 1] >= 0 && wKey(i + 1) !== k) || (i + W < W * H && WD.idx[i + W] >= 0 && wKey(i + W) !== k)) { r = ink[0]; g = ink[1]; b = ink[2]; } }
    const q = 4 * i; d[q] = r; d[q + 1] = g; d[q + 2] = b; d[q + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  const MW = 3600; if (!wRows) { const y0 = mercY(W_TOP), y1 = mercY(W_BOT), MH = Math.round(MW / (2 * Math.PI) * (y0 - y1)); wRows = new Int32Array(MH); for (let y = 0; y < MH; y++) { const my = y0 - (y + .5) / MH * (y0 - y1), lat = (2 * Math.atan(Math.exp(my)) - Math.PI / 2) * 180 / Math.PI; wRows[y] = Math.floor((90 - lat) / .1); } }
  wMerc.width = MW; wMerc.height = wRows.length; const mc = wMerc.getContext("2d"); mc.imageSmoothingEnabled = false; mc.clearRect(0, 0, MW, wMerc.height);
  let y = 0; while (y < wRows.length) { let z = y; while (z + 1 < wRows.length && wRows[z + 1] === wRows[y]) z++; mc.drawImage(wSrc, 0, wRows[y], W, 1, 0, y, MW, z - y + 1); y = z + 1; }
}
function renderAll() { renderUK(); renderWorld(); legend(); }

/* ===== the map ===== */
let map, base = null, hillTiles = null, ukOverlay = null, wOverlay = null, nameL = null, pin = null;
const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/";
const ESRI_ATT = "Tiles &copy; Esri";
const CanvasOverlay = window.L && L.ImageOverlay.extend({
  _initImage() { const c = this._image = this._url; L.DomUtil.addClass(c, "leaflet-image-layer"); if (this.options.px) L.DomUtil.addClass(c, "px"); if (this._zoomAnimated) L.DomUtil.addClass(c, "leaflet-zoom-animated"); c.onselectstart = L.Util.falseFn; c.onmousemove = L.Util.falseFn; }
});
function setTiles() {
  [base, hillTiles].forEach(l => { if (l) map.removeLayer(l); }); base = null;
  const t = isDark() ? "Dark" : "Light";
  if (LY.base !== "plain") {
    const url = LY.base === "satellite" ? ESRI + "World_Imagery/MapServer/tile/{z}/{y}/{x}" : `${ESRI}Canvas/World_${t}_Gray_Base/MapServer/tile/{z}/{y}/{x}`;
    base = L.tileLayer(url, { maxZoom: 16, attribution: ESRI_ATT }).addTo(map);
  }
  hillTiles = L.tileLayer(ESRI + "Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}", { maxZoom: 16, pane: "hills", attribution: ESRI_ATT });
  applyLayers();
}
function applyLayers() {
  if (!map) return;
  const op = LY.colour / 100; if (ukOverlay) ukOverlay.setOpacity(op); if (wOverlay) wOverlay.setOpacity(op);
  if (LY.hills && S.view === "world") { hillTiles.addTo(map); hillTiles.setOpacity(Math.min(1, .2 + LY.hillK / 120)); } else if (hillTiles) map.removeLayer(hillTiles);
  if (LY.names) nameL.addTo(map); else map.removeLayer(nameL);
  placeNames();
}
function initLayers() {
  const Ctl = L.Control.extend({ options: { position: "topright" }, onAdd() {
    const d = L.DomUtil.create("div"); L.DomEvent.disableClickPropagation(d); L.DomEvent.disableScrollPropagation(d);
    d.innerHTML = `<button class="lyrBtn" aria-expanded="false" aria-controls="lyrPanel">Map layers</button>
<div class="lyrPanel" id="lyrPanel" hidden>
 <div class="row"><label for="lyBase">Base map</label><div class="sub"><select id="lyBase" aria-label="Base map"><option value="plain">Plain</option><option value="grey">Grey map</option><option value="satellite">Satellite</option></select></div></div>
 <div class="row"><label><input type="checkbox" id="lyHills"> Hills</label><div class="sub"><span>strength</span><input type="range" id="lyHillK" min="10" max="100" step="5" aria-label="Hill shading strength"></div></div>
 <div class="row"><label><input type="checkbox" id="lyRivers"> Rivers (Britain and Ireland)</label><div class="sub"><span>how many</span><select id="lyRiverLvl" aria-label="How many rivers"><option value="1">Main rivers</option><option value="2">Rivers</option><option value="3">Streams too</option><option value="4">Every stream</option></select></div></div>
 <div class="row"><label><input type="checkbox" id="lySheds"> Watershed lines</label></div>
 <div class="row"><label><input type="checkbox" id="lyNames"> Place names</label><div class="sub"><span>how many</span><select id="lyNameLvl" aria-label="How many place names"><option value="0">Cities only</option><option value="1">Cities and towns</option><option value="2">Down to villages</option></select></div></div>
 <div class="row"><label>Colour</label><div class="sub"><span>strength</span><input type="range" id="lyColour" min="25" max="100" step="5" aria-label="Colour strength"></div></div>
 <button class="reset" id="lyReset">Reset layers</button>
</div>`;
    return d; } });
  map.addControl(new Ctl());
  const q = id => document.getElementById(id), btn = map.getContainer().querySelector(".lyrBtn"), pan = q("lyrPanel");
  btn.onclick = () => { const o = pan.hidden; pan.hidden = !o; btn.setAttribute("aria-expanded", o); };
  const sync = () => { q("lyBase").value = LY.base; q("lyHills").checked = LY.hills; q("lyHillK").value = LY.hillK; q("lyRivers").checked = LY.rivers; q("lyRiverLvl").value = LY.riverLvl; q("lySheds").checked = LY.sheds; q("lyNames").checked = LY.names; q("lyNameLvl").value = LY.nameLvl; q("lyColour").value = LY.colour; };
  let rq = 0; const redraw = () => { cancelAnimationFrame(rq); rq = requestAnimationFrame(() => { renderAll(); refresh(); }); };
  const on = (id, ev, f, how) => q(id).addEventListener(ev, e => { f(e.target); saveLY(); how === "tiles" ? setTiles() : how === "redraw" ? redraw() : applyLayers(); });
  on("lyBase", "change", t => LY.base = t.value, "tiles");
  on("lyHills", "change", t => LY.hills = t.checked, "redraw"); on("lyHillK", "input", t => { LY.hillK = +t.value; LY.hills = q("lyHills").checked = true; }, "redraw");
  on("lyRivers", "change", t => LY.rivers = t.checked, "redraw"); on("lyRiverLvl", "change", t => { LY.riverLvl = +t.value; LY.rivers = q("lyRivers").checked = true; }, "redraw");
  on("lySheds", "change", t => LY.sheds = t.checked, "redraw");
  on("lyNames", "change", t => LY.names = t.checked); on("lyNameLvl", "change", t => { LY.nameLvl = +t.value; LY.names = q("lyNames").checked = true; });
  on("lyColour", "input", t => LY.colour = +t.value);
  q("lyReset").onclick = () => { Object.assign(LY, LYDEF); saveLY(); sync(); setTiles(); redraw(); };
  sync();
}
function refresh() {
  // canvases were redrawn in place; ask Leaflet to repaint them
  [ukOverlay, wOverlay].forEach(o => { if (o && o._image) { o._image.style.opacity = o._image.style.opacity; } });
}
function placeNames() {
  if (!map || !nameL) return;
  nameL.clearLayers(); if (!LY.names || !PLACES) return;
  const z = map.getZoom(), bb = map.getBounds().pad(.05), lvl = LY.nameLvl, out = [], boxes = [];
  const cand = [];
  const ukv = S.view === "uk" || z >= 6;
  const minPop = [[2, 8e6], [3, 4e6], [4, 1.5e6], [5, 5e5], [6, 2e5], [7, 1e5], [99, 5e4]].find(([zz]) => z < zz + (lvl === 2 ? 1 : lvl === 0 ? -1 : 0))[1];
  if (z < 6.5 || S.view === "world") for (const c of PLACES.world) if (c[4] >= minPop && !(c[1] === "GB" || c[1] === "IE") ) cand.push({ nm: c[0], lat: c[2], lon: c[3], r: Math.log10(c[4]) });
  if (ukv) { const minT = lvl === 0 ? 3 : lvl === 1 ? (z >= 8 ? 2 : 3) : (z >= 10 ? 1 : z >= 8 ? 2 : 3); for (const c of PLACES.uk) if (c[4] >= minT) cand.push({ nm: c[0], lat: c[2], lon: c[3], r: c[4] + 5 }); }
  const vis = cand.filter(c => bb.contains([c.lat, c.lon])).sort((a, b) => b.r - a.r);
  for (const c of vis) {
    const pt = map.latLngToContainerPoint([c.lat, c.lon]); const bx = [pt.x - 4, pt.y - 8, pt.x + 10 + c.nm.length * 6.6, pt.y + 7];
    if (boxes.some(o => bx[0] < o[2] && bx[2] > o[0] && bx[1] < o[3] && bx[3] > o[1])) continue;
    boxes.push(bx); out.push(c); if (out.length >= 220) break;
  }
  for (const c of out) L.marker([c.lat, c.lon], { interactive: false, keyboard: false, icon: L.divIcon({ className: "city" + (c.r < 7 && c.r > 5 ? " s" : ""), html: `<i></i>${esc(c.nm)}`, iconSize: null, iconAnchor: [3, 6] }) }).addTo(nameL);
}
const UKB = () => L.latLngBounds(UK.bounds);
function setView(v, fly = true) {
  S.view = v; document.querySelectorAll("[data-view]").forEach(b => b.setAttribute("aria-pressed", b.dataset.view === v));
  if (fly) { if (v === "uk") map.fitBounds([[49.9, -10.6], [60.9, 1.8]]); else map.setView([25, 10], innerWidth < 600 ? 1 : 2); }
  applyLayers();
}
async function initMap() {
  if (!window.L) { document.getElementById("lmap").innerHTML = '<p style="padding:16px">The map library did not load.</p>'; return; }
  try { await loadAll(); } catch (e) { document.getElementById("lmap").innerHTML = '<p style="padding:16px">The map data did not load.</p>'; console.error(e); return; }
  document.getElementById("lmap").innerHTML = "";
  map = L.map("lmap", { zoomSnap: .5, minZoom: 1, maxZoom: 13, scrollWheelZoom: false, worldCopyJump: false, maxBounds: [[-75, -220], [88, 220]] });
  map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
  map.createPane("hills"); map.getPane("hills").style.zIndex = 420; map.getPane("hills").style.pointerEvents = "none";
  map.fitBounds([[49.9, -10.6], [60.9, 1.8]]);
  renderUK(); renderWorld();
  wOverlay = new CanvasOverlay(wMerc, [[W_BOT, -180], [W_TOP, 180]], { opacity: LY.colour / 100, attribution: "HydroSHEDS | IHO Sea Areas | GeoNames" }).addTo(map);
  ukOverlay = new CanvasOverlay(ukCv, UK.bounds, { px: true, opacity: LY.colour / 100, attribution: "OS data © Crown copyright 2026" }).addTo(map);
  nameL = L.layerGroup();
  initLayers(); setTiles();
  map.on("zoomend moveend", placeNames);
  map.on("click", ev => { map.scrollWheelZoom.enable(); answer(ev.latlng.lat, ev.latlng.lng, null); });
  legend();
  heroMark();
}

/* ===== legend ===== */
function legend() {
  const box = document.getElementById("legend"); if (!P) return; let h = "";
  const sw = c => `<i class="sw" style="background:rgb(${c.join(",")})"></i>`;
  if (S.mode === "dist") { const labs = ["under 10 km", "10 to 30", "30 to 100", "100 to 300", "300 to 1,000", "1,000 to 3,000", "over 3,000 km"]; h = labs.map((l, k) => `<span>${sw(DCOL[k])}${l}</span>`).join(""); }
  else if (S.mode === "ocean") h = Object.keys(OCEAN_HEX).filter(o => o !== "Southern").map(o => `<span>${sw(OCEAN_RGB[o])}${o === "Inland" ? "Inland (no outlet)" : o}</span>`).join("");
  else {
    const list = S.view === "uk" ? ["North Sea", "English Channel", "Bristol Channel", "Celtic Sea", "Irish Sea and St. George's Channel", "Inner Seas off the West Coast of Scotland", "North Atlantic Ocean"]
      : ["North Atlantic Ocean", "South Atlantic Ocean", "Gulf of Mexico", "Mediterranean Sea - Eastern Basin", "Black Sea", "Kara Sea", "Laptev Sea", "Hudson Bay", "Bay of Bengal", "Arabian Sea", "Indian Ocean", "South China Sea", "Eastern China Sea", "Sea of Okhotsk", "North Pacific Ocean"];
    h = list.map(s => { const k = P.seas.indexOf(s); return `<span>${sw(SEA_RGB[k])}${esc(P.seas_short[k])}</span>`; }).join("") + (S.view === "world" ? `<span>${sw(INLAND_RGB)}Inland (no outlet)</span><span style="color:var(--muted)">and 85 more seas: tap the map</span>` : "");
  }
  box.innerHTML = h;
}

/* ===== the answer card ===== */
function routeHTML(names, seaName) {
  return `<div class="route">${names.map(n => `<b>${esc(n)}</b><i>→</i>`).join("")}<b class="sea">${esc(seaName)}</b></div>`;
}
function ukAnswer(i) {
  const l = UK.lab[i]; if (!l) return null;
  const names = []; let c = UK.chain[i]; let g = 0;
  while (c >= 0 && g < 60) { const e = P.uk.chains[c]; if (!e) break; names.push(P.uk.names[e[0]]); c = e[1]; g++; }
  const k = P.uk.sea[l - 1], sea = P.seas[k], d = UK.dist[i];
  // a different sea in the 3 x 3 block around = on a watershed
  const W = UK.w, other = new Set(); for (const o of [-W - 1, -W, -W + 1, -1, 1, W - 1, W, W + 1]) { const v = UK.lab[i + o]; if (v && v !== l) other.add(P.seas_short[P.uk.sea[v - 1]]); }
  return { sea, short: P.seas_short[k], ocean: P.ocean_of[k], km: d, names, other: [...other], gb: UK.region[i] === 1 };
}
function wAnswer(lat, lon) {
  const i = worldCell(lat, lon); if (i < 0) return null; const b = WD.idx[i]; if (b < 0) return null;
  const B = WD.B, s = WD.sea[i];
  const inland = s === 255, percell = !inland && (s & 128), k = inland ? -1 : (s & 127) - 1;
  const names = []; let j = b, cur = 99, g = 0; const sink = B.m[b];
  if (!percell) while (j >= 0 && g < 4000) { const n = B.n[j]; if (n >= 0) { const nm = P.world.names[n], rk = P.world.rank[n]; if (!names.includes(nm) && (!names.length || rk <= cur)) { names.push(nm); cur = rk; } } if (j === sink) break; j = B.nd[j]; g++; }
  const km = percell ? null : B.d[b] + (B.x[b] == null ? 0 : hav(lat, lon, B.y[b], B.x[b]));
  const inlandName = inland ? (P.world.inland[sink] || "a closed basin with no outlet") : null;
  return { sea: inland ? null : P.seas[k], short: inland ? null : P.seas_short[k], ocean: inland ? "Inland" : P.ocean_of[k], km, names, inland, inlandName, percell };
}
const the = s => (/ Bay$/.test(s) && !/^Bay /.test(s)) || /^(Bass|Hudson|Davis|Malacca|Makassar|Singapore) Strait$/.test(s) ? s : "the " + s;
function nearestPlace(lat, lon) {
  let best = null, bd = 1e9; const c = ukCell(lat, lon), ukv = c >= 0 && UK.lab[c] && UK.region[c] === 1;
  const list = ukv ? PLACES.uk : PLACES.world;
  for (const p of list) { const d = (p[2] - lat) ** 2 + ((p[3] - lon) * Math.cos(lat * Math.PI / 180)) ** 2; if (d < bd) { bd = d; best = p; } }
  if (!best) return ""; const km = Math.sqrt(bd) * 111; return km < 2 ? best[0] : `${Math.round(km)} km from ${best[0]}`;
}
function answer(lat, lon, name, fly = false) {
  if (!UK) return;
  const box = document.getElementById("answer");
  const ui = ukCell(lat, lon); let A = ui >= 0 ? ukAnswer(ui) : null; if (!A) A = wAnswer(lat, lon);
  if (pin) map.removeLayer(pin);
  pin = L.marker([lat, lon], { icon: L.divIcon({ className: "", html: '<div class="pin"></div>', iconSize: [18, 18], iconAnchor: [9, 9] }), keyboard: false }).addTo(map);
  if (fly) { map.setView([lat, lon], Math.max(map.getZoom(), ui >= 0 ? 9 : 6)); document.getElementById("lmap").scrollIntoView({ behavior: "smooth", block: "center" }); }
  const where = name || nearestPlace(lat, lon);
  if (!A) { box.innerHTML = `<div class="pn">${esc(where || "Here")}: sea, or land outside the model (Antarctica is not included).</div>`; return; }
  let h = `<div class="pn">${esc(where)} · ${lat.toFixed(3)}, ${lon.toFixed(3)}</div>`;
  if (A.inland) {
    h += `<div class="big">Rain here never reaches the sea. It ends in <b>${esc(A.inlandName)}</b>${A.km != null ? `, about ${fmt(A.km)} km away` : ""}.</div>` + routeHTML(A.names, "no outlet");
  } else if (A.gb !== undefined) {
    const isGB = A.gb;
    h += `<div class="big">Rain here reaches ${the("")}<b>${esc(A.short)}</b> after about <b>${fmt(A.km)} km</b>.</div>`;
    h += A.names.length ? routeHTML(A.names, A.short) : `<div class="pn">${isGB ? "It runs straight down to the nearby coast." : "River names are only available for Great Britain; Ireland and the Isle of Man follow the terrain alone."}</div>`;
    if (A.other.length) h += `<div class="pn">This spot is right on a watershed: a few hundred metres away, rain goes to the ${esc(A.other.join(" or the "))} instead.</div>`;
    h += `<div class="pn">${esc(A.sea)} (IHO sea area), part of the ${esc(A.ocean)}. Distance: the modelled path over the land surface and along the rivers.</div>`;
  } else {
    h += `<div class="big">Rain here reaches ${the(A.short) === A.short ? "" : "the "}<b>${esc(A.short)}</b>${A.km != null ? ` after about <b>${fmt(A.km)} km</b>` : ""}.</div>`;
    h += A.percell ? `<div class="pn">It drains straight to the nearby coast (a coastal sub-basin of many small streams).</div>` : routeHTML(A.names, A.short);
    h += `<div class="pn">${esc(A.sea)} (IHO sea area), part of the ${esc(A.ocean)}.${A.percell ? "" : " Distance: HydroBASINS river distance from this sub-basin's outlet plus the straight line to it."}</div>`;
  }
  box.innerHTML = h;
}

/* ===== search ===== */
const qi = document.getElementById("q"), sug = document.getElementById("sug"); let sugItems = [], sugIdx = -1;
function showSug(items) { sugItems = items; sugIdx = -1; sug.innerHTML = items.map((p, k) => `<li role="option" data-k="${k}">${esc(p.name)} <span>${esc(p.sub)}</span></li>`).join(""); sug.style.display = items.length ? "block" : "none"; qi.setAttribute("aria-expanded", items.length > 0); }
const norm = s => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
qi.addEventListener("input", () => {
  const v = norm(qi.value.trim()); if (v.length < 2 || !PLACES) { showSug([]); return; }
  const out = [];
  for (const p of PLACES.uk) if (norm(p[0]).startsWith(v)) out.push({ name: p[0], sub: p[1], lat: p[2], lon: p[3], r: p[4] + 10 });
  for (const p of PLACES.world) if (norm(p[0]).startsWith(v)) out.push({ name: p[0], sub: p[1], lat: p[2], lon: p[3], r: Math.log10(p[4]) + 4 });
  out.sort((a, b) => b.r - a.r || a.name.length - b.name.length);
  showSug(out.slice(0, 12));
});
qi.addEventListener("keydown", e => {
  if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); if (!sugItems.length) return; sugIdx = (sugIdx + (e.key === "ArrowDown" ? 1 : -1) + sugItems.length) % sugItems.length; [...sug.children].forEach((li, k) => li.setAttribute("aria-selected", k === sugIdx)); }
  else if (e.key === "Enter") { e.preventDefault(); if (sugItems.length) pick(sugItems[Math.max(0, sugIdx)]); else postcode(qi.value); }
  else if (e.key === "Escape") showSug([]);
});
sug.addEventListener("click", e => { const li = e.target.closest("li"); if (li) pick(sugItems[+li.dataset.k]); });
function pick(p) { showSug([]); qi.value = p.name; if (ukCell(p.lat, p.lon) < 0 && S.view === "uk") setView("world", false); answer(p.lat, p.lon, `${p.name}, ${p.sub}`, true); }
async function postcode(pc) {
  const v = pc.replace(/\s+/g, "").toUpperCase(); if (!/^[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}$/.test(v)) return;
  try { const r = await (await fetch("https://api.postcodes.io/postcodes/" + encodeURIComponent(v))).json(); if (r.result) { answer(r.result.latitude, r.result.longitude, r.result.postcode, true); } }
  catch (e) { document.getElementById("answer").innerHTML = '<div class="pn">The postcode service did not answer. Try a place name instead.</div>'; }
}
document.querySelectorAll("[data-view]").forEach(b => b.onclick = () => { setView(b.dataset.view); legend(); });
document.querySelectorAll("[data-mode]").forEach(b => b.onclick = () => { S.mode = b.dataset.mode; document.querySelectorAll("[data-mode]").forEach(x => x.setAttribute("aria-pressed", x === b)); renderAll(); });
const flyTo = (lat, lon, z) => { if (!map) return; const uk = lat > 49.8 && lat < 61 && lon > -11 && lon < 2; if (!uk && S.view === "uk") setView("world", false); map.setView([lat, lon], z); answer(lat, lon, null); document.getElementById("lmap").scrollIntoView({ behavior: "smooth", block: "center" }); };

/* ===== charts ===== */
const NAT = ["England", "Scotland", "Wales", "Northern Ireland", "Isle of Man", "Ireland", "Great Britain"];
const SEA_ORDER = ["North Sea", "English Channel", "Celtic Sea", "Bristol Channel", "Irish Sea", "Inner Seas (west Scotland)", "Atlantic Ocean"];
const SHORT2FULL = { "Irish Sea": "Irish Sea and St. George's Channel", "Inner Seas (west Scotland)": "Inner Seas off the West Coast of Scotland", "Atlantic Ocean": "North Atlantic Ocean" };
const seaHex = s => SEA_HEX[SHORT2FULL[s] || s];
resp(document.getElementById("nations"), (w, nar) => {
  const L0 = nar ? 112 : 140, rowH = 30, H = NAT.length * rowH + 50, svg = el("svg", { viewBox: `0 0 ${w} ${H}` }, document.getElementById("nations"));
  NAT.forEach((n, r) => {
    const a = R.uk.areas[n]; if (!a) return; let x = L0; const y = r * rowH + 4;
    lbl(svg, L0 - 8, y + 16, n, "lab b", "end");
    for (const s of SEA_ORDER) { const v = a[s] ? a[s].share : 0; if (!v) continue; const ww = v * (w - L0 - 4);
      const rc = el("rect", { x, y, width: Math.max(0, ww - 1), height: rowH - 8, fill: seaHex(s) }, svg); hover(rc, `<b>${n}</b><br>${s}: ${pct(v, 1)} (${fmt(a[s].km2)} km²)`);
      if (ww > 34) lbl(svg, x + 4, y + 15, pct(v), "lab s w"); x += ww; }
  });
  let lx = 0, ly = NAT.length * rowH + 16; for (const s of SEA_ORDER) { const tw = s.length * 7 + 22; if (lx + tw > w) { lx = 0; ly += 16; } el("rect", { x: lx, y: ly - 9, width: 11, height: 11, fill: seaHex(s) }, svg); lbl(svg, lx + 15, ly, s, "lab s"); lx += tw; }
  svg.setAttribute("viewBox", `0 0 ${w} ${ly + 8}`);
});
resp(document.getElementById("spine"), (w, nar) => {
  const H = nar ? 230 : 280, m = { l: 44, r: 10, t: 10, b: 34 }, svg = el("svg", { viewBox: `0 0 ${w} ${H}` }, document.getElementById("spine"));
  const la0 = 50.5, la1 = 59, e1 = 1200, X = v => m.l + (v - la0) / (la1 - la0) * (w - m.l - m.r), Y = v => H - m.b - v / e1 * (H - m.t - m.b);
  for (const e of [0, 300, 600, 900, 1200]) { el("line", { x1: m.l, x2: w - m.r, y1: Y(e), y2: Y(e), stroke: css("--rule") }, svg); lbl(svg, m.l - 6, Y(e) + 4, e, "lab s m", "end"); }
  for (const t of [51, 52, 53, 54, 55, 56, 57, 58]) lbl(svg, X(t), H - m.b + 16, t + "° N", "lab s m", "middle");
  const g = el("g", { fill: css("--rain"), "fill-opacity": .55 }, svg);
  for (let k = 0; k < SPINE.lat.length; k++) el("circle", { cx: X(SPINE.lat[k]).toFixed(1), cy: Y(SPINE.e[k]).toFixed(1), r: 1.4 }, g);
  const hi = R.uk.north_sea_divide_points.highest; el("circle", { cx: X(hi.lat), cy: Y(hi.elev_m), r: 4, fill: "none", stroke: css("--fg"), "stroke-width": 1.5 }, svg);
  lbl(svg, X(hi.lat) - 8, Y(hi.elev_m) + 4, `${hi.hill}, ${fmt(hi.elev_m)} m`, "lab s", "end");
  lbl(svg, X(52.5), H - 4, "south (Kent and the Midlands)", "lab s m", "middle"); lbl(svg, X(57.6), H - 4, "north (Highlands)", "lab s m", "middle");
});
(function triples() {
  const t = document.getElementById("triples");
  t.innerHTML = `<thead><tr><th>Where</th><th>The three seas and their rivers</th><th class="num">Height</th></tr></thead><tbody>` +
    R.uk.gb_triple_points.map((p, k) => `<tr class="go" data-k="${k}"><td>${esc(p.nearest_hill)}<small>near ${esc(p.nearest_place)}, ${esc(p.county.split(" - ")[0])}</small></td><td>${p.rivers.split(" | ").map(x => esc(x)).join("<br>")}</td><td class="num">${fmt(p.elev_m)} m</td></tr>`).join("") + "</tbody>";
  t.querySelectorAll("tr.go").forEach(tr => tr.onclick = () => { const p = R.uk.gb_triple_points[+tr.dataset.k]; flyTo(p.lat, p.lon, 11); });
})();
(function longCards() {
  const box = document.getElementById("longcards");
  box.innerHTML = R.uk.longest_gb.slice(0, 6).map((x, k) => `<div class="card" data-k="${k}" style="border-left-color:${seaHex(x.sea)}"><b>${esc(x.sea)}</b><div class="big">${fmt(x.km)} <span>km</span></div>from near ${esc(x.near)}<br>${esc(x.route.split(" > ").slice(-2).join(", then the "))}</div>`).join("");
  box.querySelectorAll(".card").forEach(c => c.onclick = () => { const x = R.uk.longest_gb[+c.dataset.k]; flyTo(x.lat, x.lon, 10); });
})();
resp(document.getElementById("systems"), (w, nar) => {
  const rows = R.uk.river_systems_top.slice(0, 12), L0 = nar ? 150 : 210, rh = 24, H = rows.length * rh + 6, mx = rows[0].km2;
  const svg = el("svg", { viewBox: `0 0 ${w} ${H}` }, document.getElementById("systems"));
  rows.forEach((r, k) => { const y = k * rh, ww = r.km2 / mx * (w - L0 - 70);
    lbl(svg, L0 - 8, y + 15, r.name.replace(/ \(.*\)/, ""), "lab", "end");
    const rc = el("rect", { x: L0, y: y + 3, width: ww, height: rh - 8, fill: seaHex(r.sea) }, svg); hover(rc, `<b>${esc(r.name)}</b><br>${esc(r.sea)}<br>${fmt(r.km2)} km²`);
    lbl(svg, L0 + ww + 6, y + 15, fmt(r.km2), "lab s m"); });
});
resp(document.getElementById("oceans"), (w, nar) => {
  const o = R.world.ocean_share, keys = ["Atlantic", "Arctic", "Pacific", "Indian", "Inland (no outlet to the sea)"], L0 = nar ? 120 : 170, rh = 30;
  const svg = el("svg", { viewBox: `0 0 ${w} ${keys.length * rh + 4}` }, document.getElementById("oceans"));
  keys.forEach((k, i) => { const v = o[k].share, ww = v / .4 * (w - L0 - 60), y = i * rh; const nm = k.startsWith("Inland") ? "No outlet" : k;
    lbl(svg, L0 - 8, y + 18, nm, "lab b", "end"); el("rect", { x: L0, y: y + 4, width: ww, height: rh - 10, fill: OCEAN_HEX[k.startsWith("Inland") ? "Inland" : k] }, svg);
    lbl(svg, L0 + ww + 6, y + 18, pct(v, 1), "lab"); });
});
(function inlandTable() {
  const t = document.getElementById("inland");
  t.innerHTML = `<thead><tr><th>Ends in</th><th class="wide">Rivers</th><th class="num">Area (km²)</th></tr></thead><tbody>` + R.world.inland_top.slice(0, 10).map((r, k) => `<tr class="go" data-k="${k}"><td>${esc(r.lake ? (r.lake.includes("Sea") ? r.lake : "Lake " + r.lake.replace(/^Lake /, "")) : "Closed basin")}<small>${esc(r.country || "Caspian region")}</small></td><td class="wide">${esc((r.rivers || "").split(" | ").join(", "))}</td><td class="num">${fmt(r.km2)}</td></tr>`).join("") + "</tbody>";
  t.querySelectorAll("tr.go").forEach(tr => tr.onclick = () => { const r = R.world.inland_top[+tr.dataset.k]; flyTo(r.sink_lat, r.sink_lon, 5); });
})();
(function worldCards() {
  const box = document.getElementById("worldcards"), L = R.world.longest_by_ocean.filter(x => x.km > 500);
  box.innerHTML = L.map((x, k) => `<div class="card" data-k="${k}" style="border-left-color:${OCEAN_HEX[x.ocean.startsWith("Inland") ? "Inland" : x.ocean]}"><b>${esc(x.ocean.startsWith("Inland") ? "Inland" : x.ocean)}</b><div class="big">${fmt(x.km)} <span>km</span></div>${esc(x.route.split(" > ").slice(0, 1).concat(x.route.split(" > ").slice(-1)).join(" … "))}<br>to the ${esc(x.sea === "inland" ? "Caspian Sea" : x.sea)}</div>`).join("");
  box.querySelectorAll(".card").forEach(c => c.onclick = () => { const x = L[+c.dataset.k]; flyTo(x.lat, x.lon, 5); });
})();
function heroMark() {
  // a raindrop splitting three ways, in the three main colours of the British map
  const g = document.getElementById("heroMark"); g.innerHTML = "";
  el("path", { d: "M60 10 C48 30 40 42 40 54 a20 20 0 0 0 40 0 C80 42 72 30 60 10 Z", fill: "#2F67B1" }, g);
  el("path", { d: "M60 74 L60 92 M60 92 L30 112 M60 92 L90 112 M60 92 L60 116", stroke: css("--fg"), "stroke-width": 3, fill: "none", "stroke-linecap": "round" }, g);
  el("circle", { cx: 30, cy: 112, r: 5, fill: "#3E9E66" }, g); el("circle", { cx: 90, cy: 112, r: 5, fill: "#E3A23A" }, g); el("circle", { cx: 60, cy: 116, r: 5, fill: "#8B56B4" }, g);
}
heroMark();
initMap();
