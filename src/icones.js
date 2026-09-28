/* La bibliothèque d'icônes des projets : des pictogrammes au trait, dans l'esprit du site (trait régulier, bouts arrondis).
   Chaque icône = des tracés SVG dans un carré de 24 × 24. On les dessine dans les pastilles de la carte (Path2D)
   et dans le menu de l'admin (SVG). Dans les projets, l'icône est notée « ic:identifiant ». */
const O = (cx, cy, r) => `M${cx - r} ${cy}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;   // un cercle

export const CATEGORIES = [
  ['Numérique', [
    ['web', 'Site web', ['M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0', 'M3 12h18', 'M12 3c3.5 3.5 3.5 14.5 0 18', 'M12 3c-3.5 3.5 -3.5 14.5 0 18']],
    ['mobile', 'Application mobile', ['M8 2h8a2 2 0 0 1 2 2v16a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2v-16a2 2 0 0 1 2 -2z', 'M11 18h2']],
    ['ordinateur', 'Logiciel', ['M5 5h14a1 1 0 0 1 1 1v9h-16v-9a1 1 0 0 1 1 -1z', 'M2 18h20', 'M9 21h6']],
    ['code', 'Développement', ['M8 8l-4 4l4 4', 'M16 8l4 4l-4 4', 'M13.5 5l-3 14']],
    ['ia', 'Intelligence artificielle', ['M11 3l1.8 5.2l5.2 1.8l-5.2 1.8l-1.8 5.2l-1.8 -5.2l-5.2 -1.8l5.2 -1.8z', 'M18.5 14.5l.8 2.2l2.2 .8l-2.2 .8l-.8 2.2l-.8 -2.2l-2.2 -.8l2.2 -.8z']],
    ['donnees', 'Données, statistiques', ['M4 20h16', 'M7 16v-4', 'M12 16v-9', 'M17 16v-6']],
    ['securite', 'Sécurité', ['M12 3l8 3v6c0 5 -3.5 8 -8 9c-4.5 -1 -8 -4 -8 -9v-6z', 'M9 12l2 2l4 -4']],
    ['jeu', 'Jeu vidéo', ['M6 8h12a4 4 0 0 1 4 4l-1 4a2.5 2.5 0 0 1 -4.5 1l-1.5 -2h-6l-1.5 2a2.5 2.5 0 0 1 -4.5 -1l-1 -4a4 4 0 0 1 4 -4z', 'M7.5 10.5v3', 'M6 12h3', O(16, 11, .6), O(18, 13, .6)]],
  ]],
  ['Création', [
    ['design', 'Design, graphisme', ['M12 3a9 9 0 1 0 0 18c1.5 0 2 -1 2 -2s-1 -1.5 -1 -2.5s1 -1.5 2 -1.5h2a4 4 0 0 0 4 -4c0 -4.5 -4 -8 -9 -8z', O(8, 11, 1), O(10.5, 7.5, 1), O(15, 7.5, 1)]],
    ['marque', 'Identité de marque', ['M3 12v-8a1 1 0 0 1 1 -1h8l9 9l-9 9z', O(7.5, 7.5, 1.3)]],
    ['photo', 'Photographie', ['M4 7h3l2 -3h6l2 3h3a1 1 0 0 1 1 1v11a1 1 0 0 1 -1 1h-16a1 1 0 0 1 -1 -1v-11a1 1 0 0 1 1 -1z', O(12, 13, 3.6)]],
    ['video', 'Vidéo, film', ['M4 6h11a1 1 0 0 1 1 1v10a1 1 0 0 1 -1 1h-11a1 1 0 0 1 -1 -1v-10a1 1 0 0 1 1 -1z', 'M16 10l5 -3v10l-5 -3']],
    ['musique', 'Musique', ['M9 18v-13l11 -2v13', O(6.5, 18, 2.5), O(17.5, 16, 2.5)]],
    ['podcast', 'Podcast, audio', ['M9 5a3 3 0 0 1 6 0v6a3 3 0 0 1 -6 0z', 'M5 11a7 7 0 0 0 14 0', 'M12 18v3', 'M9 21h6']],
    ['art', 'Art, illustration', ['M18 3l3 3l-9 9l-3 -3z', 'M9 12c-3 0 -5 2 -5 5c0 1 -1 2 -2 2c3 2 8 1 9 -3']],
    ['ecriture', 'Écriture, blog', ['M4 20l4 -1l11 -11a2.1 2.1 0 0 0 -3 -3l-11 11z', 'M14 7l3 3', 'M13 20h7']],
    ['objet3d', '3D, produit', ['M12 2l9 5v10l-9 5l-9 -5v-10z', 'M3 7l9 5l9 -5', 'M12 12v10']],
    ['impression', 'Impression, édition', ['M6 9v-6h12v6', 'M6 18h-2v-8h16v8h-2', 'M6 14h12v7h-12z']],
    ['mode', 'Mode', ['M12 7a2 2 0 1 1 2 -2', 'M12 7v1l9 7h-18l9 -7']],
    ['beaute', 'Beauté, bijoux', ['M6 3h12l4 6l-10 12l-10 -12z', 'M2 9h20', 'M9 3l3 6l3 -6']],
  ]],
  ['Commerce et services', [
    ['boutique', 'Boutique, e-commerce', ['M5 8h14l-1 13h-12z', 'M9 8v-2a3 3 0 0 1 6 0v2']],
    ['restaurant', 'Restaurant', ['M7 3v18', 'M5 3v5a2 2 0 0 0 4 0v-5', 'M17 21v-18c-2 1 -3 4 -3 7h3']],
    ['cafe', 'Café, bar', ['M4 9h13v5a5 5 0 0 1 -5 5h-3a5 5 0 0 1 -5 -5z', 'M17 11h1a2 2 0 0 1 0 4h-1', 'M8 3v3', 'M12 3v3']],
    ['finance', 'Finance', [O(12, 12, 9), 'M15 9a4 4 0 1 0 0 6', 'M7.5 11h5.5', 'M7.5 13h5.5']],
    ['conseil', 'Conseil', ['M4 5h16v11h-11l-5 4z', 'M8 9h8', 'M8 12h5']],
    ['marketing', 'Marketing, communication', ['M3 10v4h4l8 5v-14l-8 5z', 'M18 9a4 4 0 0 1 0 6']],
    ['immobilier', 'Immobilier', ['M3 11l9 -8l9 8', 'M5 9v12h14v-12', 'M10 21v-6h4v6']],
    ['architecture', 'Architecture', ['M4 21v-13l8 -5l8 5v13', 'M9 21v-6h6v6', 'M3 21h18', 'M9 10h.01', 'M15 10h.01']],
    ['artisanat', 'Artisanat, travaux', ['M15 4a5 5 0 0 0 -5 6l-7 7l4 4l7 -7a5 5 0 0 0 6 -5l-3 3l-3 -1l-1 -3z']],
    ['transport', 'Transport, auto', ['M3 13l2 -6h14l2 6v5h-18z', 'M3 13h18', O(7, 18, 1.8), O(17, 18, 1.8)]],
    ['voyage', 'Voyage, tourisme', ['M22 2l-11 11', 'M22 2l-7 20l-4 -9l-9 -4z']],
    ['contact', 'Service client', ['M3 6h18v12h-18z', 'M3 7l9 6l9 -6']],
  ]],
  ['Société', [
    ['sante', 'Santé', ['M9 3h6v6h6v6h-6v6h-6v-6h-6v-6h6z']],
    ['soin', 'Soin, bien-être', ['M12 20s-7 -4.5 -9 -9a4.5 4.5 0 0 1 9 -3a4.5 4.5 0 0 1 9 3c-2 4.5 -9 9 -9 9z']],
    ['education', 'Éducation', ['M2 9l10 -5l10 5l-10 5z', 'M6 11v5c3 2 9 2 12 0v-5', 'M22 9v6']],
    ['livre', 'Lecture, culture', ['M4 5a2 2 0 0 1 2 -2h13v16h-13a2 2 0 0 0 -2 2z', 'M4 21a2 2 0 0 1 2 -2h13v2']],
    ['communaute', 'Communauté, association', [O(9, 8, 3), 'M3 20c0 -3 3 -5 6 -5s6 2 6 5', 'M16 5.5a2.5 2.5 0 1 1 0 5', 'M18 15c2 .5 3 2 3 5']],
    ['evenement', 'Événement', ['M4 6h16v15h-16z', 'M4 10h16', 'M8 3v4', 'M16 3v4']],
    ['sport', 'Sport', [O(12, 12, 9), 'M12 7.5l4 3l-1.5 4.5h-5l-1.5 -4.5z', 'M12 3v4.5', 'M16 10.5l4.5 -1.5', 'M14.5 15l2.5 4', 'M9.5 15l-2.5 4', 'M8 10.5l-4.5 -1.5']],
    ['trophee', 'Récompense', ['M8 4h8v5a4 4 0 0 1 -8 0z', 'M8 6h-3a3 3 0 0 0 3 4', 'M16 6h3a3 3 0 0 1 -3 4', 'M12 13v4', 'M8 21h8', 'M9 17h6v4']],
    ['animaux', 'Animaux', [O(8, 8, 2), O(16, 8, 2), O(4.8, 12.5, 1.8), O(19.2, 12.5, 1.8), 'M12 13c-3 0 -5 4 -5 6a2 2 0 0 0 2 2c1 0 2 -1 3 -1s2 1 3 1a2 2 0 0 0 2 -2c0 -2 -2 -6 -5 -6z']],
    ['lieu', 'Lieu, local', ['M12 22s7 -6.5 7 -12a7 7 0 0 0 -14 0c0 5.5 7 12 7 12z', O(12, 10, 2.5)]],
  ]],
  ['Sciences et nature', [
    ['nature', 'Nature, écologie', ['M5 19c0 -9 6 -15 15 -15c0 9 -6 15 -15 15z', 'M5 19l8 -8']],
    ['recyclage', 'Environnement', ['M4 12a8 8 0 0 1 14 -5', 'M18 3v4h-4', 'M20 12a8 8 0 0 1 -14 5', 'M6 21v-4h4']],
    ['energie', 'Énergie', ['M13 2l-9 12h7l-1 8l9 -12h-7z']],
    ['science', 'Science, laboratoire', ['M9 3h6', 'M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2 -3l-5 -9v-6', 'M7.5 15h9']],
    ['recherche', 'Recherche', [O(11, 11, 7), 'M16 16l5 5']],
  ]],
  ['Idées', [
    ['fusee', 'Startup, lancement', ['M12 2c4 2 6 6 6 11l-3 3h-6l-3 -3c0 -5 2 -9 6 -11z', O(12, 9, 1.6), 'M9 16l-2 5l3 -2', 'M15 16l2 5l-3 -2']],
    ['idee', 'Idée, innovation', ['M9 18h6', 'M10 21h4', 'M12 3a6 6 0 0 0 -4 10.5c.8 .8 1 1.5 1 2.5h6c0 -1 .2 -1.7 1 -2.5a6 6 0 0 0 -4 -10.5z']],
    ['etoile', 'Coup de cœur', ['M12 3l2.8 5.8l6.2 .9l-4.5 4.4l1 6.2l-5.5 -2.9l-5.5 2.9l1 -6.2l-4.5 -4.4l6.2 -.9z']],
    ['coeur', 'Projet personnel', ['M12 20s-7 -4.5 -9 -9a4.5 4.5 0 0 1 9 -3a4.5 4.5 0 0 1 9 3c-2 4.5 -9 9 -9 9z', 'M12 9v6', 'M9 12h6']],
  ]],
];
export const ICONES = Object.fromEntries(CATEGORIES.flatMap(([, l]) => l.map(([id, nom, d]) => [id, { nom, d }])));
export const svgIcone = (id, size = 22, stroke = 'currentColor') => {
  const ic = ICONES[id]; if (!ic) return '';
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="${stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ic.d.map(p => `<path d="${p}"/>`).join('')}</svg>`;
};
/* dans un canvas : centré en (0, 0), taille en pixels */
export function dessineIcone(g, id, size, color) {
  const ic = ICONES[id]; if (!ic) return false;
  g.save(); g.scale(size / 24, size / 24); g.translate(-12, -12);
  g.strokeStyle = color; g.lineWidth = 2; g.lineCap = 'round'; g.lineJoin = 'round';
  for (const p of ic.d) g.stroke(new Path2D(p));
  g.restore(); return true;
}
