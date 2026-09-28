"""Textures de feuillage (générées, rien à télécharger) : un atlas de feuilles et un atlas d'aiguilles,
avec transparence. Chaque carte d'arbre prend un quart de l'atlas au hasard."""
import math, random, os
from PIL import Image, ImageDraw, ImageFilter

def leaf_atlas(path, size=1024, seed=3):
    rnd = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for q in range(4):                      # 4 tuiles : 4 amas de feuilles différents
        ox, oy = (q % 2) * size // 2, (q // 2) * size // 2
        tile = Image.new("RGBA", (size // 2, size // 2), (0, 0, 0, 0)); d = ImageDraw.Draw(tile)
        c = size // 4
        for k in range(520):
            # les feuilles s'accumulent vers le centre de la tuile (un rameau feuillu)
            a = rnd.uniform(0, 6.283); r = (rnd.random() ** .7) * c * .92
            x, y = c + math.cos(a) * r, c + math.sin(a) * r
            L, W = rnd.uniform(14, 26), rnd.uniform(6, 11)
            ang = rnd.uniform(0, 6.283)
            g = rnd.uniform(.55, 1.15)
            col = (int(70 * g + rnd.uniform(-8, 8)), int(118 * g + rnd.uniform(-10, 10)), int(42 * g), 255)
            pts = []
            for t in range(12):
                tt = t / 11 * math.pi
                px = math.cos(tt) * L / 2; py = math.sin(tt) * W / 2 * (1 if t < 12 else -1)
                pts.append((px, py))
            pts += [(p[0], -p[1]) for p in reversed(pts)]
            ca, sa = math.cos(ang), math.sin(ang)
            d.polygon([(x + p[0] * ca - p[1] * sa, y + p[0] * sa + p[1] * ca) for p in pts], fill=col)
            # nervure
            d.line([(x - ca * L / 2, y - sa * L / 2), (x + ca * L / 2, y + sa * L / 2)], fill=(col[0] - 15, col[1] - 20, col[2] - 10, 255), width=1)
        # tige
        d.line([(c, c), (c + rnd.uniform(-60, 60), size // 2 - 4)], fill=(60, 45, 30, 255), width=3)
        im.paste(tile, (ox, oy), tile)
    im = im.filter(ImageFilter.SMOOTH)
    im.save(path)

def needle_atlas(path, size=1024, seed=5):
    rnd = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for q in range(4):
        ox, oy = (q % 2) * size // 2, (q // 2) * size // 2
        tile = Image.new("RGBA", (size // 2, size // 2), (0, 0, 0, 0)); d = ImageDraw.Draw(tile)
        h = size // 2
        # une branche de conifère : un axe et des aiguilles serrées de part et d'autre
        d.line([(h * .1, h / 2), (h * .95, h / 2)], fill=(55, 40, 28, 255), width=4)
        for k in range(260):
            t = rnd.uniform(.1, .95); x = h * t; y = h / 2
            L = (1 - t) * rnd.uniform(60, 110) + 20
            for sgn in (-1, 1):
                ang = sgn * rnd.uniform(.5, 1.2)
                g = rnd.uniform(.6, 1.1)
                col = (int(32 * g), int(70 * g), int(40 * g), 255)
                d.line([(x, y), (x + math.cos(ang) * L * .35, y + math.sin(ang) * L)], fill=col, width=2)
        im.paste(tile, (ox, oy), tile)
    im.save(path)

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    leaf_atlas(os.path.join(here, "leaves.png")); needle_atlas(os.path.join(here, "needles.png"))
