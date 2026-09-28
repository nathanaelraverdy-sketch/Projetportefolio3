/* ───────── Les projets : un projet = un bâtiment de la ville ─────────
   Le plus simple est de les modifier avec la page admin (double-clic sur « Ouvrir l'admin.command »).
   Pour chaque projet :
   name      = le titre du projet
   emplacement = le bâtiment de l'image qui le représente (p1 à p5 : voir public/city/emplacements.json)
   hue       = couleur d'accent [R, G, B] (pastille, balise lumineuse)
   role      = ton rôle ; tags = les étiquettes de la fiche (ex. ["Webdesign", "Développement"])
   desc      = la description courte
   image     = l'image de la fiche (obligatoire s'il y a une vidéo) ; video = une vidéo (facultative)
   tools     = les outils utilisés (identifiants de src/outils.json)
   page      = le projet en détail, en blocs sur une grille de 3 colonnes :
               { type: "texte", titre, texte, w, h } · { type: "media", image, video, w, h } · { type: "outils" }
               (w = largeur en colonnes, de 1 à 3 ; h = hauteur, en demi-rangées)
   (la position de la pastille dans l'image vient de public/city/emplacements.json.)                                   */
export const PROJECTS = [
  {
    "id": "myrtille-raverdy-sage-femme",
    "name": "Myrtille Raverdy - Sage femme",
    "uv": [
      0.1497,
      0.94345
    ],
    "icone": "ic:soin",
    "statut": "Nouveau",
    "progression": 40,
    "grille": 2,
    "hue": [
      63,
      143,
      90
    ],
    "tags": [
      "Webdesign",
      "Developpement",
      "Mockups"
    ],
    "desc": "L'ensemble a été pensé de façon itérative et responsive : navigation contextuelle (le CTA \"Prendre rendez-vous\" apparaît dans la barre au scroll, un bouton équivalent existe sur la page Contact), mise en page qui se réorganise intelligemment sur mobile (empilement, réordonnanceme",
    "image": "/medias/copy-of-macbook-air-mockup-on-a-wooden-console-mockuuups-stu-mufw7baf-web.webp",
    "tools": [
      "html",
      "css",
      "javascript",
      "json",
      "googlecloud"
    ],
    "page": [
      {
        "type": "media",
        "w": 3,
        "h": 6,
        "image": "/medias/copy-of-macbook-air-mockup-on-a-wooden-console-mockuuups-stu-mufw82dy-web.webp",
        "video": "/medias/ultramock-timeline-16-9-4s-2026-09-06t19-05-43-970z-mufw8f73.mp4"
      },
      {
        "type": "texte",
        "w": 3,
        "h": 3,
        "titre": "Expérience utilisateur",
        "texte": "L'ensemble a été pensé de façon itérative et responsive : navigation contextuelle (le CTA \"Prendre rendez-vous\" apparaît dans la barre au scroll, un bouton équivalent existe sur la page Contact), mise en page qui se réorganise intelligemment sur mobile (empilement, réordonnancement de blocs, galerie de photos en éventail plutôt qu'en liste plate), et une lightbox navigable au clavier et à la souris qui ne propose que les images visibles à l'écran. Le résultat est un site vitrine sobre mais soigné, où chaque décision de mise en page sert la lisibilité du contenu autant que l'image professionnelle de la sage-femme qu'il présente.\n\n"
      },
      {
        "type": "outils"
      },
      {
        "type": "texte",
        "w": 2,
        "h": 4,
        "titre": "Architecture technique",
        "texte": "Le site est construit en HTML/CSS/JavaScript vanilla, sans framework ni bundler quatre pages statiques (accueil, contact, rendez-vous, mentions légales) partageant une feuille de style commune (style.css) et des feuilles spécifiques par page. La logique interactive reste légère : un main.js gère les animations d'apparition au scroll via IntersectionObserver, le bouton de navigation flottant et une lightbox générique pour l'agrandissement d'images, tandis que calendar.js orchestre un système de prise de rendez-vous connecté à l'API Google Calendar, avec une génération de créneaux dynamique tenant compte d'horaires différenciés par jour de la semaine et de la durée de consultation. r.js orchestre un système de prise de rendez-vous connecté à l'API Gkjnhnnnnnnnnn l'API Gkjnhnnnnnnnnn l'API Gkjnhnnnnnnnnn l'API Gkjnhnn,,,,,,,"
      },
      {
        "type": "media",
        "w": 1.5,
        "h": 6,
        "image": "/medias/svg-vector-2026-09-06-mufwbasd-web.webp"
      },
      {
        "type": "texte",
        "w": 1,
        "h": 4,
        "titre": "Direction artistique",
        "texte": "Le design repose sur un système cohérent plutôt que sur des choix ponctuels : une palette lavande/violet unique, une police (Unageo) et un rayon de coin unifié qui structure aussi bien les sections que les images et les boutons. L'identité visuelle s'appuie sur des illustrations douces, un logo colibri en silhouette et des flèches point les images et les bo"
      },
      {
        "type": "media",
        "w": 1.5,
        "h": 6,
        "image": "/medias/svg-vector-2026-09-06-mufw7ne5-web.webp"
      }
    ]
  },
];
