#!/bin/bash
# Rend les moments de la journée avec Blender (carte graphique du Mac) et met le site à jour.
#   bash tools/rendre.sh                    → tout : matin, jour, soir, nuit (8192 px) + la course du soleil
#   bash tools/rendre.sh day                → seulement le jour
#   bash tools/rendre.sh day --res=4096     → plus rapide, pour tester
#   bash tools/rendre.sh soleil             → la course du soleil (images intermédiaires matin → jour → soir, 2048 px)
#   bash tools/rendre.sh soleil --soleil=12 → plus d'images intermédiaires (8 par défaut) : les ombres glissent encore plus doucement
cd "$(dirname "$0")"
BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
[ -x "$BLENDER" ] || BLENDER="$(ls -d /Applications/Blender*.app 2>/dev/null | head -1)/Contents/MacOS/Blender"
if [ ! -x "$BLENDER" ]; then echo "Blender introuvable dans /Applications"; exit 1; fi
LOOKS=""; EXTRA=""
for a in "$@"; do case "$a" in --*) EXTRA="$EXTRA $a";; *) LOOKS="$LOOKS $a";; esac; done
[ -z "$LOOKS" ] && LOOKS="day morning dusk night soleil"
for L in $LOOKS; do
  echo "=== Rendu : $L  (ça peut prendre plusieurs minutes, laisse tourner) ==="
  X="$EXTRA"
  if [ "$L" = "soleil" ]; then ARG="--soleil"; case "$EXTRA" in *--soleil=*) ARG="";; esac; X="$(echo "$EXTRA" | sed -E 's/--res=[0-9]+//g')"   # la course du soleil reste en 2048 px
  else ARG="--look=$L"; X="$(echo "$EXTRA" | sed -E 's/--soleil(=[0-9]+)?//g')"; fi
  "$BLENDER" -b -P build.py -- $ARG $X 2>&1 | grep --line-buffered -E "rendu sur|quartiers|lotissements|Sample [0-9]+/|rendu :|site mis|Error|rror|Traceback|Killed" | awk '/Sample/{ if (NR % 25) next } {print; fflush()}'
done
echo "Terminé. Recharge le site (Cmd + R)."
