/* Configuration de Vite (le petit serveur qui fait tourner le site en local).
   On y ajoute ce dont la page admin a besoin : lire et enregistrer src/projets.js, et mettre en ligne.
   Tout cela n'existe que quand le site tourne sur ton ordinateur (npm run dev) : la version en ligne
   ne contient ni la page admin, ni ces fonctions. */
import { defineConfig } from 'vite';
import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';

const FICHIER = path.resolve('src/projets.js');
const SAUVEGARDES = path.resolve('sauvegardes');

function lireProjets() {                                          // le fichier est du JavaScript : on en extrait la liste
  const txt = fs.readFileSync(FICHIER, 'utf8');
  const code = txt.slice(txt.indexOf('export const PROJECTS')).replace(/export const PROJECTS\s*=/, 'return');
  return new Function(code)();
}
const OUTILS = path.resolve('src/outils.json');
const ACCUEIL = path.resolve('src/accueil.json');                   // ce qu'affichent les écrans de la page d'accueil
function ecrireProjets(list) {                                    // un projet par bloc, lisible ; les champs complexes (page, étiquettes…) en JSON
  const txt = fs.readFileSync(FICHIER, 'utf8'), entete = txt.slice(0, txt.indexOf('export const PROJECTS'));
  sauvegarder('projets', txt);
  const propre = list.map(p => {
    const o = {};
    for (const k of ['id', 'name', 'emplacement', 'uv', 'icone', 'statut', 'progression', 'grille', 'hue', 'role', 'tags', 'desc', 'image', 'video', 'tools', 'page']) if (p[k] !== undefined && p[k] !== '' && !(Array.isArray(p[k]) && !p[k].length && k !== 'tools')) o[k] = p[k];
    o.hue = (p.hue || [224, 113, 77]).map(v => Math.max(0, Math.min(255, Math.round(v))));
    return '  ' + JSON.stringify(o, null, 2).replace(/\n/g, '\n  ') + ',';
  });
  fs.writeFileSync(FICHIER, entete + 'export const PROJECTS = [\n' + propre.join('\n') + '\n];\n');
}
function sauvegarder(nom, txt) { fs.mkdirSync(SAUVEGARDES, { recursive: true }); fs.writeFileSync(path.join(SAUVEGARDES, nom + '-' + new Date().toISOString().replace(/[:.]/g, '-') + '.txt'), txt); }
const nomPropre = s => {                                                // un nom de fichier sans accents ni espaces, raccourci sans jamais perdre son extension
  const t = String(s || 'fichier').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9.]+/g, '-').replace(/^-+|-+$/g, '');
  const ext = (t.match(/\.[a-z0-9]{2,5}$/) || [''])[0], base = t.slice(0, t.length - ext.length).slice(0, 50).replace(/-+$/, '');
  return (base || 'fichier') + ext;
};
function recevoirFichier(req, dossier) {                           // enregistre le fichier envoyé tel quel dans public/<dossier>/
  return new Promise((ok, ko) => {
    const u = new URL(req.url, 'http://x'), nom = nomPropre(u.searchParams.get('nom')), ext = path.extname(nom) || '', base = nom.slice(0, nom.length - ext.length);
    const fin = `${base}-${Date.now().toString(36)}${ext}`, dir = path.resolve('public', dossier);
    fs.mkdirSync(dir, { recursive: true });
    const out = fs.createWriteStream(path.join(dir, fin));
    req.pipe(out); out.on('finish', () => ok('/' + dossier + '/' + fin)); out.on('error', ko); req.on('error', ko);
  });
}
const git = args => new Promise(res => execFile('git', args, { cwd: path.resolve('.') }, (err, out, errOut) => res({ ok: !err, out: (out || '') + (errOut || '') })));
const corps = req => new Promise(res => { let b = ''; req.on('data', c => { b += c; }); req.on('end', () => res(b)); });
const repondre = (res, code, obj) => { res.statusCode = code; res.setHeader('Content-Type', 'application/json; charset=utf-8'); res.end(JSON.stringify(obj)); };

function admin() {
  return {
    name: 'admin-projets',
    apply: 'serve',
    handleHotUpdate({ file, server }) {                            // projets.js a changé : seule la ville se recharge, pas la page admin
      if (path.resolve(file) === FICHIER || path.resolve(file) === OUTILS) { server.ws.send({ type: 'custom', event: 'projets:maj' }); return []; }
    },
    configureServer(server) {
      server.middlewares.use('/__admin/projets', async (req, res) => {
        try {
          if (req.method === 'GET') return repondre(res, 200, lireProjets());
          const list = JSON.parse(await corps(req));
          if (!Array.isArray(list) || list.some(p => !p || !p.id || !p.name)) return repondre(res, 400, { erreur: 'Chaque projet doit avoir un nom.' });
          ecrireProjets(list);
          repondre(res, 200, { ok: true });
        } catch (e) { repondre(res, 500, { erreur: String(e.message || e) }); }
      });
      server.middlewares.use('/__admin/media', async (req, res) => {       // image ou vidéo d'un projet → public/medias/
        if (req.method !== 'POST') return repondre(res, 405, { erreur: 'POST seulement' });
        try { repondre(res, 200, { url: await recevoirFichier(req, 'medias') }); } catch (e) { repondre(res, 500, { erreur: String(e.message || e) }); }
      });
      server.middlewares.use('/__admin/outil-icone', async (req, res) => { // icône d'un outil → public/outils/
        if (req.method !== 'POST') return repondre(res, 405, { erreur: 'POST seulement' });
        try { repondre(res, 200, { url: await recevoirFichier(req, 'outils') }); } catch (e) { repondre(res, 500, { erreur: String(e.message || e) }); }
      });
      server.middlewares.use('/__admin/outils', async (req, res) => {      // la bibliothèque d'outils (src/outils.json)
        try {
          if (req.method === 'GET') return repondre(res, 200, JSON.parse(fs.readFileSync(OUTILS, 'utf8')));
          const list = JSON.parse(await corps(req));
          if (!Array.isArray(list)) return repondre(res, 400, { erreur: 'liste attendue' });
          sauvegarder('outils', fs.readFileSync(OUTILS, 'utf8'));
          fs.writeFileSync(OUTILS, JSON.stringify(list, null, 2) + '\n');
          repondre(res, 200, { ok: true });
        } catch (e) { repondre(res, 500, { erreur: String(e.message || e) }); }
      });
      server.middlewares.use('/__admin/accueil', async (req, res) => {     // les écrans de la page d'accueil (src/accueil.json)
        try {
          if (req.method === 'GET') return repondre(res, 200, JSON.parse(fs.readFileSync(ACCUEIL, 'utf8')));
          const o = JSON.parse(await corps(req));
          if (!o || typeof o !== 'object' || typeof o.ecrans !== 'object') return repondre(res, 400, { erreur: 'objet attendu' });
          sauvegarder('accueil', fs.readFileSync(ACCUEIL, 'utf8'));
          fs.writeFileSync(ACCUEIL, JSON.stringify(o, null, 2) + '\n');
          repondre(res, 200, { ok: true });
        } catch (e) { repondre(res, 500, { erreur: String(e.message || e) }); }
      });
      server.middlewares.use('/__admin/etat', async (req, res) => {
        const r = await git(['remote']);
        repondre(res, 200, { enLigne: r.ok && r.out.trim().length > 0 });
      });
      server.middlewares.use('/__admin/publier', async (req, res) => {
        const remote = await git(['remote']);
        if (!remote.ok || !remote.out.trim()) return repondre(res, 200, { ok: false, message: "La mise en ligne n'est pas encore branchée : il faut d'abord relier le projet à un site en ligne." });
        await git(['add', 'src/projets.js', 'src/outils.json', 'src/accueil.json', 'public/medias', 'public/outils']);
        const c = await git(['commit', '-m', 'Mise à jour des projets', '--', 'src/projets.js', 'src/outils.json', 'src/accueil.json', 'public/medias', 'public/outils']);
        if (!c.ok && !/nothing to commit|rien à valider/i.test(c.out)) return repondre(res, 200, { ok: false, message: "Impossible d'enregistrer la version : " + c.out.slice(0, 300) });
        const p = await git(['push']);
        repondre(res, 200, p.ok ? { ok: true, message: 'Envoyé ! Le site en ligne se met à jour dans quelques minutes.' } : { ok: false, message: "L'envoi a échoué : " + p.out.slice(0, 300) });
      });
    },
  };
}

export default defineConfig({
  plugins: [admin()],
  server: { port: 5180, strictPort: true, watch: { ignored: ['**/sauvegardes/**'] } },   // un port à lui : jamais confondu avec Projetcarte (5173)
  build: { target: 'es2022', rollupOptions: { input: 'index.html' } },   // la page admin n'est jamais publiée en ligne (es2022 : chargement de la ville avec « await »)
});
