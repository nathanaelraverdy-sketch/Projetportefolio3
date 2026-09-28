/* ═════════════ La page d'accueil ═════════════
   1. la vitre : « Finding the extraordinary in the ordinary ». « Press » suit la souris ; on appuie, un anneau se remplit
      autour du pointeur ; quand il est plein, la vitre se fissure puis se brise en éclats qui tombent et découvrent la page.
   2. la page : chaque titre monte mot à mot depuis le bas, les objets entrent en tournant puis flottent (ils suivent un peu
      le défilement et la souris), l'iPhone et le Macintosh se redressent en 3D, les couches se posent l'une après l'autre,
      la Terre naît depuis Bruxelles, les chiffres défilent comme un compteur.
   3. le bouton « Explore the projects map » ouvre la carte (la ville), qui se charge pendant qu'on lit.
   La page de l'admin (#vitrine) et les rechargements depuis l'admin vont directement à la carte. */
import './accueil.css';
import ACCUEIL from './accueil.json';
import { PROJECTS } from './projets.js';

const $ = id => document.getElementById(id);
const page = $('accueil'), vitre = $('acVitre'), curseur = $('acCurseur');
const CALME = matchMedia('(prefers-reduced-motion: reduce)').matches;
const TACTILE = matchMedia('(hover: none)').matches;
const PETIT = TACTILE || innerWidth < 760;
const ease = t => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

let direct = /vitrine/.test(location.hash);
try { if (sessionStorage.getItem('sansIntro')) direct = true; } catch (e) { /* stockage indisponible */ }

if (direct || !page) {                                 // directement la carte : la page d'accueil n'existe pas
  vitre?.remove(); curseur?.remove(); if (page) page.hidden = true;
  window.__accueilOuvert = false;
} else {
  window.__accueilOuvert = true;
  document.body.classList.add('accueil-ouvert', 'vitre-ouverte');
  demarrer();
}

function demarrer() {
  /* ─── les mots : chaque mot dans son petit cadre, pour monter depuis le bas ─── */
  document.querySelectorAll('[data-r="mots"]').forEach(el => {
    let k = 0;
    const couper = node => [...node.childNodes].forEach(n => {
      if (n.nodeType === 3) {
        const frag = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach(w => {
          if (!w) return;
          if (/^\s+$/.test(w)) { frag.appendChild(document.createTextNode(' ')); return; }
          const s = document.createElement('span'); s.className = 'mot'; const i = document.createElement('i'); i.textContent = w; i.style.setProperty('--i', k++); s.appendChild(i); frag.appendChild(s);
        });
        n.replaceWith(frag);
      } else if (n.nodeType === 1 && n.tagName !== 'BR') couper(n);
    });
    couper(el);
  });

  /* ─── la vitre : le titre apparaît, puis on attend l'appui ─── */
  const heroR = vitre.querySelectorAll('[data-r]');
  const montrer = () => { heroR.forEach(e => e.classList.add('vu')); setTimeout(() => vitre.classList.add('pret'), 900); };
  // l'iPhone et le Macintosh se chargent pendant qu'on lit le titre (pas pendant la casse) ; ils attendent derrière la vitre
  const modeles = () => import('./ecrans.js').then(({ creerEcran }) => {
    const E = ACCUEIL.ecrans || {};
    creerEcran($('acPhone'), 'iphone', E.iphone || {}, { base: [.06, -.28], amplitude: [.3, .14], incl: innerWidth < 760 ? -.13 : 0 });   // (sur téléphone : penché, comme sur la maquette)
    creerEcran($('acMac'), 'mac', E.mac || {}, { base: [.14, .55], amplitude: [.2, .1], incl: .05 });
  });
  window.__pause3D = true;
  setTimeout(() => (window.requestIdleCallback || (f => setTimeout(f, 1)))(modeles, { timeout: 1500 }), 1300);
  (document.fonts?.ready || Promise.resolve()).then(() => setTimeout(montrer, 180));

  const souris = { x: innerWidth / 2, y: innerHeight / 2, cx: innerWidth / 2, cy: innerHeight / 2, nx: 0, ny: 0 };
  addEventListener('pointermove', e => { souris.x = e.clientX; souris.y = e.clientY; souris.nx = e.clientX / innerWidth * 2 - 1; souris.ny = e.clientY / innerHeight * 2 - 1; }, { passive: true });
  /* sur téléphone : l'inclinaison remplace la souris (les objets 3D et les images bougent quand on penche le téléphone).
     La façon dont on le tient devient peu à peu la position « neutre » ; iPhone : l'autorisation est demandée au premier toucher. */
  const incliner = () => {
    let ref = null;
    addEventListener('deviceorientation', e => {
      if (e.beta == null || e.gamma == null) return;
      const a = (screen.orientation && screen.orientation.angle) || window.orientation || 0;
      const x = a === 90 ? e.beta : a === -90 || a === 270 ? -e.beta : e.gamma, y = a === 90 ? -e.gamma : a === -90 || a === 270 ? e.gamma : e.beta;
      if (!ref) ref = { x, y };
      ref.x += (x - ref.x) * .004; ref.y += (y - ref.y) * .004;
      const nx = Math.max(-1, Math.min(1, (x - ref.x) / 18)), ny = Math.max(-1, Math.min(1, (y - ref.y) / 18));
      souris.nx = nx; souris.ny = ny;
      dispatchEvent(new CustomEvent('incline', { detail: { nx, ny } }));
    });
  };
  if (TACTILE && 'DeviceOrientationEvent' in window) {
    if (typeof DeviceOrientationEvent.requestPermission === 'function')
      addEventListener('touchend', () => DeviceOrientationEvent.requestPermission().then(r => { if (r === 'granted') incliner(); }).catch(() => {}), { once: true, capture: true });
    else incliner();
  }
  if (TACTILE) curseur.classList.add('cache');

  const anneau = $('acAnneau'), L = 2 * Math.PI * 34, DUREE = 1150;
  const appui = { actif: false, p: 0, t0: 0, fini: false };
  const commencer = (x, y) => {
    if (appui.fini) return;
    appui.actif = true; appui.t0 = performance.now() - appui.p * DUREE;
    if (x !== undefined) { souris.x = souris.cx = x; souris.y = souris.cy = y; }
    curseur.classList.add('appui'); curseur.classList.remove('cache');
    preparer(souris.x, souris.y);                                              // tout est prêt avant la fin de l'anneau : la vitre cède à l'instant exact
  };
  const relacher = () => { if (appui.fini) return; appui.actif = false; curseur.classList.remove('appui'); if (TACTILE) curseur.classList.add('cache'); };
  const btn = $('acPressBtn');
  btn.addEventListener('pointerdown', e => { e.preventDefault(); btn.setPointerCapture?.(e.pointerId); commencer(e.clientX, e.clientY); });
  btn.addEventListener('pointerup', relacher); btn.addEventListener('pointercancel', relacher); btn.addEventListener('lostpointercapture', relacher);
  btn.addEventListener('keydown', e => { if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) { e.preventDefault(); commencer(innerWidth / 2, innerHeight * .62); } });
  btn.addEventListener('keyup', e => { if (e.key === ' ' || e.key === 'Enter') relacher(); });
  btn.addEventListener('contextmenu', e => e.preventDefault());
  setTimeout(() => btn.focus({ preventScroll: true }), 400);

  const decosVitre = [...vitre.querySelectorAll('.deco')];
  const bouclePointeur = now => {
    if (!vitre.isConnected) return;
    requestAnimationFrame(bouclePointeur);
    souris.cx += (souris.x - souris.cx) * .22; souris.cy += (souris.y - souris.cy) * .22;
    curseur.style.transform = `translate(${souris.cx.toFixed(1)}px, ${souris.cy.toFixed(1)}px)`;
    if (appui.actif) appui.p = Math.min(1, (now - appui.t0) / DUREE);
    else appui.p = Math.max(0, appui.p - .045);                                   // on lâche trop tôt : l'anneau se vide
    if (appui.p >= 1 && !appui.fini) { appui.fini = true; anneau.style.strokeDashoffset = 0; navigator.vibrate?.(18); briser(); return; }   // l'anneau est plein : la vitre cède dans la même image
    anneau.style.strokeDashoffset = (L * (1 - appui.p)).toFixed(2);              // (linéaire : ce qu'on voit est exactement le temps qui reste)
    if (appui.actif && PREP.pret && Math.hypot(souris.cx - PREP.x, souris.cy - PREP.y) > 40) preparer(souris.cx, souris.cy);   // on a bougé en appuyant
    decosVitre.forEach(d => { const k = +d.dataset.prof; d.style.transform = `translate3d(${(souris.nx * k * -40).toFixed(1)}px, ${(souris.ny * k * -30).toFixed(1)}px, 0)`; });
  };
  requestAnimationFrame(bouclePointeur);

  /* ─── la casse : une photo de la vitre, des fissures qui filent depuis le point d'appui, puis des éclats qui tombent ───
     Tout est dessiné dans une seule toile (canvas) : léger, et identique à la vitre au moment où elle cède. */
  function photographier(W, H, dpr) {
    const c = document.createElement('canvas'); c.width = W * dpr; c.height = H * dpr; const g = c.getContext('2d'); g.scale(dpr, dpr);
    g.fillStyle = getComputedStyle(vitre).backgroundColor; g.fillRect(0, 0, W, H);
    vitre.querySelectorAll('.deco img').forEach(img => {                       // les objets, à leur place et leur angle du moment
      if (!img.complete || !img.naturalWidth) return;
      const r = img.getBoundingClientRect(), m = new DOMMatrix(getComputedStyle(img).transform), a = Math.atan2(m.b, m.a), w = img.offsetWidth, h = img.offsetHeight;
      g.save(); g.translate(r.left + r.width / 2, r.top + r.height / 2); g.rotate(a); g.globalAlpha = +getComputedStyle(img.parentElement).opacity || 1; g.drawImage(img, -w / 2, -h / 2, w, h); g.restore();
    });
    vitre.querySelectorAll('.mot>i').forEach(i => {                            // les mots, sur leur ligne de base exacte
      const cs = getComputedStyle(i), mark = document.createElement('b'); mark.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
      i.appendChild(mark); const base = mark.getBoundingClientRect().top; mark.remove();
      const r = i.getBoundingClientRect();
      g.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`; g.fillStyle = cs.color; g.textBaseline = 'alphabetic';
      if ('letterSpacing' in g) g.letterSpacing = cs.letterSpacing === 'normal' ? '0px' : cs.letterSpacing;
      g.fillText(i.textContent, r.left, base);
    });
    return c;
  }
  /* la préparation (au moment où l'on appuie) : la photo de la vitre, la découpe en éclats, et chaque éclat déjà découpé
     dans sa petite image — pendant la chute, il ne reste qu'à les poser, image après image */
  const PREP = { pret: false };
  function preparer(x, y) {
    const W = innerWidth, H = innerHeight, dpr = Math.min(1.5, devicePixelRatio || 1), diag = Math.hypot(Math.max(x, W - x), Math.max(y, H - y)) * 1.15;
    const photo = PREP.photo && PREP.W === W && PREP.H === H ? PREP.photo : photographier(W, H, dpr);
    const hasard = (a, b) => a + Math.random() * (b - a);
    const NR = PETIT ? 10 : 13, angles = [], rayons = [0, hasard(38, 64), hasard(140, 220), hasard(310, 440), hasard(560, 760), diag];
    for (let i = 0; i < NR; i++) angles.push((i + hasard(-.32, .32)) / NR * Math.PI * 2);
    const V = angles.map(a => rayons.map((r, j) => { const rr = j === 0 ? 0 : j === rayons.length - 1 ? r : r * hasard(.86, 1.14), aa = a + (j ? hasard(-.06, .06) : 0); return [x + Math.cos(aa) * rr, y + Math.sin(aa) * rr]; }));
    const polys = [];
    for (let j = 0; j < rayons.length - 1; j++) for (let i = 0; i < NR; i++) {
      const i2 = (i + 1) % NR, a = V[i][j], b = V[i2][j], c = V[i2][j + 1], d = V[i][j + 1];
      if (j === 0) polys.push([a, c, d]);
      else if (Math.random() < .4 && j < rayons.length - 2) { polys.push([a, b, c]); polys.push([a, c, d]); }
      else polys.push([a, b, c, d]);
    }
    const eclats = [];
    polys.forEach(pts => {
      const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
      const x0 = Math.floor(Math.max(0, Math.min(...xs))), x1 = Math.ceil(Math.min(W, Math.max(...xs))), y0 = Math.floor(Math.max(0, Math.min(...ys))), y1 = Math.ceil(Math.min(H, Math.max(...ys)));
      if (x1 - x0 < 1 || y1 - y0 < 1) return;
      const sp = document.createElement('canvas'); sp.width = Math.ceil((x1 - x0) * dpr); sp.height = Math.ceil((y1 - y0) * dpr);
      const g = sp.getContext('2d'); g.scale(dpr, dpr); g.translate(-x0, -y0);
      g.beginPath(); pts.forEach((p, k) => k ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.clip();
      g.drawImage(photo, x0 * dpr, y0 * dpr, (x1 - x0) * dpr, (y1 - y0) * dpr, x0, y0, x1 - x0, y1 - y0);
      const cx = xs.reduce((s, v) => s + v, 0) / xs.length, cy = ys.reduce((s, v) => s + v, 0) / ys.length;
      const dx = cx - x, dy = cy - y, dist = Math.hypot(dx, dy) || 1, force = 360 + 1150 * Math.exp(-dist / 420);
      const chemin = new Path2D(); pts.forEach((p, k) => k ? chemin.lineTo(p[0] - cx, p[1] - cy) : chemin.moveTo(p[0] - cx, p[1] - cy)); chemin.closePath();
      eclats.push({ sp, chemin, cx, cy, ox: x0 - cx, oy: y0 - cy, w: x1 - x0, h: y1 - y0, vx: dx / dist * force * hasard(.7, 1.2), vy: dy / dist * force * hasard(.7, 1.2) - hasard(80, 380), g: hasard(2300, 3000),
        rx: hasard(-5, 5), ry: hasard(-5, 5), rz: hasard(-2.6, 2.6), retard: .14 + dist / 2800 + hasard(0, .05), pousse: hasard(2, 5), ux: dx / dist, uy: dy / dist, lum: hasard(-1, 1), fis: dist / 2800 * .5 });
    });
    Object.assign(PREP, { pret: true, x, y, W, H, dpr, photo, eclats });
  }
  function briser() {
    curseur.remove();
    if (CALME) { vitre.style.transition = 'opacity .6s'; vitre.style.opacity = 0; setTimeout(apresCasse, 50); setTimeout(() => { vitre.remove(); window.__pause3D = false; lancerVille(); }, 700); return; }
    if (!PREP.pret) preparer(souris.cx, souris.cy);
    const { W, H, dpr, eclats } = PREP;
    const cv = document.createElement('canvas'); cv.className = 'ac-casse'; cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    const g = cv.getContext('2d', { alpha: true });
    // à l'instant de la casse : le Mac et l'iPhone visibles se retournent tout de suite (ils étaient de dos derrière la vitre)
    window.__pause3D = false;
    page.querySelectorAll('.ac-modele').forEach(m => { const r = m.getBoundingClientRect(); if (r.top < innerHeight && r.bottom > 0) m.classList.add('vu'); });
    const t0 = performance.now();
    const image = now => {
      const t = Math.max(0, (now - t0) / 1000); let vivants = 0;
      g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cv.width, cv.height);
      for (const s of eclats) {
        const u = t - s.retard; let X, Y, rz = 0, kx = 1, ky = 1, o = 1;
        if (u < 0) { const k = Math.min(1, t / .1) * s.pousse; X = s.ux * k; Y = s.uy * k; }                   // la fissure : les morceaux s'écartent à peine
        else {
          X = s.ux * s.pousse + s.vx * u; Y = s.uy * s.pousse + s.vy * u + s.g * u * u / 2; rz = s.rz * u;
          kx = Math.cos(s.ry * u); ky = Math.cos(s.rx * u); o = 1 - Math.min(1, Math.max(0, (u - .45) / .65));   // il se retourne : il s'amincit, comme vu de profil
          if (o <= 0 || Y > H * 1.5) continue;
        }
        vivants++;
        const c = Math.cos(rz), sn = Math.sin(rz), a = c * kx * dpr, b = sn * kx * dpr, cc = -sn * ky * dpr, d = c * ky * dpr;
        g.setTransform(a, b, cc, d, (s.cx + X) * dpr, (s.cy + Y) * dpr); g.globalAlpha = o;
        g.drawImage(s.sp, s.ox, s.oy, s.w, s.h);
        if (u >= 0) { const l = s.lum * .5 + (1 - Math.abs(kx * ky)) * .9;                                            // le reflet du verre selon son angle
          g.fillStyle = l > 0 ? `rgba(255,255,255,${Math.min(.5, l * .42).toFixed(3)})` : `rgba(42,34,34,${Math.min(.16, -l * .12).toFixed(3)})`; g.fill(s.chemin); }
        const f = u < 0 ? Math.min(1, Math.max(0, (t - s.fis) * 16)) : 1;                                              // les fissures filent depuis le point d'appui
        g.lineWidth = 1.1 / Math.max(.35, Math.min(Math.abs(kx), Math.abs(ky))); g.strokeStyle = `rgba(255,255,255,${((u < 0 ? .95 : .55) * f).toFixed(3)})`; g.stroke(s.chemin);
      }
      g.globalAlpha = 1;
      if (vivants && t < 3) requestAnimationFrame(image);
      else { cv.remove(); setTimeout(lancerVille, 1200); }
    };
    image(t0);                                                                      // la première image tout de suite, à la place exacte de la vitre
    document.body.appendChild(cv); vitre.remove();
    page.animate([{ transform: 'scale(1.02)' }, { transform: 'none' }], { duration: 1400, easing: 'cubic-bezier(.16,1,.3,1)' });
    setTimeout(apresCasse, 240);
    requestAnimationFrame(image);
  }

  /* ─── la page : apparitions, objets qui flottent, modèles 3D, couches, Terre, chiffres ─── */
  function apresCasse() {
    document.body.classList.remove('vitre-ouverte');
    const obs = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target; el.classList.add('vu'); obs.unobserve(el);
      if (el.id === 'acCartes') setTimeout(() => el.classList.add('pret'), 1700);
      if (el.id === 'acChiffres') compter();
    }), { root: page, threshold: .16, rootMargin: '0px 0px -6% 0px' });
    page.querySelectorAll('[data-r], #acChiffres').forEach(el => obs.observe(el));
    // les modèles 3D et la Terre : créés un peu avant d'arriver à l'écran
    const bientot = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting) return; bientot.unobserve(e.target);
      if (e.target.id === 'acAbout') import('./globe.js').then(({ creerGlobe }) => creerGlobe($('acGlobe'), $('acBxl'), { petit: PETIT, sombre: document.documentElement.dataset.theme === 'sombre' }));
    }), { root: page, rootMargin: '60% 0px 60% 0px' });
    bientot.observe($('acAbout'));
    requestAnimationFrame(parallaxe);
  }

  // les objets suivent le défilement (chacun à sa profondeur) et un peu la souris ; ils tournent doucement en défilant
  const decos = [...page.querySelectorAll('.deco')];
  const parallaxe = () => {
    if (!page.classList.contains('part')) {
      const sc = page.scrollTop, vh = innerHeight;
      decos.forEach(d => {
        const k = +d.dataset.prof || .3, r = d.getBoundingClientRect(), c = (r.top + r.height / 2 - vh / 2) - (d._y || 0);
        d._y = (d._y || 0) + ((-c * k * .35) - (d._y || 0)) * .12;
        d._mx = (d._mx || 0) + ((souris.nx * k * -34) - (d._mx || 0)) * .08; d._my = (d._my || 0) + ((souris.ny * k * -24) - (d._my || 0)) * .08;
        d.style.transform = `translate3d(${d._mx.toFixed(1)}px, ${(d._y + d._my).toFixed(1)}px, 0) rotate(${(sc * k * .03).toFixed(2)}deg)`;
      });
    }
    requestAnimationFrame(parallaxe);
  };

  /* les couches : la carte à la hauteur de la souris remonte ; sur téléphone, elles se relaient toutes seules */
  const cartes = $('acCartes'), liste = [...cartes.querySelectorAll('.ac-carte')];
  const choisir = k => { cartes.classList.toggle('choix', k >= 0); liste.forEach((c, i) => { c.classList.toggle('haut', i === k); const e = Math.min(1.4, cartes.offsetWidth / 620); c.style.setProperty('--y', k < 0 ? '0px' : i < k ? `${(-80 - (k - i - 1) * 30) * e}px` : i === k ? `${-22 * e}px` : `${(48 + (i - k - 1) * 24) * e}px`); }); };   // la pile s'ouvre à ce niveau
  cartes.addEventListener('pointermove', e => {
    if (!cartes.classList.contains('pret') || e.pointerType === 'touch') return;
    const r = cartes.getBoundingClientRect(), y = (e.clientY - r.top) / r.height;
    const centres = liste.map(c => (c.offsetTop + c.offsetHeight * .5) / cartes.offsetHeight);   // (lu dans la mise en page : ordinateur ou téléphone)
    let k = 0; centres.forEach((c, i) => { if (Math.abs(y - c) < Math.abs(y - centres[k])) k = i; });
    choisir(k);
  });
  cartes.addEventListener('pointerleave', () => { liste.forEach(c => c.style.removeProperty('--y')); cartes.classList.remove('choix'); liste.forEach(c => c.classList.remove('haut')); });
  if (TACTILE) { let k = 0; setInterval(() => { if (cartes.classList.contains('pret') && !page.classList.contains('part')) choisir(k = (k + 1) % 3); }, 2600); }

  /* les chiffres : un compteur qui roule */
  // le vrai nombre de projets : tous ceux de src/projets.js (ceux que tu ajoutes dans l'admin), mis à jour tout seul
  const nb = PROJECTS.filter(p => p && (p.name || p.id)).length;
  $('acNbProjets').dataset.n = String(nb); $('acNbProjets').textContent = String(nb);
  const etiq = $('acNbProjets').previousElementSibling; if (etiq) etiq.textContent = nb > 1 ? 'Projects' : 'Project';
  document.querySelectorAll('.ac-chiffre b').forEach(b => {
    const n = b.dataset.n; b.textContent = '';
    [...n].forEach((ch, i) => { const col = document.createElement('span'); col.style.setProperty('--i', i); col.dataset.v = ch;
      col.innerHTML = Array.from({ length: 20 }, (_, k) => `<i>${k % 10}</i>`).join(''); b.appendChild(col); });
    b.setAttribute('aria-label', n);
  });
  function compter() {
    document.querySelectorAll('.ac-chiffre b span').forEach(col => { const v = +col.dataset.v; col.style.transform = `translateY(${-(10 + v) * 1.02}em)`; });
  }

  /* le bouton vers la carte : il suit un peu la souris (bouton « aimanté ») */
  const vers = $('acVersCarte'), zone = $('acZone');
  zone.addEventListener('pointermove', e => {
    const r = vers.getBoundingClientRect(), dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
    vers.style.transform = `translate(${(dx * .12).toFixed(1)}px, ${(dy * .18).toFixed(1)}px)`;
    const z = zone.getBoundingClientRect(); zone.style.setProperty('--mx', `${((e.clientX - z.left) / z.width - .5) * 40}%`); zone.style.setProperty('--my', `${((e.clientY - z.top) / z.height - .5) * 40}%`);
  });
  zone.addEventListener('pointerleave', () => { vers.style.transform = ''; });
  vers.addEventListener('click', allerCarte);
  // arrivé en bas de la page, on continue à défiler : la carte (plus tard, la roue des projets prendra cette place)
  let pousse = 0, tyA = null;
  const auBout = () => page.scrollTop + page.clientHeight >= page.scrollHeight - 4;
  page.addEventListener('wheel', e => { if (!window.__accueilOuvert || !auBout() || e.deltaY <= 0) { pousse = 0; return; } pousse += e.deltaY * (e.deltaMode === 1 ? 30 : 1); if (pousse > 420) { pousse = 0; allerCarte(); } }, { passive: true });
  page.addEventListener('touchstart', e => { tyA = e.touches[0].clientY; pousse = 0; }, { passive: true });
  page.addEventListener('touchmove', e => { if (tyA === null || !auBout()) return; pousse += tyA - e.touches[0].clientY; tyA = e.touches[0].clientY; if (pousse > 160) { pousse = 0; tyA = null; allerCarte(); } }, { passive: true });

  /* la barre de navigation : elle ramène à la page d'accueil, à la bonne section */
  const cible = { '#about': 'acAbout', '#service': 'acAdaptive', '#contact': 'acRoue' };
  document.querySelectorAll('.navbar a').forEach(a => a.addEventListener('click', e => {
    const id = cible[a.getAttribute('href')]; if (!id) return; e.preventDefault();
    if (!window.__accueilOuvert) retourAccueil();
    setTimeout(() => page.scrollTo({ top: $(id).offsetTop - 20, behavior: CALME ? 'auto' : 'smooth' }), window.__accueilOuvert ? 0 : 350);
  }));
}

/* ─── vers la carte : la page se couvre de nuages, puis les nuages s'écartent sur la ville (la caméra descend) ───
   Les nuages attendent si la ville n'est pas encore prête : ils servent d'écran de chargement. */
let enRoute = false;
function lancerVille() {                                            // la ville (lourde) commence à se charger : après la casse, ou tout de suite si on la demande
  if (window.__villeGo) return; window.__villeGo = true; dispatchEvent(new Event('ville-go'));
}
function allerCarte() {
  if (enRoute) return; enRoute = true; lancerVille();
  const cv = $('acNuages'), g = cv.getContext('2d'), SC = .5;
  const W = Math.ceil(innerWidth * SC), H = Math.ceil(innerHeight * SC); cv.width = W; cv.height = H; cv.classList.add('actif');
  const rgb = v => { const c = document.createElement('i'); c.style.color = v; document.body.appendChild(c); const m = getComputedStyle(c).color.match(/\d+/g).map(Number); c.remove(); return m; };
  const fond = rgb(getComputedStyle(document.documentElement).getPropertyValue('--ac-fond').trim() || '#eff6f8');
  const sombre = document.documentElement.dataset.theme === 'sombre';
  const clair = sombre ? fond.map(v => Math.min(255, v + 26)) : [255, 255, 255], ombre = sombre ? fond.map(v => Math.max(0, v - 14)) : [214, 228, 233];
  let sd = 7; const r01 = () => (sd = (sd * 16807) % 2147483647) / 2147483647;
  const puffs = []; for (let i = 0; i < 110; i++) { const a = r01() * Math.PI * 2, d = Math.pow(r01(), .7) * .75; puffs.push({ x: Math.cos(a) * d * 1.25, y: Math.sin(a) * d, r: .16 + r01() * .2, t: Math.min(.95, d * .9 + r01() * .25), k: r01() }); }
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`, lisse = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const dessiner = (ecart, base, entree) => {                     // ecart : 0 = nuages serrés, 1 = dispersés ; entree : les nuages arrivent (de l'extérieur)
    g.clearRect(0, 0, W, H);
    if (base > 0) { g.fillStyle = rgba(fond, base); g.fillRect(0, 0, W, H); }
    const cx = W / 2, cy = H / 2, M = Math.max(W, H);
    for (const b of puffs) {
      const l = entree !== undefined ? Math.max(0, 1 - lisse(b.t * .5, b.t * .5 + .5, entree)) : lisse(.08 + b.t * .6, .08 + b.t * .6 + .34, ecart), a = 1 - l; if (a <= .002) continue;
      const x = cx + b.x * M * (1 + l * 1.1), y = cy + b.y * M * (1 + l * 1.1), r = b.r * M * (1 + l * .7);
      const gr = g.createRadialGradient(x - r * .15, y - r * .2, r * .05, x, y, r), c1 = b.k < .5 ? clair : fond;
      gr.addColorStop(0, rgba(c1, a)); gr.addColorStop(.55, rgba(fond, a * .85)); gr.addColorStop(.8, rgba(ombre, a * .35)); gr.addColorStop(1, rgba(ombre, 0));
      g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    }
  };
  const ARRIVEE = CALME ? .2 : 1, DEPART = CALME ? .4 : 3.4, t0 = performance.now();
  let phase = 1, t1 = 0;
  const image = now => {
    if (phase === 1) {                                              // 1. les nuages arrivent et couvrent la page
      const k = Math.min(1, (now - t0) / 1000 / ARRIVEE);
      dessiner(0, lisse(.35, 1, k), k);
      if (k >= 1) {
        phase = 2; window.__accueilOuvert = false; page.classList.add('part', 'sec');
        document.body.classList.remove('accueil-ouvert'); dispatchEvent(new CustomEvent('couvre', { detail: false }));
      }
    } else if (phase === 2) {                                       // 2. on attend la ville (les nuages ondulent à peine)
      dessiner(Math.sin(now / 900) * .015 + .015, 1);
      if (window.__villePrete) { phase = 3; t1 = now; dispatchEvent(new CustomEvent('descente', { detail: DEPART })); }
    } else {                                                        // 3. ils s'écartent : la ville apparaît, vue de haut, puis la caméra descend
      const p = Math.min(1, (now - t1) / 1000 / DEPART);
      dessiner(p, 1 - lisse(.06, .55, p));
      if (p >= 1) { cv.classList.remove('actif'); page.classList.remove('sec'); enRoute = false; return; }
    }
    requestAnimationFrame(image);
  };
  requestAnimationFrame(image);
}
function retourAccueil() {
  window.__accueilOuvert = true; page.classList.remove('part');
  document.body.classList.add('accueil-ouvert');
  dispatchEvent(new CustomEvent('couvre', { detail: true }));
}

/* ─── le thème : auto (celui de l'ordinateur) → clair → sombre ─── */
(function theme() {
  const btn = $('themeBtn'); if (!btn) return;
  const NOMS = { auto: 'follows your computer', clair: 'light', sombre: 'dark' };
  const ordi = matchMedia('(prefers-color-scheme: dark)');
  const appliquer = mode => {
    const sombre = mode === 'sombre' || (mode === 'auto' && ordi.matches);
    document.documentElement.dataset.theme = sombre ? 'sombre' : 'clair'; document.documentElement.dataset.themeMode = mode;
    btn.dataset.mode = mode; btn.setAttribute('aria-label', 'Theme: ' + NOMS[mode]); btn.title = 'Theme: ' + NOMS[mode];
    dispatchEvent(new CustomEvent('theme', { detail: sombre }));
  };
  let mode = document.documentElement.dataset.themeMode || 'auto';
  appliquer(mode);
  btn.addEventListener('click', () => { mode = { auto: 'clair', clair: 'sombre', sombre: 'auto' }[mode]; try { localStorage.setItem('theme', mode); } catch (e) { /* rien */ } appliquer(mode); });
  ordi.addEventListener?.('change', () => { if (mode === 'auto') appliquer('auto'); });
})();
