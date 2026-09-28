import { CATEGORIES, ICONES, svgIcone } from '../icones.js';
/* ═════════════ La page admin ═════════════
   Elle lit la liste des projets (src/projets.js) et la bibliothèque d'outils (src/outils.json),
   permet de tout modifier, puis réécrit ces fichiers quand on appuie sur « Enregistrer ».
   Les images et vidéos envoyées sont rangées dans public/medias/, les icônes d'outils dans public/outils/.
   L'aperçu est la vraie ville (l'image pré-rendue), en mode « vitrine » : tous les emplacements numérotés.
   Un emplacement = un bâtiment de l'image (public/city/emplacements.json, produit par tools/build_city.py). */
document.getElementById('nojs')?.remove();
const $ = id => document.getElementById(id);
const COLORS = ['#e0714d', '#d6809f', '#c8a858', '#569c8c', '#6084c8', '#8a6fb5', '#3f8f5a', '#c0392b', '#2c3e50'];
let peutEnregistrer = true, outilsModifies = false, accueilModifie = false, accueil = { ecrans: { mac: {}, iphone: {} } };
let projects = [], outils = [], sel = -1, dirty = false, catalogue = null, reloadT = 0, vitrineKey = '';

/* ─── petits outils ─── */
const hex = c => '#' + c.map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const nomDe = id => (catalogue && catalogue.find(c => c.id === id)?.nom) || (id ? id : 'Premier emplacement libre');
const ouEst = p => Array.isArray(p.uv) ? `Posé sur la carte (${Math.round(p.uv[0] * 100)} %, ${Math.round(p.uv[1] * 100)} %)` : nomDe(p.emplacement);
const slug = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'projet';
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html !== undefined) e.innerHTML = html; return e; };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
function toast(msg, bad = false, ms = 2600) { const t = $('toast'); t.textContent = msg; t.classList.toggle('bad', bad); t.classList.add('show'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), ms); }
function setDirty(v = true) { dirty = v; $('save').disabled = !v || !peutEnregistrer; $('save').textContent = v ? 'Enregistrer' : 'Enregistré ✓'; }
addEventListener('beforeunload', ev => { if (dirty) { ev.preventDefault(); ev.returnValue = ''; } });
const P = () => projects[sel];

/* ─── envoyer un fichier (image, vidéo, icône) : il est rangé dans le projet ─── */
function choisirFichier(accept) {
  return new Promise(ok => { const f = $('filePick'); f.value = ''; f.accept = accept; f.onchange = () => ok(f.files[0] || null); f.click(); });
}
async function envoyer(file, route = 'media') {
  if (!peutEnregistrer) { toast('L’envoi de fichiers demande que l’admin soit ouverte avec « Ouvrir l’admin.command ».', true, 5000); return null; }
  toast('Envoi de « ' + file.name + ' »…', false, 60000);
  try {
    const r = await fetch(`/__admin/${route}?nom=${encodeURIComponent(file.name)}`, { method: 'POST', body: file }), j = await r.json();
    if (!r.ok || !j.url) throw new Error(j.erreur || 'erreur');
    toast('Fichier ajouté.'); return j.url;
  } catch (e) { toast('Impossible d’envoyer le fichier : ' + e.message, true, 5000); return null; }
}
/* une photo de 6000 pixels et 25 Mo est bien trop lourde pour un site : avant l'envoi, on la ramène à 2400 pixels au plus,
   en WebP (ou JPEG / PNG si le navigateur ne sait pas faire de WebP). Les GIF et SVG sont envoyés tels quels. */
async function alleger(file) {
  if (!/^image\/(png|jpe?g|webp|bmp|heic|heif|avif)$/i.test(file.type)) return file;
  try {
    const img = await createImageBitmap(file), MAX = 2400, k = Math.min(1, MAX / Math.max(img.width, img.height));
    if (k === 1 && file.size < 900 * 1024) return file;                   // déjà légère
    const cv = document.createElement('canvas'); cv.width = Math.round(img.width * k); cv.height = Math.round(img.height * k);
    cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
    const enBlob = (type, q) => new Promise(ok => cv.toBlob(ok, type, q));
    let blob = await enBlob('image/webp', .86), ext = '.webp';
    if (!blob || blob.type !== 'image/webp') {                             // pas de WebP : JPEG pour une photo, PNG s'il y a de la transparence
      const px = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; let alpha = false;
      for (let i = 3; i < px.length; i += 4 * 97) if (px[i] < 250) { alpha = true; break; }
      blob = alpha ? await enBlob('image/png') : await enBlob('image/jpeg', .86); ext = alpha ? '.png' : '.jpg';
    }
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name.replace(/\.[^.]+$/, '') + ext, { type: blob.type });
  } catch (e) { return file; }
}
/* une zone « image + vidéo » réutilisable : pour la fiche, et pour chaque bloc image/vidéo */
function zoneMedia(obj, onChange, compact = false) {
  const box = el('div', 'media-zone' + (compact ? ' compact' : ''));
  const draw = () => {
    box.innerHTML = '';
    const vis = el('div', 'media-apercu');
    if (obj.video) vis.innerHTML = `<video src="${esc(obj.video)}" poster="${esc(obj.image || '')}" muted loop autoplay playsinline></video>` +
      (obj.image ? `<figure class="media-vignette" title="L’image affichée pendant le chargement de la vidéo"><img src="${esc(obj.image)}" alt=""><figcaption>Image</figcaption></figure>` : '');
    else if (obj.image) vis.innerHTML = `<img src="${esc(obj.image)}" alt="">`;
    else vis.innerHTML = `<span>Glisse une image ou une vidéo ici,<br>ou clique pour en choisir une</span>`;
    vis.onclick = async () => { const f = await choisirFichier('image/*,video/*'); if (f) prendre(f); };
    box.appendChild(vis);
    const bar = el('div', 'media-barre');
    const b = (txt, fn, cls = '') => { const x = el('button', 'mini ' + cls, txt); x.type = 'button'; x.onclick = ev => { ev.stopPropagation(); fn(); }; bar.appendChild(x); };
    if (obj.image) b(obj.video ? 'Changer l’image' : 'Changer', async () => { const f = await choisirFichier('image/*'); if (f) prendre(f, 'image'); });
    else if (obj.video) b('Ajouter l’image (obligatoire)', async () => { const f = await choisirFichier('image/*'); if (f) prendre(f, 'image'); }, 'alerte');
    if (obj.video) b('Retirer la vidéo', () => { delete obj.video; onChange(); draw(); });
    else if (obj.image) b('Ajouter une vidéo', async () => { const f = await choisirFichier('video/*'); if (f) prendre(f, 'video'); });
    if (obj.image && !obj.video) b('Retirer', () => { delete obj.image; onChange(); draw(); });
    if (bar.children.length) box.appendChild(bar);
    if (obj.video && !obj.image) box.appendChild(el('p', 'media-alerte', 'Avec une vidéo, une image est obligatoire.'));
  };
  const prendre = async (file, force) => {
    const kind = force || (file.type.startsWith('video') ? 'video' : 'image');
    if (kind === 'image') { toast('Préparation de l’image…', false, 30000); file = await alleger(file); }
    const url = await envoyer(file); if (!url) return;
    obj[kind] = url; onChange(); draw();
  };
  box.addEventListener('dragover', ev => { ev.preventDefault(); box.classList.add('survol'); });
  box.addEventListener('dragleave', () => box.classList.remove('survol'));
  box.addEventListener('drop', ev => { ev.preventDefault(); box.classList.remove('survol'); const f = ev.dataTransfer.files[0]; if (f && /^(image|video)\//.test(f.type)) prendre(f); });
  draw();
  return box;
}

/* ─── la liste des projets ─── */
function renderList() {
  const L = $('list'); L.innerHTML = '';
  $('count').textContent = projects.length ? `(${projects.length})` : '';
  projects.forEach((p, i) => {
    const li = el('li', 'item' + (i === sel ? ' on' : '')); li.tabIndex = 0;
    li.innerHTML = `<span class="dot"></span><span class="txt"><b></b><small></small></span><span class="mv"><button type="button" aria-label="Monter">▲</button><button type="button" aria-label="Descendre">▼</button></span>`;
    li.querySelector('.dot').style.background = p.image ? `center/cover url("${p.image}")` : hex(p.hue);
    li.querySelector('b').textContent = p.name || 'Sans nom';
    li.querySelector('small').textContent = ouEst(p);
    const [up, down] = li.querySelectorAll('.mv button'); up.disabled = i === 0; down.disabled = i === projects.length - 1;
    up.onclick = ev => { ev.stopPropagation(); move(i, -1); }; down.onclick = ev => { ev.stopPropagation(); move(i, 1); };
    li.onclick = () => select(i); li.onkeydown = ev => { if (ev.key === 'Enter') select(i); };
    L.appendChild(li);
  });
  $('empty').hidden = projects.length > 0; $('form').hidden = sel < 0;
}
function move(i, d) { const j = i + d; [projects[i], projects[j]] = [projects[j], projects[i]]; if (sel === i) sel = j; else if (sel === j) sel = i; setDirty(); renderList(); }
function select(i) { sel = i; renderList(); fillForm(); }
function add() {
  toast('Clique sur la carte, en bas, pour poser le nouveau projet où tu veux.', false, 4500);
  projects.push({ id: '', name: 'New project', emplacement: '', uv: [.5, .6], hue: rgb(COLORS[projects.length % COLORS.length]), role: '', tags: [], desc: '', tools: [],
    grille: 2, page: [{ type: 'texte', w: 2, h: 4, titre: '', texte: '' }, { type: 'media', w: 1, h: 4 }, { type: 'outils' }] });
  setDirty(); select(projects.length - 1); $('f-name').select(); $('f-name').focus();
}

/* ─── 1. le projet ─── */
function fillForm() {
  const p = P(); if (!p) return;
  if (!p.tags) p.tags = p.tag ? [p.tag] : []; delete p.tag;
  if (!p.page) p.page = [{ type: 'outils' }];
  if (!p.page.some(b => b.type === 'outils')) p.page.push({ type: 'outils' });
  $('f-name').value = p.name; $('f-role').value = p.role || ''; $('f-desc').value = p.desc || '';
  countDesc(); renderTags(); renderSwatches(); renderIcones(); renderStatut(); renderBatiments();
  $('cardMedia').innerHTML = ''; $('cardMedia').appendChild(zoneMedia(p, () => { setDirty(); renderList(); }));
  $('chosen').textContent = ouEst(p);
  $('del-confirm').hidden = true; $('del').hidden = false;
  renderGrille(); showVitrine();
}
const bind = (id, key) => $(id).addEventListener('input', () => { const p = P(); if (!p) return; p[key] = $(id).value; setDirty(); if (key === 'name') renderList(); if (key === 'desc') countDesc(); });
bind('f-name', 'name'); bind('f-role', 'role'); bind('f-desc', 'desc');
function countDesc() { $('desc-count').textContent = `${$('f-desc').value.length} / 280`; }
function renderTags() {
  const box = $('tags'), inp = $('f-tag'); box.querySelectorAll('.chip').forEach(c => c.remove());
  P().tags.forEach((t, k) => {
    const c = el('span', 'chip'); c.textContent = t;
    const x = el('button', '', '×'); x.type = 'button'; x.setAttribute('aria-label', 'Retirer ' + t);
    x.onclick = () => { P().tags.splice(k, 1); setDirty(); renderTags(); };
    c.appendChild(x); box.insertBefore(c, inp);
  });
}
$('f-tag').addEventListener('keydown', ev => {
  const v = $('f-tag').value.trim();
  if ((ev.key === 'Enter' || ev.key === ',') && v) { ev.preventDefault(); P().tags.push(v); $('f-tag').value = ''; setDirty(); renderTags(); }
  else if (ev.key === 'Enter') ev.preventDefault();
  else if (ev.key === 'Backspace' && !v && P().tags.length) { P().tags.pop(); setDirty(); renderTags(); }
});
$('form').addEventListener('submit', ev => ev.preventDefault());

/* ─── 2. le bâtiment : menu déroulant + aperçu 3D ─── */
function renderBatiments() {
  const s = $('f-bat'); if (!catalogue) return;
  s.innerHTML = catalogue.map((c, k) => {
    const other = projects.find((q, i) => i !== sel && q.emplacement === c.id);
    return `<option value="${c.id}">${k + 1}. ${esc(c.nom)}${other ? ' — déjà pris par « ' + esc(other.name) + ' »' : ''}</option>`; }).join('')
    + (Array.isArray(P().uv) ? '<option value="__libre">★ Position libre (posée sur la carte)</option>' : '');
  s.value = Array.isArray(P().uv) ? '__libre' : (P().emplacement || '');
}
$('f-bat').addEventListener('change', () => { if ($('f-bat').value !== '__libre') chooseBuilding($('f-bat').value); });
function renderSwatches() {
  const box = $('swatches'), cur = hex(P().hue); box.innerHTML = '';
  COLORS.forEach(c => { const b = el('button', 'sw' + (c === cur ? ' on' : '')); b.type = 'button'; b.style.background = c; b.setAttribute('aria-label', 'Couleur ' + c); b.onclick = () => setColor(c); box.appendChild(b); });
  const l = el('label', '', '<input type="color"> autre'), ci = l.querySelector('input'); ci.value = cur;
  ci.addEventListener('input', () => setColor(ci.value)); box.appendChild(l);
}
function setColor(c) { P().hue = rgb(c); setDirty(); renderSwatches(); renderList(); showVitrine(); }

/* l'icône du projet (sur sa pastille) : un menu déroulant avec la bibliothèque d'icônes, le numéro, ou une image perso */
const estImage = s => typeof s === 'string' && /^(\/|https?:|data:)/.test(s);
function apercuIcone(ic) {
  if (!ic) return ['<span class="ic-num">N°</span>', 'Numéro du projet'];
  if (ic.startsWith('ic:') && ICONES[ic.slice(3)]) return [svgIcone(ic.slice(3), 22), ICONES[ic.slice(3)].nom];
  if (estImage(ic)) return [`<img src="${esc(ic)}" alt="">`, 'Image perso'];
  return [`<span class="ic-num">${esc(ic)}</span>`, 'Texte'];
}
function renderIcones() {
  const box = $('icones'), cur = P().icone || ''; box.innerHTML = '';
  const [vis, nom] = apercuIcone(cur);
  const bt = el('button', 'ic-choix', `<span class="ic-rond">${vis}</span><span class="ic-nom">${esc(nom)}</span><span class="ic-fleche">▾</span>`); bt.type = 'button';
  const pan = el('div', 'ic-menu'); pan.hidden = true;
  const q = el('input', 'ic-cherche'); q.placeholder = 'Chercher : web, santé, musique…'; pan.appendChild(q);
  const liste = el('div', 'ic-liste'); pan.appendChild(liste);
  const item = (val, html, label) => { const b = el('button', 'ic-item' + (val === cur ? ' on' : ''), `<span class="ic-rond">${html}</span><span>${esc(label)}</span>`); b.type = 'button'; b.dataset.q = label.toLowerCase(); b.onclick = () => { pan.hidden = true; setIcone(val); }; return b; };
  const dessine = () => {
    const f = q.value.trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); liste.innerHTML = '';
    if (!f) {
      const g0 = el('div', 'ic-groupe'); g0.appendChild(el('h4', '', 'Par défaut'));
      const gr0 = el('div', 'ic-grille'); gr0.appendChild(item('', '<span class="ic-num">N°</span>', 'Numéro du projet'));
      const im = item('__image', '<span class="ic-num">⤒</span>', 'Image perso…'); im.onclick = async () => { pan.hidden = true; const fl = await choisirFichier('image/*'); if (!fl) return; const url = await envoyer(await alleger(fl)); if (url) setIcone(url); };
      gr0.appendChild(im); g0.appendChild(gr0); liste.appendChild(g0);
    }
    for (const [cat, icones] of CATEGORIES) {
      const ok = icones.filter(([id, n]) => !f || (n + ' ' + id + ' ' + cat).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').includes(f));
      if (!ok.length) continue;
      const gp = el('div', 'ic-groupe'); gp.appendChild(el('h4', '', esc(cat)));
      const gr = el('div', 'ic-grille'); ok.forEach(([id, n]) => gr.appendChild(item('ic:' + id, svgIcone(id, 22), n))); gp.appendChild(gr); liste.appendChild(gp);
    }
    if (!liste.children.length) liste.appendChild(el('p', 'ic-vide', 'Aucune icône ne correspond.'));
  };
  q.addEventListener('input', dessine); dessine();
  bt.onclick = () => { pan.hidden = !pan.hidden; if (!pan.hidden) { q.value = ''; dessine(); setTimeout(() => q.focus(), 30); } };
  document.addEventListener('pointerdown', ev => { if (!box.contains(ev.target)) pan.hidden = true; });
  box.appendChild(bt); box.appendChild(pan);
}
function setIcone(ic) { const p = P(); if (ic) p.icone = ic; else delete p.icone; setDirty(); renderIcones(); showVitrine(); }

/* le statut (en surimpression sur l'image de la fiche) et l'avancement (barre, pour les projets en cours) */
const STATUTS = ['In progress', 'Completed', 'On hold', 'Coming soon'];
const VERS_EN = { 'en cours': 'In progress', 'terminé': 'Completed', 'en pause': 'On hold', 'bientôt': 'Coming soon' };   // anciens statuts en français
function renderStatut() {
  const p = P(); if (p.statut && VERS_EN[p.statut.toLowerCase()]) p.statut = VERS_EN[p.statut.toLowerCase()];
  const st = p.statut || '', autre = st && !STATUTS.includes(st);
  $('f-statut').value = autre ? '__autre' : st;
  $('f-statut-autre').hidden = !autre; $('f-statut-autre').value = autre ? st : '';
  const enCours = /in progress/i.test(st); $('prog-champ').hidden = !enCours;
  const v = Number.isFinite(Number(p.progression)) && p.progression !== undefined ? Number(p.progression) : 50;
  $('f-prog').value = v; $('f-prog-val').textContent = v + ' %';
}
$('f-statut').addEventListener('change', () => {
  const p = P(), v = $('f-statut').value;
  if (v === '__autre') { p.statut = $('f-statut-autre').value.trim() || 'New'; }
  else if (v) p.statut = v; else delete p.statut;
  if (/in progress/i.test(p.statut || '') && p.progression === undefined) p.progression = 50;
  setDirty(); renderStatut(); if (v === '__autre') $('f-statut-autre').focus();
});
$('f-statut-autre').addEventListener('input', () => { const p = P(); p.statut = $('f-statut-autre').value.trim() || 'New'; setDirty(); });
$('f-prog').addEventListener('input', () => { const p = P(); p.progression = Number($('f-prog').value); $('f-prog-val').textContent = p.progression + ' %'; setDirty(); });
function chooseBuilding(id) {
  const p = P(); if (!p || !catalogue) return;
  const other = projects.find((q, i) => i !== sel && q.emplacement === id);
  if (other) { other.emplacement = p.emplacement || ''; toast(`« ${other.name} » avait cet emplacement : les deux projets échangent leur place.`, false, 4200); }
  delete p.uv; p.emplacement = id; setDirty(); renderList(); renderBatiments(); $('chosen').textContent = nomDe(id); showVitrine();
}
function showVitrine() {                                       // l'aperçu se recharge (après une petite pause) quand le bâtiment ou la couleur changent
  const p = P(), fr = $('vitrine'); if (!p) return;
  const key = (Array.isArray(p.uv) ? 'uv' + p.uv.join(',') : (p.emplacement || '')) + '|' + hex(p.hue) + '|' + (p.icone || '');
  if (key === vitrineKey) return;
  const onlyMove = vitrineKey && vitrineKey.split('|')[1] === hex(p.hue) && (vitrineKey.split('|')[2] || '') === (p.icone || '');
  if (onlyMove && !Array.isArray(p.uv) && !vitrineKey.startsWith('uv')) { fr.contentWindow?.postMessage({ type: 'vitrine:voir', id: p.emplacement }, '*'); vitrineKey = key; return; }
  clearTimeout(reloadT);
  reloadT = setTimeout(() => { vitrineKey = key; $('vload').hidden = false; fr.src = `/?v=${Date.now()}#vitrine&sel=libre&nom=${encodeURIComponent(p.name || '')}&acc=${hex(p.hue).slice(1)}${p.icone ? '&ic=' + encodeURIComponent(p.icone) : ''}${Array.isArray(p.uv) ? '&uv=' + p.uv.join(',') : ''}`; }, 400);
}
addEventListener('message', ev => {
  const m = ev.data || {};
  if (m.type === 'vitrine:pret') $('vload').hidden = true;
  if (m.type === 'vitrine:choix' && sel >= 0 && m.id !== 'libre' && (m.id !== P().emplacement || Array.isArray(P().uv))) chooseBuilding(m.id);
  if (m.type === 'vitrine:pose' && sel >= 0 && Array.isArray(m.uv)) {                // posé à la main sur la carte
    const p = P(); p.uv = m.uv; p.emplacement = '';
    vitrineKey = 'uv' + p.uv.join(',') + '|' + hex(p.hue) + '|' + (p.icone || '');                          // l'aperçu a déjà déplacé la pastille : pas de rechargement
    setDirty(); renderList(); renderBatiments(); $('chosen').textContent = ouEst(p);
  }
});

/* ─── 3. le projet dans sa globalité : blocs sur une grille de 3 colonnes ───
   Chaque bloc a une largeur w (1 à 3 colonnes) et une hauteur h (en quarts de colonne : h = 4 fait un carré ; grille v2).
   On déplace un bloc en le tirant par sa poignée ⠿ ; on change sa taille par un coin du bas.
   Le bloc « outils » fait toute la largeur et une seule hauteur : on peut seulement le déplacer. */
const grille = $('grille');
function renderGrille() {
  const p = P(); grille.innerHTML = '';
  p.page.forEach((b, i) => grille.appendChild(blocEl(b, i)));
}
function blocEl(b, i) {
  const out = b.type === 'outils';
  const e = el('div', 'g-bloc g-' + b.type); e.dataset.i = i;
  if (!out) { b.w = LARG.reduce((a, v) => Math.abs(v - (b.w || 1)) < Math.abs(a - (b.w || 1)) ? v : a, 1); b.h = Math.max(1, Math.min(24, b.h || 4)); placer(e, b); }
  const tools = el('div', 'g-outils-bloc');
  const poignee = el('button', 'g-poignee', '⠿'); poignee.type = 'button'; poignee.title = 'Déplacer'; poignee.setAttribute('aria-label', 'Déplacer ce bloc');
  tools.appendChild(poignee);
  if (!out) {
    const droite = el('span', 'g-droite');
    const c = el('button', 'g-centrer', '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2v16M4 6h12M6 10h8M4 14h12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'); c.type = 'button';
    c.title = 'Centrer ce bloc sur sa ligne'; c.setAttribute('aria-pressed', b.centre ? 'true' : 'false');
    c.onclick = () => { b.centre = !b.centre; if (!b.centre) delete b.centre; setDirty(); renderGrille(); };
    const x = el('button', 'g-suppr', '×'); x.type = 'button'; x.title = 'Supprimer ce bloc'; x.onclick = () => { P().page.splice(i, 1); setDirty(); renderGrille(); };
    droite.append(c, x); tools.appendChild(droite);
  }
  e.appendChild(tools);
  poignee.addEventListener('pointerdown', ev => deplacer(ev, e, i));
  poignee.addEventListener('keydown', ev => {                    // au clavier : flèches haut / bas
    if (ev.key === 'ArrowUp' || ev.key === 'ArrowLeft') { ev.preventDefault(); if (i > 0) { const pg = P().page; [pg[i - 1], pg[i]] = [pg[i], pg[i - 1]]; setDirty(); renderGrille(); grille.children[i - 1].querySelector('.g-poignee').focus(); } }
    if (ev.key === 'ArrowDown' || ev.key === 'ArrowRight') { ev.preventDefault(); const pg = P().page; if (i < pg.length - 1) { [pg[i + 1], pg[i]] = [pg[i], pg[i + 1]]; setDirty(); renderGrille(); grille.children[i + 1].querySelector('.g-poignee').focus(); } }
  });
  if (b.type === 'texte') {
    const t = el('input', 'g-titre'); t.placeholder = 'Titre (facultatif)'; t.value = b.titre || ''; t.oninput = () => { b.titre = t.value; setDirty(); };
    const x = el('textarea', 'g-txt'); x.placeholder = 'Écris ton texte ici. Une ligne vide sépare deux paragraphes.'; x.value = b.texte || '';
    const cpt = el('div', 'g-compte');
    const compter = () => {                                              // « 312 / 480 caractères » ; en rouge si le texte ne tient plus sans défiler
      const n = (b.texte || '').length, max = capacite(b), ok = tient(b, b.titre, paras(b.texte));
      cpt.textContent = `${n} / ${max} caractères` + (ok ? '' : ' · trop long : une barre de défilement apparaîtra');
      cpt.classList.toggle('trop', !ok);
    };
    let tc = 0; const plusTard = () => { clearTimeout(tc); tc = setTimeout(compter, 120); };
    x.oninput = () => { b.texte = x.value; setDirty(); plusTard(); };
    t.addEventListener('input', plusTard);
    e.compter = plusTard;
    e.append(t, x, cpt); document.fonts.ready.then(() => setTimeout(compter, 0));   // on attend les vraies polices pour mesurer juste
  } else if (b.type === 'media') {
    e.appendChild(zoneMedia(b, () => setDirty(), true));
  } else if (out) {
    e.appendChild(outilsEditeur());
  }
  if (!out) for (const cote of ['g', 'd']) {                    // les deux coins du bas pour changer la taille
    const c = el('div', 'g-coin g-coin-' + cote); c.title = 'Changer la taille';
    c.addEventListener('pointerdown', ev => redimensionner(ev, e, b, cote));
    e.appendChild(c);
  }
  return e;
}
/* les largeurs possibles, en tiers de la grille : 1/3, 1/2, 2/3, toute la largeur (la grille a 12 colonnes : un tiers = 4, une moitié = 6) */
const LARG = [1, 1.5, 2, 3];
function placer(e, b) {
  const sp = Math.round(b.w * 4);
  e.style.gridColumn = b.centre && sp < 12 ? `${(12 - sp) / 2 + 1} / span ${sp}` : `span ${sp}`;
  e.style.gridRow = `span ${b.h}`;
  e.classList.toggle('centre', !!b.centre && sp < 12);
}
const unites = () => {                                             // taille d'une colonne et d'une demi-rangée, en pixels
  const cs = getComputedStyle(grille), gap = parseFloat(cs.columnGap) || 14, W = grille.clientWidth, col = (W - 2 * gap) / 3;
  return { col: col + gap, row: ((col - gap) / 2 - gap) / 2 + gap };      // 4 rangées par colonne (deux fois plus fin qu'avant)
};
function redimensionner(ev, e, b, cote) {
  ev.preventDefault(); ev.stopPropagation();
  const u = unites(), x0 = ev.clientX, y0 = ev.clientY, w0 = b.w, h0 = b.h;
  e.classList.add('actif'); document.body.classList.add('redim'); grille.classList.add('guides');
  const mv = m => {
    const dx = (m.clientX - x0) * (cote === 'g' ? -1 : 1), dy = m.clientY - y0;
    const brut = w0 + dx / u.col * (b.centre ? 2 : 1), w = LARG.reduce((a, v) => Math.abs(v - brut) < Math.abs(a - brut) ? v : a, 1), h = Math.max(1, Math.min(24, h0 + Math.round(dy / u.row)));
    if (w !== b.w || h !== b.h) { b.w = w; b.h = h; placer(e, b); setDirty(); e.compter?.(); }
  };
  const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up); e.classList.remove('actif'); document.body.classList.remove('redim'); grille.classList.remove('guides'); };
  addEventListener('pointermove', mv); addEventListener('pointerup', up);
}
function deplacer(ev, e, i) {                                      // on tire le bloc : il s'insère avant ou après le bloc survolé
  ev.preventDefault();
  const pg = P().page, fant = e.cloneNode(true), r = e.getBoundingClientRect(), dx = ev.clientX - r.left, dy = ev.clientY - r.top;
  fant.className += ' fantome'; Object.assign(fant.style, { width: r.width + 'px', height: r.height + 'px', left: r.left + 'px', top: r.top + 'px' });
  document.body.appendChild(fant); e.classList.add('deplace');
  let cible = null;
  const mv = m => {
    fant.style.left = (m.clientX - dx) + 'px'; fant.style.top = (m.clientY - dy) + 'px';
    grille.querySelectorAll('.g-bloc').forEach(x => x.classList.remove('avant', 'apres'));
    fant.style.display = 'none'; const sous = document.elementFromPoint(m.clientX, m.clientY)?.closest('.g-bloc'); fant.style.display = '';
    if (sous && sous !== e && grille.contains(sous)) {
      const b = sous.getBoundingClientRect(), apres = sous.classList.contains('g-outils') || b.width > b.height * 1.6 ? m.clientY > b.top + b.height / 2 : (m.clientX > b.left + b.width / 2);
      cible = { j: +sous.dataset.i, apres }; sous.classList.add(apres ? 'apres' : 'avant');
    } else cible = null;
    const g = grille.getBoundingClientRect(); if (m.clientY > innerHeight - 60) scrollBy(0, 18); if (m.clientY < 60) scrollBy(0, -18); void g;
  };
  const up = () => {
    removeEventListener('pointermove', mv); removeEventListener('pointerup', up); fant.remove(); e.classList.remove('deplace');
    if (cible) { const [b] = pg.splice(i, 1); let j = cible.j + (cible.apres ? 1 : 0); if (j > i) j--; pg.splice(j, 0, b); setDirty(); }
    renderGrille();
  };
  addEventListener('pointermove', mv); addEventListener('pointerup', up);
}
$('addTexte').onclick = () => { P().page.push({ type: 'texte', w: 1.5, h: 4, titre: '', texte: '' }); setDirty(); renderGrille(); grille.lastElementChild.scrollIntoView({ behavior: 'smooth', block: 'center' }); };
$('addMedia').onclick = () => { P().page.push({ type: 'media', w: 1.5, h: 4 }); setDirty(); renderGrille(); grille.lastElementChild.scrollIntoView({ behavior: 'smooth', block: 'center' }); };

/* combien de caractères tiennent dans un bloc de texte sans barre de défilement ?
   On le mesure vraiment : une copie invisible du bloc, à la taille qu'il a sur le site (carte de 1055 px de large : le texte
   grandit avec la carte, donc c'est vrai sur tous les écrans d'ordinateur), avec les mêmes polices et les mêmes marges. */
const REF = 1055, GAP = 16;
const tailleBloc = b => { const c = (REF - 11 * GAP) / 12, sp = Math.round(b.w * 4), R = (((REF - 2 * GAP) / 3 - GAP) / 2 - GAP) / 2; return [sp * c + (sp - 1) * GAP, b.h * R + (b.h - 1) * GAP]; };
let banc = null;
function bancDeMesure() {
  if (banc) return banc;
  banc = el('div', 'banc'); banc.setAttribute('aria-hidden', 'true'); document.body.appendChild(banc); return banc;
}
const paras = t => String(t || '').split(/\n\s*\n/).map(x => x.trim()).filter(Boolean).map(x => `<p>${esc(x).replace(/\n/g, '<br>')}</p>`).join('');
const FILLER = 'Le projet est né d’une idée simple : rendre les choses plus claires pour celles et ceux qui les utilisent chaque jour. ';
function tient(b, titre, html) { const B = bancDeMesure(), [w, h] = tailleBloc(b); B.style.width = w + 'px'; B.style.height = h + 'px'; B.innerHTML = (titre ? `<h3>${esc(titre)}</h3>` : '') + html; return B.scrollHeight <= B.clientHeight + 1; }
function capacite(b) {                                                   // le nombre de caractères d'un texte ordinaire qui tiennent (recherche par dichotomie)
  let lo = 0, hi = 4000;
  const txt = n => FILLER.repeat(Math.ceil(n / FILLER.length) + 1).slice(0, n);
  while (lo < hi) { const m = Math.ceil((lo + hi) / 2); if (tient(b, b.titre, `<p>${txt(m)}</p>`)) lo = m; else hi = m - 1; }
  return lo;
}
/* ─── le bloc « outils utilisés » : les outils cochés, choisis dans la bibliothèque ─── */
function outilsEditeur() {
  const box = el('div', 'o-edit'), p = P();
  const draw = () => {
    box.innerHTML = '<h4>Outils utilisés</h4>';
    const row = el('div', 'o-choisis');
    (p.tools || []).forEach(id => {
      const t = outils.find(o => o.id === id) || { id, name: id };
      const c = el('span', 'o-puce', `${t.icon ? `<img src="${esc(t.icon)}" alt="">` : ''}${esc(t.name)}`);
      const x = el('button', '', '×'); x.type = 'button'; x.onclick = () => { p.tools = p.tools.filter(v => v !== id); setDirty(); draw(); };
      c.appendChild(x); row.appendChild(c);
    });
    const plus = el('button', 'mini', p.tools?.length ? 'Modifier' : 'Choisir les outils'); plus.type = 'button';
    plus.onclick = () => ouvrirChoix(); row.appendChild(plus);
    box.appendChild(row);
  };
  const ouvrirChoix = () => {
    const pan = el('div', 'o-choix');
    pan.innerHTML = '<input class="o-cherche" type="search" placeholder="Chercher un outil (ex. Kotlin)"><div class="o-liste"></div><div class="o-nouveau"><input placeholder="Nom d’un nouvel outil"><button type="button" class="mini">Choisir son icône et l’ajouter</button></div><button type="button" class="btn o-ok">Terminé</button>';
    const liste = pan.querySelector('.o-liste'), cases = [];
    const cats = [...new Set(outils.map(t => t.cat || 'Autres'))];
    cats.forEach(cat => {                                            // une rubrique par famille d'outils
      const sec = el('section', 'o-rubrique', `<h5>${esc(cat)}</h5>`), g = el('div', 'o-grille');
      outils.filter(t => (t.cat || 'Autres') === cat).forEach(t => {
        const on = (p.tools || []).includes(t.id);
        const b = el('button', 'o-case' + (on ? ' on' : ''), `${t.icon ? `<img src="${esc(t.icon)}" alt="">` : ''}<span>${esc(t.name)}</span>`); b.type = 'button';
        b.onclick = () => { p.tools = p.tools || []; if (p.tools.includes(t.id)) p.tools = p.tools.filter(v => v !== t.id); else p.tools.push(t.id); b.classList.toggle('on'); setDirty(); };
        b.dataset.nom = (t.name + ' ' + t.id).toLowerCase(); cases.push(b); g.appendChild(b);
      });
      sec.appendChild(g); liste.appendChild(sec);
    });
    const cherche = pan.querySelector('.o-cherche');
    cherche.oninput = () => {
      const q = cherche.value.trim().toLowerCase();
      cases.forEach(b => { b.hidden = !!q && !b.dataset.nom.includes(q); });
      liste.querySelectorAll('.o-rubrique').forEach(r => { r.hidden = ![...r.querySelectorAll('.o-case')].some(b => !b.hidden); });
    };
    setTimeout(() => cherche.focus(), 30);
    const nom = pan.querySelector('.o-nouveau input');
    pan.querySelector('.o-nouveau button').onclick = async () => {
      const n = nom.value.trim(); if (!n) { toast('Donne d’abord un nom à l’outil.', true); nom.focus(); return; }
      const f = await choisirFichier('image/svg+xml,image/png,image/jpeg,image/webp'); if (!f) return;
      const url = await envoyer(f, 'outil-icone'); if (!url) return;
      let id = slug(n), k = 2; while (outils.some(o => o.id === id)) id = slug(n) + '-' + k++;
      outils.push({ id, name: n, icon: url, cat: 'Autres' }); outilsModifies = true; p.tools = [...(p.tools || []), id]; setDirty(); pan.remove(); draw(); ouvrirChoix();
    };
    pan.querySelector('.o-ok').onclick = () => { pan.remove(); draw(); };
    box.appendChild(pan);
  };
  draw();
  return box;
}

/* ─── supprimer ─── */
$('del').onclick = () => { $('del').hidden = true; $('del-confirm').hidden = false; };
$('del-no').onclick = () => { $('del').hidden = false; $('del-confirm').hidden = true; };
$('del-yes').onclick = () => { const n = P().name; projects.splice(sel, 1); sel = Math.min(sel, projects.length - 1); setDirty(); renderList(); if (sel >= 0) fillForm(); toast(`« ${n} » supprimé. Pense à enregistrer.`); };

/* ─── enregistrer, mettre en ligne ─── */
async function save() {
  const bad = projects.findIndex(p => !p.name.trim());
  if (bad >= 0) { select(bad); toast('Ce projet n’a pas de titre.', true); $('f-name').focus(); return false; }
  const sansImage = projects.findIndex(p => (p.video && !p.image) || (p.page || []).some(b => b.video && !b.image));
  if (sansImage >= 0) { select(sansImage); toast('Une vidéo n’a pas d’image : ajoute l’image obligatoire avant d’enregistrer.', true, 5000); return false; }
  if (Object.values(accueil.ecrans || {}).some(e => e.video && !e.image)) { toast('Un écran de la page d’accueil a une vidéo sans image : ajoute son image avant d’enregistrer.', true, 5000); return false; }
  const ids = new Set();
  projects.forEach(p => { p.name = p.name.trim(); if (!p.id) { let id = slug(p.name), k = 2; while (ids.has(id) || projects.some(q => q !== p && q.id === id)) id = slug(p.name) + '-' + k++; p.id = id; } ids.add(p.id); });
  try {
    if (outilsModifies) { const r0 = await fetch('/__admin/outils', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(outils) }); if (!r0.ok) throw new Error('outils'); outilsModifies = false; }
    if (accueilModifie) { const r1 = await fetch('/__admin/accueil', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(accueil) }); if (!r1.ok) throw new Error('écrans de la page d’accueil'); accueilModifie = false; }
    const r = await fetch('/__admin/projets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(projects) });
    const j = await r.json(); if (!r.ok) throw new Error(j.erreur || 'erreur');
    setDirty(false); toast('Enregistré ! Le site sur ton ordinateur est à jour.'); return true;
  } catch (e) { toast('Impossible d’enregistrer : ' + e.message, true, 5000); return false; }
}
$('save').onclick = save;
addEventListener('keydown', ev => { if ((ev.metaKey || ev.ctrlKey) && ev.key === 's') { ev.preventDefault(); if (dirty) save(); } });
$('publish').onclick = async () => {
  if (dirty && !(await save())) return;
  $('publish').disabled = true; $('publish').textContent = 'Envoi…';
  try { const r = await fetch('/__admin/publier', { method: 'POST' }), j = await r.json(); toast(j.message, !j.ok, 6000); }
  catch (e) { toast('La mise en ligne a échoué.', true); }
  $('publish').disabled = false; $('publish').textContent = 'Mettre en ligne';
};
$('add').onclick = add; $('add2').onclick = add;

/* ─── au démarrage ─── */
function banniere(txt) { let b = $('banniere'); if (!b) { b = el('div', 'banniere'); b.id = 'banniere'; document.querySelector('.wrap').before(b); } b.textContent = txt; }
(async () => {
  try {                                                             // les emplacements : les bâtiments-projets de l'image
    catalogue = (await (await fetch('/city/emplacements.json')).json()).emplacements.map(e => ({ id: e.id, nom: e.nom, uv: e.uv }));
  } catch (e) { console.warn('emplacements', e); catalogue = []; }
  const lire = async (url, secours) => {
    try { const r = await fetch(url), t = await r.text(); if (!r.ok || !/^\s*\[/.test(t)) throw new Error(); return JSON.parse(t); }
    catch (e) { peutEnregistrer = false; return secours(); }
  };
  projects = await lire('/__admin/projets', async () => { try { const m = await import(/* @vite-ignore */ '/src/projets.js?t=' + Date.now()); return JSON.parse(JSON.stringify(m.PROJECTS)); } catch (e2) { return []; } });
  outils = await lire('/__admin/outils', async () => { try { const m = await import(/* @vite-ignore */ '/src/outils.json?import&t=' + Date.now()); return m.default; } catch (e2) { return []; } });
  if (!peutEnregistrer) {
    banniere('Tes projets sont affichés, mais l’enregistrement ne marche pas encore : ferme la fenêtre noire du Terminal (ou arrête « npm run dev » dans WebStorm), puis rouvre l’admin avec « Ouvrir l’admin.command ».');
    $('save').disabled = true; $('publish').disabled = true;
  } else { setDirty(false); $('save').textContent = 'Enregistrer'; }
  // tous les projets passent en position libre : ceux qui avaient un bâtiment gardent son endroit exact
  for (const p of projects) if (p.grille !== 2) { (p.page || []).forEach(b => { if (b.type !== 'outils') b.h = (b.h || 2) * 2; }); p.grille = 2; }   // grille deux fois plus fine en hauteur : mêmes tailles qu'avant
  const pris = new Set(projects.map(p => p.emplacement));
  for (const p of projects) if (!Array.isArray(p.uv)) {
    let c = (catalogue || []).find(c => c.id === p.emplacement);
    if (!c) { c = (catalogue || []).find(c => !pris.has(c.id)); if (c) pris.add(c.id); }       // comme sur le site : le premier bâtiment libre
    p.uv = c && c.uv ? c.uv.slice() : [.5, .6];
  }
  try { const r = await fetch('/__admin/accueil'); if (r.ok) accueil = await r.json(); } catch (e) { /* pas de serveur : on garde les écrans vides */ }
  accueil.ecrans = Object.assign({ mac: {}, iphone: {} }, accueil.ecrans || {});
  const ecranModifie = () => { accueilModifie = true; setDirty(); };
  $('ecranIphone').appendChild(zoneMedia(accueil.ecrans.iphone, ecranModifie));
  $('ecranMac').appendChild(zoneMedia(accueil.ecrans.mac, ecranModifie));
  renderList();
  if (projects.length) select(0);
  else $('vitrine').src = '/?v=0#vitrine';
  setTimeout(() => { if (!$('vload').hidden) $('vload').textContent = 'L’aperçu 3D ne se charge pas. Recharge la page (Cmd + R).'; }, 30000);
})();
