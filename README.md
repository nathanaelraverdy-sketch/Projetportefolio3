# Ville des projets — v3 (image pré-rendue, façon why.zero.university)

La ville n'est plus construite dans le navigateur : c'est **une image photoréaliste** rendue dans
Blender (`tools/build_city.py`), posée à plat et filmée par une caméra orthographique, exactement
comme la carte de why.zero.university. Par-dessus, tout ce qui venait de **Projetcarte** :

- l'écran de chargement, l'écran d'accueil qui se dissipe en nuages au scroll ;
- la barre de navigation (About · Service · Contact) ;
- le bouton de l'heure (heure réelle → matin → jour → soir → nuit) ;
- la fiche projet, le « View more » (projet en détail, bandeau d'outils) ;
- la page admin (projets, médias, outils, enregistrement, mise en ligne).

## Lancer

- **La ville** : dans WebStorm, `package.json` → ▶ à côté de `dev` (ou `npm install` puis `npm run dev`).
- **L'admin** : double-clic sur « Ouvrir l'admin.command » (ou ▶ à côté de `admin`).

⚠️ Ne pas ouvrir `index.html` avec l'aperçu navigateur de WebStorm (adresse en `:63342`) : la page reste
figée sur l'accueil, le scroll ne fait rien. Il faut passer par `npm run dev` (adresse `localhost:5180`).

## Où sont les choses

| Fichier | Rôle |
|---|---|
| `src/projets.js` | les projets (modifiés par l'admin) ; `emplacement` = le bâtiment de l'image (voir l'admin) |
| `public/city/city.webp` | la ville le jour ; `city_morning/dusk/night.webp` pour les autres moments (facultatifs) |
| `public/city/emplacements.json` | la position de chaque bâtiment-projet dans l'image |
| `src/main.js` | carte, pastilles, fiche, accueil en nuages, heure de la journée |
| `src/detail.js`, `src/style.css`, `src/admin/` | repris de Projetcarte |
| `tools/build.py` | construit et rend la ville dans Blender (quartiers, relief, lotissements…) |

## Regénérer la ville (Blender sur le Mac)

Dans le Terminal, depuis le dossier du projet :

```bash
bash tools/rendre.sh              # les 4 moments : jour, matin, soir, nuit
bash tools/rendre.sh day          # seulement le jour
```

Blender utilise la carte graphique du Mac. Chaque rendu écrit directement dans `public/city/` :
`city*.webp` (8192 px), `city*_4k.webp` (4096 px, téléphones) et `emplacements.json`.
Recharge ensuite le site (Cmd + R).

Aperçu rapide (1600 px, dans `tools/preview.png`) :

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -P tools/build.py -- --preview
```

Le plan de la ville se règle en haut de `tools/build.py` : le centre-ville (`CORE`), le parc, les
deux pôles industrie + logistique, le massif boisé (`NATURE_`).
