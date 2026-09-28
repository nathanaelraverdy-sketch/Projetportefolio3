#!/bin/bash
# Double-clique sur ce fichier pour ouvrir la page admin de la ville des projets.
# Une fenêtre de Terminal s'ouvre : laisse-la ouverte tant que tu travailles, ferme-la quand tu as fini.
cd "$(dirname "$0")"
if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js n'est pas installé sur cet ordinateur."
  echo "Installe-le depuis https://nodejs.org (bouton « LTS »), puis double-clique à nouveau sur ce fichier."
  read -n 1 -s -r -p "Appuie sur une touche pour fermer."
  exit 1
fi
if [ ! -d node_modules ]; then
  echo "Première ouverture : installation (une minute environ)…"
  npm install
fi
echo ""
echo "La page admin s'ouvre dans ton navigateur."
echo "Laisse cette fenêtre ouverte pendant que tu travailles. Pour arrêter : ferme-la."
echo ""
npx vite --open /admin.html
