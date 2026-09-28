/* ═════════════ Le projet en détail (« View more ») ═════════════
   Une grande carte en verre dépoli, par-dessus la ville. On y retrouve le projet tel qu'il a été
   composé dans la page admin : des blocs de texte et d'images/vidéos sur une grille de 3 colonnes,
   et le bandeau des outils utilisés (icônes en éventail qui se redressent au passage de la souris). */
import OUTILS from './outils.json';

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const paras = t => String(t || '').split(/\n\s*\n/).map(x => x.trim()).filter(Boolean).map(x => `<p>${esc(x).replace(/\n/g, '<br>')}</p>`).join('');
export const mediaHTML = (image, video, cls = '') => video
  ? `<video class="${cls}" src="${esc(video)}" poster="${esc(image || '')}" autoplay muted loop playsinline></video>`
  : image ? `<img class="${cls}" src="${esc(image)}" alt="">` : '';

const ROT = [-9, 6, -7, 8, -5, 7, -6, 9, -8, 5];
function outilsHTML(ids) {
  const byId = new Map(OUTILS.map(t => [t.id, t]));
  const list = (ids || []).map(id => byId.get(id) || { id, name: id, icon: '' });
  if (!list.length) return '';
  const tile = 124;   // taille maximale ; la largeur de la carte décide du reste (voir --t dans style.css)
  const tuile = (t, i) => `<div class="d-outil" style="--rest-rot:${ROT[i % ROT.length]}deg;--z:${i + 1}" data-nom="${esc(t.name)}"><div class="d-outil-tuile">${t.icon ? `<img src="${esc(t.icon)}" alt="${esc(t.name)}">` : `<span>${esc(t.name)}</span>`}</div></div>`;
  const moitie = list.length > 6 ? Math.ceil(list.length / 2) : list.length;   // sur téléphone, beaucoup d'outils → deux rangées égales
  const rangees = [list.slice(0, moitie), list.slice(moitie)].filter(r => r.length);
  let i = 0;
  return `<div class="d-outils"><div class="d-outils-lignes" style="--tile:${tile}px;--n:${list.length};--n2:${moitie}">${rangees.map(r => `<div class="d-outils-row">${r.map(t => tuile(t, i++)).join('')}</div>`).join('')}</div><div class="d-outil-nom"></div></div>`;
}
export function pageHTML(p) {
  const blocks = (p.page && p.page.length ? p.page : [{ type: 'outils' }]).map(b => {
    if (b.type === 'outils') return (p.tools || []).length ? `</div><section class="d-bloc-outils">${outilsHTML(p.tools)}</section><div class="d-grille">` : '';   // le bandeau des outils coupe la grille : il prend juste sa hauteur
    const w = Math.max(1, Math.min(3, b.w || 1)), h = p.grille === 2 ? Math.max(1, b.h || 4) : Math.max(1, b.h || 2) * 2,   // h en quarts de colonne (anciens projets : demi-colonnes)
       cs = Math.round(w * 4), c0 = b.centre && cs < 12 ? (12 - cs) / 2 + 1 : 'auto';   // 12 colonnes : un tiers = 4, une moitié = 6 ; un bloc centré commence au milieu de ce qui reste
    const st = `style="--cs:${cs};--c0:${c0};--h:${h};--ar:${(4 * w / h).toFixed(3)}"`;   // --ar : la forme du bloc, gardée sur mobile
    if (b.type === 'texte') return (b.titre || b.texte) ? `<section class="d-bloc d-texte" ${st}>${b.titre ? `<h3>${esc(b.titre)}</h3>` : ''}${paras(b.texte)}</section>` : '';
    if (b.type === 'media') return b.image || b.video ? `<figure class="d-bloc d-media" ${st}>${mediaHTML(b.image, b.video)}</figure>` : '';
    return '';
  }).join('');
  return `<header class="d-tete">
      <h2>${esc(p.name)}</h2>
      ${(p.tags || []).length ? `<div class="d-tags">${p.tags.map(t => `<span>${esc(t)}</span>`).join('')}</div>` : ''}
      ${p.role ? `<p class="d-role">${esc(p.role)}</p>` : ''}
      ${p.desc ? `<p class="d-desc">${esc(p.desc)}</p>` : ''}
    </header>
    <div class="d-grille">${blocks}</div>`.replace(/<div class="d-grille"><\/div>/g, '');
}

/* bandeau d'outils : chaque icône réagit à la distance du curseur (repris de portefolioV2) */
let raf = 0;
export function animerOutils(root) {
  cancelAnimationFrame(raf);
  const icons = [...root.querySelectorAll('.d-outil')], nom = root.querySelector('.d-outil-nom');
  if (!icons.length) return;
  const S = icons.map(el => ({ el, rest: parseFloat(el.style.getPropertyValue('--rest-rot')) || 0, x: 0, y: 0, r: 0, s: 1 }));
  icons.forEach(el => { el.onmouseenter = () => { if (nom) nom.textContent = el.dataset.nom; }; el.onmouseleave = () => { if (nom) nom.textContent = ''; }; });
  let mx = -9999, my = -9999;
  root.onmousemove = e => { mx = e.clientX; my = e.clientY; };
  const tick = () => {
    for (const s of S) {
      const b = s.el.getBoundingClientRect(), dx = mx - (b.left + b.width / 2), dy = my - (b.top + b.height / 2), d = Math.hypot(dx, dy), R = 140;
      let tx = 0, ty = 0, ts = 1, tr = 0;
      if (d < R) { const k = 1 - d / R, n = d || 1; tx = dx / n * k * 20; ty = dy / n * k * 20 - k * 22; ts = 1 + k * .26; tr = -s.rest * k; }
      s.x += (tx - s.x) * .16; s.y += (ty - s.y) * .16; s.s += (ts - s.s) * .16; s.r += (tr - s.r) * .2;
      s.el.style.setProperty('--tx', s.x.toFixed(2) + 'px'); s.el.style.setProperty('--ty', s.y.toFixed(2) + 'px');
      s.el.style.setProperty('--rot', s.r.toFixed(2) + 'deg'); s.el.style.setProperty('--scale', s.s.toFixed(3));
    }
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
}
export const arreterOutils = () => cancelAnimationFrame(raf);
