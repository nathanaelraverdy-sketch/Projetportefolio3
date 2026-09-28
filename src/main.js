/* ═════════════ La ville des projets — version « image pré-rendue » (façon why.zero.university) ═════════════
   La ville n'est plus construite dans le navigateur : c'est UNE image photoréaliste calculée dans Blender
   (tools/build_city.py), posée sur un plan et filmée par une caméra orthographique. Il y en a une par moment
   de la journée (matin, jour, soir, nuit) : même ville, même cadrage, elles se fondent l'une dans l'autre.
   Par-dessus : les pastilles des projets, la fiche, le projet en détail, l'écran d'accueil en nuages,
   la barre de navigation et le bouton de l'heure — repris du projet « Projetcarte ». */
import { dessineIcone } from './icones.js';
import * as THREE from 'three';
import { PROJECTS } from './projets.js';
import { pageHTML, mediaHTML, animerOutils, arreterOutils } from './detail.js';
import './style.css';

const $ = id => document.getElementById(id);
const charge = k => { try { window.__charge?.(k); } catch (e) { /* pas d'écran de chargement */ } };
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

/* aperçu de la page admin : #vitrine&sel=p2&acc=e0714d */
const VITRINE = (() => { try { const h = location.hash.slice(1); if (!/^vitrine/.test(h)) return null; const q = new URLSearchParams(h.replace(/^vitrine&?/, '')); const uv = (q.get('uv') || '').split(',').map(Number); return { sel: q.get('sel') || '', nom: q.get('nom') || '', icone: q.get('ic') || '', acc: '#' + (q.get('acc') || 'e0714d').replace('#', ''), uv: uv.length === 2 && uv.every(isFinite) ? uv : null }; } catch (e) { return null; } })();
if (VITRINE) document.body.classList.add('vitrine');

/* ═════════════ 1. Les images de la ville ═════════════ */
// l'image 8K sur ordinateur ; la version 4K sur téléphone (ou si la carte graphique ne sait pas faire plus)
const Q8K = (() => { try { const g = document.createElement('canvas').getContext('webgl2'); return g && g.getParameter(g.MAX_TEXTURE_SIZE) >= 8192 && Math.min(screen.width, screen.height) > 700; } catch (e) { return false; } })();
// Téléphone (ou petite carte graphique) : tout est allégé — images 4K, pas de course du soleil (simple fondu),
// pas d'anticrénelage ni d'effet maquette, résolution d'écran plafonnée, 30 images/s quand rien ne bouge.
const PETIT = !Q8K || matchMedia('(pointer: coarse)').matches;
const IMG = k => `/city/city${k === 'day' ? '' : '_' + k}${Q8K ? '' : '_4k'}.webp`;
const IMAGES = { morning: IMG('morning'), day: IMG('day'), dusk: IMG('dusk'), night: IMG('night') };
const LOOK_IDS = ['morning', 'day', 'dusk', 'night'];
// si l'image d'un moment n'existe pas encore, on teinte celle du jour
const FALLBACK_TINT = { morning: [1.05, .93, .82], day: [1, 1, 1], dusk: [1.02, .78, .62], night: [.16, .2, .32] };
/* l'étalonnage de chaque moment (teinte, exposition, chaud, bleuté, saturation, contraste) */
const GRADES = [
  { tint: [1.07, .98, .87], expo: .97, warm: .9, cool: .3, sat: .3, con: .12 },    // matin
  { tint: [1, 1, 1], expo: .94, warm: .7, cool: .26, sat: .28, con: .12 },          // jour
  { tint: [1.08, .93, .84], expo: .9, warm: 1, cool: .36, sat: .24, con: .14 },    // soir
  { tint: [1, 1, 1], expo: 1, warm: .35, cool: .3, sat: .1, con: .06 },  // nuit
];

const canvas = $('webgl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: !PETIT, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, PETIT ? 1.5 : 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setClearColor('#cfe3e6');
const scene = new THREE.Scene();
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, .1, 20);
camera.position.set(0, 0, 5);

function loadImage(url, onProgress) {
  return new Promise((ok, ko) => {
    new THREE.FileLoader().setResponseType('blob').load(url, async blob => {
      try {
        if (/^text\//.test(blob.type)) throw new Error('pas une image : ' + url);   // (Vite renvoie index.html pour un fichier absent)
        const bmp = await createImageBitmap(blob, { imageOrientation: 'flipY' });
        const t = new THREE.Texture(bmp); t.flipY = false; t.colorSpace = THREE.SRGBColorSpace;
        t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy()); t.needsUpdate = true;
        ok(t);
      } catch (e) { ko(e); }
    }, onProgress, ko);
  });
}

// la page d'accueil est devant : la ville attend son tour (après la casse de la vitre), pour ne pas faire saccader l'animation
if (window.__accueilOuvert && !window.__villeGo) await new Promise(ok => addEventListener('ville-go', ok, { once: true }));
const TEX = {};
const [meta] = await Promise.all([
  fetch('/city/emplacements.json').then(r => r.json()),
  loadImage(IMAGES.day, e => e.total && charge(.05 + .85 * e.loaded / e.total)).then(t => { TEX.day = t; }),
]);
charge(.95);
const IMG_W = TEX.day.image.width, IMG_H = TEX.day.image.height, ASPECT = IMG_W / IMG_H;
const PLANE_H = 10, PLANE_W = PLANE_H * ASPECT;

/* ═════════════ 2. Le plan de la ville : 4 moments mélangés, ombres de nuages, brume ═════════════ */
const U = {
  uTex: { value: [TEX.day, TEX.day, TEX.day, TEX.day] }, uJour: { value: TEX.day },   // (le jour sert aussi de base à la nuit, éclairée par la lune)
  uW: { value: new THREE.Vector4(0, 1, 0, 0) },             // poids matin, jour, soir, nuit
  uLights: { value: 1 },                                    // la part des lumières de la nuit déjà allumées
  uSeq: { value: 0 }, uSeqA: { value: TEX.day }, uSeqB: { value: TEX.day }, uSeqF: { value: 0 },   // la course du soleil : deux images voisines et le mélange entre elles
  uTint: { value: LOOK_IDS.map(k => new THREE.Vector3(...FALLBACK_TINT[k])) },
  uLook: { value: GRADES.map(g => new THREE.Vector3(...g.tint).multiplyScalar(g.expo)) },          // teinte et exposition de chaque moment
  uGrade: { value: GRADES.map(g => new THREE.Vector4(g.warm, g.cool, g.sat, g.con)) },             // étalonnage de chaque moment
  uTilt: { value: VITRINE || PETIT ? 0 : .9 }, uRes: { value: new THREE.Vector2(1, 1) },
  uTime: { value: 0 }, uCloud: { value: 0 }, uHaze: { value: .16 }, uAspect: { value: ASPECT },
};
const mapMat = new THREE.ShaderMaterial({
  uniforms: U,
  vertexShader: /* glsl */`varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`,
  fragmentShader: /* glsl */`
    uniform sampler2D uTex[4], uJour, uSeqA, uSeqB; uniform vec4 uW; uniform vec3 uTint[4], uLook[4]; uniform vec4 uGrade[4];
    uniform float uLights, uTilt, uSeq, uSeqF; uniform vec2 uRes;
    uniform float uTime, uCloud, uHaze, uAspect; varying vec2 vUv;
    float h21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
    float vn(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3. - 2. * f);
      return mix(mix(h21(i), h21(i + vec2(1, 0)), u.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), u.x), u.y); }
    float fbm(vec2 p){ float a = .5, s = 0.; for (int i = 0; i < 5; i++){ s += a * vn(p); p = p * 2.03 + 17.1; a *= .5; } return s; }
    float lum(vec3 c){ return dot(c, vec3(.2126, .7152, .0722)); }
    void main(){
      vec2 A = vUv * vec2(uAspect, 1.);
      vec4 w = uW;
      // l'effet maquette : un léger flou en haut et en bas de l'écran
      float ty = gl_FragCoord.y / uRes.y, bias = smoothstep(.34, .5, abs(ty - .5)) * uTilt;
      vec3 c = vec3(0.);
      if (uSeq > .5) {
        // le soleil tourne : on passe d'une image de sa course à la suivante (les ombres glissent)
        vec3 T = w.x * uLook[0] + w.y * uLook[1] + w.z * uLook[2];
        c = mix(texture2D(uSeqA, vUv, bias).rgb, texture2D(uSeqB, vUv, bias).rgb, uSeqF) * T;
      } else {
        if (w.x > .001) c += w.x * texture2D(uTex[0], vUv, bias).rgb * uTint[0] * uLook[0];
        if (w.y > .001) c += w.y * texture2D(uTex[1], vUv, bias).rgb * uTint[1] * uLook[1];
        if (w.z > .001) c += w.z * texture2D(uTex[2], vUv, bias).rgb * uTint[2] * uLook[2];
        if (w.w > .001) {
          // la nuit : la ville au clair de lune, puis les lumières qui s'allument par quartiers
          vec3 n = texture2D(uTex[3], vUv, bias).rgb * uTint[3];
          float L = lum(n); vec3 nb = n * min(1., .012 / max(L, 1e-4)); vec3 nl = n - nb;
          vec3 lune = texture2D(uJour, vUv, bias).rgb * vec3(.05, .075, .14);
          float allume = 1.;
          if (uLights < .999) {
            float thr = clamp((fbm(A * 5.5 + 3.7) - .28) / .44, 0., 1.) * .78 + h21(floor(A * 260.)) * .22;
            allume = smoothstep(thr - .05, thr + .05, uLights * 1.1);
          }
          c += w.w * ((max(nb, lune) + vec3(.002, .003, .008)) * uLook[3] + nl * allume);
        }
      }
      // ombres de nuages qui dérivent — pas la nuit
      if (uCloud > 0.) { vec2 q = A * 1.35 + vec2(uTime * .010, uTime * .004); c *= 1. - smoothstep(.48, .78, fbm(q)) * uCloud * (1. - w.w); }
      // brume de distance : le haut de l'image est le plus loin
      vec3 haze = mix(vec3(.80, .86, .90), vec3(.05, .07, .12), w.w);
      c = mix(c, haze, smoothstep(.5, 1.05, vUv.y) * uHaze);
      // l'étalonnage (comme sur Projet Carte) : lumières chaudes, ombres bleutées, couleurs franches, contraste en S
      vec4 G = w.x * uGrade[0] + w.y * uGrade[1] + w.z * uGrade[2] + w.w * uGrade[3];
      vec3 p = pow(max(c, 0.), vec3(1. / 2.2)); float l = lum(p);
      p = mix(p, p * vec3(1.05, 1.005, .92), smoothstep(.35, .95, l) * G.x);
      p = mix(p, p * vec3(.9, .97, 1.08), (1. - smoothstep(.05, .5, l)) * G.y);
      p = mix(vec3(l), p, 1. + G.z);
      p = clamp(p, 0., 1.); p = mix(p, p * p * (3. - 2. * p), G.w);
      gl_FragColor = vec4(pow(p, vec3(2.2)), 1.);
      #include <colorspace_fragment>
    }`,
});
const mapMesh = new THREE.Mesh(new THREE.PlaneGeometry(PLANE_W, PLANE_H), mapMat); scene.add(mapMesh);

/* les autres moments se chargent ensuite, sans bloquer l'ouverture */
/* les autres moments ne se chargent que quand on en a besoin (une image 8K pèse ~130 Mo en mémoire graphique) ;
   on garde toujours le jour, et au plus un autre moment */
const LOADING = {}, MISSING = {};
function ensureTex(k) {
  if (TEX[k] || LOADING[k] || MISSING[k]) return;
  LOADING[k] = true;
  loadImage(IMAGES[k]).then(t => { TEX[k] = t; LOADING[k] = false; refreshTex(); }).catch(() => { MISSING[k] = true; LOADING[k] = false; });
}
function dropUnused(w) {
  for (const k of ['morning', 'dusk', 'night']) {
    const i = LOOK_IDS.indexOf(k);
    if (TEX[k] && w.getComponent(i) < .001 && T4.getComponent(i) === 0 && TR.from.getComponent(i) === 0 && TR.to.getComponent(i) === 0) { TEX[k].dispose(); delete TEX[k]; refreshTex(); }
  }
}
function refreshTex() {
  LOOK_IDS.forEach((k, i) => { U.uTex.value[i] = TEX[k] || TEX.day; U.uTint.value[i].set(...(TEX[k] ? [1, 1, 1] : FALLBACK_TINT[k])); });
}
refreshTex();

/* ═════════════ 3. Matin, jour, soir et nuit (repris de Projetcarte) ═════════════
   Par défaut la lumière suit l'heure réelle ; le bouton permet de choisir soi-même. */
const HOURS = [[0, 'night'], [5, 'night'], [6.5, 'morning'], [8.5, 'day'], [17, 'day'], [19, 'dusk'], [20.5, 'night'], [24, 'night']];
let look = VITRINE ? 'day' : 'auto';
const W4 = new THREE.Vector4(0, 1, 0, 0), T4 = new THREE.Vector4();
function targetWeights() {
  T4.set(0, 0, 0, 0);
  if (look !== 'auto') { T4.setComponent(LOOK_IDS.indexOf(look), 1); return T4; }
  const d = new Date(), h = d.getHours() + d.getMinutes() / 60;
  let k = 0; while (k < HOURS.length - 2 && HOURS[k + 1][0] <= h) k++;
  const [h0, a] = HOURS[k], [h1, b] = HOURS[k + 1]; let f = h1 > h0 ? (h - h0) / (h1 - h0) : 0; f = f * f * (3 - 2 * f);
  T4.setComponent(LOOK_IDS.indexOf(a), 1 - f); T4.setComponent(LOOK_IDS.indexOf(b), T4.getComponent(LOOK_IDS.indexOf(b)) + f);
  return T4;
}
W4.copy(targetWeights());
/* la transition entre deux moments (5 s) :
   - entre matin, jour et soir, le soleil tourne autour de la ville : on enchaîne les images de sa course (tools/rendre.sh soleil),
     les ombres glissent ; sans ces images, un simple fondu ;
   - vers la nuit : la ville s'assombrit, puis les lumières s'allument par quartiers ; en sortant de la nuit, l'inverse */
const TR = { from: new THREE.Vector4().copy(W4), to: new THREE.Vector4().copy(W4), p: 1, dur: 5, versNuit: false, deNuit: false };
const ecart = (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y) + Math.abs(a.z - b.z) + Math.abs(a.w - b.w);
const lisse = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
const plage = (x, a, b) => Math.min(1, Math.max(0, (x - a) / (b - a)));
// les images de la course du soleil (petites : 2048 px) — chargées en arrière-plan, gardées décodées, envoyées à la carte graphique au besoin
const SOLEIL = { segs: null, tex: {}, attente: {} };
if (!PETIT) fetch('/city/soleil.json').then(r => r.ok ? r.json() : null).then(j => {
  if (!j || !j.segments) return; SOLEIL.segs = j.segments;
  setTimeout(() => Object.keys(SOLEIL.segs).forEach(chargeSegment), 2500);
}).catch(() => {});
function chargeSegment(seg) {
  if (!SOLEIL.segs || !SOLEIL.segs[seg] || SOLEIL.tex[seg] || SOLEIL.attente[seg]) return;
  SOLEIL.attente[seg] = true;
  Promise.all(SOLEIL.segs[seg].map(u => loadImage('/city/' + u))).then(ts => { SOLEIL.tex[seg] = ts; }).catch(() => { delete SOLEIL.segs[seg]; }).finally(() => { SOLEIL.attente[seg] = false; });
}
// le segment de la course du soleil qui correspond à ce mélange (deux moments voisins, pas la nuit), ou null
function segmentDe(w) {
  if (w.w > .001) return null;
  if (w.z < .001 && w.x > .001 && w.y > .001) return { seg: 'morning-day', a: 0, b: 1, t: w.y / (w.x + w.y) };
  if (w.x < .001 && w.y > .001 && w.z > .001) return { seg: 'day-dusk', a: 1, b: 2, t: w.z / (w.y + w.z) };
  return null;
}
function soleilPret(from, to) {                                       // la course est-elle prête pour cette transition ?
  const a = [from.x, from.y, from.z, from.w].indexOf(1), b = [to.x, to.y, to.z, to.w].indexOf(1);
  const seg = a === 0 && b === 1 || a === 1 && b === 0 ? 'morning-day' : a === 1 && b === 2 || a === 2 && b === 1 ? 'day-dusk' : null;
  if (!seg || !SOLEIL.segs || !SOLEIL.segs[seg]) return true;           // pas de course pour ce passage : fondu simple
  chargeSegment(seg); return !!SOLEIL.tex[seg];
}
function transition(dt) {
  const tw = targetWeights();
  LOOK_IDS.forEach((k, i) => { if (tw.getComponent(i) > 0) ensureTex(k); });
  if (ecart(tw, TR.to) > 1e-4) {
    if (TR.p >= 1 && ecart(tw, TR.to) < .03) { TR.to.copy(tw); TR.from.copy(tw); }           // l'heure réelle avance doucement
    else if (LOOK_IDS.every((k, i) => tw.getComponent(i) === 0 || TEX[k] || MISSING[k]) && soleilPret(W4, tw)) {   // on attend que les images soient chargées
      TR.from.copy(W4); TR.to.copy(tw); TR.p = 0;
      TR.versNuit = TR.to.w > TR.from.w + .3; TR.deNuit = TR.from.w > TR.to.w + .3;
    }
  }
  TR.p = Math.min(1, TR.p + dt / TR.dur);
  let sw, li;
  if (TR.versNuit) { sw = plage(TR.p, 0, .55); li = plage(TR.p, .45, 1); }                   // l'obscurité, puis les lumières
  else if (TR.deNuit) { li = 1 - plage(TR.p, 0, .45); sw = plage(TR.p, .35, 1); }            // les lumières s'éteignent, puis le jour se lève
  else { sw = TR.p; li = 1; }
  W4.copy(TR.from).lerp(TR.to, TR.versNuit || TR.deNuit ? lisse(sw) : sw * sw * (3 - 2 * sw)); U.uW.value.copy(W4);
  U.uLights.value = TR.versNuit || TR.deNuit ? li : 1;
  // la course du soleil
  const sg = segmentDe(W4), ts = sg && SOLEIL.tex[sg.seg];
  if (ts && TEX[LOOK_IDS[sg.a]] && TEX[LOOK_IDS[sg.b]]) {
    const suite = [TEX[LOOK_IDS[sg.a]], ...ts, TEX[LOOK_IDS[sg.b]]], pos = sg.t * (suite.length - 1), i = Math.min(suite.length - 2, Math.floor(pos));
    U.uSeq.value = 1; U.uSeqA.value = suite[i]; U.uSeqB.value = suite[i + 1]; U.uSeqF.value = pos - i;
  } else U.uSeq.value = 0;
}
const timeBtn = $('timeBtn');
const MODES = ['auto', 'morning', 'day', 'dusk', 'night'], MODE_NOM = { auto: 'Heure réelle', morning: 'Matin', day: 'Jour', dusk: 'Soir', night: 'Nuit' };
function showMode() {
  if (!timeBtn) return;
  const next = MODES[(MODES.indexOf(look) + 1) % MODES.length];
  timeBtn.dataset.mode = look; timeBtn.title = MODE_NOM[look];
  timeBtn.setAttribute('aria-label', `Lumière : ${MODE_NOM[look].toLowerCase()}. Cliquer pour passer à : ${MODE_NOM[next].toLowerCase()}`);
}
if (timeBtn) timeBtn.onclick = () => { look = MODES[(MODES.indexOf(look) + 1) % MODES.length]; showMode(); };
showMode();

/* ═════════════ 4. Caméra : pan, zoom, inertie ═════════════ */
let vw = innerWidth, vh = innerHeight;
const S = { zoom: 3, zoomT: 3, zMin: 1.2, zMax: 5, zHome: 3, pan: new THREE.Vector2(), panT: new THREE.Vector2(), vel: new THREE.Vector2(),
  drag: false, last: { x: 0, y: 0 }, start: { x: 0, y: 0 }, ptrs: new Map(), pinch: 0, libre: !!VITRINE };
function limits() {
  const a = vw / vh;
  S.zMax = Math.min(PLANE_H / 2, PLANE_W / 2 / a);                                  // l'écran ne sort jamais de l'image
  // zoom le plus proche : on voit ~460 m de large (c'était le dézoom maximal de la version précédente)
  const mPerUnit = (meta.largeur_m || 1600) / PLANE_W;
  S.zMin = Math.min(S.zMax, Math.max(PLANE_H * vh / (2 * IMG_H * 1.6), 460 / (2 * a * mPerUnit)));
  S.zHome = Math.min(S.zMax, Math.max(S.zMin, S.zMax * .78));
}
function clampPan(p, z) {
  const a = vw / vh, mx = Math.max(0, PLANE_W / 2 - z * a), my = Math.max(0, PLANE_H / 2 - z);
  p.x = THREE.MathUtils.clamp(p.x, -mx, mx); p.y = THREE.MathUtils.clamp(p.y, -my, my);
}
function resize() { vw = innerWidth; vh = innerHeight; renderer.setSize(vw, vh, false); renderer.getDrawingBufferSize(U.uRes.value); limits(); S.zoomT = THREE.MathUtils.clamp(S.zoomT, S.zMin, S.zMax); }
addEventListener('resize', resize); resize();
const HOME = new THREE.Vector2(0, -.4);
S.zoom = S.zoomT = VITRINE ? S.zMax * .8 : S.zMax; S.pan.copy(HOME); S.panT.copy(HOME);
const wpp = () => 2 * S.zoom / vh;                                                  // unités monde par pixel
const zoomBy = f => { S.zoomT = THREE.MathUtils.clamp(S.zoomT * f, S.zMin, S.zMax); };
$('zoomIn') && ($('zoomIn').onclick = () => zoomBy(.8));
$('zoomOut') && ($('zoomOut').onclick = () => zoomBy(1.25));

/* ═════════════ 5. Les pastilles des projets ═════════════ */
const posUV = uv => new THREE.Vector3((uv[0] - .5) * PLANE_W, (uv[1] - .5) * PLANE_H, .05);
const SLOTS = meta.emplacements.map(e => ({ ...e, pos: posUV(e.uv) }));
const hexOf = h => '#' + (h || [224, 113, 77]).map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
/* chaque projet prend sa position libre (posée à la main dans l'admin), sinon l'emplacement choisi, sinon le premier libre */
function placer() {
  const pris = new Set(), out = [];
  for (const [k, p] of PROJECTS.entries()) {
    if (Array.isArray(p.uv) && p.uv.length === 2) { out.push([p, { id: 'libre-' + k, nom: p.name, uv: p.uv, pos: posUV(p.uv) }]); continue; }
    const s = SLOTS.find(s => s.id === p.emplacement && !pris.has(s.id)); if (s) { pris.add(s.id); out.push([p, s]); } else out.push([p, null]);
  }
  for (const o of out) if (!o[1]) { const s = SLOTS.find(s => !pris.has(s.id)); if (s) { pris.add(s.id); o[1] = s; } }
  const hors = out.filter(o => !o[1]).map(o => o[0].name);
  if (hors.length) console.warn('Plus de projets que d’emplacements dans l’image : non affichés →', hors.join(', '));
  return out.filter(o => o[1]);
}
const LIBRE = { id: 'libre', nom: 'Position libre' };
/* aperçu admin : seulement la pastille du projet en cours (on la pose où on veut en cliquant sur la carte) */
const ENTRIES = VITRINE ? (VITRINE.uv ? [{ p: { id: 'libre', name: VITRINE.nom || 'Ce projet', hue: [255, 255, 255] }, s: { ...LIBRE, uv: VITRINE.uv, pos: posUV(VITRINE.uv) } }] : [])
  : placer().map(([p, s]) => ({ p, s }));

/* la pastille : un numéro par défaut, ou l'icône choisie dans l'admin (un symbole, un emoji, ou une image) */
const estImage = s => typeof s === 'string' && /^(\/|https?:|data:)/.test(s);
function markerTexture(n, color) {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const g = c.getContext('2d'); g.translate(128, 128);
  const sh = g.createRadialGradient(0, 10, 40, 0, 10, 124); sh.addColorStop(0, 'rgba(0,0,0,.42)'); sh.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = sh; g.beginPath(); g.arc(0, 10, 124, 0, 7); g.fill();
  g.fillStyle = '#eff6f8'; g.beginPath(); g.arc(0, 0, 64, 0, 7); g.fill();
  g.strokeStyle = color; g.lineWidth = 10; g.beginPath(); g.arc(0, 0, 50, 0, 7); g.stroke();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  if (estImage(n)) {                                                    // une image, découpée en rond dans l'anneau
    const im = new Image(); im.crossOrigin = 'anonymous';
    im.onload = () => { g.save(); g.beginPath(); g.arc(0, 0, 44, 0, 7); g.clip(); const k = Math.max(88 / im.width, 88 / im.height);
      g.drawImage(im, -im.width * k / 2, -im.height * k / 2, im.width * k, im.height * k); g.restore(); t.needsUpdate = true; };
    im.src = n; return t;
  }
  if (typeof n === 'string' && n.startsWith('ic:') && dessineIcone(g, n.slice(3), 58, '#2a2222')) return t;   // une icône de la bibliothèque
  const txt = String(n), emoji = /\p{Extended_Pictographic}/u.test(txt);
  g.fillStyle = '#2a2222'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.font = emoji ? '52px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif' : `600 ${txt.length > 2 ? 36 : 52}px Urbanist, Manrope, system-ui, sans-serif`;
  g.fillText(txt, 0, emoji ? 6 : 4);
  return t;
}
const rippleMat = () => new THREE.ShaderMaterial({
  uniforms: { uColor: { value: new THREE.Color('#fff') }, uOpacity: { value: 0 } },
  vertexShader: `varying vec2 vL; void main(){ vL = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`,
  fragmentShader: `uniform vec3 uColor; uniform float uOpacity; varying vec2 vL;
    void main(){ float r = length(vL); float a = pow(smoothstep(.78, .95, r), 2.5) * (1. - smoothstep(.97, 1., r)) * uOpacity; gl_FragColor = vec4(uColor * a, a); }`,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
});
const discGeo = new THREE.PlaneGeometry(4, 4), ringGeo = new THREE.CircleGeometry(1, 64);
const labelsEl = $('labels');
function makePin({ p, s }, i) {
  const color = VITRINE ? VITRINE.acc : hexOf(p.hue);
  const group = new THREE.Group(); group.position.copy(s.pos);
  const disc = new THREE.Mesh(discGeo, new THREE.MeshBasicMaterial({ map: markerTexture(s.id === 'libre' ? (VITRINE.icone || '★') : (p.icone || i + 1), color), transparent: true, depthWrite: false }));
  disc.renderOrder = 3; group.add(disc);
  const ripples = [0, 1, 2].map(() => { const m = new THREE.Mesh(ringGeo, rippleMat()); m.renderOrder = 2; group.add(m); return m; });
  scene.add(group);
  const l = document.createElement('div'); l.className = 'lbl'; l.textContent = p.name; labelsEl.appendChild(l);
  return { p, s, i, color: new THREE.Color(color), group, disc, ripples, label: l, pop: VITRINE ? 1 : 0, hover: 1 };
}
const PINS = ENTRIES.map(makePin);

/* la balise lumineuse du projet ouvert : une colonne de lumière et des particules qui montent */
const beacon = new THREE.Group(), grow = { v: 0 }, BEAM_H = 7; beacon.visible = false;
const beamU = { uColor: { value: new THREE.Color('#4dff4d') }, uAlpha: { value: 0 }, uTime: U.uTime };
const beam = new THREE.Mesh(new THREE.PlaneGeometry(2, BEAM_H).translate(0, BEAM_H / 2, 0), new THREE.ShaderMaterial({
  uniforms: beamU,
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`,
  fragmentShader: `uniform vec3 uColor; uniform float uAlpha, uTime; varying vec2 vUv;
    void main(){ float x = abs(vUv.x - .5) * 2.; float a = pow(1. - x, 3.) * pow(1. - vUv.y, 1.6) * smoothstep(0., .08, vUv.y) * (.85 + .15 * sin(uTime * 3. + vUv.y * 12.)) * uAlpha;
      gl_FragColor = vec4(uColor * a, a); }`,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
}));
beam.renderOrder = 1; beacon.add(beam);
const NP = 28, pPos = new Float32Array(NP * 3), pInfo = new Float32Array(NP * 3);
for (let k = 0; k < NP; k++) { const a = Math.random() * 6.283, r = Math.sqrt(Math.random()) * .9; pPos.set([Math.cos(a) * r, 0, 0], k * 3); pInfo.set([.15 + Math.random() * .25, Math.random(), 2 + Math.random() * 3], k * 3); }
const pGeo = new THREE.BufferGeometry(); pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3)); pGeo.setAttribute('aInfo', new THREE.BufferAttribute(pInfo, 3));
const partU = { uColor: beamU.uColor, uAlpha: beamU.uAlpha, uTime: U.uTime, uRise: { value: BEAM_H * .8 }, uDpr: { value: renderer.getPixelRatio() } };
const particles = new THREE.Points(pGeo, new THREE.ShaderMaterial({
  uniforms: partU,
  vertexShader: `uniform float uTime, uRise, uDpr; attribute vec3 aInfo; varying float vA;
    void main(){ float t = fract(uTime * aInfo.x + aInfo.y); vec3 p = position; p.y += t * uRise; p.x *= 1. - t * .5; vA = sin(t * 3.14159);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.); gl_PointSize = aInfo.z * uDpr; }`,
  fragmentShader: `uniform vec3 uColor; uniform float uAlpha; varying float vA;
    void main(){ float a = smoothstep(.5, 0., length(gl_PointCoord - .5)) * vA * uAlpha; gl_FragColor = vec4(uColor * a, a); }`,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
}));
particles.frustumCulled = false; beacon.add(particles); scene.add(beacon);

let current = -1, hover = -1;
const tweens = [];                                                   // de petites animations sans bibliothèque
function tween(obj, key, to, dur, ease = t => 1 - Math.pow(1 - t, 3)) { const from = obj[key], t0 = performance.now(); tweens.push({ obj, key, from, to, dur: dur * 1000, t0, ease }); }
function runTweens(now) { for (let i = tweens.length - 1; i >= 0; i--) { const w = tweens[i], k = Math.min(1, (now - w.t0) / w.dur); w.obj[w.key] = w.from + (w.to - w.from) * w.ease(k); if (k >= 1) tweens.splice(i, 1); } }
function lightBeacon(pin) {
  beacon.visible = true; beacon.position.copy(pin.s.pos).setZ(.04);
  beamU.uColor.value.copy(pin.color).lerp(new THREE.Color('#ffffff'), .25);
  beamU.uAlpha.value = 0; grow.v = 0; tween(beamU.uAlpha, 'value', 1, 1.2); tween(grow, 'v', 1, 1.1);
}
function dimBeacon() { tween(beamU.uAlpha, 'value', 0, .5); }

/* ═════════════ 6. Fiche projet (repris de Projetcarte) ═════════════ */
const card = $('card');
function drawHero(p) {
  const c = $('heroCv'), g = c.getContext('2d'), [r, gg, b] = p.hue || [224, 113, 77];
  const grd = g.createLinearGradient(0, 0, c.width, c.height); grd.addColorStop(0, `rgb(${r},${gg},${b})`); grd.addColorStop(1, '#243234');
  g.fillStyle = grd; g.fillRect(0, 0, c.width, c.height); g.fillStyle = 'rgba(246,242,234,.16)';
  let x = 0; while (x < c.width) { const w = 30 + Math.random() * 50, h = 60 + Math.random() * 170; g.fillRect(x, c.height - h, w - 6, h); x += w; }
}
function focusOn(pin, sideCard) {                                    // on recadre : le bâtiment reste visible à côté de la fiche
  S.zoomT = Math.max(S.zMin, Math.min(S.zoomT, S.zMin * 1.7));
  const k = 2 * S.zoomT / vh; S.panT.set(pin.s.pos.x, pin.s.pos.y); S.vel.set(0, 0);
  if (!sideCard) return;
  if (vw > 720) S.panT.x += ((card.offsetWidth || 380) + 24) / 2 * k; else S.panT.y -= vh * .2 * k;
}
function openProject(i) {
  const pin = PINS[i]; if (!pin) return; current = i;
  PINS.forEach((q, k) => q.label.classList.toggle('on', k === i));
  lightBeacon(pin);
  if (VITRINE) { try { parent.postMessage({ type: 'vitrine:choix', id: pin.s.id }, '*'); } catch (e) { /* pas de page parente */ } focusOn(pin, false); return; }
  const p = pin.p;
  $('cTitle').textContent = p.name;
  // statut en surimpression sur l'image, et barre d'avancement pour les projets en cours
  const EN = { 'en cours': 'In progress', 'terminé': 'Completed', 'termine': 'Completed', 'en pause': 'On hold', 'bientôt': 'Coming soon', 'bientot': 'Coming soon' };
  const st0 = (p.statut || '').trim(), st = EN[st0.toLowerCase()] || st0, sb = $('cStatut');
  sb.hidden = !st; sb.textContent = st; sb.dataset.s = st.toLowerCase().replace(/\s+/g, '-');
  const pr = Number(p.progression), avec = /in progress/i.test(st) && isFinite(pr) && p.progression !== undefined && p.progression !== '';
  $('cProg').hidden = !avec;
  if (avec) { const v = Math.max(0, Math.min(100, Math.round(pr))); $('cProgVal').textContent = v + ' %'; const b = $('cProgBar'); b.style.width = '0%'; requestAnimationFrame(() => requestAnimationFrame(() => { b.style.width = v + '%'; })); }
  const tags = p.tags || (p.tag ? [p.tag] : []); $('cTags').innerHTML = '';
  tags.forEach(t => { const c = document.createElement('span'); c.className = 'chip'; c.textContent = t; $('cTags').appendChild(c); });
  const hero = $('cHero'); hero.querySelectorAll('img,video').forEach(m => m.remove());
  const m1 = p.image || p.video ? p : (p.page || []).find(b => b.type === 'media' && (b.image || b.video)) || {};
  if (m1.image || m1.video) { hero.insertAdjacentHTML('beforeend', mediaHTML(m1.image, m1.video, 'hero-media')); $('heroCv').hidden = true; } else { $('heroCv').hidden = false; drawHero(p); }
  card.classList.add('open'); card.setAttribute('aria-hidden', 'false');
  focusOn(pin, true);
}
function closeCard() {
  card.classList.remove('open'); card.setAttribute('aria-hidden', 'true');
  if (current >= 0) dimBeacon(); current = -1; PINS.forEach(q => q.label.classList.remove('on'));
}
$('close').onclick = closeCard;
const cycle = d => PINS.length && openProject(((current < 0 ? (d > 0 ? -1 : 0) : current) + d + PINS.length) % PINS.length);
$('next').onclick = () => cycle(1);
$('prev').onclick = () => cycle(-1);

/* « View more » : le projet en détail, par-dessus la ville */
const detail = $('detail'); let enPause = false, pauseT = 0;
function openDetail() {
  const pin = PINS[current]; if (!pin) return;
  $('detailContenu').innerHTML = pageHTML(pin.p); detail.classList.add('open'); detail.setAttribute('aria-hidden', 'false'); document.body.classList.add('detail-ouvert');
  $('detailDefil').scrollTop = 0; clearTimeout(pauseT); pauseT = setTimeout(() => { enPause = true; }, 400); animerOutils($('detailContenu')); setTimeout(() => $('detailFermer').focus(), 50);
}
function closeDetail() {
  if (!detail.classList.contains('open')) return; clearTimeout(pauseT); enPause = false;
  detail.classList.remove('open'); detail.setAttribute('aria-hidden', 'true'); document.body.classList.remove('detail-ouvert');
  arreterOutils(); detail.querySelectorAll('video').forEach(v => v.pause()); $('more').focus();
}
$('more').onclick = openDetail; $('detailFermer').onclick = closeDetail;
detail.addEventListener('pointerdown', ev => { if (ev.target === detail) closeDetail(); });

addEventListener('keydown', ev => {
  if (ev.key === 'Escape') { if (detail.classList.contains('open')) { closeDetail(); return; } closeCard(); }
  if (detail.classList.contains('open') || !S.libre) return;
  if (ev.key === '+' || ev.key === '=') zoomBy(.85);
  if (ev.key === '-') zoomBy(1 / .85);
  if (current < 0) return;
  if (ev.key === 'ArrowRight') cycle(1);
  if (ev.key === 'ArrowLeft') cycle(-1);
});

/* ═════════════ 7. Glisser, zoomer, pincer ═════════════ */
const stage = $('stage'), ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
function pick(x, y) {
  ndc.set(x / vw * 2 - 1, -(y / vh) * 2 + 1); ray.setFromCamera(ndc, camera);
  const h = ray.intersectObjects(PINS.map(p => p.disc)); return h.length ? PINS.findIndex(p => p.disc === h[0].object) : -1;
}
stage.addEventListener('pointerdown', ev => {
  if (!S.libre) return;
  stage.setPointerCapture(ev.pointerId); S.ptrs.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
  if (S.ptrs.size === 2) { const [a, b] = [...S.ptrs.values()]; S.pinch = Math.hypot(a.x - b.x, a.y - b.y); S.drag = false; return; }
  S.drag = true; S.vel.set(0, 0); S.last = { x: ev.clientX, y: ev.clientY }; S.start = { ...S.last }; stage.classList.add('dragging');
});
stage.addEventListener('pointermove', ev => {
  if (!S.libre) return;
  if (S.ptrs.has(ev.pointerId)) S.ptrs.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
  if (S.ptrs.size === 2) {
    const [a, b] = [...S.ptrs.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
    if (S.pinch > 0) S.zoomT = THREE.MathUtils.clamp(S.zoomT * S.pinch / d, S.zMin, S.zMax); S.pinch = d; return;
  }
  if (S.drag) {
    const dx = ev.clientX - S.last.x, dy = ev.clientY - S.last.y, k = wpp();
    S.panT.x -= dx * k; S.panT.y += dy * k; S.vel.set(-dx * k, dy * k); S.last = { x: ev.clientX, y: ev.clientY };
  } else { hover = pick(ev.clientX, ev.clientY); stage.classList.toggle('over-pin', hover >= 0); }
});
function up(ev) {
  const wasPinch = S.ptrs.size === 2; S.ptrs.delete(ev.pointerId); if (S.ptrs.size < 2) S.pinch = 0;
  if (!S.drag) return; S.drag = false; stage.classList.remove('dragging');
  if (!wasPinch && Math.hypot(ev.clientX - S.start.x, ev.clientY - S.start.y) < 6) {
    S.vel.set(0, 0); const h = pick(ev.clientX, ev.clientY);
    if (h >= 0) (h === current && !VITRINE ? closeCard() : openProject(h)); else if (!VITRINE) closeCard(); else poseLibre(ev.clientX, ev.clientY);
  }
}
stage.addEventListener('pointerup', up); stage.addEventListener('pointercancel', up);
stage.addEventListener('wheel', ev => {                                 // zoom vers le curseur
  ev.preventDefault(); if (!S.libre) return;
  const before = S.zoomT; S.zoomT = THREE.MathUtils.clamp(before * Math.exp(ev.deltaY * .0012), S.zMin, S.zMax);
  const r = before - S.zoomT;
  if (r) { S.panT.x += (ev.clientX / vw * 2 - 1) * r * vw / vh; S.panT.y += -(ev.clientY / vh * 2 - 1) * r; }
}, { passive: false });

/* ═════════════ 8. L'écran d'accueil (repris de Projetcarte) ═════════════
   Une page claire le jour, sombre le soir, avec la phrase d'accroche. On fait défiler (molette, doigt, flèche du bas
   ou clic sur « Scroll to see more ») : la page se dissipe en nuages qui s'écartent depuis le centre et découvrent la ville,
   pendant que la caméra descend vers elle. */
let cityReady = false;
(function intro() {
  const box = $('intro'), cv = $('veil');
  let skip = !!VITRINE;
  try { if (sessionStorage.getItem('sansIntro')) { skip = true; sessionStorage.removeItem('sansIntro'); } } catch (e) { /* stockage indisponible */ }
  if (!box || !cv || skip) {
    document.body.classList.add('dans-la-ville'); S.libre = true;
    if (window.__accueilOuvert) { S.zoom = S.zoomT = S.zMax; return; }        // la page d'accueil est devant : les pastilles apparaîtront à la descente
    PINS.forEach(p => { p.pop = 1; p.label.classList.add('show'); }); S.zoom = S.zoomT = S.zHome; return;
  }
  const title = box.querySelector('.intro-title'), more = $('introMore'), sign = box.querySelector('.intro-sign');
  const g = cv.getContext('2d'), sombre = document.documentElement.classList.contains('sombre');
  const fond = sombre ? [42, 34, 34] : [239, 246, 248], clair = sombre ? [66, 56, 56] : [255, 255, 255], ombre = sombre ? [30, 24, 24] : [214, 228, 233];
  let W2 = 0, H2 = 0; const SC = .5;
  const size = () => { W2 = Math.ceil(innerWidth * SC); H2 = Math.ceil(innerHeight * SC); cv.width = W2; cv.height = H2; };
  size(); addEventListener('resize', size);
  let sd = 7; const r01 = () => (sd = (sd * 16807) % 2147483647) / 2147483647;
  const puffs = [];
  for (let i = 0; i < 120; i++) { const a = r01() * Math.PI * 2, d = Math.pow(r01(), .7) * .75; puffs.push({ x: Math.cos(a) * d * 1.25, y: Math.sin(a) * d, r: .16 + r01() * .2, t: Math.min(.95, d * .9 + r01() * .25), k: r01() }); }
  let p = 0, goal = 0, last = performance.now(), done = false, auto = false;
  const DUREE = 4.2;
  const push = d => { if (!done) goal = Math.min(1, Math.max(0, goal + d)); };
  // la molette est écoutée sur toute la fenêtre (et plus seulement sur le texte) : le défilement marche où que soit la souris
  addEventListener('wheel', ev => { if (done || S.libre) return; ev.preventDefault(); push(ev.deltaY * (ev.deltaMode === 1 ? .014 : .00045)); }, { passive: false });
  let ty = null;
  addEventListener('touchstart', ev => { ty = ev.touches[0].clientY; }, { passive: true });
  addEventListener('touchmove', ev => { if (done || S.libre || ty === null) return; const y = ev.touches[0].clientY; push((ty - y) * .0014); ty = y; ev.preventDefault(); }, { passive: false });
  addEventListener('keydown', ev => { if (done || S.libre) return; if (['ArrowDown', 'PageDown', ' ', 'Enter'].includes(ev.key)) { ev.preventDefault(); goal = 1; auto = true; } });
  more.onclick = () => { goal = 1; auto = true; };
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  const zFar = S.zMax, zNear = S.zHome;
  function frame(now) {
    const dt = Math.min(.25, (now - last) / 1000); last = now;              // (temps réel : même un ordinateur lent finit en ~4 s)
    if (!auto && goal >= .22) { auto = true; goal = 1; }                 // on a commencé : la suite se joue toute seule
    const cap = cityReady ? 1 : .45;                                     // la ville n'est pas encore prête : les nuages attendent
    if (auto) p = Math.min(cap, p + dt * (reduce ? 5 : 1 / DUREE));
    else p += (Math.min(goal, cap) - p) * Math.min(1, dt * (reduce ? 20 : 1.8));
    const tp = smooth(0, .4, p);
    more.style.animation = tp > .001 ? 'none' : '';
    for (const el of [title, more, sign]) { el.style.opacity = String(1 - tp); el.style.transform = `translateY(${-tp * 70}px) scale(${1 + tp * .06})`; el.style.filter = `blur(${tp * 10}px)`; }
    g.clearRect(0, 0, W2, H2);
    const base = 1 - smooth(.06, .55, p);
    if (base > 0) { g.fillStyle = rgba(fond, base); g.fillRect(0, 0, W2, H2); }
    const cx = W2 / 2, cy = H2 / 2, M = Math.max(W2, H2);
    if (p > .01) for (const b of puffs) {
      const l = smooth(.08 + b.t * .6, .08 + b.t * .6 + .34, p), a = 1 - l; if (a <= .002) continue;
      const x = cx + b.x * M * (1 + l * 1.1), y = cy + b.y * M * (1 + l * 1.1), r = b.r * M * (1 + l * .7);
      const gr = g.createRadialGradient(x - r * .15, y - r * .2, r * .05, x, y, r), c1 = b.k < .5 ? clair : fond;
      gr.addColorStop(0, rgba(c1, a)); gr.addColorStop(.55, rgba(fond, a * .85)); gr.addColorStop(.8, rgba(ombre, a * .35)); gr.addColorStop(1, rgba(ombre, 0));
      g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    }
    if (cityReady && !S.libre) { const k = smooth(.1, .85, p); S.zoom = S.zoomT = zFar + (zNear - zFar) * k; }   // la caméra descend vers la ville
    if (!S.libre && p > .8 && cityReady) {
      S.libre = true; document.body.classList.add('intro-libre');
      PINS.forEach((q, i) => setTimeout(() => { tween(q, 'pop', 1, .8, t => 1 + 2.7 * Math.pow(t - 1, 3) + 1.7 * Math.pow(t - 1, 2)); q.label.classList.add('show'); }, 150 + i * 110));
      tween(U.uCloud, 'value', .35, 2);
    }
    if (p > .995 && cityReady) { done = true; document.body.classList.add('dans-la-ville'); return; }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
if (document.body.classList.contains('dans-la-ville')) U.uCloud.value = .35;

/* ═════════════ 9. Aperçu de la page admin ═════════════ */
if (VITRINE) {
  const post = m => { try { parent.postMessage(m, '*'); } catch (e) { /* pas de page parente */ } };
  const i0 = PINS.findIndex(p => p.s.id === VITRINE.sel); if (i0 >= 0) { current = i0; PINS[i0].label.classList.add('on'); lightBeacon(PINS[i0]); focusOn(PINS[i0], false); }
  addEventListener('message', ev => {
    const m = ev.data || {};
    if (m.type === 'vitrine:voir') { const i = PINS.findIndex(p => p.s.id === m.id); if (i >= 0) { current = i; PINS.forEach((q, k) => q.label.classList.toggle('on', k === i)); lightBeacon(PINS[i]); focusOn(PINS[i], false); } }
  });
  setTimeout(() => post({ type: 'vitrine:pret', emplacements: SLOTS.map(s => ({ id: s.id, nom: s.nom })) }), 300);
}

/* aperçu admin : un clic ailleurs que sur un numéro pose le projet exactement là (position libre) */
function poseLibre(x, y) {
  ndc.set(x / vw * 2 - 1, -(y / vh) * 2 + 1); ray.setFromCamera(ndc, camera);
  const h = ray.intersectObject(mapMesh); if (!h.length) return;
  const uv = [+(h[0].point.x / PLANE_W + .5).toFixed(5), +(h[0].point.y / PLANE_H + .5).toFixed(5)];
  let i = PINS.findIndex(q => q.s.id === 'libre');
  if (i < 0) { const pin = makePin({ p: { id: 'libre', name: VITRINE.nom || 'Ce projet', hue: [255, 255, 255] }, s: { ...LIBRE, uv, pos: posUV(uv) } }, PINS.length); pin.label.classList.add('show'); PINS.push(pin); i = PINS.length - 1; }
  else { PINS[i].s.uv = uv; PINS[i].s.pos.copy(posUV(uv)); PINS[i].group.position.copy(PINS[i].s.pos); }
  current = i; PINS.forEach((q, k) => q.label.classList.toggle('on', k === i)); lightBeacon(PINS[i]);
  try { parent.postMessage({ type: 'vitrine:pose', uv }, '*'); } catch (e) { /* pas de page parente */ }
}

/* l'admin a enregistré : on recharge la ville (sans repasser par l'accueil) */
if (import.meta.hot) import.meta.hot.on('projets:maj', () => { try { sessionStorage.setItem('sansIntro', '1'); } catch (e) { /* rien */ } location.reload(); });

/* ═════════════ 9 bis. La nuit : de temps en temps, une fenêtre s'allume ou s'éteint ═════════════
   public/city/fenetres.json (écrit par tools/build.py avec le rendu de nuit) donne, pour chaque fenêtre visible, sa position
   dans l'image, sa forme, et si elle est allumée dans le rendu. Au plus une fenêtre toutes les 5 à 8 secondes (jamais plus
   de 2 en 10 s) : une ville qui vit, pas une boîte de nuit. */
const FEN = { list: null, overlays: new Map(), next: 0 };
fetch('/city/fenetres.json').then(r => r.ok ? r.json() : null).then(j => { if (j && Array.isArray(j.fenetres)) FEN.list = j.fenetres; }).catch(() => {});
const matGlow = new THREE.MeshBasicMaterial({ color: new THREE.Color(1, .85, .64), transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending });
const matNoir = new THREE.MeshBasicMaterial({ color: new THREE.Color(.03, .04, .065), transparent: true, opacity: 0, depthWrite: false });
function vitre(f, allume) {
  const [u, v, ax, ay, bx, by] = f, cx = (u - .5) * PLANE_W, cy = (v - .5) * PLANE_H;
  const A_ = [ax * PLANE_W / 2, ay * PLANE_H / 2], B_ = [bx * PLANE_W / 2, by * PLANE_H / 2], k = allume ? 1.08 : 1.2;   // la vitre éteinte déborde un peu : elle couvre bien la lumière
  const pts = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => new THREE.Vector3(cx + (A_[0] * a + B_[0] * b) * k, cy + (A_[1] * a + B_[1] * b) * k, .03));
  const g = new THREE.BufferGeometry().setFromPoints([pts[0], pts[1], pts[2], pts[0], pts[2], pts[3]]);
  const m = new THREE.Mesh(g, (allume ? matGlow : matNoir).clone()); m.renderOrder = 1; scene.add(m); return m;
}
function fenetresNuit(now) {
  if (!FEN.list || !TEX.night || W4.w < .6 || !S.libre || enPause) { FEN.overlays.forEach(o => { o.mesh.material.opacity *= .9; }); return; }
  if (FEN.overlays.size) FEN.overlays.forEach(o => { o.mesh.material.opacity += ((o.cible * W4.w * U.uLights.value) - o.mesh.material.opacity) * .04; });
  if (now < FEN.next) return;
  FEN.next = now + 5000 + Math.random() * 3000;
  const a = vw / vh, x0 = S.pan.x - S.zoom * a, x1 = S.pan.x + S.zoom * a, y0 = S.pan.y - S.zoom, y1 = S.pan.y + S.zoom;
  for (let essai = 0; essai < 40; essai++) {                        // une fenêtre qu'on voit à l'écran
    const i = (Math.random() * FEN.list.length) | 0, f = FEN.list[i], x = (f[0] - .5) * PLANE_W, y = (f[1] - .5) * PLANE_H;
    if (x < x0 || x > x1 || y < y0 || y > y1) continue;
    const o = FEN.overlays.get(i), allumee = o ? o.allume : !!f[6];
    if (o) { o.cible = 0; o.allume = !o.allume; setTimeout(() => { if (FEN.overlays.get(i) === o && o.cible === 0) { scene.remove(o.mesh); o.mesh.geometry.dispose(); FEN.overlays.delete(i); } }, 3000); }
    else FEN.overlays.set(i, { mesh: vitre(f, !allumee), cible: allumee ? .96 : .85, allume: !allumee });
    break;
  }
}

/* ═════════════ 10. Boucle de rendu ═════════════ */
const clock = new THREE.Clock(), tv = new THREE.Vector3();
let pauseAPropos = !!window.__accueilOuvert; addEventListener('couvre', e => { pauseAPropos = e.detail; if (!e.detail) clock.getDelta(); });   // la page d'accueil couvre la carte : on ne la dessine plus
function loop(now = 0) {
  requestAnimationFrame(loop);
  const brut = clock.getDelta(), dt = Math.min(brut, .05);
  if (enPause || pauseAPropos) return;
  runTweens(performance.now());
  U.uTime.value += dt;

  // lumière : on glisse vers le moment visé
  transition(Math.min(brut, .5));                                  // en temps réel, même si l'image rame
  if ((U.uTime.value | 0) % 3 === 0) dropUnused(W4);
  const nuit = W4.w > .45; if (nuit !== document.body.classList.contains('nuit')) document.body.classList.toggle('nuit', nuit);
  renderer.setClearColor(nuit ? '#141b26' : '#cfe3e6');
  fenetresNuit(performance.now());

  // caméra : inertie, bornes, lissage
  if (S.libre && !S.drag) { S.panT.add(S.vel); S.vel.multiplyScalar(Math.pow(.9, dt * 60)); }
  clampPan(S.panT, S.zoomT);
  S.zoom += (S.zoomT - S.zoom) * (1 - Math.exp(-dt * 6));
  S.pan.lerp(S.panT, 1 - Math.exp(-dt * 9)); clampPan(S.pan, S.zoom);
  const a = vw / vh;
  camera.left = -S.zoom * a; camera.right = S.zoom * a; camera.top = S.zoom; camera.bottom = -S.zoom;
  camera.position.set(S.pan.x, S.pan.y, 5); camera.updateProjectionMatrix();

  // pastilles de taille constante à l'écran, anneaux, étiquettes
  const PIN = 13, r = PIN * wpp(), t = U.uTime.value;                          // taille des pastilles (en pixels à l'écran)
  PINS.forEach((q, i) => {
    const on = i === hover || i === current;
    q.hover += ((on ? 1.18 : 1) - q.hover) * (1 - Math.exp(-dt * 12));
    q.group.scale.setScalar(Math.max(1e-4, r * q.pop * q.hover));
    const act = i === current;
    q.ripples.forEach((rp, k) => {
      const f = (t * (act ? .7 : .35) + k / 3 + i * .13) % 1;
      rp.scale.setScalar(1 + f * (act ? 2.6 : 1.6));
      rp.material.uniforms.uOpacity.value = (1 - f) * (act ? .9 : .4) * q.pop;
      rp.material.uniforms.uColor.value.copy(act ? q.color : new THREE.Color(1, 1, 1));
    });
    tv.copy(q.s.pos).project(camera);
    q.label.style.left = ((tv.x + 1) / 2 * vw) + 'px';
    q.label.style.top = ((1 - tv.y) / 2 * vh + PIN * q.hover * q.pop + 2) + 'px';
  });
  beacon.scale.set(r, r * Math.max(1e-4, grow.v), r);
  if (beamU.uAlpha.value < .002 && current < 0) beacon.visible = false;

  // téléphone : quand rien ne bouge, une image sur deux suffit (la batterie dit merci)
  if (PETIT) {
    const calme = TR.p >= 1 && !S.drag && S.vel.lengthSq() < 1e-10 && Math.abs(S.zoomT - S.zoom) < 1e-4 && S.pan.distanceToSquared(S.panT) < 1e-10;
    DEMI = calme ? !DEMI : false; if (DEMI) return;
  }
  renderer.render(scene, camera);
}
let DEMI = false;
/* depuis la page d'accueil : les nuages s'écartent, la caméra descend sur la ville et les pastilles apparaissent */
addEventListener('descente', e => {
  const d = e.detail || 3, z0 = S.zMax, z1 = S.zHome, t0 = performance.now();
  S.zoom = S.zoomT = z0; S.vel.set(0, 0);
  const f = now => { const k = Math.min(1, (now - t0) / 1000 / d), e2 = smooth(.08, .9, k); S.zoom = S.zoomT = z0 + (z1 - z0) * e2; if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
  PINS.forEach((q, i) => setTimeout(() => { if (q.pop >= 1) return; tween(q, 'pop', 1, .8, t => 1 + 2.7 * Math.pow(t - 1, 3) + 1.7 * Math.pow(t - 1, 2)); q.label.classList.add('show'); }, d * 1000 * .5 + i * 110));
  if (U.uCloud.value < .3) tween(U.uCloud, 'value', .35, 2);
});
cityReady = true;
if (import.meta.env.DEV) window.__ville = { S, PINS, U };   // pour déboguer dans la console
charge(1);
loop();
