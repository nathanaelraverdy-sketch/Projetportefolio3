"""
Ville des projets v2 — une ville en QUARTIERS reliés par des routes organiques, avec du relief.

  Très haute densité / bureaux · Haute densité · Pavillons · Parc · Industrie · Logistique ·
  Bâtiments uniques (théâtre, cinéma, musée, opéra, bibliothèque, hôtel de ville, stade, amphithéâtre)

Tout est construit en procédural puis rendu dans Cycles, vue aérienne orthographique
(comme la carte de why.zero.university). Le script exporte aussi emplacements.json :
la position, dans l'image, de chaque bâtiment qui peut porter un projet.

  blender -b -P build.py -- --preview            aperçu 1600x800
  blender -b -P build.py --                      rendu final 8192x4096 (jour)
  blender -b -P build.py -- --look=night         morning | day | dusk | night
  blender -b -P build.py -- --no-render          seulement emplacements.json
(ou  pip install bpy  puis  python3 build.py ...)
"""
import bpy, math, random, json, sys, os
from mathutils import Matrix
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
PREVIEW = "--preview" in ARGS
LOOK = next((a.split("=")[1] for a in ARGS if a.startswith("--look=")), "day")
CROP = next((tuple(float(v) for v in a.split("=")[1].split(",")) for a in ARGS if a.startswith("--crop=")), None)
RESX = next((int(a.split("=")[1]) for a in ARGS if a.startswith("--res=")), 1600 if PREVIEW else 2048 if any(a.startswith("--soleil") for a in ARGS) else 8192)
RATIO = .6875                 # hauteur / largeur de l'image (la carte descend jusqu'au bourg du sud)
RES = (RESX, int(round(RESX * RATIO / 16)) * 16)
SAMPLES = next((int(a.split("=")[1]) for a in ARGS if a.startswith("--samples=")), 12 if PREVIEW else 16 if any(a.startswith("--soleil") for a in ARGS) else 32)
OUT = next((a.split("=")[1] for a in ARGS if a.startswith("--out=")), HERE)

LOOKS = {  # élévation, rotation, couleur, énergie du soleil, ciel, exposition, nuit, taille du soleil (°), brume, air
    "morning": (15, 105, (1.0, .74, .5), 4.6, .24, .1, .0, 1.8, 5.0, 1.5),    # soleil bas à l'est, lumière dorée, brume légère
    "day":     (50, 215, (1.0, .97, .92), 4.2, .30, -.1, .0, 1.0, 1.4, 1.0),    # plein jour lumineux, ombres courtes et nettes
    "dusk":    (8,  287, (1.0, .5, .24), 6.0, .2, .45, .25, 1.4, 3.5, 1.5),    # coucher de soleil : ombres très longues, lampadaires qui s'allument
    "night":   (35, 160, (.55, .65, 1.0), .14, .0, .1, 1.0, 1.2, 2.2, 1.2),
}
L_EL, L_ROT, L_SUNC, L_SUNE, L_SKY, L_EXPO, NIGHT, L_ANG, L_DUST, L_AIR = LOOKS[LOOK]
# --soleil : les images intermédiaires de la course du soleil (matin → jour → soir), pour que le site fasse tourner les ombres
SOLEIL = next((int(a.split("=")[1]) if "=" in a else 8 for a in ARGS if a.startswith("--soleil")), 0)
SEGMENTS = (("morning", "day"), ("day", "dusk"))
def soleil_params(a, b, t):
    A, B = LOOKS[a], LOOKS[b]
    lerp = lambda x, y: tuple(lerp(u, v) for u, v in zip(x, y)) if isinstance(x, tuple) else x + (y - x) * t
    return tuple(lerp(x, y) for x, y in zip(A, B))

import mats
from mats import MAT
from geo import Acc
from roads import Net, Kit, cum, at, cut, length, resample, seg_dist

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene; COL = scene.collection
mats.build_all(NIGHT)
A = Acc()
# fenêtres visibles (centre, axe le long de la façade, largeur, hauteur) : la nuit, le site en allume / éteint quelques-unes
WINDOWS = []
_box0 = A.box
def _box_fenetres(mat, x, y, z0, w, d, h, rot=0., col=(.5, .5, .5), top=None, fh=3.4, bay=2.6, uoff=0., sides=True, *a, **k):
    if mat == "facade" and sides and h > 2 * fh and R_WIN.random() < .35:
        c, s_ = math.cos(rot), math.sin(rot)
        for (ax, ay), (bx, by) in (((-w / 2, -d / 2), (w / 2, -d / 2)), ((w / 2, -d / 2), (w / 2, d / 2)), ((w / 2, d / 2), (-w / 2, d / 2)), ((-w / 2, d / 2), (-w / 2, -d / 2))):
            nx, ny = (by - ay), -(bx - ax); wy = nx * s_ + ny * c
            if wy >= -.3 * math.hypot(nx, ny): continue                   # seulement les façades tournées vers la caméra
            L = math.hypot(bx - ax, by - ay); tx, ty = (bx - ax) / L, (by - ay) / L
            wtx, wty = tx * c - ty * s_, tx * s_ + ty * c
            nb = int(L / bay)
            for n in range(nb):
                t = (n + .5 - (uoff % 1)) * bay
                if not (0 < t < L): continue
                for m in range(1, int(h / fh)):
                    lx, ly = ax + tx * t, ay + ty * t
                    WINDOWS.append((x + lx * c - ly * s_, y + lx * s_ + ly * c, z0 + (m + .54) * fh, wtx, wty, bay * .46, fh * .46))
    return _box0(mat, x, y, z0, w, d, h, rot, col, top, fh, bay, uoff, sides, *a, **k)
A.box = _box_fenetres
R_WIN = random.Random(5)
NET = Net()            # le réseau de routes (kit de route : roads.py)
R = random.Random(11)        # la ville (identique pour tous les moments de la journée)
RN = random.Random(77)       # ce qui n'existe que la nuit

VIEW_W = 1600.
def catmull(ctrl, step=6.):
    out = []
    P = [ctrl[0]] + ctrl + [ctrl[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, int(math.dist(p1, p2) / step))
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2 + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in (0, 1)))
    out.append(ctrl[-1]); return out
HWY = catmull([(-1080, -228), (-700, -244), (-400, -248), (-150, -262), (150, -282), (450, -300), (750, -303), (1080, -290)])
HWY_H, HWY_W = 10.5, 23.
def near_hwy(x, y, m=0.): return any(abs(x - p[0]) < 40 + m and math.hypot(x - p[0], y - p[1]) < HWY_W / 2 + m for p in HWY[::2])               # largeur couverte par l'image (m)
SHORE = lambda x: 700 - .56 * x + 26 * math.sin(x / 150) + 14 * math.sin(x / 61 + 1.3)   # côte en diagonale (en haut à droite)

# ═══════════════════════════════════════ prototypes instanciés (arbres, voitures…)
import bmesh
def mesh_from_bm(name, bm, mats_):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats_: me.materials.append(MAT[m])
    return me

mats.m_foliage_img("leafcards", os.path.join(HERE, "leaves.png"), ((.55, .75, .45), (1.05, 1.0, .62)))
mats.m_foliage_img("needlecards", os.path.join(HERE, "needles.png"), ((.7, .85, .75), (1.0, 1.05, .9)))

def tree_mesh(i, conifer=False):
    """un arbre avec un VRAI feuillage : tronc, branches, et des centaines de cartes portant de vraies
    feuilles dessinées (atlas leaves.png, transparence), réparties en houppiers"""
    bm = bmesh.new(); rr = random.Random(200 + i)
    uvl = bm.loops.layers.uv.new("UVMap")
    def card(c, sz, n=None):
        if n is None:
            a, e = rr.uniform(0, 6.283), rr.uniform(.35, 1.4)
            n = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        t = n.orthogonal().normalized(); b_ = n.cross(t)
        rot = rr.uniform(0, 6.283); t, b_ = t * math.cos(rot) + b_ * math.sin(rot), -t * math.sin(rot) + b_ * math.cos(rot)
        vs = [bm.verts.new(c + (t * sx + b_ * sy) * sz / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        f = bm.faces.new(vs); f.material_index = 0
        q = rr.randrange(4); ox, oy = (q % 2) * .5, (q // 2) * .5
        for lp, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): lp[uvl].uv = (ox + u * .5, oy + v * .5)
    def limb(p0, p1, r0, r1):
        d = p1 - p0; L = d.length
        res = bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=r0, radius2=r1, depth=L)
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        for v in res["verts"]: v.co = q @ (v.co + Vector((0, 0, L / 2))) + p0
        for f in {f for v in res["verts"] for f in v.link_faces}: f.material_index = 1
    if conifer:
        H = rr.uniform(9, 13)
        limb(Vector((0, 0, 0)), Vector((0, 0, H)), .3, .05)
        for k in range(16):
            z = 1.6 + (H - 1.8) * k / 16; rad = 2.8 * (1 - k / 16) + .4
            for m in range(7):
                a = m / 7 * 6.283 + k * .7
                card(Vector((math.cos(a) * rad * .55, math.sin(a) * rad * .55, z)), rad * 1.25 + .6, Vector((math.cos(a) * .35, math.sin(a) * .35, 1)).normalized())
    else:
        shape = i % 4
        H = [5.5, 7.5, 4.8, 6.5][shape]
        top = Vector((rr.uniform(-.3, .3), rr.uniform(-.3, .3), H * .55))
        limb(Vector((0, 0, 0)), top, .28, .18)
        if shape == 0: clumps = [(Vector((0, 0, H * .95)), 2.6)] + [(Vector((rr.uniform(-1.6, 1.6), rr.uniform(-1.6, 1.6), H * rr.uniform(.8, 1.1))), rr.uniform(1.4, 2)) for _ in range(4)]
        elif shape == 1: clumps = [(Vector((rr.uniform(-.5, .5), rr.uniform(-.5, .5), H * (.6 + .15 * k))), 1.7 - .15 * k) for k in range(5)]
        elif shape == 2: clumps = [(Vector((math.cos(a) * 2.6, math.sin(a) * 2.6, H * .95 + rr.uniform(-.3, .4))), rr.uniform(1.7, 2.3)) for a in [k * 1.26 + rr.uniform(-.2, .2) for k in range(5)]] + [(Vector((0, 0, H * 1.05)), 2.2)]
        else: clumps = [(Vector((rr.uniform(-2, 2), rr.uniform(-2, 2), H * rr.uniform(.75, 1.15))), rr.uniform(1.3, 2.1)) for _ in range(6)]
        for c, r in clumps:
            limb(top, c + Vector((0, 0, -r * .4)), .12, .05)
            for k in range(int(22 * r * r)):
                d = Vector((rr.gauss(0, 1), rr.gauss(0, 1), rr.gauss(0, 1) * .8)).normalized() * (rr.random() ** .35) * r
                card(c + d, rr.uniform(1.1, 1.8))
    me = bpy.data.meshes.new(f"tree{i}{'c' if conifer else ''}"); bm.to_mesh(me); bm.free()
    for f in me.polygons: f.use_smooth = True
    me.materials.append(MAT["needlecards" if conifer else "leafcards"]); me.materials.append(MAT["trunk"])
    return me

TREES = [tree_mesh(i) for i in range(8)]
PINES = [tree_mesh(i, True) for i in range(3)]

def rock_mesh(i):
    bm = bmesh.new(); rr = random.Random(300 + i)
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
    for v in bm.verts:
        v.co *= 1 + rr.uniform(-.28, .28)
        v.co.z *= .7
    for f in bm.faces: f.smooth = False
    return mesh_from_bm(f"rock{i}", bm, ["rock"])
ROCKS = [rock_mesh(i) for i in range(4)]

def car_mesh(truck=False):
    bm = bmesh.new()
    def cube(sx, sy, sz, cx, cz, mi):
        r = bmesh.ops.create_cube(bm, size=1)
        for v in r["verts"]: v.co = Vector((v.co.x * sx + cx, v.co.y * sy, v.co.z * sz + cz))
        for f in bm.faces:
            if all(v in r["verts"] for v in f.verts): f.material_index = mi
    if truck:
        cube(2.4, 2.4, 2.6, 5.6, 1.7, 0)     # cabine
        cube(1.2, 2.3, 1.2, 6.2, 2.2, 1)     # pare-brise
        cube(12.5, 2.5, 2.9, -2.2, 2.1, 2)   # remorque
    else:
        cube(4.4, 1.8, .75, 0, .65, 0); cube(2.3, 1.6, .6, -.2, 1.3, 1)
        for f in bm.faces:
            if f.material_index == 1 and f.normal.z > .5: f.material_index = 0
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=.1, segments=1, affect="EDGES")
    for f in bm.faces: f.smooth = True
    return mesh_from_bm("truck" if truck else "car", bm, ["paint", "carglass", "white"])
CAR, TRUCK = car_mesh(), car_mesh(True)

def wtower_mesh():
    bm = bmesh.new()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=1.6, radius2=1.6, depth=3.2)
    bmesh.ops.translate(bm, verts=r["verts"], vec=(0, 0, 3.6))
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=1.75, radius2=.1, depth=1.2)
    bmesh.ops.translate(bm, verts=r["verts"], vec=(0, 0, 5.8))
    for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=.1, radius2=.1, depth=2)
        bmesh.ops.translate(bm, verts=r["verts"], vec=(dx * 1.05, dy * 1.05, 1))
    return mesh_from_bm("wtower", bm, ["wood"])
WTOWER = wtower_mesh()

N_OBJ = [0]
def inst(mesh, x, y, z=0., rot=0., s=1., color=None, sz=None):
    ob = bpy.data.objects.new(f"i{N_OBJ[0]}", mesh); N_OBJ[0] += 1
    ob.location = (x, y, z); ob.rotation_euler = (0, 0, rot); ob.scale = (s, s, sz or s)
    if color: ob.color = (*color, 1)
    COL.objects.link(ob); return ob

# ═══════════════════════════════════════ occupation du sol (grille de 4 m)
CELL = 4.
ROAD = set()      # cellules de chaussée
BUSY = set()      # cellules construites
def cells_of_rect(x, y, w, d, rot, pad=0.):
    c, s = math.cos(rot), math.sin(rot); out = set()
    n = max(1, int((w + 2 * pad) / 3) + 1); m = max(1, int((d + 2 * pad) / 3) + 1)
    for i in range(n + 1):
        for j in range(m + 1):
            lx = -w / 2 - pad + (w + 2 * pad) * i / n; ly = -d / 2 - pad + (d + 2 * pad) * j / m
            out.add((int(math.floor((x + lx * c - ly * s) / CELL)), int(math.floor((y + lx * s + ly * c) / CELL))))
    return out
def free(x, y, w, d, rot, pad=0., roads_only=False):
    cs = cells_of_rect(x, y, w, d, rot, pad)
    return not (cs & ROAD) and (roads_only or not (cs & BUSY))
def claim(x, y, w, d, rot, pad=0.): BUSY.update(cells_of_rect(x, y, w, d, rot, pad))
def mark_road(pts, width):
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        n = int(math.hypot(x1 - x0, y1 - y0) / 2) + 1
        for k in range(n + 1):
            x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
            r = int(width / 2 / CELL) + 1
            for a in range(-r, r + 1):
                for b in range(-r, r + 1):
                    if math.hypot(a * CELL, b * CELL) <= width / 2 + 1:
                        ROAD.add((int(math.floor(x / CELL)) + a, int(math.floor(y / CELL)) + b))
def on_road(x, y): return (int(math.floor(x / CELL)), int(math.floor(y / CELL))) in ROAD

# ═══════════════════════════════════════ les quartiers
class Zone:
    def __init__(s, key, kind, c, half, rot):
        s.key, s.kind, s.c, s.h, s.rot = key, kind, c, half, math.radians(rot)
        s.cs, s.sn = math.cos(s.rot), math.sin(s.rot)
    def w(s, u, v): return (s.c[0] + u * s.cs - v * s.sn, s.c[1] + u * s.sn + v * s.cs)
    def l(s, x, y):
        dx, dy = x - s.c[0], y - s.c[1]; return (dx * s.cs + dy * s.sn, -dx * s.sn + dy * s.cs)
    def inside(s, x, y, m=0.):
        u, v = s.l(x, y); return abs(u) < s.h[0] + m and abs(v) < s.h[1] + m

def in_nature_(x, y): return math.hypot((x - NATURE_[0]) / 1.15, (y - NATURE_[1]) / .95) < 140
NATURE_ = (-70, -420)

class Core(Zone):
    """le centre-ville : une seule grille ; seuls certains îlots existent (bord irrégulier)"""
    PU, PV, SW = 84., 72., 13.
    def __init__(s, *a):
        super().__init__(*a); s.incl = {}
        s.nu, s.nv = int(2 * s.h[0] / s.PU), int(2 * s.h[1] / s.PV)
        s.us = [-s.h[0] + k * s.PU for k in range(s.nu + 1)]; s.vs = [-s.h[1] + k * s.PV for k in range(s.nv + 1)]
    def cell(s, u, v): return (int(math.floor((u + s.h[0]) / s.PU)), int(math.floor((v + s.h[1]) / s.PV)))
    def inside(s, x, y, m=0.):
        u, v = s.l(x, y)
        return any(s.cell(u + du, v + dv) in s.incl for du in (-m - s.SW / 2, 0, m + s.SW / 2) for dv in (-m - s.SW / 2, 0, m + s.SW / 2))

CORE = Core("core", "centre", (-60, 110), (504, 324), 16)
ZONES = [CORE,
         Zone("parc", "parc", (470, -118), (165, 112), -12),
         Zone("i1", "industrie", (300, -482), (126, 100), -8),
         Zone("i2", "industrie", (-540, -468), (120, 100), 10)]
GLUE = {"l1": ("i1", 1), "l2": ("i2", -1)}   # logistique → (industrie voisine, côté) : les deux quartiers se touchent
for key, (ik, side) in GLUE.items():
    ind = next(z for z in ZONES if z.key == ik); hu = 110
    d = ind.h[0] + hu
    ZONES.append(Zone(key, "logistique", (ind.c[0] + side * d * ind.cs, ind.c[1] + side * d * ind.sn), (hu, ind.h[1]), math.degrees(ind.rot)))
NATURE = (-70, -420)   # un massif boisé au sud
# les îlots du centre : un bord irrégulier, et un type qui dépend de la distance au cœur (avec du flou)
ph = [R.uniform(0, 6.3) for _ in range(4)]
TYPES = {}
for i in range(CORE.nu):
    for j in range(CORE.nv):
        cu, cv = (CORE.us[i] + CORE.us[i + 1]) / 2, (CORE.vs[j] + CORE.vs[j + 1]) / 2
        dd = math.hypot(cu / CORE.h[0], cv / CORE.h[1]) + .17 * math.sin(cu / 95 + ph[0]) * math.cos(cv / 70 + ph[1]) + .08 * math.sin(cu / 41 + ph[2]) + R.gauss(0, .045)
        if dd > 1: continue
        x, y = CORE.w(cu, cv)
        if any(z.inside(x, y, 50) for z in ZONES[1:]) or y > SHORE(x) - 70 or in_nature_(x, y) or near_hwy(x, y, 92): continue
        t = dd + R.gauss(0, .07)
        TYPES[(i, j)] = "bureaux" if t < .34 else "haute" if t < .76 else "faible"
        CORE.incl[(i, j)] = t
# des parcs partout (pas au cœur des tours), un grand parc urbain, et le quartier culturel
cand = [c for c, t in CORE.incl.items() if .3 < t < .95]
for c in R.sample(cand, max(4, int(len(cand) * .2) - 3)): TYPES[c] = "parcbloc"
cand_u = [c for c, t in CORE.incl.items() if .22 < t < .75 and TYPES[c] != "parcbloc"]
R.shuffle(cand_u); grp = []
for c in cand_u:   # jamais deux bâtiments uniques côte à côte (même en diagonale) : il y a toujours un îlot entre eux
    if all(max(abs(c[0] - g[0]), abs(c[1] - g[1])) >= 2 for g in grp): grp.append(c)
    if len(grp) == 6: break
for c in grp: TYPES[c] = "unique"
# équipements de la grande ville (clinique, gymnase, supermarché) : en périphérie, jamais à côté d'un bâtiment unique
cand_e = [c for c, t in CORE.incl.items() if .5 < t < .9 and TYPES[c] in ("faible", "haute")]
R.shuffle(cand_e); EQUIP = []
for c in cand_e:
    if all(max(abs(c[0] - g[0]), abs(c[1] - g[1])) >= 2 for g in grp + EQUIP): EQUIP.append(c)
    if len(EQUIP) == 3: break
for c in EQUIP: TYPES[c] = "equip"
class Town(Core):
    """le bourg du sud : une petite grille, ses équipements (mairie, église, école…) et des maisons"""
    PU, PV, SW = 96., 80., 12.
TOWN = Town("town", "bourg", (-80, -768), (240, 160), 4)
for i in range(TOWN.nu):
    for j in range(TOWN.nv):
        cu, cv = (TOWN.us[i] + TOWN.us[i + 1]) / 2, (TOWN.vs[j] + TOWN.vs[j + 1]) / 2
        dd = math.hypot(cu / TOWN.h[0], cv / TOWN.h[1]) + R.gauss(0, .08)
        if dd < .95: TOWN.incl[(i, j)] = dd
ZONES.append(TOWN)
ZK = {z.key: z for z in ZONES}
def zone_at(x, y, m=0.):
    for z in ZONES:
        if z.inside(x, y, m): return z
    return None

PITCH = {"bureaux": (78, 78, 16), "haute": (92, 64, 13), "unique": (100, 100, 14),
         "industrie": (150, 110, 14), "logistique": (130, 110, 16)}
SLOTS = []     # emplacements de projets : (id, nom, point 3D)

def grid_lines(z):
    pu, pv, sw = PITCH[z.kind]
    nu = max(1, round(2 * z.h[0] / pu)); nv = max(1, round(2 * z.h[1] / pv))
    us = [-z.h[0] + 2 * z.h[0] * k / nu for k in range(nu + 1)]
    vs = [-z.h[1] + 2 * z.h[1] * k / nv for k in range(nv + 1)]
    return us, vs, sw

GATES = {}
def lanes_cars(pts, width, two_way=True, dens=1.):
    """voitures le long d'une polyligne (orientées selon la tangente)"""
    total = 0; seglens = []
    for i in range(len(pts) - 1):
        l = math.dist(pts[i], pts[i + 1]); seglens.append(l); total += l
    for lane in ([-width / 4, width / 4] if two_way else [0]):
        d = R.uniform(0, 20)
        while d < total - 3:
            acc = 0
            for i, l in enumerate(seglens):
                if acc + l >= d:
                    t = (d - acc) / l; (x0, y0), (x1, y1) = pts[i], pts[i + 1]
                    x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                    ang = math.atan2(y1 - y0, x1 - x0); nx, ny = -math.sin(ang), math.cos(ang)
                    if lane < 0: ang += math.pi
                    px, py = x + nx * lane, y + ny * lane
                    car_at(px, py, ang)
                    break
                acc += l
            d += R.uniform(9, 40) / dens

CARS = []
TAXI = (.85, .55, .02)
CAR_COLS = [(.02, .02, .02), (.6, .6, .62), (.8, .8, .8), (.08, .12, .25), (.3, .02, .02), (.15, .15, .16), (.5, .52, .55)]
def car_at(x, y, ang, truck=False, parked=False):
    if truck: inst(TRUCK, x, y, 0, ang, 1, R.choice([(.7, .1, .08), (.1, .2, .5), (.9, .9, .9), (.1, .1, .1)]))
    else: inst(CAR, x, y, 0, ang, 1, TAXI if R.random() < .25 else R.choice(CAR_COLS))
    if not parked: CARS.append((x, y, ang, truck))

LAMPS = []
def lamp(x, y, rot):
    A.cyl("dark", x, y, 0, 7, .12, 6, top=False)
    hx, hy = x + math.cos(rot) * 1.2, y + math.sin(rot) * 1.2
    A.box("dark", (x + hx) / 2, (y + hy) / 2, 6.9, 1.4, .15, .12, rot)
    A.box("lamphead", hx, hy, 6.75, .7, .35, .18, rot)
    LAMPS.append((hx, hy))

def bench(x, y, rot):
    A.box("wood", x, y, .45, 1.8, .5, .08, rot)
    c, s = math.cos(rot), math.sin(rot)
    A.box("wood", x - s * .25, y + c * .25, .5, 1.8, .06, .45, rot)
    for k in (-.75, .75): A.box("dark", x + c * k, y + s * k, 0, .08, .5, .45, rot, top="dark")

def bin_(x, y): A.cyl("painted", x, y, 0, .95, .28, 8, col=(.08, .2, .1))

def street_props(p0, p1, side_off, kinds=("tree", "lamp", "bench", "bin"), tree_step=11, zlevel=.18, check_road=False):
    """le long d'un trottoir : arbres, lampadaires, bancs, poubelles"""
    (x0, y0), (x1, y1) = p0, p1
    L = math.dist(p0, p1); ang = math.atan2(y1 - y0, x1 - x0)
    nx, ny = -math.sin(ang), math.cos(ang)
    d = R.uniform(4, 8); k = 0
    while d < L - 4:
        x, y = x0 + (x1 - x0) * d / L + nx * side_off, y0 + (y1 - y0) * d / L + ny * side_off
        if not (check_road and on_road(x, y)):
            if "tree" in kinds and R.random() < .85: inst(R.choice(TREES), x, y, zlevel, R.uniform(0, 6.3), R.uniform(.75, 1.05))
            if "lamp" in kinds and k % 3 == 1: lamp(x + math.cos(ang) * 3, y + math.sin(ang) * 3, math.atan2(-ny, -nx))
            if "bench" in kinds and k % 4 == 2: bench(x + math.cos(ang) * 5.5, y + math.sin(ang) * 5.5, ang)
            if "bin" in kinds and k % 5 == 3: bin_(x - math.cos(ang) * 4, y - math.sin(ang) * 4)
        d += tree_step; k += 1

# ─── les rues d'un quartier en grille (+ trottoirs, marquages, passages piétons)
def build_grid_streets(z):
    us, vs, sw = grid_lines(z)
    # une nappe d'asphalte sous tout le quartier : les rues sont ce qui reste entre les îlots
    A.box("asphalt", z.c[0], z.c[1], 0, 2 * z.h[0] + sw, 2 * z.h[1] + sw, .012 + .0021 * (ZONES.index(z) % 7), z.rot, sides=False)
    for u in us:
        pts = [z.w(u, -z.h[1] - sw / 2), z.w(u, z.h[1] + sw / 2)]; mark_road(pts, sw)
        GATES.setdefault(z.key, []).extend([(z.w(u, -z.h[1] - sw / 2), (z.sn, -z.cs), sw, ("S", u)), (z.w(u, z.h[1] + sw / 2), (-z.sn, z.cs), sw, ("N", u))])
    for v in vs:
        pts = [z.w(-z.h[0] - sw / 2, v), z.w(z.h[0] + sw / 2, v)]; mark_road(pts, sw)
        GATES[z.key].extend([(z.w(-z.h[0] - sw / 2, v), (-z.cs, -z.sn), sw, ("W", v)), (z.w(z.h[0] + sw / 2, v), (z.cs, z.sn), sw, ("E", v))])
    # marquages : ligne centrale en tirets
    for u in us:
        for k in range(int(2 * z.h[1] / 9)):
            v0 = -z.h[1] + k * 9 + 2
            if any(abs(v0 - vv) < sw for vv in vs): continue
            A.box("paint_w", *z.w(u, v0 + 1.5), .025, .22, 3, .005, z.rot, sides=False)
    for v in vs:
        for k in range(int(2 * z.h[0] / 9)):
            u0 = -z.h[0] + k * 9 + 2
            if any(abs(u0 - uu) < sw for uu in us): continue
            A.box("paint_w", *z.w(u0 + 1.5, v), .025, 3, .22, .005, z.rot, sides=False)
    # passages piétons : seulement sur les branches qui existent
    for ii, u in enumerate(us):
        for jj, v in enumerate(vs):
            arms = {"E": ii < len(us) - 1, "W": ii > 0, "N": jj < len(vs) - 1, "S": jj > 0}
            if sum(arms.values()) < 3: continue
            # feux tricolores aux angles où deux rues se croisent (potence au-dessus de la rue qui arrive)
            for n_, (su, sv) in enumerate(((1, 1), (-1, -1), (1, -1), (-1, 1))):
                if not (arms["E" if su > 0 else "W"] and arms["N" if sv > 0 else "S"]): continue
                if n_ >= 2 and R.random() < .5: continue
                fx, fy = z.w(u + su * (sw / 2 + 1.1), v + sv * (sw / 2 + 1.1))
                traffic_light(fx, fy, z.rot + math.atan2(-sv, 0), arm=sw * .42, green=(n_ % 2 == 0))
            if R.random() < .12:
                mx_, my_ = z.w(u + R.choice([-1, 1]) * (sw / 2 + 2.2), v + R.choice([-1, 1]) * (sw / 2 + 4))
                if (int(mx_ // CELL), int(my_ // CELL)) not in BUSY: morris(mx_, my_)
            for key, (du, dv, along) in (("E", (sw / 2 + 2.2, 0, "v")), ("W", (-sw / 2 - 2.2, 0, "v")), ("N", (0, sw / 2 + 2.2, "u")), ("S", (0, -sw / 2 - 2.2, "u"))):
                if not arms[key]: continue
                for k in range(-4, 5):
                    if along == "v": A.box("paint_w", *z.w(u + du, v + k * 1.3), .025, 3, .6, .005, z.rot, sides=False)
                    else: A.box("paint_w", *z.w(u + k * 1.3, v + dv), .025, .6, 3, .005, z.rot, sides=False)
    # voitures
    for u in us:
        for k in range(len(vs) - 1):
            lanes_cars([z.w(u, vs[k] + sw / 2 + 5), z.w(u, vs[k + 1] - sw / 2 - 5)], sw * .8)
    for v in vs:
        for k in range(len(us) - 1):
            lanes_cars([z.w(us[k] + sw / 2 + 5, v), z.w(us[k + 1] - sw / 2 - 5, v)], sw * .8)
    blocks = []
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            u0, u1, v0, v1 = us[i] + sw / 2, us[i + 1] - sw / 2, vs[j] + sw / 2, vs[j + 1] - sw / 2
            blocks.append((u0, u1, v0, v1))
    return blocks

RC = 3.5          # rayon des bordures aux carrefours (angles d'îlots arrondis)
def prism(mat, pts, h, z0=0., side=None, col=(.5, .5, .5), fan0=False):
    """un dallage en relief de forme quelconque (étoilé depuis son centre, ou depuis son 1er point) : dessus + bordure"""
    n = len(pts); cx, cy = (pts[0] if fan0 else (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n))
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        A.face(mat, [(cx, cy, z0 + h), (a[0], a[1], z0 + h), (b[0], b[1], z0 + h)], None, col)
        A.face(side or mat, [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z0 + h), (a[0], a[1], z0 + h)], None, col)
def rounded_rect(z, u0, u1, v0, v1, r=RC):
    pts = []
    for cu, cv, a0 in ((u1 - r, v0 + r, -90), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)):
        for k in range(7):
            a = math.radians(a0 + k * 15); pts.append(z.w(cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts
def block_pad(z, b, mat="sidewalk", h=.18):
    u0, u1, v0, v1 = b
    prism(mat, rounded_rect(z, u0, u1, v0, v1), h)
    return h

def block_props(z, b, inset=2.2, kinds=("tree", "lamp", "bench", "bin")):
    u0, u1, v0, v1 = b
    edges = [((u0, v0), (u1, v0)), ((u1, v0), (u1, v1)), ((u1, v1), (u0, v1)), ((u0, v1), (u0, v0))]
    for a, bb in edges:
        street_props(z.w(*a), z.w(*bb), inset, kinds)   # côté intérieur (à gauche du sens de parcours)

# ═══════════════════════════════════════ bâtiments
def roof_clutter(x, y, rot, w, d, z, kind="std"):
    """sur le toit : CVC avec ventilateurs, ventilations, climatiseurs, panneaux solaires, château d'eau"""
    c, s = math.cos(rot), math.sin(rot)
    P = lambda lu, lv: (x + lu * c - lv * s, y + lu * s + lv * c)
    A.box("wall", x, y, z, w, d, .9, rot, col=(.45, .44, .42), top=False, sides=True)  # acrotère (contour)
    A.box("roof", x, y, z + .05, w - .6, d - .6, .01, rot, col=(.26, .26, .26), sides=False)
    n = max(1, int(w * d / 260))
    for _ in range(min(n, 7)):
        if w < 8 or d < 8: break
        bw, bd = R.uniform(2.5, 5), R.uniform(2, 3.5)
        lu, lv = R.uniform(-w / 2 + bw / 2 + 1, w / 2 - bw / 2 - 1), R.uniform(-d / 2 + bd / 2 + 1, d / 2 - bd / 2 - 1)
        px, py = P(lu, lv)
        r = R.random()
        if r < .45:                                    # centrale CVC + 1 ou 2 ventilateurs
            A.box("metalattr", px, py, z, bw, bd, 1.6, rot, col=(.6, .61, .6))
            for kk in range(1 if bw < 4 else 2):
                fx, fy = P(lu + (kk - .5 * (bw >= 4)) * 1.6, lv)
                A.cyl("dark", fx, fy, z + 1.6, .08, .7, 12)
        elif r < .7:                                   # climatiseurs en rangée
            for kk in range(R.randint(2, 5)):
                ax, ay = P(lu + kk * 1.3 - 2, lv)
                A.box("metalattr", ax, ay, z, 1., .8, .9, rot, col=(.75, .75, .72))
        elif r < .85:                                  # ventilations
            for kk in range(R.randint(2, 4)):
                vx, vy = P(lu + R.uniform(-1.5, 1.5), lv + R.uniform(-1, 1))
                A.cyl("metal", vx, vy, z, R.uniform(.8, 1.8), .22, 8)
                A.cyl("metal", vx, vy, z + 1.8, .15, .38, 8)
        else:                                          # édicule d'escalier
            A.box("wall", px, py, z, 3.2, 3, 2.8, rot, col=(.5, .48, .45), top="roof")
    if kind in ("solar", "logi") and w > 12:
        for i in range(int((w - 6) / 3)):
            for j in range(int((d - 6) / 5)):
                sx, sy = P(-w / 2 + 3 + i * 3 + 1.2, -d / 2 + 3 + j * 5 + 1.8)
                A.box("solar", sx, sy, z + .5, 2.4, 3.4, .12, rot, top="solar", sides=False)
    if kind == "wt" and w > 7 and R.random() < .55:
        px, py = P(R.uniform(-w / 2 + 2.5, w / 2 - 2.5), R.uniform(-d / 2 + 2.5, d / 2 - 2.5))
        inst(WTOWER, px, py, z, R.uniform(0, 6))

def gridded(x, y, rot, w, d, z0, h, fh, bay, style, wmat="wall"):
    """bâtiment à fenêtres EN CREUX : le verre au fond, une grille de trumeaux et d'allèges en saillie
    (seulement sur les façades que la caméra voit)"""
    wallc, glassc, pw, sh, dp = style
    A.box("glass", x, y, z0, w, d, h, rot, col=glassc, top=None, fh=fh, bay=bay, only_visible=True)
    c, s = math.cos(rot), math.sin(rot)
    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    nfl = max(1, int(h / fh))
    for i in range(4):
        (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
        nx, ny = (by - ay), -(bx - ax); L = math.hypot(bx - ax, by - ay); nx, ny = nx / L, ny / L
        wy = nx * s + ny * c
        if wy >= -.02:          # façade invisible : un mur plein suffit (il sert d'ombre)
            A.face(wmat, [(x + ax * c - ay * s, y + ax * s + ay * c, z0), (x + bx * c - by * s, y + bx * s + by * c, z0),
                            (x + bx * c - by * s, y + bx * s + by * c, z0 + h), (x + ax * c - ay * s, y + ax * s + ay * c, z0 + h)], None, wallc)
            continue
        tx, ty = (bx - ax) / L, (by - ay) / L
        nb = max(1, round(L / bay))
        # trumeaux (verticaux)
        for k in range(nb + 1):
            t = -L / 2 + L * k / nb
            lx, ly = (ax + bx) / 2 + tx * t + nx * dp / 2, (ay + by) / 2 + ty * t + ny * dp / 2
            A.box(wmat, x + lx * c - ly * s, y + lx * s + ly * c, z0, pw if 0 < k < nb else pw * 1.6, dp, h, rot + math.atan2(ty, tx), col=wallc, top="wall")
        # allèges (horizontales), à chaque étage sauf le rez-de-chaussée vitré
        if R_WIN.random() < .5:                                   # quelques fenêtres de cette façade, pour les allumer / éteindre la nuit
            tl = math.atan2(ty, tx) + rot; wtx, wty = math.cos(tl), math.sin(tl)
            for k in range(nb):
                t = -L / 2 + L * (k + .5) / nb
                lx, ly = (ax + bx) / 2 + tx * t, (ay + by) / 2 + ty * t
                for j in range(1, nfl):
                    WINDOWS.append((x + lx * c - ly * s, y + lx * s + ly * c, z0 + j * fh + (fh - sh) / 2 + sh * .5, wtx, wty, L / nb - pw, fh - sh))
        for j in range(1, nfl + 1):
            zz = z0 + j * fh - sh * .5
            lx, ly = (ax + bx) / 2 + nx * dp / 2, (ay + by) / 2 + ny * dp / 2
            A.box(wmat, x + lx * c - ly * s, y + lx * s + ly * c, zz, L + pw, dp, sh, rot + math.atan2(ty, tx), col=wallc, top="wall")
    # toit
    A.box("roof", x, y, z0 + h, w, d, .01, rot, col=(.3, .3, .3), sides=False)

STYLES = {
    #            mur                 verre               trumeau allège profondeur
    "glass":   ((.55, .6, .64),   (.10, .16, .21),    .22, .45, .3),
    "glass2":  ((.2, .22, .24),   (.08, .12, .14),    .25, .5, .35),
    "office":  ((.62, .58, .5),   (.12, .15, .18),    .9, 1.2, .45),
    "brick":   ((.38, .14, .08),  (.07, .09, .1),     .9, 1.3, .35),
    "brick2":  ((.46, .22, .13),  (.07, .09, .1),     .8, 1.2, .35),
    "stone":   ((.52, .47, .38),  (.07, .09, .1),     .9, 1.3, .4),
    "stucco":  ((.72, .68, .6),   (.07, .09, .1),     .8, 1.1, .3),
    "dark":    ((.13, .13, .14),  (.1, .12, .14),     .5, .9, .4),
    "pierre":  ((.82, .77, .66),  (.06, .08, .1),     1.25, 1.5, .55),     # façades classiques (bâtiments uniques)
}

def tower(x, y, rot, w, d, h, style, crown=True, setbacks=0, slot=None):
    fh = 3.9; bay = 3.2 if style.startswith("glass") else 2.8
    z = 0.
    if h > 40:                           # socle
        gridded(x, y, rot, w + 6, d + 6, 0, 12, 4.5, 4, STYLES["office" if style != "dark" else "dark"])
        z = 12
    tiers = [(w, d, h)]
    if setbacks:
        tiers = [(w, d, h * .62), (w * .78, d * .78, h * .85), (w * .56, d * .56, h)][:setbacks + 1]
    for tw, td, th in tiers:
        gridded(x, y, rot, tw, td, z, th - z, fh, bay, STYLES[style]); z = th
    tw, td = tiers[-1][0], tiers[-1][1]
    if crown:
        r = R.random()
        if r < .3: A.box("metalattr", x, y, h, tw * .6, td * .6, 5, rot, col=(.35, .37, .4))
        elif r < .5: A.cyl("metal", x, y, h, 18, .5, 6, r2=.05)
        elif r < .65:
            A.cyl("concrete", x, y, h, .4, min(tw, td) * .38, 24)
            A.box("paint_w", x, y, h + .41, 5, 1, .01, rot, sides=False)
        roof_clutter(x, y, rot, tw * .9, td * .9, h, "std")
    if slot: SLOTS.append((slot[0], slot[1], (x, y, h * .62)))

def midrise(x, y, rot, w, d, floors, style, shop=True):
    fh = 3.3; h = floors * fh + .6
    gridded(x, y, rot, w, d, 0, h, fh, R.uniform(2.4, 3.0), STYLES[style])
    A.box("wall", x, y, h - .2, w + .5, d + .5, .7, rot, col=tuple(c * .9 for c in STYLES[style][0]), top="roof")  # corniche
    roof_clutter(x, y, rot, w - .5, d - .5, h + .5, "wt")
    return h

WALLS_H = [(.8, .78, .72), (.72, .66, .55), (.6, .55, .5), (.82, .8, .78), (.55, .6, .62), (.7, .62, .5), (.78, .7, .6), (.62, .5, .42)]
ROOFS_H = [(.35, .12, .07), (.18, .18, .19), (.28, .24, .22), (.42, .2, .12), (.12, .13, .15)]

def hip(x, y, z0, w, d, rh, rot, col, over=.4):
    """toit à quatre pans"""
    c, s_ = math.cos(rot), math.sin(rot)
    P = lambda lx, ly, z: (x + lx * c - ly * s_, y + lx * s_ + ly * c, z)
    hw, hd = w / 2 + over, d / 2 + over; k = max(0., hw - hd)
    a, b, cc, dd = P(-hw, -hd, z0), P(hw, -hd, z0), P(hw, hd, z0), P(-hw, hd, z0)
    r0, r1 = P(-k, 0, z0 + rh), P(k, 0, z0 + rh)
    for q in ([a, b, r1, r0], [cc, dd, r0, r1]): A.face("roof", q, None, col)
    A.face("roof", [b, cc, r1], None, col); A.face("roof", [dd, a, r0], None, col)

def house(x, y, rot, w, d):
    """une maison : à deux pans, à quatre pans, en L, ou moderne à toit plat"""
    kind = R.choices(["gable", "hip", "L", "flat"], [4, 3, 2, 1.2])[0]
    floors = 1 if R.random() < .35 else 2
    h = floors * 3.0 + .3
    wc, rc = R.choice(WALLS_H), R.choice(ROOFS_H)
    c, s_ = math.cos(rot), math.sin(rot)
    A.box("facade", x, y, 0, w, d, h, rot, col=wc, top="roof", fh=3.0, bay=2.6, uoff=R.random())
    if kind == "gable":
        rh = min(w, d) * .38; A.gable("roof", x, y, h, w, d, rh, rot, rc); A.gable_ends("wall", x, y, h, w, d, rh, rot, wc)
    elif kind == "hip":
        hip(x, y, h, w, d, min(w, d) * .36, rot, rc)
    elif kind == "L":
        rh = min(w, d) * .38; A.gable("roof", x, y, h, w, d, rh, rot, rc); A.gable_ends("wall", x, y, h, w, d, rh, rot, wc)
        ex, ey = x + (w * .3) * c - (d * .55) * s_, y + (w * .3) * s_ + (d * .55) * c
        A.box("facade", ex, ey, 0, w * .4, d * .7, h - (3 if floors == 2 else 0), rot, col=wc, top="roof", fh=3.0, bay=2.6)
        hh = h - (3 if floors == 2 else 0)
        A.gable("roof", ex, ey, hh, d * .7, w * .4, w * .16, rot + math.pi / 2, rc)
    else:   # moderne : toit-terrasse, bardage bois, grande baie
        A.box("wood", x + w * .1 * c, y + w * .1 * s_, h, w * .6, d * .8, 3.0, rot, top="roof")
        A.box("wall", x, y, h - .05, w + .3, d + .3, .3, rot, col=(.85, .84, .8), top="roof")
    if kind != "flat" and R.random() < .25:
        A.box("solar", x - s_ * d * .22, y + c * d * .22, h + min(w, d) * .17, w * .5, d * .22, .1, rot, top="solar", sides=False)

def townhouses(x, y, rot, L, d):
    """rangée de maisons de ville mitoyennes (façades de couleurs différentes)"""
    n = max(2, int(L / 6.5)); uw = L / n; c, s_ = math.cos(rot), math.sin(rot)
    for k in range(n):
        t = -L / 2 + uw * (k + .5)
        hx, hy = x + t * c, y + t * s_
        h = R.choice([6.6, 6.6, 9.6])
        A.box("facade", hx, hy, 0, uw - .1, d, h, rot, col=R.choice(WALLS_H), top="roof", fh=3.2, bay=2.2)
        A.gable("roof", hx, hy, h, uw - .1, d, d * .3, rot, R.choice(ROOFS_H[:3]), over=.1)

# ═══════════════════════════════════════ bâtiments en forme de lettres
def shape_parts(shape, W, D):
    """la forme (vue de dessus) en rectangles locaux (u, v, largeur, profondeur, angle), dans un lot W x D"""
    t = max(9., min(W, D) * .36)
    if shape == "I": return [(0, 0, W, D, 0)]
    if shape == "L": return [(0, -D / 2 + t / 2, W, t, 0), (-W / 2 + t / 2, 0, t, D, 0)]
    if shape == "U": return [(0, -D / 2 + t / 2, W, t, 0), (-W / 2 + t / 2, 0, t, D, 0), (W / 2 - t / 2, 0, t, D, 0)]
    if shape == "T": return [(0, D / 2 - t / 2, W, t, 0), (0, 0, t, D, 0)]
    if shape == "X": return [(0, 0, W, t, 0), (0, 0, t, D, 0)]
    if shape == "H": return [(-W / 2 + t / 2, 0, t, D, 0), (W / 2 - t / 2, 0, t, D, 0), (0, 0, W, t, 0)]
    if shape == "O": return [(0, -D / 2 + t / 2, W, t, 0), (0, D / 2 - t / 2, W, t, 0), (-W / 2 + t / 2, 0, t, D, 0), (W / 2 - t / 2, 0, t, D, 0)]
    if shape == "E": return [(-W / 2 + t / 2, 0, t, D, 0), (0, -D / 2 + t * .45, W, t * .9, 0), (0, 0, W * .8, t * .8, 0), (0, D / 2 - t * .45, W, t * .9, 0)]
    if shape == "B":   # un dos droit et deux ventres arrondis
        return [(-W / 2 + t / 2, 0, t, D, 0), (0, -D / 4, W * .75, D / 2 - 1, 0), (0, D / 4, W * .65, D / 2 - 1, 0), ("cyl", W * .37, -D / 4, D / 4 - .5), ("cyl", W * .32, D / 4, D / 4 - .5)]
    if shape == "V":
        a = math.atan2(W * .35, D)
        return [(-W * .2, 0, t * .9, D / math.cos(a), -a), (W * .2, 0, t * .9, D / math.cos(a), a)]
    if shape == "Z": return [(-W / 4, D / 2 - t / 2, W / 2 + t / 2, t, 0), (0, 0, t, D, 0), (W / 4, -D / 2 + t / 2, W / 2 + t / 2, t, 0)]
    if shape == "Y":
        return [(0, -D / 4, t, D / 2, 0), (-W * .2, D / 4, t * .85, D * .6, .5), (W * .2, D / 4, t * .85, D * .6, -.5)]
    return [(0, 0, W, D, 0)]

ALL_SHAPES = ["I", "L", "U", "T", "X", "H", "O", "E", "B", "V", "Z", "Y"]
PLACED = []    # (x, y, forme, style) : deux voisins n'ont jamais la même forme ni le même parement
def pick_shape(x, y, W, D, radius=60., allowed=ALL_SHAPES, taboo_style=None):
    near = [p for p in PLACED if math.hypot(p[0] - x, p[1] - y) < radius]
    shapes = [s_ for s_ in allowed if s_ not in {p[2] for p in near}]
    if min(W, D) < 26: shapes = [s_ for s_ in shapes if s_ in ("I", "L", "T", "Z")] or shapes
    if not shapes: shapes = [s_ for s_ in allowed if s_ != (near[-1][2] if near else None)]
    sh = R.choice(shapes)
    styles = [k for k in ("brick", "brick2", "stone", "stucco", "office", "dark", "glass", "glass2") if k not in {p[3] for p in near[-3:]}]
    return sh, styles

def shaped(x, y, rot, W, D, shape, h, style, fh=3.3, tower_=False):
    """construit la forme : chaque branche a sa grille de fenêtres en creux, parfois une hauteur différente"""
    c, s_ = math.cos(rot), math.sin(rot)
    top = h
    for k, part in enumerate(shape_parts(shape, W, D)):
        hk = h * (1 if k == 0 or not R.random() < .45 else R.uniform(.7, .92)) + k * .07
        if part[0] == "cyl":
            _, lu, lv, r = part
            px, py = x + lu * c - lv * s_, y + lu * s_ + lv * c
            A.cyl("glass", px, py, 0, hk, r, 20, col=STYLES[style][1], top=False)
            for j in range(1, int(hk / fh) + 1):
                A.cyl("wall", px, py, j * fh - .6, 1.2, r + .35, 20, col=STYLES[style][0], cap="wall")
            A.cyl("roof", px, py, hk, .01, r + .35, 20, col=(.3, .3, .3))
            continue
        lu, lv, w, d, a = part
        px, py = x + lu * c - lv * s_, y + lu * s_ + lv * c
        gridded(px, py, rot + a, w, d, 0, hk, fh, R.uniform(2.5, 3.2), STYLES[style])
        if not tower_:
            A.box("wall", px, py, hk - .2, w + .5, d + .5, .7, rot + a, col=tuple(cc * .9 for cc in STYLES[style][0]), top="roof")
        roof_clutter(px, py, rot + a, w - .6, d - .6, hk + (.5 if not tower_ else 0), "wt" if not tower_ else "std")
    PLACED.append((x, y, shape, style))
    claim(x, y, W, D, rot)

def bez(p0, p1, p2, p3, n):
    out = []
    for k in range(n + 1):
        t = k / n; a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; d = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


# ═══════════════════════════════════════ lotissements organiques
FRAME = (-840, -960, 840, 560)
def in_frame(x, y): return FRAME[0] < x < FRAME[2] and FRAME[1] < y < FRAME[3] and y < SHORE(x) - 55
def in_nature(x, y): return in_nature_(x, y)

HOUSES = 0
LOTS = set()           # cellules des parcelles : le relief est aplani dessous
def hedge(p0, p1, h=1.0, style="haie"):
    """limite de parcelle : haie (le plus souvent), palissade en bois ou muret"""
    L = math.dist(p0, p1)
    if L < .5: return
    x, y, r = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    if style == "haie": A.box("painted", x, y, 0, L + .5, .7, h + R.uniform(-.1, .25), r, col=(.06 + R.uniform(-.01, .02), .16 + R.uniform(-.02, .03), .05))
    elif style == "bois": A.box("wood", x, y, 0, L + .1, .12, 1.6, r, top="wood")
    else: A.box("wall", x, y, 0, L + .3, .3, .9, r, col=(.72, .68, .6), top="concrete")

GARDENS = ["pelouse", "piscine", "potager", "terrasse", "jeux", "fleurs", "verger", "mineral"]
GARDEN_W = [2.5, 1.6, 1.2, 1.6, 1.2, 1.3, 1.0, .8]
def parasol(x, y):
    A.cyl("dark", x, y, 0, 2.3, .05, 6, top=False)
    A.cyl("painted", x, y, 2.0, .45, 1.5, 8, r2=.05, col=R.choice([(.85, .85, .8), (.75, .2, .12), (.12, .3, .55), (.9, .7, .15)]))

def garden(P, F, fg, hd, D, uh, hw):
    """le jardin de derrière : un style par maison, pour que deux voisins ne se ressemblent pas"""
    v0, v1 = fg + hd + .8, D - 1.2; back = v1 - v0
    u0, u1 = -F / 2 + 1.2, F / 2 - 1.2
    if back < 3.5: return
    st = R.choices(GARDENS, GARDEN_W)[0]
    if st == "piscine" and (back < 8 or F < 12): st = "terrasse"
    rot = math.atan2(P(1, 0)[1] - P(0, 0)[1], P(1, 0)[0] - P(0, 0)[0])
    tree = lambda u, v, sc=(.6, 1.): inst(R.choice(TREES), *P(u, v), 0, R.uniform(0, 6), R.uniform(*sc))
    if st in ("terrasse", "piscine", "jeux") or R.random() < .35:        # terrasse en bois contre la maison
        tw = min(hw, 7.); A.box("wood", *P(uh, v0 + 1.4), 0, tw, 2.8, .14, rot, top="wood")
        if R.random() < .7:
            tx, ty = P(uh + R.uniform(-1, 1), v0 + 1.4); A.cyl("white", tx, ty, 0, .75, .55, 10)
            if st == "terrasse": parasol(tx, ty)
    if st == "pelouse":
        for k in range(R.randint(1, 3)): tree(R.uniform(u0 + 1.5, u1 - 1.5), R.uniform(v0 + 3.5, v1 - 1))
    elif st == "piscine":
        pw, pd = min(7.5, F - 5.5), min(3.8, back - 4.2); px, py = P(uh * .3, v0 + 3.2 + pd / 2 + .6)
        A.box("white", px, py, 0, pw + 1.4, pd + 1.4, .07, rot, sides=False); A.box("pool", px, py, 0, pw, pd, .08, rot, sides=False)
        for k in (-1, 1): A.box("white", *P(uh * .3 + k * 1.2, v0 + 2.4), .08, .7, 1.9, .3, rot + math.pi / 2)
        if back > 11: tree(u1 - 1.5, v1 - 1)
    elif st == "potager":
        dw, dd = F - 4, min(6.5, back - 1.5); cx, cy = P(0, v1 - dd / 2)
        A.box("dirt", cx, cy, 0, dw, dd, .09, rot, sides=False)
        for k in range(int(dd / 1.1)):
            A.box("painted", *P(0, v1 - .6 - k * 1.1), .09, dw - .8, .45, .28, rot, col=(.1 + R.uniform(0, .08), .3 + R.uniform(-.05, .08), .06))
        if F > 13: A.box("white", *P(u0 + 1.6, v0 + 1.8), 0, 2.6, 2.0, 2.1, rot, col=(.85, .9, .88), top="white")   # serre
    elif st == "jeux":
        tx, ty = P(R.uniform(u0 + 2.5, u1 - 2.5), v1 - 2.6)
        A.cyl("painted", tx, ty, 0, .9, 1.8, 16, col=(.1, .45, .2)); A.cyl("dark", tx, ty, .9, .02, 1.6, 16)      # trampoline
        sx, sy = P(R.uniform(u0 + 1.5, u1 - 1.5), v0 + back * .55)
        A.box("painted", sx, sy, 2.1, 3.2, .12, .12, rot, col=(.75, .2, .1))                                   # portique
        for k in (-1.5, 1.5):
            qx, qy = sx + math.cos(rot) * k, sy + math.sin(rot) * k
            A.box("painted", qx, qy, 0, .12, .12, 2.1, rot, col=(.75, .2, .1))
    elif st == "fleurs":
        for k in range(int((u1 - u0) / 1.3)):
            A.box("painted", *P(u0 + .7 + k * 1.3, v1 - .5), 0, 1.2, .9, .35, rot, col=R.choice(FLOWERS))
        for k in range(int(back / 1.6)):
            A.box("painted", *P(u1 - .5, v0 + .8 + k * 1.6), 0, .9, 1.5, .35, rot, col=R.choice(FLOWERS))
        tree(R.uniform(u0 + 2, u1 - 3), R.uniform(v0 + 2, v1 - 2))
    elif st == "verger":
        nu, nv = max(1, int((u1 - u0) / 4.5)), max(1, int(back / 4.5))
        for i in range(nu):
            for j in range(nv): tree(u0 + (i + .5) * (u1 - u0) / nu, v0 + (j + .5) * back / nv, (.4, .55))
    else:   # minéral : graviers, conifères taillés
        cx, cy = P(0, (v0 + v1) / 2); A.box("plaza", cx, cy, 0, u1 - u0, back, .06, rot, sides=False)
        for k in range(R.randint(2, 4)):
            inst(R.choice(PINES), *P(R.uniform(u0 + 1, u1 - 1), R.uniform(v0 + 1, v1 - 1)), 0, R.uniform(0, 6), R.uniform(.3, .45))
    if R.random() < .3 and st not in ("potager",):
        A.box("wood", *P(R.choice([u0 + 1.4, u1 - 1.4]), v1 - 1.2), 0, 2.4, 2.0, 2.2, rot, top="roof")      # abri de jardin

def lot(x0, y0, t, n, F, D, ok_town=False, first=True, defer=False):
    """une parcelle pavillonnaire, devant = côté rue (x0, y0 = milieu du bord avant, t = sens de la rue, n = vers le fond) :
    jardin devant, allée + voiture, maison, jardin derrière (un style par maison), limites partagées avec les voisins"""
    global HOUSES
    rot = math.atan2(n[1], n[0]) - math.pi / 2          # axe local x le long de la rue, y vers le fond
    P = lambda u, v: (x0 + t[0] * u + n[0] * v, y0 + t[1] * u + n[1] * v)
    ds = R.choice([-1, 1])                                # côté de l'allée
    bstyle = R.choices(["haie", "bois", "muret"], [6, 2, 1])[0]
    if ok_town:
        L_ = F - 1.5; hx, hy = P(0, 3.5 + 5)
        townhouses(hx, hy, rot, L_, 10)
        for k in range(int(L_ / 6.5)):
            if R.random() < .6: car_at(*P(-L_ / 2 + 3.2 + k * 6.5, 1.6), rot, parked=True)
        for k in range(int(L_ / 6.5)):              # petits jardins de derrière, séparés par des haies
            u = -L_ / 2 + k * 6.5
            if k: hedge(P(u, 14), P(u, D), .9)
            if R.random() < .5: inst(R.choice(TREES), *P(u + 3.2, D - 3), 0, R.uniform(0, 6), R.uniform(.5, .75))
            elif R.random() < .5: A.box("wood", *P(u + 3.2, 15.5), 0, 4, 2.5, .12, rot, top="wood")
    else:
        fg = R.uniform(4.5, 6.5) if D >= 24 else 3.6
        hw = min(R.uniform(8.5, 11.5), F - 5.2); hd = min(R.uniform(7.5, 10), D - fg - 4.5)
        uh = -ds * (F / 2 - .9 - hw / 2)
        hx, hy = P(uh, fg + hd / 2)
        house(hx, hy, rot, hw, hd)
        ud = ds * (F / 2 - .7 - 1.6)
        dl = fg + hd * .8
        A.box(R.choice(["concrete", "concrete", "plaza"]), *P(ud, dl / 2), 0, 3.2, dl, .06, rot, sides=False)
        if R.random() < .8:
            car_at(*P(ud, fg - 1.2 if R.random() < .5 else fg + 2.8), rot + math.pi / 2 + (math.pi if R.random() < .5 else 0), parked=True)
        A.box("concrete", *P(uh, fg / 2), 0, 1.1, fg, .055, rot, sides=False)       # allée piétonne jusqu'à la porte
        # le devant : massif de fleurs le long de la façade, arbre, ou clôture basse
        fr = R.random()
        if fr < .4:
            for k in range(int((hw - 2) / 1.2)):
                u = uh - hw / 2 + .8 + k * 1.2
                if abs(u - uh) > .9: A.box("painted", *P(u, fg - .6), 0, 1.1, .8, .3, rot, col=R.choice(FLOWERS))
        elif fr < .7: inst(R.choice(TREES), *P(-ds * (F / 2 - 2.2), fg * .5), 0, R.uniform(0, 6), R.uniform(.5, .75))
        if R.random() < .3:                          # clôture basse blanche, ouverte devant l'allée et le chemin
            for a_, b_ in ((-F / 2, min(ud, uh) - 1.8), (min(ud, uh) + 1.8, max(ud, uh) - 1.8), (max(ud, uh) + 1.8, F / 2)):
                if b_ - a_ > .6: A.box("white", *P((a_ + b_) / 2, .5), 0, b_ - a_, .1, .8, rot, top="white")
        garden(P, F, fg, hd, D, uh, hw)
    # limites : le fond, et le côté « suivant » ; le côté « précédent » seulement en début de rangée (sinon c'est celle du voisin)
    hedge(P(-F / 2, D), P(F / 2, D), style=bstyle)
    hedge(P(F / 2, fg if not ok_town else 14), P(F / 2, D), style=bstyle)
    if first: hedge(P(-F / 2, fg if not ok_town else 14), P(-F / 2, D), style=bstyle)
    cx, cy = P(0, D / 2)
    cells = cells_of_rect(cx, cy, F, D, rot)
    LOTS.update(cells_of_rect(cx, cy, F, D, rot, 2)); HOUSES += 1
    if defer: return cells
    BUSY.update(cells)

def rects_overlap(a, b, shrink=.4):
    """deux rectangles orientés (cx, cy, w, d, rot) se recouvrent-ils ? (axes séparateurs)"""
    def corners(r):
        cx, cy, w, d, rot = r; c, s_ = math.cos(rot), math.sin(rot); w, d = w / 2 - shrink, d / 2 - shrink
        return [(cx + u * c - v * s_, cy + u * s_ + v * c) for u, v in ((-w, -d), (w, -d), (w, d), (-w, d))]
    A_, B_ = corners(a), corners(b)
    for r in (a, b):
        for ax in ((math.cos(r[4]), math.sin(r[4])), (-math.sin(r[4]), math.cos(r[4]))):
            pa = [p[0] * ax[0] + p[1] * ax[1] for p in A_]; pb = [p[0] * ax[0] + p[1] * ax[1] for p in B_]
            if max(pa) < min(pb) or max(pb) < min(pa): return False
    return True

def lots_along(pts, road_w, walk, ok, town_p=0., fronts=(17, 15, 13), depths=(30, 25, 20, 16)):
    """remplissage dynamique : on avance le long de la rue et on case la plus grande parcelle qui tient, sinon
    une plus petite, sinon on glisse de 2 m. Les parcelles d'une même rangée se touchent : haies mitoyennes."""
    if len(pts) < 2: return
    L = length(pts); C = cum(pts); H = road_w / 2 + walk + .6
    for side in (-1, 1):
        s_ = 1.; run = []; pend = set(); prev_end = -99.
        while s_ < L - 6:
            placed = False
            town = R.random() < town_p
            for F in ((R.uniform(24, 34),) + tuple(fronts) if town else fronts):
                if s_ + F > L: continue
                p, t, _ = at(pts, s_ + F / 2, C); n = (-t[1] * side, t[0] * side)
                for D in ((20,) if F > 20 else depths):
                    x0, y0 = p[0] + n[0] * H, p[1] + n[1] * H
                    # le bord avant touche le trottoir : on ne vérifie qu'à partir de 5 m (les cellules « route » débordent)
                    cx, cy = x0 + n[0] * (D + 6.5) / 2, y0 + n[1] * (D + 6.5) / 2
                    rot = math.atan2(n[1], n[0]) - math.pi / 2
                    corners = [(x0 + t[0] * u + n[0] * v, y0 + t[1] * u + n[1] * v) for u in (-F / 2 + .5, 0, F / 2 - .5) for v in (7, (D + 6.5) / 2, D)]
                    me = (x0 + n[0] * D / 2, y0 + n[1] * D / 2, F, D, rot)
                    if all(ok(*q) for q in corners) and free(cx, cy, F - .6, D - 6.9, rot) and not any(rects_overlap(me, r) for r in run[-3:]):
                        pend |= lot(x0, y0, t, n, F, D, F > 20, first=abs(s_ - prev_end) > .1, defer=True)
                        run.append(me); placed = True; prev_end = s_ + F; break
                if placed: break
            s_ += F if placed else 2.
        BUSY.update(pend)

# ═══════════════════════════════════════ quartiers : remplissage
def fill_bureaux(z, blocks=None):
    blocks = build_grid_streets(z) if blocks is None else blocks
    best = None
    for b in blocks:
        u0, u1, v0, v1 = b
        block_pad(z, b, "plaza")
        block_props(z, b)
        cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
        x, y = z.w(cu, cv)
        dc = math.hypot(cu, cv) / math.hypot(*z.h)
        hmax = max(90, 240 - 330 * dc)
        bw, bd = u1 - u0 - 12, v1 - v0 - 12
        r = R.random()
        if r < .6:
            w, d = bw * R.uniform(.6, .82), bd * R.uniform(.6, .82)
            h = R.uniform(.7, 1) * hmax
            sh, styles = pick_shape(x, y, w, d, 90, ["I", "L", "X", "T", "V", "Y", "H", "B"])
            st = R.choice([k for k in styles if k in ("glass", "glass2", "office", "dark")] or ["glass"])
            if sh == "I":
                tower(x, y, z.rot, w, d, h, st, setbacks=R.choice([0, 1, 2])); PLACED.append((x, y, "I", st)); claim(x, y, w + 8, d + 8, z.rot)
            else:
                gridded(x, y, z.rot, w + 6, d + 6, 0, 12, 4.5, 4, STYLES["office" if st != "dark" else "dark"])
                shaped(x, y, z.rot, w, d, sh, h, st, 3.9, tower_=True)
            if best is None or h > best[0]: best = (h, x, y, w, d, st)
        elif r < .85:
            for sgn in (-1, 1):
                w, d = bw * .42, bd * .6
                tx, ty = z.w(cu + sgn * bw * .25, cv + R.uniform(-4, 4))
                tower(tx, ty, z.rot, w, d, R.uniform(.45, .8) * hmax, R.choice(["glass", "office", "glass2"]))
        else:
            # petite place : fontaine, arbres, un pavillon vitré
            A.cyl("concrete", x, y, .18, .5, 7, 32); A.cyl("water", x, y, .18, .55, 6.3, 32)
            for k in range(8):
                a = k / 8 * 6.283; inst(R.choice(TREES), x + math.cos(a) * 14, y + math.sin(a) * 14, .18, a, .9)
            for k in range(4):
                a = k / 4 * 6.283 + .4; bench(x + math.cos(a) * 9.5, y + math.sin(a) * 9.5, a + 1.57)
    # la plus haute tour devient un emplacement de projet
    if best: SLOTS.append(("tour", "Tour de bureaux", (best[1], best[2], best[0] * .6)))

def construction_site(z, b):
    u0, u1, v0, v1 = b
    x, y = z.w((u0 + u1) / 2, (v0 + v1) / 2)
    prism("dirt", rounded_rect(z, u0, u1, v0, v1), .25)
    w, d = (u1 - u0) * .6, (v1 - v0) * .55
    c, s = math.cos(z.rot), math.sin(z.rot)
    floors = 7
    for f in range(floors + 1):
        if f <= 5: A.box("concrete", x, y, .25 + f * 3.4, w, d, .35, z.rot)
    for i in range(6):
        for j in range(4):
            lu, lv = -w / 2 + w * i / 5, -d / 2 + d * j / 3
            A.box("concrete", x + lu * c - lv * s, y + lu * s + lv * c, .25, .5, .5, 5 * 3.4 + .35, z.rot, top="concrete")
    # grue à tour
    gx, gy = z.w(u1 - 8, v0 + 8)
    A.box("painted", gx, gy, 0, 1.6, 1.6, 58, 0, col=(.85, .6, .05))
    ja = .5; jc, js = math.cos(ja), math.sin(ja)
    A.box("painted", gx + 18 * jc, gy + 18 * js, 58, 48, 1.4, 1.4, ja, col=(.85, .6, .05))
    A.box("concrete", gx - 9 * jc, gy - 9 * js, 56.5, 6, 2.6, 2.4, ja)
    A.cyl("dark", gx + 30 * jc, gy + 30 * js, 20, 38, .05, 4, top=False)
    for k in range(5):
        hx, hy = z.w(u0 + 5 + k * 6.5, v1 - 5)
        A.box("painted", hx, hy, .25, 6, 2.5, 2.6, z.rot, col=R.choice([(.9, .9, .9), (.2, .35, .6), (.8, .5, .1)]))
    for k in range(3):
        px, py = z.w(u0 + 8 + k * 8, (v0 + v1) / 2)
        A.box("dirt", px, py, .25, 5, 5, 2.2, z.rot + k, top="dirt")

def fill_haute(z, chantier=False, blocks=None):
    blocks = build_grid_streets(z) if blocks is None else blocks
    site = R.randrange(len(blocks)) if chantier else -1
    for bi, b in enumerate(blocks):
        u0, u1, v0, v1 = b
        block_pad(z, b)
        block_props(z, b)
        if bi == site: construction_site(z, b); continue
        iu0, iu1, iv0, iv1 = u0 + 4.5, u1 - 4.5, v0 + 4.5, v1 - 4.5
        if R.random() < .7:
            # 1 à 3 bâtiments en forme de lettre par îlot
            n = R.choice([1, 2, 2, 3]) if (iu1 - iu0) > 60 else R.choice([1, 2])
            lw = (iu1 - iu0) / n
            for k in range(n):
                cu = iu0 + lw * (k + .5); cv = (iv0 + iv1) / 2
                W, Dd = lw - 4, iv1 - iv0 - 2
                x, y = z.w(cu, cv)
                sh, styles = pick_shape(x, y, W, Dd, 70)
                st = R.choice([k2 for k2 in styles if k2 in ("brick", "brick2", "stone", "stucco", "office")] or ["brick"])
                shaped(x, y, z.rot, W, Dd, sh, R.randint(5, 15) * 3.3 + .6, st)
                if sh in ("U", "O", "H", "E"):
                    A.box("grass", x, y, .19, W * .35, Dd * .3, .04, z.rot, top="grass", sides=False)
            continue
        D = R.uniform(14, 18)
        placed = []
        def ok(r):
            return all(r[1] <= q[0] or r[0] >= q[1] or r[3] <= q[2] or r[2] >= q[3] for q in placed)
        # rangées sur les 4 côtés de l'îlot
        for side in range(4):
            t = iu0 if side in (0, 2) else iv0
            tend = iu1 if side in (0, 2) else iv1
            while t < tend - 6:
                wl = R.uniform(9, 22); te = min(tend, t + wl)
                if tend - te < 7: te = tend
                if side == 0: r = (t, te, iv0, iv0 + D)
                elif side == 2: r = (t, te, iv1 - D, iv1)
                elif side == 1: r = (iu1 - D, iu1, t, te)
                else: r = (iu0, iu0 + D, t, te)
                if ok(r):
                    placed.append(r)
                    cu, cv = (r[0] + r[1]) / 2, (r[2] + r[3]) / 2
                    x, y = z.w(cu, cv)
                    midrise(x, y, z.rot, r[1] - r[0], r[3] - r[2], R.randint(5, 13), R.choice(["brick", "brick2", "stone", "stucco", "brick"]))
                    claim(x, y, r[1] - r[0], r[3] - r[2], z.rot)
                t = te
        # cour intérieure
        cu, cv = (iu0 + iu1) / 2, (iv0 + iv1) / 2
        cw, cd = iu1 - iu0 - 2 * D - 2, iv1 - iv0 - 2 * D - 2
        if cw > 6 and cd > 6:
            x, y = z.w(cu, cv)
            A.box("grass", x, y, .18, cw, cd, .05, z.rot, top="grass", sides=False)
            for k in range(int(cw * cd / 120) + 1):
                tx, ty = z.w(cu + R.uniform(-cw / 2 + 2, cw / 2 - 2), cv + R.uniform(-cd / 2 + 2, cd / 2 - 2))
                inst(R.choice(TREES), tx, ty, .2, R.uniform(0, 6.3), R.uniform(.7, 1))

UNIQUES = ["theatre", "cinema", "musee", "opera", "bibliotheque", "hotel_de_ville"]
NOMS = {"mairie": "Mairie", "eglise": "Église", "ecole": "École", "clinique": "Clinique", "gymnase": "Gymnase",
        "supermarche": "Supermarché", "station": "Station-service", "theatre": "Théâtre", "cinema": "Cinéma", "musee": "Musée", "opera": "Opéra", "bibliotheque": "Bibliothèque",
        "hotel_de_ville": "Hôtel de ville", "stade": "Stade", "amphi": "Amphithéâtre", "tour": "Tour de bureaux",
        "entrepot": "Entrepôt", "usine": "Usine", "loft": "Loft", "maison": "Maison"}

def unique_building(kind, x, y, rot, w, d):
    c, s = math.cos(rot), math.sin(rot)
    P = lambda lu, lv, dz=0: (x + lu * c - lv * s, y + lu * s + lv * c)
    if kind == "theatre":
        A.box("wall", x, y, 0, w * .7, d * .6, 20, rot, col=(.72, .66, .56), top="roof")
        fx, fy = P(0, d * .12); A.box("wall", fx, fy, 20, w * .5, d * .25, 10, rot, col=(.68, .62, .52), top="roof")   # cage de scène
        px, py = P(0, -d * .3 - 4)
        A.box("wall", px, py, 0, w * .5, 8, 1.5, rot, col=(.78, .74, .66), top="plaza")                              # emmarchement
        for k in range(8):
            cx_, cy_ = P(-w * .22 + k * w * .44 / 7, -d * .3 - 5.5)
            A.cyl("white", cx_, cy_, 1.5, 13, .75, 12)
        A.box("wall", px, py, 14.5, w * .5, 8, 1.6, rot, col=(.78, .74, .66), top="roof")
        tx, ty = P(0, -d * .3 - 5.5); A.gable("wall", tx, ty, 16.1, w * .5, 7, 4, rot + 0, (.78, .74, .66), over=0)
        return 22
    if kind == "cinema":
        A.box("painted", x, y, 0, w * .75, d * .6, 17, rot, col=(.08, .08, .1), top="roof")
        mx, my = P(0, -d * .3 - .6); A.box("sign", mx, my, 9, w * .6, 1.2, 4, rot, top="sign")          # enseigne lumineuse
        bx, by = P(w * .3, -d * .3 - 1.5); A.box("signred", bx, by, 5, 1, 2.5, 16, rot, top="signred")  # enseigne verticale
        cx_, cy_ = P(0, -d * .3 - 4); A.box("dark", cx_, cy_, 4.5, w * .5, 7, .5, rot, top="painted", col=(.7, .1, .08))  # marquise
        roof_clutter(x, y, rot, w * .7, d * .55, 17)
        return 19
    if kind == "musee":
        for i in range(5):
            A.cyl("white", x, y, i * 4, 4, min(w, d) * .22 + i * 1.8, 48)
            A.cyl("carglass", x, y, i * 4 + 3, .7, min(w, d) * .22 + i * 1.8 + .05, 48, top=False)
        A.dome("glass", x, y, 20, min(w, d) * .22 + 6, 3, 32, 4, col=(.4, .5, .55))
        return 23
    if kind == "opera":
        A.box("wall", x, y, 0, w * .8, d * .55, 5, rot, col=(.75, .7, .62), top="plaza")
        for k, (sc, hh) in enumerate(((1, 26), (.8, 21), (.6, 15))):
            ox, oy = P(-w * .2 + k * w * .2, 0)
            A.dome("white", ox, oy, 5, 14 * sc, hh, 24, 7, col=(.9, .9, .88))
        return 30
    if kind == "bibliotheque":
        A.box("wall", x, y, 0, w * .8, d * .5, 16, rot, col=(.66, .62, .55), top="roof")
        for k in range(14):
            cx_, cy_ = P(-w * .38 + k * w * .76 / 13, -d * .25 - 2)
            A.cyl("white", cx_, cy_, 0, 14, .6, 10)
        px, py = P(0, -d * .25 - 2); A.box("wall", px, py, 14, w * .8, 4.5, 2, rot, col=(.72, .68, .6), top="roof")
        gx, gy = P(0, 0); A.box("glass", gx, gy, 16, w * .6, 4, .5, rot, col=(.3, .4, .45), top="glass")
        return 18
    if kind == "hotel_de_ville":
        A.box("facade", x, y, 0, w * .8, d * .5, 18, rot, col=(.74, .7, .62), top="roof", fh=4.5, bay=3.4)
        A.box("wall", x, y, 18, 14, 14, 10, rot, col=(.74, .7, .62), top="roof")
        A.cyl("wall", x, y, 28, 5, 6.5, 24, col=(.74, .7, .62))
        A.dome("metalattr", x, y, 33, 6.5, 8, 24, 6, col=(.25, .45, .4))
        A.cyl("metal", x, y, 41, 6, .12, 6)
        return 45
    return 10

def fill_unique(z, blocks=None, kinds=None):
    blocks = build_grid_streets(z) if blocks is None else blocks
    kinds = kinds or UNIQUES
    for n, b in enumerate(blocks): landmark_block(z, b, kinds[n % len(kinds)])

def stadium(x, y, rot, a, b):
    A.cyl("concrete", x, y, 0, 3, a + 6, 48, rx=1, ry=b / a, top=False)
    seg = 48
    for ring in range(6):   # gradins en anneaux qui montent
        r0 = a + ring * 2.2; z0 = 3 + ring * 2.2
        A.cyl("painted", x, y, z0 - 2.2, 2.2, r0 + 2.2, seg, col=(.55, .1, .08) if ring % 2 else (.62, .6, .58), rx=1, ry=b / a, r2=r0 + 2.2, top=False)
        pts = [(x + (r0 + 2.2) * math.cos(2 * math.pi * k / seg), y + (r0 + 2.2) * b / a * math.sin(2 * math.pi * k / seg), z0) for k in range(seg)]
        pin = [(x + r0 * math.cos(2 * math.pi * k / seg), y + r0 * b / a * math.sin(2 * math.pi * k / seg), z0 - 2.2) for k in range(seg)]
        for k in range(seg):
            k2 = (k + 1) % seg
            A.face("painted", [pin[k], pin[k2], pts[k2], pts[k]], None, (.75, .74, .72) if ring % 2 == 0 else (.62, .12, .1))
    A.cyl("painted", x, y, 0, 16.2, a + 13.4, seg, col=(.85, .85, .84), rx=1, ry=b / a, top=False)
    # pelouse
    pw, pd = a * 1.2, b * 1.1
    A.box("pitch", x, y, 0, pw, pd, .3, rot, top="pitch", sides=False)
    for dx in (-pw / 2, 0, pw / 2): A.box("paint_w", x + dx * math.cos(rot), y + dx * math.sin(rot), .31, .25, pd, .01, rot, sides=False)
    A.cyl("paint_w", x, y, .31, .01, 6, 24, top=False)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):   # projecteurs
        px, py = x + sx * (a + 16), y + sy * (b + 10)
        A.cyl("metal", px, py, 0, 38, .5, 8)
        A.box("flood", px, py, 38, 5, 1.2, 3, math.atan2(-sy, -sx) + 1.57, top="flood")
        if NIGHT > 0: A.disc_decal("floodpool", x + sx * a * .4, y + sy * b * .4, .35, a * 1.3)

def amphitheatre(x, y, rot, r):
    for k in range(7):
        rr = r * .35 + k * r * .09
        pts_o = [(x + (rr + r * .09) * math.cos(rot + math.pi * t / 20), y + (rr + r * .09) * math.sin(rot + math.pi * t / 20)) for t in range(21)]
        pts_i = [(x + rr * math.cos(rot + math.pi * t / 20), y + rr * math.sin(rot + math.pi * t / 20)) for t in range(21)]
        zz = .3 + k * .9
        for t in range(20):
            A.face("concrete", [(*pts_i[t], zz), (*pts_i[t + 1], zz), (*pts_o[t + 1], zz), (*pts_o[t], zz)], None)
            A.face("concrete", [(*pts_i[t], zz - .9), (*pts_i[t + 1], zz - .9), (*pts_i[t + 1], zz), (*pts_i[t], zz)], None)
    A.cyl("plaza", x, y, 0, .3, r * .3, 24)

def fill_parc(z):
    hu, hv = z.h
    # route de ceinture : une boucle aux coins arrondis, dans le réseau (4 tronçons entre les milieux des côtés)
    rc = 24.; loop = []
    for (cu, cv, a0) in ((hu - rc, -hv + rc, -90), (hu - rc, hv - rc, 0), (-hu + rc, hv - rc, 90), (-hu + rc, -hv + rc, 180)):
        for k in range(10):
            a = math.radians(a0 + k * 10); loop.append(z.w(cu + rc * math.cos(a), cv + rc * math.sin(a)))
    mids = [z.w(hu, 0), z.w(0, hv), z.w(-hu, 0), z.w(0, -hv)]
    pts_all = []
    for k in range(4):            # coin k suivi du milieu du côté suivant
        pts_all += loop[k * 10:(k + 1) * 10] + [mids[k]]
    pts_all = [mids[3]] + pts_all
    ids = [NET.node(m) for m in (mids[3], mids[0], mids[1], mids[2])]
    cuts = [0] + [i for i, p in enumerate(pts_all) if p in mids[:3]] + [len(pts_all) - 1]
    for k in range(4):
        NET.edge(ids[k], ids[(k + 1) % 4], pts_all[cuts[k]:cuts[k + 1] + 1], 12., 3., "avenue")
    mark_road(pts_all, 20)
    GATES[z.key] = [(z.w(0, -hv), (z.sn, -z.cs), 12., "ring"), (z.w(0, hv), (-z.sn, z.cs), 12., "ring"),
                    (z.w(-hu, 0), (-z.cs, -z.sn), 12., "ring"), (z.w(hu, 0), (z.cs, z.sn), 12., "ring")]
    A.box("grass", z.c[0], z.c[1], 0, 2 * hu - 12, 2 * hv - 12, .12, z.rot, top="grass", sides=False)
    # lac aux bords irréguliers
    lu, lv, lr = -hu * .35, hv * .1, 48
    lake = []
    for k in range(40):
        a = k / 40 * 6.283; rr = lr * (1 + .22 * math.sin(3 * a + 1) + .12 * math.sin(5 * a))
        lake.append(z.w(lu + rr * math.cos(a) * 1.3, lv + rr * math.sin(a) * .8))
    cx0, cy0 = z.w(lu, lv)
    A.poly("sand", [(cx0 + (px - cx0) * 1.1, cy0 + (py - cy0) * 1.1) for px, py in lake], .13)
    A.poly("water", lake, .16)
    lx, ly = z.w(lu, lv)
    for k in range(5):                                      # pédalos sur le lac
        px_, py_ = z.w(lu + R.uniform(-25, 25), lv + R.uniform(-12, 12))
        A.box("white", px_, py_, .16, 2.4, 1.4, .5, z.rot + R.uniform(0, 3), col=(.9, .9, .88), top="painted")
        A.cyl("painted", px_, py_, .66, .5, .35, 8, col=R.choice([(.9, .7, .1), (.8, .2, .1), (.1, .4, .8)]))
    A.cyl("white", lx + 10, ly - 5, .16, .3, 1.5, 12)      # jet d'eau
    A.cyl("white", lx + 10, ly - 5, .16, 5, .25, 8, r2=.05)
    claim(lx, ly, lr * 2.8, lr * 1.8, z.rot)
    # stade (emplacement) et amphithéâtre
    sx, sy = z.w(hu * .55, -hv * .1)
    stadium(sx, sy, z.rot, 34, 25); claim(sx, sy, 110, 90, z.rot)
    SLOTS.append(("stade", NOMS["stade"], (sx, sy, 16)))
    ax, ay = z.w(hu * .06, -hv * .5)
    amphitheatre(ax, ay, z.rot + math.pi / 2 + .0, 23); claim(ax, ay - 0, 70, 66, z.rot)
    SLOTS.append(("amphi", NOMS["amphi"], (ax, ay, 4)))
    # allées : une boucle autour du lac, une autour du stade, et des branches depuis les entrées
    def path(pts, zz):
        A.ribbon("path", pts, 4, zz)
        for p in pts[::2]: BUSY.add((int(p[0] // CELL), int(p[1] // CELL)))
        for i_ in range(3, len(pts) - 1, 7):
            bx, by = pts[i_]; ang = math.atan2(pts[i_ + 1][1] - by, pts[i_ + 1][0] - bx)
            bench(bx - math.sin(ang) * 3, by + math.cos(ang) * 3, ang)
            if i_ % 14 == 3: lamp(bx + math.sin(ang) * 3, by - math.cos(ang) * 3, ang)
    loop = [z.w(lu + math.cos(k / 48 * 6.283) * lr * 1.88, lv + math.sin(k / 48 * 6.283) * lr * 1.25) for k in range(49)]
    path(loop, .15)
    sl = [z.w(hu * .55 + math.cos(k / 48 * 6.283) * 52, -hv * .1 + math.sin(k / 48 * 6.283) * 44) for k in range(49)]
    path(sl, .152)
    def spoke(gate, target_loop, zz):
        q = min(target_loop, key=lambda p: math.dist(p, gate))
        mid = ((gate[0] + q[0]) / 2 + R.uniform(-12, 12), (gate[1] + q[1]) / 2 + R.uniform(-12, 12))
        path(bez(gate, mid, mid, q, 16), zz)
    spoke(z.w(-hu + 9.5, hv * .3), loop, .154)             # entrée ouest → lac
    spoke(z.w(-hu * .45, hv - 9.5), loop, .156)            # entrée nord → lac
    spoke(z.w(hu * .55, hv - 9.5), sl, .158)               # entrée nord-est → stade
    spoke(z.w(hu * .55, -hv + 9.5), sl, .16)               # entrée sud-est → stade
    spoke(z.w(-hu * .45, -hv + 9.5), loop, .162)           # entrée sud → lac (passe à l'ouest de l'amphithéâtre)
    a1 = min(loop, key=lambda p: math.dist(p, z.w(hu * .55, -hv * .1))); a2 = min(sl, key=lambda p: math.dist(p, a1))
    path([a1, ((a1[0] + a2[0]) / 2, (a1[1] + a2[1]) / 2), a2], .164)   # lac ↔ stade
    # beaucoup d'arbres, en bosquets
    for k in range(520):
        cu, cv = R.uniform(-hu + 8, hu - 8), R.uniform(-hv + 8, hv - 8)
        x, y = z.w(cu, cv)
        if (int(x // CELL), int(y // CELL)) in BUSY or on_road(x, y): continue
        if math.sin(cu / 23) * math.cos(cv / 17) < -.2 and R.random() < .6: continue   # clairières
        inst(R.choice(TREES), x, y, .12, R.uniform(0, 6.3), R.uniform(.9, 1.5))
    # aire de jeux
    px, py = z.w(-hu * .7, -hv * .7)
    A.box("sand", px, py, .12, 16, 12, .1, z.rot, top="sand", sides=False)
    park_extras("jeux", lambda a_, b_: z.w(-hu * .7 + a_ * .75, -hv * .7 + b_ * .6), 16, 12, px, py, z.rot, z0=.22)

def in_frame_or_close(x, y): return -900 < x < 900 and -1000 < y < 620 and y < SHORE(x) - 50

# une usine différente par îlot ; deux quartiers voisins (industrie + logistique collés) n'ont jamais la même
IND_BY_ZONE = {"i1": ["usine", "chimie", "centrale", "metal"], "l1": ["agro", "scierie"],
               "i2": ["agro", "usine", "scierie", "chimie"], "l2": ["metal", "centrale"]}
IND_I = {}
def next_industry(zk="i1"):
    lst = IND_BY_ZONE.get(zk, ["usine"]); n = IND_I.get(zk, 0); IND_I[zk] = n + 1; return lst[n % len(lst)]
def fill_industrie(z):
    """chaque îlot est une usine différente, qui occupe tout l'îlot"""
    for b in build_grid_streets(z): industrial_block(z, b, next_industry(z.key))

LOGI_SHAPES = ["I", "II", "T", "E", "Z", "H"]
def fill_logistique(z):
    blocks = build_grid_streets(z)
    first = True
    # chaque pôle logistique a au moins un entrepôt en L et un en U (souvent deux), le reste varie ; jamais deux pareils
    seq = ["L", "U", "L", "U"][:max(2, len(blocks) // 2)] + R.sample(LOGI_SHAPES, len(LOGI_SHAPES))
    R.shuffle(seq)
    seq = [x for n_, x in enumerate(seq) if n_ == 0 or x != seq[n_ - 1]]
    factories = set(R.sample(range(len(blocks)), len(blocks) // 2))     # la moitié des îlots : des usines
    for bi, b in enumerate(blocks):
        if bi in factories: industrial_block(z, b, next_industry(z.key)); continue
        u0, u1, v0, v1 = b
        block_pad(z, b, "concrete", .1)
        W, D = u1 - u0 - 10, v1 - v0 - 10
        sh = seq[bi % len(seq)]
        big = sh in ("L", "U", "H", "E")
        cu, cv = (u0 + u1) / 2, v1 - 5 - D * (.78 if big else .62) / 2
        ww, wd = W * .88, D * (.78 if big else .62)
        if sh == "II":
            parts = [(0, -wd * .27, ww, wd * .42, 0), (0, wd * .27, ww * .8, wd * .42, 0)]
        else:
            parts = shape_parts(sh, ww, wd)
        hgt = R.choice([11, 13, 15]); wc = R.choice([(.72, .72, .7), (.62, .64, .66), (.75, .7, .62), (.55, .58, .6)])
        docks = []
        for part in parts:
            lu, lv, w_, d_, a_ = part
            px, py = z.w(cu + lu, cv + lv)
            h_ = hgt - (2 if (w_ < d_ and sh != "I") else 0)
            A.box("facade", px, py, 0, w_, d_, h_, z.rot + a_, col=wc, top=None, fh=h_, bay=6)
            A.box("roof", px, py, h_, w_, d_, .01 + .03 * parts.index(part), z.rot + a_, col=(.62, .62, .6), sides=False)
            for k in range(int(w_ / 10)):      # lanterneaux
                lx, ly = z.w(cu + lu - w_ / 2 + 5 + k * 10, cv + lv)
                A.box("glass", lx, ly, h_, 1.5, d_ * .75, .4, z.rot, col=(.5, .6, .65), top="glass")
            roof_clutter(px, py, z.rot + a_, w_ * .95, d_ * .95, h_ + .05, "logi")
            claim(px, py, w_, d_, z.rot + a_)
            if w_ >= d_: docks.append((cu + lu, cv + lv - d_ / 2, w_))     # quais sur la façade sud des ailes longues
        if first: SLOTS.append(("entrepot", NOMS["entrepot"], (*z.w(cu, cv), hgt + 1))); first = False
        # quais de chargement + camions
        for du0, dv, L_ in docks:
            for k in range(int(L_ / 5)):
                du = du0 - L_ / 2 + 2.5 + k * 5
                dx, dy = z.w(du, dv - .1)
                A.box("dark", dx, dy, .8, 3.2, .3, 3.6, z.rot)
                if R.random() < .5 and dv - 10 > v0 + 3:
                    tx, ty = z.w(du, dv - 10)
                    car_at(tx, ty, z.rot - math.pi / 2, truck=True, parked=True)
        # conteneurs ou parking de remorques, dans la cour
        if R.random() < .5:
            for k in range(R.randint(6, 16)):
                ccu, ccv = u0 + 8 + (k % 6) * 13, v0 + 6 + (k // 6) * 3
                cx_, cy_ = z.w(ccu, ccv)
                for st in range(R.randint(1, 3)):
                    A.box("painted", cx_, cy_, .1 + st * 2.6, 12, 2.45, 2.6, z.rot, col=R.choice([(.6, .12, .08), (.1, .25, .5), (.1, .4, .25), (.8, .55, .1), (.5, .5, .52)]))
        else:
            for k in range(R.randint(4, 9)):
                tx, ty = z.w(u0 + 8 + k * 4.5, v0 + 12)
                inst(TRUCK, tx, ty, 0, z.rot + math.pi / 2, 1, (.9, .9, .9))

def build_core_streets(z):
    """les rues n'existent qu'autour des îlots retenus. Les « portes » sont les prolongements des lignes de la grille
    au bord du centre : une route qui part de là continue la rue, dans l'axe."""
    sw, us, vs = z.SW, z.us, z.vs
    I = z.incl
    segU = lambda i, j: 0 <= j < z.nv and ((i - 1, j) in I or (i, j) in I)     # rue verticale u = us[i], entre vs[j] et vs[j+1]
    segV = lambda i, j: 0 <= i < z.nu and ((i, j - 1) in I or (i, j) in I)     # rue horizontale v = vs[j], entre us[i] et us[i+1]
    z.segU, z.segV = segU, segV
    segs = [("u", i, j) for i in range(z.nu + 1) for j in range(z.nv) if segU(i, j)] + \
           [("v", i, j) for i in range(z.nu) for j in range(z.nv + 1) if segV(i, j)]
    GATES[z.key] = []
    for n, (ax, i, j) in enumerate(segs):
        if ax == "u":
            u = us[i]; a, b = z.w(u, vs[j] - sw / 2), z.w(u, vs[j + 1] + sw / 2)
            A.box("asphalt", *z.w(u, (vs[j] + vs[j + 1]) / 2), 0, sw, vs[j + 1] - vs[j] - sw, .014, z.rot, sides=False)
            for k in range(int((vs[j + 1] - vs[j] - sw) / 9)):
                A.box("paint_w", *z.w(u, vs[j] + sw / 2 + 3 + k * 9), .03, .22, 3, .005, z.rot, sides=False)
            lanes_cars([z.w(u, vs[j] + sw / 2 + 4), z.w(u, vs[j + 1] - sw / 2 - 4)], sw * .8)
        else:
            v = vs[j]; a, b = z.w(us[i] - sw / 2, v), z.w(us[i + 1] + sw / 2, v)
            A.box("asphalt", *z.w((us[i] + us[i + 1]) / 2, v), 0, us[i + 1] - us[i] - sw, sw, .014, z.rot, sides=False)
            for k in range(int((us[i + 1] - us[i] - sw) / 9)):
                A.box("paint_w", *z.w(us[i] + sw / 2 + 3 + k * 9, v), .03, 3, .22, .005, z.rot, sides=False)
            lanes_cars([z.w(us[i] + sw / 2 + 4, v), z.w(us[i + 1] - sw / 2 - 4, v)], sw * .8)
        mark_road([a, b], sw)
    for i in range(z.nu + 1):
        for j in range(z.nv + 1):
            if not any((i - a_, j - b_) in I for a_ in (0, 1) for b_ in (0, 1)): continue
            A.box("asphalt", *z.w(us[i], vs[j]), 0, sw, sw, .0145, z.rot, sides=False)
            A.box("asphalt", *z.w(us[i], vs[j]), 0, sw + 2 * RC, sw + 2 * RC, .0128, z.rot, sides=False)
            # les portes : une branche qui existe d'un côté et pas de l'autre
            cand = []
            if segU(i, j - 1) and not segU(i, j): cand.append(("+v", z.w(us[i], vs[j] + sw / 2), (-z.sn, z.cs)))
            if segU(i, j) and not segU(i, j - 1): cand.append(("-v", z.w(us[i], vs[j] - sw / 2), (z.sn, -z.cs)))
            if segV(i - 1, j) and not segV(i, j): cand.append(("+u", z.w(us[i] + sw / 2, vs[j]), (z.cs, z.sn)))
            if segV(i, j) and not segV(i - 1, j): cand.append(("-u", z.w(us[i] - sw / 2, vs[j]), (-z.cs, -z.sn)))
            for key, p, d in cand:
                far = (p[0] + d[0] * 40, p[1] + d[1] * 40)
                if z.inside(*far, 8) or any(zz.inside(*far, 20) for zz in ZONES[1:]) or near_hwy(*far, 30) or far[1] > SHORE(far[0]) - 60: continue
                GATES[z.key].append((p, d, sw, (i, j, key)))

def core_finish(z):
    """après le réseau : trottoirs du côté extérieur des rues de bord (là où il n'y a pas d'îlot), et passages piétons
    sur chaque branche réellement présente (y compris les routes qui partent des portes)"""
    sw, I, WK = z.SW, z.incl, 3.5
    U = lambda i: -z.h[0] + i * z.PU; V = lambda j: -z.h[1] + j * z.PV
    used = {m for (zk, m) in GATE_USED if zk == z.key}
    border = {"+v": [(-1, 0), (0, 0)], "-v": [(-1, -1), (0, -1)], "+u": [(0, -1), (0, 0)], "-u": [(-1, -1), (-1, 0)]}
    skipc = set()          # (cellule, coin) recouverts par le trottoir d'une route qui part d'une porte
    for (i, j, key) in used:
        for di, dj in border[key]: skipc.add(((i + di, j + dj), (i, j)))
    def arm(i, j, k_):
        return {"N": z.segU(i, j) or (i, j, "+v") in used, "S": z.segU(i, j - 1) or (i, j, "-v") in used,
                "E": z.segV(i, j) or (i, j, "+u") in used, "W": z.segV(i - 1, j) or (i, j, "-u") in used}[k_]
    def pad(u0, u1, v0, v1):
        if u1 - u0 > .1 and v1 - v0 > .1:
            A.box("sidewalk", *z.w((u0 + u1) / 2, (v0 + v1) / 2), 0, u1 - u0, v1 - v0, .18, z.rot, col=(.5, .5, .5), top="sidewalk")
    for ci in range(-1, z.nu + 1):
        for cj in range(-1, z.nv + 1):
            if (ci, cj) in I: continue
            u0, u1, v0, v1 = U(ci) + sw / 2, U(ci + 1) - sw / 2, V(cj) + sw / 2, V(cj + 1) - sw / 2
            if (ci - 1, cj) in I: pad(u0, u0 + WK, v0 + WK, v1 - WK)
            if (ci + 1, cj) in I: pad(u1 - WK, u1, v0 + WK, v1 - WK)
            if (ci, cj - 1) in I: pad(u0 + WK, u1 - WK, v0, v0 + WK)
            if (ci, cj + 1) in I: pad(u0 + WK, u1 - WK, v1 - WK, v1)
            for (gi, gj), (pu0, pu1), (pv0, pv1) in (((ci, cj), (u0, u0 + WK), (v0, v0 + WK)), ((ci + 1, cj), (u1 - WK, u1), (v0, v0 + WK)),
                                                     ((ci, cj + 1), (u0, u0 + WK), (v1 - WK, v1)), ((ci + 1, cj + 1), (u1 - WK, u1), (v1 - WK, v1))):
                if not any((gi - a_, gj - b_) in I for a_ in (0, 1) for b_ in (0, 1)): continue
                if ((ci, cj), (gi, gj)) in skipc: continue
                su = 1 if gi == ci else -1; sv = 1 if gj == cj else -1
                if arm(gi, gj, "E" if su > 0 else "W") and arm(gi, gj, "N" if sv > 0 else "S"):
                    # les deux rues se croisent à ce coin : bordure arrondie (quart de disque)
                    fu, fv = U(gi) + su * (sw / 2 + WK), V(gj) + sv * (sw / 2 + WK)
                    pts = [z.w(fu, fv)] + [z.w(fu - su * WK * math.cos(a), fv - sv * WK * math.sin(a)) for a in [k / 8 * math.pi / 2 for k in range(9)]]
                    prism("sidewalk", pts, .18, fan0=True)
                else:
                    pad(pu0, pu1, pv0, pv1)
    for i in range(z.nu + 1):
        for j in range(z.nv + 1):
            if not any((i - a_, j - b_) in I for a_ in (0, 1) for b_ in (0, 1)): continue
            u, v = z.us[i], z.vs[j]
            arms = {k_: arm(i, j, k_) for k_ in "NSEW"}
            # virage (deux rues à angle droit) : grand arrondi extérieur, la chaussée garde sa largeur
            for su, sv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                if arms["E" if su > 0 else "W"] or arms["N" if sv > 0 else "S"]: continue
                h_ = sw / 2; pu_, pv_ = u - su * h_, v - sv * h_
                arc = [z.w(pu_ + su * sw * math.cos(a), pv_ + sv * sw * math.sin(a)) for a in [k / 12 * math.pi / 2 for k in range(13)]]
                prism("sidewalk", [z.w(u + su * h_, v + sv * h_)] + arc, .18, fan0=True)
            # branche absente : le trottoir passe devant, en continu (pas de trou à la place d'une 4e rue)
            h = sw / 2
            if not arms["N"]: pad(u - h, u + h, v + h, v + h + WK)
            if not arms["S"]: pad(u - h, u + h, v - h - WK, v - h)
            if not arms["E"]: pad(u + h, u + h + WK, v - h, v + h)
            if not arms["W"]: pad(u - h - WK, u - h, v - h, v + h)
            if sum(arms.values()) < 3: continue
            for key, (du, dv, along) in (("E", (sw / 2 + 2.2, 0, "v")), ("W", (-sw / 2 - 2.2, 0, "v")), ("N", (0, sw / 2 + 2.2, "u")), ("S", (0, -sw / 2 - 2.2, "u"))):
                if not arms[key]: continue
                for k in range(-4, 5):
                    if along == "v": A.box("paint_w", *z.w(u + du, v + k * 1.3), .03, 3, .6, .005, z.rot, sides=False)
                    else: A.box("paint_w", *z.w(u + k * 1.3, v + dv), .03, .6, 3, .005, z.rot, sides=False)

def core_bus_stops(z, n=10):
    """quelques arrêts de bus sur les rues du centre, sur le trottoir d'un îlot"""
    segs = [("u", i, j) for i in range(z.nu + 1) for j in range(z.nv) if z.segU(i, j)] + [("v", i, j) for i in range(z.nu) for j in range(z.nv + 1) if z.segV(i, j)]
    R.shuffle(segs); sw = z.SW
    for ax, i, j in segs[:n]:
        if ax == "u":
            side = 1 if (i, j) in z.incl else -1
            if (i - 1 if side < 0 else i, j) not in z.incl: continue
            u = z.us[i] + side * (sw / 2 + 1.1); v = (z.vs[j] + z.vs[j + 1]) / 2
            ang = z.rot + math.pi / 2; road = (-side * math.cos(z.rot), -side * math.sin(z.rot))
        else:
            side = 1 if (i, j) in z.incl else -1
            if (i, j - 1 if side < 0 else j) not in z.incl: continue
            u = (z.us[i] + z.us[i + 1]) / 2; v = z.vs[j] + side * (sw / 2 + 1.1)
            ang = z.rot; road = (side * math.sin(z.rot), -side * math.cos(z.rot))
        bus_stop(*z.w(u, v), ang, R.random() < .45, road)

def ring_finish(z):
    """quartier en grille (industrie, logistique) : un trottoir tout autour, ouvert là où une route en part"""
    us, vs, sw = grid_lines(z); WK = 3.
    hu, hv = z.h[0] + sw / 2, z.h[1] + sw / 2
    used = {m: w for (zk, m), w in GATE_USED.items() if zk == z.key}
    sides = {"S": (-1, "u", -hv), "N": (1, "u", hv), "W": (-1, "v", -hu), "E": (1, "v", hu)}
    for key, (sg, ax, c) in sides.items():
        span = (-hu - WK, hu + WK) if ax == "u" else (-hv, hv)
        holes = sorted((pos - ow, pos + ow) for (sd, pos), ow in used.items() if sd == key)
        a = span[0]; pieces = []
        for h0, h1 in holes:
            if h0 > a: pieces.append((a, h0))
            a = max(a, h1)
        if a < span[1]: pieces.append((a, span[1]))
        for p0, p1 in pieces:
            n = max(1, int((p1 - p0) / 10))
            for k in range(n):
                q0, q1 = p0 + (p1 - p0) * k / n, p0 + (p1 - p0) * (k + 1) / n; m = (q0 + q1) / 2
                cu, cv = (m, c + sg * WK / 2) if ax == "u" else (c + sg * WK / 2, m)
                x, y = z.w(cu, cv); ox, oy = z.w(cu + (sg * 6 if ax == "v" else 0), cv + (sg * 6 if ax == "u" else 0))
                if any(zz is not z and zz.inside(ox, oy) for zz in ZONES) or near_hwy(x, y, 2): continue
                w_, d_ = (q1 - q0, WK) if ax == "u" else (WK, q1 - q0)
                A.box("sidewalk", x, y, 0, w_, d_, .18 + .004 * (ZONES.index(z) % 5), z.rot, col=(.5, .5, .5), top="sidewalk")

def block_of(z, c):
    i, j = c; sw = z.SW
    return (z.us[i] + sw / 2, z.us[i + 1] - sw / 2, z.vs[j] + sw / 2, z.vs[j + 1] - sw / 2)

def fill_faible(z, blocks):
    """petite densité, sur la même grille : maisons de ville tout autour de l'îlot, bâtiments d'angle, arrière-cours"""
    for b in blocks: perimeter_block(z, b)

PARKS_DBG = []
PARK_KINDS = ["fontaine", "jeux", "sport", "bosquet", "francais", "japonais", "potager", "skate", "kiosque", "roseraie", "mineral", "etang"]
FLOWERS = [(.8, .1, .12), (.9, .75, .1), (.6, .2, .7), (.95, .5, .6), (.95, .95, .9), (.9, .35, .05)]

def fill_parcbloc(z, blocks):
    """des parcs tous différents : fontaine, jeux, sport, bosquet, jardin à la française, jardin japonais,
    jardins partagés, skatepark, kiosque à musique, roseraie, place minérale, étang"""
    used = []
    # le type de parc dépend de l'endroit : place ou jardin classique au cœur dense, jeux et étangs dans
    # les quartiers habités, jardins partagés et sport en périphérie, jardin à la française près des monuments
    BY_T = [(.45, ["mineral", "fontaine", "francais", "kiosque"]),
            (.72, ["jeux", "roseraie", "etang", "japonais", "sport", "fontaine"]),
            (9.0, ["bosquet", "sport", "jeux", "etang", "japonais"])]
    for entry in blocks:
        b, t_, c_ = entry if len(entry) == 3 else (entry, .6, None)
        u0, u1, v0, v1 = b
        W, D = u1 - u0, v1 - v0
        cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
        x, y = z.w(cu, cv)
        pool = next(l for lim, l in BY_T if t_ < lim)
        if c_ is not None and any(TYPES.get((c_[0] + a, c_[1] + b_)) == "unique" for a in (-1, 0, 1) for b_ in (-1, 0, 1)):
            pool = ["francais", "mineral", "kiosque"] + pool
        # parmi les types qui conviennent, le moins utilisé jusqu'ici (chaque parc est différent de ses voisins)
        low = min(used.count(k) for k in pool)
        fresh = [k for k in pool if used.count(k) == low]
        kind = R.choice(fresh); used.append(kind); PARKS_DBG.append((kind, x, y))
        prism("plaza" if kind == "mineral" else "grass", rounded_rect(z, u0, u1, v0, v1), .18, side="sidewalk")
        claim(x, y, W - 2, D - 2, z.rot)
        P = lambda a_, b_: z.w(cu + a_, cv + b_)
        WB = 3.       # un trottoir tout autour du parc, d'où partent les allées
        if kind != "mineral":
            for (a_, b_, w_, d_) in ((0, D / 2 - WB / 2, W - 2 * RC, WB), (0, -D / 2 + WB / 2, W - 2 * RC, WB), (W / 2 - WB / 2, 0, WB, D - 2 * WB), (-W / 2 + WB / 2, 0, WB, D - 2 * WB)):
                A.box("sidewalk", *P(a_, b_), .18, w_, d_, .006, z.rot, sides=False)
        def entry(a_, b_, axis, sign, wid=3.):
            end = (sign * (W / 2 - WB + .3), b_) if axis == "u" else (a_, sign * (D / 2 - WB + .3))
            A.ribbon("path", [P(a_, b_), P(*end)], wid, .2)
        def trees_ring(n, rx, ry, s_=1.):
            for k in range(n):
                a = k / n * 6.283 + .13
                if abs(math.cos(a)) < .16 or abs(math.sin(a)) < .16: continue      # pas d'arbre sur les allées d'entrée
                inst(R.choice(TREES), *P(math.cos(a) * rx, math.sin(a) * ry), .18, a, s_)
        def trees_scatter(n, avoid=0.):
            for k in range(n):
                a_, b_ = R.uniform(-W / 2 + 5, W / 2 - 5), R.uniform(-D / 2 + 5, D / 2 - 5)
                if math.hypot(a_ / W, b_ / D) * 2 < avoid or abs(a_) < 3 or abs(b_) < 3: continue
                inst(R.choice(TREES), *P(a_, b_), .18, R.uniform(0, 6.3), R.uniform(.8, 1.3))
        if kind == "fontaine":
            for (a_, b_), (c_, d_) in (((-W / 2, -D / 2), (W / 2, D / 2)), ((-W / 2, D / 2), (W / 2, -D / 2))): A.ribbon("path", [P(a_, b_), P(c_, d_)], 3.5, .2)
            A.cyl("plaza", x, y, .18, .08, 11, 32); A.cyl("concrete", x, y, .18, .6, 6, 32); A.cyl("water", x, y, .18, .65, 5.4, 32)
            A.cyl("white", x, y, .18, 3.5, .25, 8, r2=.05); trees_scatter(int(W * D / 110), .5)
        elif kind == "jeux":
            A.box("sand", x, y, .19, 22, 16, .05, z.rot, top="sand", sides=False)
            for k in range(7): A.box("painted", *P(R.uniform(-9, 9), R.uniform(-6, 6)), .2, R.uniform(1, 3), R.uniform(1, 2), R.uniform(1, 3.5), R.uniform(0, 3), col=R.choice([(.8, .2, .1), (.1, .4, .8), (.9, .7, .1), (.2, .6, .3)]))
            A.cyl("painted", *P(8, 5), .2, 3, .15, 6, col=(.8, .2, .1)); trees_ring(12, W * .4, D * .4, .9)
            entry(0, -8, "v", -1); entry(11, 0, "u", 1)
        elif kind == "sport":
            A.box("painted", x, y, .19, W * .75, D * .6, .04, z.rot, col=(.55, .2, .12), top="painted", sides=False)
            A.box("pitch", x, y, .235, W * .6, D * .45, .01, z.rot, top="pitch", sides=False)
            A.box("paint_w", x, y, .25, .15, D * .45, .005, z.rot, sides=False); A.cyl("paint_w", x, y, .25, .005, 4, 24, top=False)
            trees_ring(16, W * .45, D * .44, .8)
            entry(0, -D * .3, "v", -1); entry(-W * .375, 0, "u", -1)
        elif kind == "bosquet":
            A.ribbon("path", [P(-W / 2 + WB - .3, R.uniform(-8, 8)), P(-W / 6, R.uniform(-10, 10)), P(W / 6, R.uniform(-10, 10)), P(W / 2 - WB + .3, R.uniform(-8, 8))], 3, .2)
            trees_scatter(int(W * D / 45))
        elif kind == "francais":   # jardin à la française : allées en croix, parterres bordés de haies, bassin
            A.ribbon("path", [P(-W / 2 + WB - .3, 0), P(W / 2 - WB + .3, 0)], 4, .2); A.ribbon("path", [P(0, -D / 2 + WB - .3), P(0, D / 2 - WB + .3)], 4, .205)
            for sa in (-1, 1):
                for sb in (-1, 1):
                    px, py = P(sa * W / 4, sb * D / 4)
                    for (a_, b_, w_, d_) in ((0, (D / 4 - 4.5), W / 2 - 8, .8), (0, -(D / 4 - 4.5), W / 2 - 8, .8), ((W / 4 - 4.5), 0, .8, D / 2 - 8), (-(W / 4 - 4.5), 0, .8, D / 2 - 8)):
                        hx, hy = P(sa * W / 4 + a_, sb * D / 4 + b_); A.box("painted", hx, hy, .2, w_, d_, .9, z.rot, col=(.06, .16, .05))
                    A.cyl("painted", px, py, .2, 2.5, .8, 10, r2=.05, col=(.05, .15, .05))
            A.cyl("concrete", x, y, .2, .5, 5, 32); A.cyl("water", x, y, .2, .55, 4.4, 32)
        elif kind == "japonais":   # étang aux bords libres, pont rouge, pierres, érables rouges
            pond = [P(math.cos(a) * W * .3 * (1 + .2 * math.sin(3 * a)), math.sin(a) * D * .28 * (1 + .15 * math.cos(2 * a))) for a in [k / 30 * 6.283 for k in range(30)]]
            A.poly("water", pond, .2)
            A.box("painted", x, y, 1.2, 3, D * .5, .3, z.rot, col=(.7, .1, .06))
            loop_ = [P(math.cos(a) * (W * .3 + 6), math.sin(a) * (D * .28 + 5)) for a in [k / 36 * 6.283 for k in range(37)]]
            A.ribbon("path", loop_, 2.2, .2); entry(W * .3 + 6, 0, "u", 1); entry(-(W * .3 + 6), 0, "u", -1)
            for k in range(12): inst(R.choice(ROCKS), *P(R.uniform(-W * .38, W * .38), R.uniform(-D * .38, D * .38)), .1, R.uniform(0, 6), R.uniform(.5, 1.3))
            for k in range(8):
                tr = inst(R.choice(TREES), *P(R.uniform(-W * .45, W * .45), R.choice([-1, 1]) * R.uniform(D * .32, D * .45)), .18, R.uniform(0, 6), R.uniform(.6, .9))
                tr.pass_index = 1
        elif kind == "potager":    # jardins partagés : parcelles de couleurs, cabanons
            for i_ in range(5):
                for j_ in range(3):
                    px, py = P(-W / 2 + 8 + i_ * (W - 16) / 4, -D / 2 + 10 + j_ * (D - 20) / 2)
                    A.box("painted", px, py, .19, (W - 24) / 5, (D - 26) / 3, .15, z.rot, col=R.choice([(.2, .35, .08), (.35, .45, .1), (.3, .2, .1), (.15, .3, .06), (.4, .28, .15)]))
            for k in range(3): A.box("wood", *P(-W / 2 + 10 + k * 18, D / 2 - 6), .18, 3, 2.5, 2.4, z.rot, top="roof")
            for j_ in range(2):
                vv = -D / 2 + 10 + (j_ + .5) * (D - 20) / 2
                A.ribbon("path", [P(-W / 2 + WB - .3, vv), P(W / 2 - WB + .3, vv)], 2.5, .2 + .002 * j_)
        elif kind == "skate":
            A.box("concrete", x, y, .18, W * .7, D * .6, .1, z.rot, top="concrete")
            for k in range(4):
                A.box("concrete", *P(-W * .25 + k * W * .17, R.uniform(-6, 6)), .28, R.uniform(4, 8), R.uniform(3, 6), R.uniform(.6, 1.6), z.rot + R.uniform(-.4, .4), top="concrete")
            A.dome("concrete", *P(W * .22, 0), .28, 6, 1.4, 20, 4)
            entry(0, -D * .3, "v", -1); entry(-W * .35, 0, "u", -1)
            trees_ring(14, W * .46, D * .45, .8)
        elif kind == "kiosque":     # kiosque à musique au centre d'allées en étoile
            for k in range(6):
                a = k / 6 * 6.283; ca, sa = math.cos(a), math.sin(a)
                r_ = min((W / 2 - WB + .3) / max(abs(ca), 1e-3), (D / 2 - WB + .3) / max(abs(sa), 1e-3))     # jusqu'au trottoir du bord
                A.ribbon("path", [P(ca * 8, sa * 8), P(ca * r_, sa * r_)], 3, .2 + .002 * k)
            A.cyl("plaza", x, y, .18, .9, 7, 8); A.cyl("roof", x, y, 5.5, 2.5, 7.8, 8, r2=.3, col=(.2, .35, .3))
            for k in range(8): A.cyl("white", *P(math.cos(k / 8 * 6.283) * 6.2, math.sin(k / 8 * 6.283) * 6.2), 1, 4.5, .18, 6)
            trees_scatter(int(W * D / 120), .6)
        elif kind == "roseraie":    # massifs de fleurs de toutes les couleurs, en anneaux
            for ring in range(3):
                n = 10 + ring * 6
                for k in range(n):
                    a = k / n * 6.283; px, py = P(math.cos(a) * (8 + ring * 8), math.sin(a) * (6 + ring * 7))
                    if abs(math.sin(a)) * (6 + ring * 7) < 2.6 or abs(math.cos(a)) * (8 + ring * 8) < 2.6: continue
                    A.cyl("painted", px, py, .18, .5, 1.3, 8, col=R.choice(FLOWERS))
            A.ribbon("path", [P(-W / 2 + WB - .3, 0), P(W / 2 - WB + .3, 0)], 3, .2); A.ribbon("path", [P(0, -D / 2 + WB - .3), P(0, D / 2 - WB + .3)], 3, .202)
            A.cyl("white", x, y, .18, 4, .6, 10); trees_ring(18, W * .47, D * .46, .8)
        elif kind == "mineral":     # place minérale : dalles, arbres en grille, bancs, sculpture
            for i_ in range(5):
                for j_ in range(4):
                    inst(R.choice(TREES), *P(-W / 2 + 7 + i_ * (W - 14) / 4, -D / 2 + 7 + j_ * (D - 14) / 3), .18, 0, .85)
            A.box("metalattr", x, y, .18, 2, 2, 6, z.rot + .4, col=(.7, .3, .1))
            for k in range(6): bench(*P(-12 + k * 5, -4), z.rot)
        else:                       # étang, pelouse et grands arbres
            pond = [P(math.cos(a) * W * .28, math.sin(a) * D * .25) for a in [k / 32 * 6.283 for k in range(32)]]
            A.poly("water", pond, .2)
            ring_ = [P(math.cos(a) * (W * .28 + 4), math.sin(a) * (D * .25 + 4)) for a in [k / 32 * 6.283 for k in range(33)]]
            A.ribbon("path", ring_, 2.5, .21)
            entry(W * .28 + 4, 0, "u", 1); entry(-(W * .28 + 4), 0, "u", -1); entry(0, -(D * .25 + 4), "v", -1)
            trees_scatter(int(W * D / 140), .75)
        park_extras(kind, P, W, D, x, y, z.rot)
        for k in range(4):
            a = k / 4 * 6.283 + .5; bench(x + math.cos(a) * W * .42, y + math.sin(a) * D * .42, a + 1.57)
        lamp(*P(W * .45, D * .42), 0); lamp(*P(-W * .45, -D * .42), math.pi)

def fill_town(z):
    build_core_streets(z)
    cells = sorted(z.incl, key=lambda c: z.incl[c])          # du centre vers le bord
    kinds = ["place", "mairie", "eglise", "ecole"]
    for n, c in enumerate(cells):
        b = block_of(z, c)
        if n < len(kinds) and kinds[n] == "place": fill_parcbloc(z, [(b, .3, None)])
        elif n < len(kinds): landmark_block(z, b, kinds[n], pad="sidewalk")
        else: perimeter_block(z, b, station=(n == len(kinds) + 1))      # la station-service, dans un îlot de maisons
    print("bourg :", len(cells), "îlots")

def fill_core(z):
    build_core_streets(z)
    by = {}
    for c, t in TYPES.items(): by.setdefault(t, []).append(c)
    fill_bureaux(z, [block_of(z, c) for c in by.get("bureaux", [])])
    fill_haute(z, True, [block_of(z, c) for c in by.get("haute", [])])
    fill_unique(z, [block_of(z, c) for c in by.get("unique", [])])
    fill_unique(z, [block_of(z, c) for c in by.get("equip", [])], ["clinique", "gymnase", "supermarche"])
    fill_faible(z, [block_of(z, c) for c in by.get("faible", [])])
    fill_parcbloc(z, [(block_of(z, c), CORE.incl[c], c) for c in by.get("parcbloc", [])])
    print("centre :", {k: len(v) for k, v in by.items()})

exec(compile(open(os.path.join(HERE, "batiments.py"), encoding="utf-8").read(), "batiments.py", "exec"))
# ═══════════════════════════════════════ construction
for z in ZONES:
    {"centre": fill_core, "bourg": fill_town, "parc": fill_parc, "industrie": fill_industrie, "logistique": fill_logistique}[z.kind](z)
print("quartiers ok")

# ═══════════════════════════════════════ le réseau routier (kit de route : roads.py)
GATE_USED = {}          # (quartier, porte) → demi-largeur de l'ouverture dans le trottoir du quartier
def band_cells(pts, r):
    out = set(); k = int(r / CELL) + 1
    for p in resample(pts, 2.) if len(pts) > 1 else pts:
        cx, cy = int(math.floor(p[0] / CELL)), int(math.floor(p[1] / CELL))
        for a in range(-k, k + 1):
            for b in range(-k, k + 1):
                if math.hypot(a * CELL, b * CELL) <= r: out.add((cx + a, cy + b))
    return out
HWY_CELLS = band_cells(HWY, HWY_W / 2 + 10)       # sous l'autoroute : pas de rue qui la longe
RAMP_CELLS = set()                                  # sous les bretelles en hauteur
cell_of = lambda x, y: (int(math.floor(x / CELL)), int(math.floor(y / CELL)))

def gate_node(zk, g, w, walk):
    """le nœud au bout d'une porte de quartier (le quartier dessine lui-même son carrefour)"""
    p, d, sw, meta = g
    if meta == "ring":          # la ceinture du parc : on la coupe là (vrai carrefour en T)
        hit = NET.closest(p, 3.)
        return NET.split(hit[1], hit[2])
    GATE_USED[(zk, meta)] = w / 2 + walk
    return NET.node(p, "gate")
def gate_free(zk, g): return g[3] == "ring" or (zk, g[3]) not in GATE_USED

def add_road(pts, w, walk, cls, na, nb, min_angle=45., check=None):
    """insère une route : chaque croisement devient un carrefour. Refusée (None) si elle coupe mal une autre route
    (angle trop fermé, trop près d'un carrefour existant) ou si elle en longe une de trop près."""
    L = length(pts)
    ends = set(NET.N[na]["e"]) | set(NET.N[nb]["e"] if isinstance(nb, int) else [])
    xs = [c for c in NET.crossings(pts) if not (c[1] in ends and (c[0] < 3 or c[0] > L - 3))]
    prev = 0.
    for sarc, eid, se, q, ang in xs:
        if ang < math.radians(min_angle) or sarc - prev < 32 or L - sarc < 32: return None
        if NET.junction_dist(eid, se) < 32: return None
        prev = sarc
    C = cum(pts)
    for i, p in enumerate(pts):          # jamais le long d'une autre route (sauf aux croisements)
        if C[i] < 20 or C[i] > L - 20 or any(abs(C[i] - c[0]) < 26 for c in xs): continue
        if NET.clearance(p) < w / 2 + walk + 3: return None
        if check and not check(p): return None
    nodes = [na]
    for sarc, eid, se, q, ang in xs:
        hit = NET.closest(q, 2.)
        nodes.append(NET.split(hit[1], hit[2]))
    if nb is None: nb = NET.node(pts[-1], "end")
    nodes.append(nb)
    marks = [0.] + [c[0] for c in xs] + [L]
    out = []
    for k in range(len(nodes) - 1):
        seg = cut(pts, marks[k], marks[k + 1])
        out.append(NET.edge(nodes[k], nodes[k + 1], seg, w, walk, cls))
    mark_road(pts, w + 2 * walk + 2)
    return out

# ─── les boulevards entre les quartiers (d'une porte à une porte)
LINKS = [("core", "parc"), ("core", "i1"), ("core", "i2"), ("parc", "l1"), ("i2", "i1"), ("town", "i2"), ("town", "i1")]
AW, AWALK = 13., 3.5
def art_ok(p): return -1000 < p[0] < 1000 and p[1] < SHORE(p[0]) - 30 and not zone_at(*p, 10)
def link(ka, kb, first=None):
    ga_list = [g for g in GATES[ka] if gate_free(ka, g)] if first is None else [first]
    cands = []
    for ga in ga_list:
        for gb in GATES[kb]:
            if not gate_free(kb, gb): continue
            d = math.dist(ga[0], gb[0])
            face = ((gb[0][0] - ga[0][0]) * ga[1][0] + (gb[0][1] - ga[0][1]) * ga[1][1]) / (d + 1) + \
                   ((ga[0][0] - gb[0][0]) * gb[1][0] + (ga[0][1] - gb[0][1]) * gb[1][1]) / (d + 1)
            cands.append((d - 120 * face, ga, gb))
    cands.sort(key=lambda c: c[0])
    for _, ga, gb in cands[:60]:
        d = math.dist(ga[0], gb[0]); Lh = d * .4
        pts = resample(bez(ga[0], (ga[0][0] + ga[1][0] * Lh, ga[0][1] + ga[1][1] * Lh), (gb[0][0] + gb[1][0] * Lh, gb[0][1] + gb[1][1] * Lh), gb[0], 60), 4.)
        C = cum(pts)
        if not all(art_ok(p) for p, c in zip(pts, C) if 24 < c < C[-1] - 24): continue
        if sum(1 for p in pts if cell_of(*p) in HWY_CELLS) > 14: continue      # la croise, ne la longe pas
        na = gate_node(ka, ga, AW, AWALK) if first is None else first[4]
        nb = gate_node(kb, gb, AW, AWALK)
        if add_road(pts, AW, AWALK, "arterial", na, nb) is not None: return True
        # annulation des portes réservées
        for zk, g in ((ka, ga), (kb, gb)):
            if g[3] != "ring": GATE_USED.pop((zk, g[3]), None)
    print("  liaison impossible :", ka, kb); return False
for ka, kb in LINKS: link(ka, kb)
# boulevard du front de mer : il vient de l'est (hors champ) et rejoint le centre par une porte
shore = [(x, SHORE(x) - 42) for x in range(1100, 260, -8)]
sg = (shore[-1], (-1., (shore[-1][1] - shore[-2][1]) / 8 * -1), AW, "shore")
off = NET.node(shore[0], "gate")
ok_shore = False
for g in sorted([g for g in GATES["core"] if gate_free("core", g)], key=lambda g: math.dist(g[0], shore[-1]))[:25]:
    t = (shore[-1][0] - shore[-2][0], shore[-1][1] - shore[-2][1]); tl = math.hypot(*t); t = (t[0] / tl, t[1] / tl)
    d = math.dist(g[0], shore[-1]); Lh = d * .4
    tail = resample(bez(shore[-1], (shore[-1][0] + t[0] * Lh, shore[-1][1] + t[1] * Lh), (g[0][0] + g[1][0] * Lh, g[0][1] + g[1][1] * Lh), g[0], 50), 4.)
    pts = shore + tail[1:]
    C = cum(pts)
    if not all(art_ok(p) or p[0] > 900 for p, c in zip(pts, C) if c < C[-1] - 24): continue
    nb = gate_node("core", g, AW, AWALK)
    if add_road(pts, AW, AWALK, "arterial", off, nb) is not None: ok_shore = True; break
    GATE_USED.pop(("core", g[3]), None)
print("boulevards :", len(NET.E), "tronçons ; front de mer", ok_shore)

# ═══════════════════════════════════════ l'autoroute sur viaduc et ses échangeurs en losange
HC = cum(HWY)
def hwy_at(sarc, lat):
    q, t, _ = at(HWY, sarc, HC); return (q[0] - t[1] * lat, q[1] + t[0] * lat), t
HWY_GAPS = []       # (côté, s0, s1) : glissière de l'autoroute ouverte (une bretelle s'en détache ou s'y insère)
RAMPS = []          # (points, altitudes, ouvertures) des bretelles en hauteur
RAMP_W = 8.5
smooth01 = lambda t: t * t * (3 - 2 * t)

TAPER_W, TAPER_P = 85., 45.      # biseau (la voie naît de 0 à 8,5 m) puis voie parallèle collée à l'autoroute
def make_ramp(sH, s, J, v, exit_):
    """une bretelle : voie d'insertion ou de décélération le long de l'autoroute (biseau + voie parallèle),
    puis descente en S jusqu'au carrefour J. Renvoie points, altitudes, largeurs (du côté autoroute vers le sol)."""
    sgn = 1 if exit_ else -1                               # sortie : en amont ; entrée : en aval
    TL = TAPER_W + TAPER_P
    s_far, s_near = sH + sgn * s * (200 + TL), sH + sgn * s * 200
    taper, tw = [], []
    for k in range(int(TL / 5) + 1):
        u = k * 5.; w = RAMP_W * smooth01(min(1., u / TAPER_W))
        taper.append(hwy_at(s_far + (s_near - s_far) * u / TL, s * (HWY_W / 2 + w / 2 + .02))[0]); tw.append(max(w, .01))
    T = taper[-1]
    if exit_:
        curve = resample(bez(T, (T[0] + v[0] * 80, T[1] + v[1] * 80), (J[0] - v[0] * 70, J[1] - v[1] * 70), J, 50), 4.)
        pts = taper + curve[1:]; ws = tw + [RAMP_W] * (len(curve) - 1)
    else:
        curve = resample(bez(J, (J[0] + v[0] * 70, J[1] + v[1] * 70), (T[0] - v[0] * 80, T[1] - v[1] * 80), T, 50), 4.)
        pts = curve + taper[::-1][1:]; ws = [RAMP_W] * (len(curve) - 1) + tw[::-1]
    C = cum(pts); L = C[-1]; GR = 46.
    zs = []
    for c in C:
        u = c if exit_ else L - c                          # distance depuis le début du biseau
        zs.append(HWY_H if u <= TL else HWY_H * (1 - smooth01(min(1, (u - TL) / max(1, L - TL - GR)))))
    return pts, zs, C, (s_far, s_near), ws

def hwy_dist(p):
    return min(math.dist(p, q) for q in HWY[::1] if abs(q[0] - p[0]) < 120) if any(abs(q[0] - p[0]) < 120 for q in HWY) else 1e9

def interchange(c):
    sH, eid, se, P, ang = c
    _, tH, _ = at(HWY, sH, HC); nH = (-tH[1], tH[0])
    made = 0
    for s in (1, -1):
        v = (-s * tH[0], -s * tH[1])                       # sens de circulation de ce côté (on roule à droite)
        for Dj in (72, 62, 54, 46, 40):
            hit = NET.closest(P, 3.)
            e = NET.E[hit[1]]; se_ = hit[2]
            tA = at(e["pts"], se_)[1]
            dsg = 1 if (tA[0] * nH[0] + tA[1] * nH[1]) * s > 0 else -1
            sJ = se_ + dsg * Dj
            if not (0 < sJ < length(e["pts"])) or NET.junction_dist(hit[1], sJ) < 26: continue
            J = at(e["pts"], sJ)[0]
            rx = make_ramp(sH, s, J, v, True); ry = make_ramp(sH, s, J, v, False)
            ok = True
            for pts, zs, C, _, _ in (rx, ry):
                for p, z_ in zip(pts, zs):
                    if zone_at(*p, 3) or p[1] > SHORE(p[0]) - 20: ok = False; break
                    if z_ < HWY_H - .01 and hwy_dist(p) < HWY_W / 2 + RAMP_W / 2 - .5: ok = False; break
                if not ok: break
                for cr in NET.crossings(pts):
                    if math.dist(cr[3], J) > 4: ok = False; break
                if not ok: break
            if not ok: continue
            # au sol : le dernier bout de chaque bretelle est une vraie route qui arrive au carrefour J
            nJ = NET.split(hit[1], sJ)
            for (pts, zs, C, (s_far, s_near), ws), exit_ in ((rx, True), (ry, False)):
                L = C[-1]
                if exit_: g = next(i for i, z_ in enumerate(zs) if i > 15 and z_ < .12); air, ground = pts[:g + 1], pts[g:]; wair = ws[:g + 1]
                else: g = max(i for i, z_ in enumerate(zs) if i < len(zs) - 15 and z_ < .12); air, ground = pts[g:], pts[:g + 1]; wair = ws[g:]
                zair = zs[:g + 1] if exit_ else zs[g:]
                nG = NET.node(ground[0] if exit_ else ground[-1], "ramp")
                if exit_: NET.edge(nG, nJ, ground, RAMP_W, 0., "ramp")
                else: NET.edge(nJ, nG, ground, RAMP_W, 0., "ramp")
                # le musoir : là où la bretelle s'est assez écartée de l'autoroute (2,5 m entre les deux tabliers)
                order = list(range(len(air))) if exit_ else list(range(len(air) - 1, -1, -1))
                Ca = cum(air); La = Ca[-1]
                gore = []
                for i in order:
                    if abs(Ca[i] - (0 if exit_ else La)) < TAPER_W + TAPER_P - .1: continue
                    gap = hwy_dist(air[i]) - HWY_W / 2 - RAMP_W / 2
                    gore.append((i, gap))
                    if gap > 2.5: break
                ig = gore[-1][0] if gore else order[0]
                ug = Ca[ig] if exit_ else La - Ca[ig]
                gaps = [(1, 0, ug + 1)] if exit_ else [(1, La - ug - 1, La)]
                sg = min(range(len(HWY)), key=lambda k: math.dist(HWY[k], air[ig])); sgH = HC[sg]
                RAMPS.append((air, zair, gaps, wair, gore, exit_))
                HWY_GAPS.append((s, s_far, sgH + 1) if s_far < sgH else (s, sgH - 1, s_far))   # s'arrête pile au début du biseau
                RAMP_CELLS.update(band_cells(air, RAMP_W / 2 + 9))
                mark_road(pts, RAMP_W + 4)
            made += 1; break
    print("échangeur", [round(q) for q in P], ": côtés équipés", made)

cr = [c for c in NET.crossings(HWY) if NET.E[c[1]]["cls"] == "arterial" and c[4] > math.radians(55)]
chosen = []
for target in (100, -450):
    c = min((c for c in cr if all(abs(c[3][0] - o[3][0]) > 300 for o in chosen)), key=lambda c: abs(c[3][0] - target), default=None)
    if c: chosen.append(c)
for c in chosen: interchange(c)

# ═══════════════════════════════════════ les rues de quartier : elles poussent depuis les routes existantes
INTERCH = [c[3] for c in chosen]    # les losanges des échangeurs : ni maison ni rue dedans
def free_land(x, y):
    return in_frame_or_close(x, y) and not zone_at(x, y, 10) and not on_road(x, y) and not in_nature(x, y) \
        and cell_of(x, y) not in HWY_CELLS and cell_of(x, y) not in RAMP_CELLS and all(math.hypot(x - p[0], y - p[1]) > 150 for p in INTERCH)
def street_ok(x, y, ang, w, walk, zone_ok=False):
    H = w / 2 + walk; sx, sy = -math.sin(ang), math.cos(ang)
    for o in (-H - 1.5, 0, H + 1.5):
        px, py = x + sx * o, y + sy * o
        if not in_frame_or_close(px, py) or in_nature(px, py): return False
        c = cell_of(px, py)
        if c in BUSY or c in HWY_CELLS or c in RAMP_CELLS or any(math.hypot(px - p[0], py - p[1]) < 140 for p in INTERCH): return False
        if not zone_ok and zone_at(px, py, 14): return False
    return True

def bulb_ok(x, y, w, walk):
    Rb = w / 2 + 6.5 + walk
    if NET.clearance((x, y)) < Rb + 7: return False
    for k in range(10):
        a = k / 10 * 6.283
        px, py = x + math.cos(a) * (Rb + 1), y + math.sin(a) * (Rb + 1)
        if not in_frame_or_close(px, py) or zone_at(px, py, 10) or cell_of(px, py) in BUSY or cell_of(px, py) in HWY_CELLS or cell_of(px, py) in RAMP_CELLS: return False
    return True

BULBS = []             # raquettes : (centre, rayon extérieur, direction d'arrivée) → parcelles en éventail
GAP_ST = 26.           # écart mini entre les trottoirs de deux rues parallèles (une rangée de parcelles tient entre les deux)
N_STREETS = [0, 0, 0]     # rues, en T sur une autre, en raquette
def grow(seed):
    kind, depth = seed[0], seed[-1]
    if kind == "edge":
        _, p, side, _ = seed
        hit = NET.closest(p, 3.)
        if not hit: return
        _, eid, se, q = hit
        e = NET.E[eid]
        if e["cls"] == "ramp" or NET.junction_dist(eid, se) < 34: FAIL["jd"] += 1; return
        t = at(e["pts"], se)[1]
        ang = math.atan2(side * t[0], -side * t[1]) + R.uniform(-.15, .15)
        w, walk, cls = 8., 2.2, "rue"; start_free = e["w"] / 2 + e["walk"] + 2; zone_until = 0
        if not street_ok(q[0] + math.cos(ang) * (start_free + 6), q[1] + math.sin(ang) * (start_free + 6), ang, w, walk): FAIL["start"] += 1; return
    else:
        _, zk, g, _ = seed
        if not gate_free(zk, g): return
        eid = None; q = g[0]; ang = math.atan2(g[1][1], g[1][0])
        w, walk, cls = g[2], 3.5, "avenue"; start_free = 0; zone_until = 34
    step = 4.; x, y = q; pts = [q]; L = 0.; k = 0.
    maxL = R.uniform(80, 200) if kind == "edge" else R.uniform(100, 200)
    while L < maxL:
        kmax = .03 if cls == "rue" else .012
        k = max(-kmax, min(kmax, k + R.uniform(-.007, .007)))
        a2 = ang + (k * step if L > 20 else 0)
        nx, ny = x + math.cos(a2) * step, y + math.sin(a2) * step; L2 = L + step
        if not street_ok(nx, ny, a2, w, walk, L2 < zone_until): break
        if L2 > start_free:
            skip = {eid} if (eid is not None and L2 < start_free + w / 2 + walk + GAP_ST + 10) else set()
            if NET.clearance((nx, ny), skip) < w / 2 + walk + GAP_ST: break
        ang = a2; x, y = nx, ny; pts.append((x, y)); L = L2
    # au bout : une rue droit devant ? on s'y raccorde en T
    target = None
    if L >= 20:
        d = (math.cos(ang), math.sin(ang))
        h = NET.ray((x, y), d, 36, skip={eid} if eid is not None else set())
        if h:
            dist, heid, hse, hq, ht = h
            ok = NET.E[heid]["cls"] != "ramp" and abs(d[0] * ht[1] - d[1] * ht[0]) > .82 and NET.junction_dist(heid, hse) > 30
            for kk in range(1, int(dist / 3)):
                if not ok: break
                px, py = x + d[0] * kk * 3, y + d[1] * kk * 3
                if dist - kk * 3 > NET.E[heid]["w"] / 2 + NET.E[heid]["walk"] + 2 and not street_ok(px, py, ang, w, walk): ok = False
                if NET.clearance((px, py), {heid}) < w / 2 + walk + 4: ok = False
            if ok:
                ext = resample([(x, y), hq], 4.)
                pts += ext[1:]; L += dist; target = (hq,)
    if target is None:          # sinon : une impasse en raquette, s'il y a la place
        while len(pts) > 2 and L >= 34 and not bulb_ok(pts[-1][0], pts[-1][1], w, walk):
            pts.pop(); L -= step
        if L < 34 or not bulb_ok(pts[-1][0], pts[-1][1], w, walk): FAIL["bulb%d" % (L // 20)] += 1; return
    if L < (30 if kind == "edge" else 60): return
    na = NET.split(eid, se) if kind == "edge" else gate_node(zk, g, w, walk)
    if target:
        hh = NET.closest(target[0], 2.); nb = NET.split(hh[1], hh[2])
    else: nb = NET.node(pts[-1], "end")
    NET.edge(na, nb, pts, w, walk, cls)
    mark_road(pts, w + 2 * walk + 2)
    N_STREETS[0] += 1
    if target: N_STREETS[1] += 1
    else:
        N_STREETS[2] += 1
        cx, cy = pts[-1]; Rb = w / 2 + 6.5
        mark_road([(cx, cy), (cx + .1, cy)], 2 * (Rb + walk) + 2)
        (x0, y0), (x1, y1) = pts[-2], pts[-1]; a0 = math.atan2(y1 - y0, x1 - x0)
        BULBS.append((cx, cy, Rb + walk, a0))
    if depth > 0:
        for kk in range(R.randint(1, 3)):
            if L < 70: break
            s_ = R.uniform(35, L - 35); p_ = at(pts, s_)[0]
            QUEUE.append(("edge", p_, R.choice([-1, 1]), depth - 1))

QUEUE = []
import collections; FAIL = collections.Counter()
for eid, e in list(NET.E.items()):
    if e["cls"] not in ("arterial", "avenue"): continue
    Lx = length(e["pts"]); s_ = R.uniform(30, 60)
    while s_ < Lx - 30:
        p_ = at(e["pts"], s_)[0]
        pr = .6 if math.hypot(p_[0], p_[1] * 1.2) < 650 else .2
        for side in (-1, 1):
            if R.random() < pr: QUEUE.append(("edge", p_, side, 3))
        s_ += R.uniform(38, 60)
for zk_ in ("core", "town"):
    for g in GATES[zk_]:
        if gate_free(zk_, g) and R.random() < .6: QUEUE.append(("gate", zk_, g, 3))
R.shuffle(QUEUE)
while QUEUE:
    grow(QUEUE.pop(0))
print("rues :", N_STREETS[0], "dont en T", N_STREETS[1], "en raquette", N_STREETS[2])

CIVIC = 0

# les parcelles : toutes les rues pavillonnaires, et les boulevards près de la ville (maisons de ville, plus en retrait)
for eid, e in sorted(NET.E.items(), key=lambda kv: kv[1]["cls"] != "rue"):
    if e["cls"] == "ramp": continue
    pts = e["pts"]; mid = at(pts, length(pts) / 2)[0]; rr = math.hypot(mid[0], mid[1] * 1.2)
    if e["cls"] == "rue": lots_along(pts, e["w"], e["walk"], free_land, town_p=.18 if rr < 520 else .05)
    elif e["cls"] == "avenue": lots_along(pts, e["w"], e["walk"], free_land, town_p=.35)
    elif rr < 720: lots_along(pts, e["w"], e["walk"] + 3, free_land, town_p=.5, fronts=(18, 16), depths=(32, 26))
for cx, cy, Rt, a0 in BULBS:          # en éventail autour des raquettes
    for kk in range(7):
        a = a0 - 1.9 + kk * .63
        n = (math.cos(a), math.sin(a)); t = (-n[1], n[0])
        x0, y0 = cx + n[0] * (Rt + .6), cy + n[1] * (Rt + .6)
        for D in (26, 20):
            ccx, ccy = x0 + n[0] * D / 2, y0 + n[1] * D / 2; rot = math.atan2(n[1], n[0]) - math.pi / 2
            ccx, ccy = x0 + n[0] * (D + 5) / 2, y0 + n[1] * (D + 5) / 2
            if all(free_land(x0 + t[0] * u + n[0] * v, y0 + t[1] * u + n[1] * v) for u in (-6, 6) for v in (5.5, D)) and free(ccx, ccy, 12, D - 5.4, rot):
                lot(x0, y0, t, n, 13, D); break
print("maisons", HOUSES, "équipements", CIVIC)

# ═══════════════════════════════════════ dessin du réseau (kit rue) + le viaduc (kit autoroute)
def road_cb(pts, e, closed):
    w, walk = e["w"], e["walk"]; H = w / 2 + max(walk, .45)
    mark_road(pts, 2 * H + 2)
    if e["cls"] == "ramp":
        lanes_cars(pts, w, two_way=False, dens=.5); return
    lanes_cars(pts, w * .8, dens=.8 if e["cls"] == "arterial" else .3)
    Lx = length(pts)
    for side in (-1, 1):
        s_ = R.uniform(4, 9); k = 0
        while s_ < Lx - 4:
            p, t, _ = at(pts, s_); nx, ny = -t[1] * side, t[0] * side
            tx, ty = p[0] + nx * (H + 2.4), p[1] + ny * (H + 2.4)
            if R.random() < .8 and cell_of(tx, ty) not in BUSY and NET.clearance((tx, ty)) > 1.5 and not zone_at(tx, ty, 3) and cell_of(tx, ty) not in HWY_CELLS:
                inst(R.choice(TREES), tx, ty, 0, R.uniform(0, 6.3), R.uniform(.8, 1.1))
            if walk > 1 and k % 3 == (0 if side > 0 else 1):
                lx, ly = p[0] + nx * (H - .6), p[1] + ny * (H - .6)
                if NET.clearance((lx, ly)) > -walk - .5: lamp(lx, ly, math.atan2(-ny, -nx))
            s_ += R.uniform(10, 13); k += 1

KIT = Kit(A, NET)
KIT.node_cb = junction_props
KIT.render(lambda pts, e, closed: (road_cb(pts, e, closed), edge_props(pts, e)))
core_finish(CORE); core_finish(TOWN)
core_bus_stops(CORE, 12); core_bus_stops(TOWN, 3)
for z in ZONES:
    if z.kind in ("industrie", "logistique"): ring_finish(z)
print("réseau dessiné :", len(NET.E), "tronçons,", sum(1 for n in NET.N if len(n["e"]) >= 3), "carrefours,", sum(1 for n in NET.N if n["kind"] == "end" and n["e"]), "raquettes")

def pier_ok(x, y): return NET.clearance((x, y)) > 1.5 and not on_road_grid(x, y)
def on_road_grid(x, y): return any(z.inside(x, y, 8) for z in ZONES)
def deck(pts, zs, width, lanes=2, pier_every=34, cars=True, gaps=(), car_span=None):
    """kit autoroute : tablier (largeur fixe ou variable pour les biseaux), glissières (ouvertes là où une bretelle
    s'en détache : la ligne de rive devient pointillée), flancs, piles"""
    n = len(pts); C = cum(pts)
    W = list(width) if isinstance(width, (list, tuple)) else [width] * n
    N_ = []
    for i in range(n):
        a_, b_ = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        nx, ny = -(b_[1] - a_[1]), b_[0] - a_[0]; l = math.hypot(nx, ny) or 1; N_.append((nx / l, ny / l))
    P = lambda i, k, e, z: (pts[i][0] + N_[i][0] * (k * W[i] / 2 + e), pts[i][1] + N_[i][1] * (k * W[i] / 2 + e), z)
    col = (.55, .54, .52)
    def quad(mat, i, k0, e0, k1, e1, dz):
        A.face(mat, [P(i, k0, e0, zs[i] + dz), P(i + 1, k0, e0, zs[i + 1] + dz), P(i + 1, k1, e1, zs[i + 1] + dz), P(i, k1, e1, zs[i] + dz)], None, col)
    def wallq(mat, i, k, e, a0, a1, b0, b1):
        A.face(mat, [P(i, k, e, a0), P(i + 1, k, e, a1), P(i + 1, k, e, b1), P(i, k, e, b0)], None, col)
    for i in range(n - 1):
        z0, z1 = zs[i], zs[i + 1]; m = (C[i] + C[i + 1]) / 2
        quad("asphalt", i, -1, 0, 1, 0, 0)
        if min(z0, z1) > 1.8: quad("concrete", i, -1, 0, 1, 0, -1.7)
        for sd in (-1, 1):
            opened = any(g[0] == sd and g[1] <= m <= g[2] for g in gaps)
            barrier = not opened and min(z0, z1) > 1.2 and (min(W[i], W[i + 1]) > 2 or (lanes == 1 and sd == -1))
            top = 1. if barrier else 0.
            wallq("concrete", i, sd, 0, max(0, z0 - 1.7), max(0, z1 - 1.7), z0 + top, z1 + top)
            if barrier:
                wallq("concrete", i, sd, -sd * .5, z0, z1, z0 + 1, z1 + 1)
                quad("concrete", i, sd, -sd * .5, sd, 0, 1.)
            if not opened:
                if min(W[i], W[i + 1]) > 3: quad("paint_w", i, sd, -sd * 1.3, sd, -sd * 1.1, .02)
            elif lanes == 1 and i % 2 == 0 and min(W[i], W[i + 1]) > 1:
                quad("paint_w", i, sd, -sd * .55, sd, -sd * .15, .02)       # voie d'insertion : pointillés épais côté autoroute
    if lanes > 1:
        for sd in ([-1, 1] if lanes == 4 else [0]):
            for k in range(0, n - 2, 3):
                quad("paint_w", k, sd * .5, -.09, sd * .5, .09, .02)
    if lanes == 4:
        for i in range(n - 1):
            quad("concrete", i, 0, -.3, 0, .3, .8)
            for sd in (-1, 1): wallq("concrete", i, 0, sd * .3, zs[i], zs[i + 1], zs[i] + .8, zs[i + 1] + .8)
    nextp = pier_every / 2
    for i in range(n - 1):
        if C[i] < nextp: continue
        nextp += pier_every
        x, y = pts[i]; z_ = zs[i]
        if z_ < 3 or W[i] < 4: continue
        ang = math.atan2(pts[i + 1][1] - y, pts[i + 1][0] - x)
        if W[i] > 12:
            ok = []
            for sd in (-1, 1):
                px, py = x - math.sin(ang) * sd * W[i] * .22, y + math.cos(ang) * sd * W[i] * .22
                if pier_ok(px, py): A.box("concrete", px, py, 0, 2.4, 2.4, z_ - 1.7, ang); ok.append(sd)
            if ok: A.box("concrete", x, y, z_ - 3.1, 2.6, W[i] * .8, 1.4, ang)
        elif pier_ok(x, y):
            A.box("concrete", x, y, 0, 2, 2, z_ - 1.7, ang)
    if cars:
        total = C[-1]; lo, hi = car_span or (0, total)
        for lane in ([-W[0] * .36, -W[0] * .14, W[0] * .14, W[0] * .36] if lanes == 4 else [0]):
            d_ = lo + R.uniform(0, 30)
            while d_ < hi - 5:
                p, t, i = at(pts, d_, C); z_ = zs[i] + (zs[i + 1] - zs[i]) * ((d_ - C[i]) / ((C[i + 1] - C[i]) or 1))
                ang = math.atan2(t[1], t[0]); px, py = p[0] - t[1] * lane, p[1] + t[0] * lane
                if lane < 0: ang += math.pi
                if R.random() < .12: inst(TRUCK, px, py, z_, ang, 1, R.choice([(.9, .9, .9), (.1, .2, .5), (.7, .1, .08)]))
                else: inst(CAR, px, py, z_, ang, 1, TAXI if R.random() < .15 else R.choice(CAR_COLS))
                CARS.append((px, py, ang, False))
                d_ += R.uniform(14, 45)

def gore(pts, zs, ws, gore_pts):
    """le musoir : zone hachurée entre la bretelle qui s'écarte et l'autoroute, avec un amortisseur jaune au bout"""
    prev = None
    for i, gap in gore_pts:
        a_, b_ = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        nx, ny = -(b_[1] - a_[1]), b_[0] - a_[0]; l = math.hypot(nx, ny) or 1; nx, ny = nx / l, ny / l
        r_ = (pts[i][0] + nx * ws[i] / 2, pts[i][1] + ny * ws[i] / 2)                 # bord de la bretelle, côté autoroute
        h_ = (r_[0] + nx * max(gap, 0), r_[1] + ny * max(gap, 0))                       # bord de l'autoroute
        z = zs[i] + .01
        if prev:
            pr, ph, pz = prev
            A.face("asphalt", [(pr[0], pr[1], pz), (r_[0], r_[1], z), (h_[0], h_[1], z), (ph[0], ph[1], pz)], None, (.5, .5, .5))
            A.face("concrete", [(pr[0], pr[1], pz - 1.7), (r_[0], r_[1], z - 1.7), (h_[0], h_[1], z - 1.7), (ph[0], ph[1], pz - 1.7)], None, (.55, .54, .52))
            # hachures en diagonale
            dx, dy = h_[0] - pr[0], h_[1] - pr[1]; L_ = math.hypot(dx, dy) or 1; qx, qy = -dy / L_ * .2, dx / L_ * .2
            A.face("paint_w", [(pr[0] - qx, pr[1] - qy, pz + .02), (h_[0] - qx, h_[1] - qy, z + .02), (h_[0] + qx, h_[1] + qy, z + .02), (pr[0] + qx, pr[1] + qy, pz + .02)], None, (.5, .5, .5))
        prev = (r_, h_, z)
    if prev:
        r_, h_, z = prev; cx, cy = (r_[0] + h_[0]) / 2, (r_[1] + h_[1]) / 2
        i = gore_pts[-1][0]; a_, b_ = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        rot = math.atan2(b_[1] - a_[1], b_[0] - a_[0])
        A.box("painted", cx, cy, z, 2.6, max(1., math.dist(r_, h_) - .3), .9, rot, col=(.9, .72, .05))
        A.box("concrete", cx, cy, z - 1.7, 2.6, max(1., math.dist(r_, h_)), 1.7, rot)

deck(HWY, [HWY_H] * len(HWY), HWY_W, lanes=4, gaps=HWY_GAPS)
mark_road(HWY, HWY_W + 8)
for pts, zs, gaps, ws, gp, exit_ in RAMPS:
    La = length(pts)
    deck(pts, zs, ws, lanes=1, pier_every=26, cars=True, gaps=gaps, car_span=(TAPER_W, La) if exit_ else (0, La - TAPER_W))
    gore(pts, zs, ws, gp)
print("routes ok")
if "--plan" in ARGS:     # plan 2D du réseau (contrôle rapide, sans rendu)
    from PIL import Image, ImageDraw
    S = 2.; W_, H_ = 2000, 1400
    im = Image.new("RGB", (int(W_ * S / 1.25), int((H_ + 400) * S / 1.25)), (200, 215, 190)); dr = ImageDraw.Draw(im)
    T = lambda p: ((p[0] + 1000) * S / 1.25, (700 - p[1]) * S / 1.25)
    for z in [zz for zz in ZONES[1:] if not isinstance(zz, Core)]:
        dr.polygon([T(z.w(a * z.h[0], b * z.h[1])) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))], fill=(170, 170, 185))
    for G_ in (CORE, TOWN):
        for (i, j) in G_.incl:
            dr.polygon([T(G_.w(G_.us[i] + a, G_.vs[j] + b)) for a, b in ((0, 0), (G_.PU, 0), (G_.PU, G_.PV), (0, G_.PV))], fill=(150, 150, 170), outline=(90, 90, 90))
    for c in BUSY: dr.rectangle([T((c[0] * CELL, c[1] * CELL + CELL)), T((c[0] * CELL + CELL, c[1] * CELL))], fill=(190, 120, 100))
    for e in NET.E.values():
        col = {"arterial": (40, 40, 40), "avenue": (70, 70, 90), "rue": (90, 90, 90), "ramp": (200, 60, 30)}[e["cls"]]
        dr.line([T(p) for p in e["pts"]], fill=(235, 235, 225), width=max(1, int((e["w"] + 2 * e["walk"]) * S / 1.25)))
        dr.line([T(p) for p in e["pts"]], fill=col, width=max(1, int(e["w"] * S / 1.25)))
    for n in NET.N:
        if not n["e"]: continue
        c = {"end": (0, 120, 255), "gate": (0, 200, 0), "ramp": (255, 0, 0)}.get(n["kind"], (255, 200, 0) if len(n["e"]) >= 3 else None)
        if c: x, y = T(n["p"]); dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=c)
    dr.line([T(p) for p in HWY], fill=(120, 60, 160), width=int(HWY_W * S / 1.25))
    for pts, zs, g, *_ in RAMPS: dr.line([T(p) for p in pts], fill=(220, 120, 200), width=int(RAMP_W * S / 1.25))
    im.save(os.path.join(HERE, "plan.png")); print("plan.png"); sys.exit(0)

# ═══════════════════════════════════════ le relief : collines, rochers, plage
GX0, GX1, GY0, GY1, GS = -1080., 1080., -1260., 1100., 6.
xs = np.arange(GX0, GX1 + GS, GS); ys = np.arange(GY0, GY1 + GS, GS)
X, Y = np.meshgrid(xs, ys)
# distance aux quartiers (boîtes orientées)
DZ = np.full(X.shape, 1e9)
BOXES = [(z.c, z.h, z) for z in ZONES[1:] if not isinstance(z, Core)]
for G_ in (CORE, TOWN):
    for (i, j) in G_.incl:
        cu, cv = (G_.us[i] + G_.us[i + 1]) / 2, (G_.vs[j] + G_.vs[j + 1]) / 2
        BOXES.append((G_.w(cu, cv), (G_.PU / 2, G_.PV / 2), G_))
for c_, h_, z in BOXES:
    dx, dy = X - c_[0], Y - c_[1]
    lu, lv = dx * z.cs + dy * z.sn, -dx * z.sn + dy * z.cs
    mg = 8 if isinstance(z, Core) else 20        # autour des zones industrielles : rue de ceinture + trottoir + marge
    qu, qv = np.abs(lu) - h_[0] - mg, np.abs(lv) - h_[1] - mg
    DZ = np.minimum(DZ, np.hypot(np.maximum(qu, 0), np.maximum(qv, 0)) + np.minimum(np.maximum(qu, qv), 0))
# distance aux routes (propagation sur la grille)
RD = np.full(X.shape, 1e9)
ii = ((np.array([c[0] for c in ROAD]) * CELL + CELL / 2 - GX0) / GS).astype(int)
jj = ((np.array([c[1] for c in ROAD]) * CELL + CELL / 2 - GY0) / GS).astype(int)
ok = (ii >= 0) & (ii < len(xs)) & (jj >= 0) & (jj < len(ys))
RD[jj[ok], ii[ok]] = 0
if LOTS:                                   # les parcelles aussi sont à plat
    li = ((np.array([c[0] for c in LOTS]) * CELL + CELL / 2 - GX0) / GS).astype(int)
    lj = ((np.array([c[1] for c in LOTS]) * CELL + CELL / 2 - GY0) / GS).astype(int)
    ok2 = (li >= 0) & (li < len(xs)) & (lj >= 0) & (lj < len(ys)); RD[lj[ok2], li[ok2]] = 0
for _ in range(22):
    for sh, cst in (((0, 1), GS), ((0, -1), GS), ((1, 0), GS), ((-1, 0), GS), ((1, 1), GS * 1.41), ((-1, -1), GS * 1.41), ((1, -1), GS * 1.41), ((-1, 1), GS * 1.41)):
        RD = np.minimum(RD, np.roll(RD, sh, axis=(0, 1)) + cst)
D = np.minimum(DZ, RD)
mask = np.clip((D - 8) / 34, 0, 1); mask = mask * mask * (3 - 2 * mask)
# collines : bosses gaussiennes + petites ondulations
def vnoise(scale, seed):
    """bruit de valeur lissé (interpolation bicubique simple) sur la grille du terrain"""
    rs = np.random.RandomState(seed)
    gw, gh = int((GX1 - GX0) / scale) + 3, int((GY1 - GY0) / scale) + 3
    G = rs.rand(gh, gw)
    fx, fy = (X - GX0) / scale, (Y - GY0) / scale
    ix, iy = fx.astype(int), fy.astype(int); tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a, b, c_, d_ = G[iy, ix], G[iy, ix + 1], G[iy + 1, ix], G[iy + 1, ix + 1]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c_ * (1 - tx) + d_ * tx) * ty
def fbm(base, octaves, seed, ridged=False):
    out = np.zeros(X.shape); amp, tot = 1., 0.
    for o in range(octaves):
        n = vnoise(base / 2 ** o, seed + o)
        if ridged: n = 1 - np.abs(2 * n - 1); n = n * n
        out += amp * n; tot += amp; amp *= .5
    return out / tot
rolling = fbm(260, 5, 11)                      # grandes ondulations
ridges = fbm(180, 5, 31, ridged=True)          # crêtes et arêtes rocheuses
Rr = np.hypot(X, Y * 1.2)
outer = np.clip((Rr - 250) / 420, 0, 1)        # plus on s'éloigne du centre, plus c'est accidenté
nat = np.exp(-(((X - NATURE[0]) / 150) ** 2 + ((Y - NATURE[1]) / 120) ** 2))
Hh = 60 * (rolling - .3).clip(0) * (.45 + outer) + 75 * ridges ** 1.6 * (.15 + .85 * np.maximum(outer, nat)) + 30 * nat * fbm(90, 4, 51)
bumps = []
H = Hh * mask
# plage et fonds marins
SH = np.array([SHORE(x) for x in xs])[None, :]
beach = np.clip((Y - (SH - 30)) / 30, 0, 1)
H = np.maximum(H, 0) * (1 - beach) - np.clip((Y - SH) * .12, 0, 8)
def height(x, y):
    fi, fj = (x - GX0) / GS, (y - GY0) / GS
    i, j = int(fi), int(fj)
    if i < 0 or j < 0 or i >= len(xs) - 1 or j >= len(ys) - 1: return 0.
    tx, ty = fi - i, fj - j
    return float(H[j, i] * (1 - tx) * (1 - ty) + H[j, i + 1] * tx * (1 - ty) + H[j + 1, i] * (1 - tx) * ty + H[j + 1, i + 1] * tx * ty)
# couleurs : herbe, herbe sèche en hauteur, roche sur les pentes, sable
gy_, gx_ = np.gradient(H, GS)
slope = np.hypot(gx_, gy_)
colg = np.stack([np.full(X.shape, .07), np.full(X.shape, .13), np.full(X.shape, .045)], -1)
dry = np.clip(H / 40, 0, 1)[..., None]
colg = colg * (1 - dry) + np.array([.11, .13, .05]) * dry
rock = np.clip((slope - .7) / .4, 0, 1)[..., None] * .7
colg = colg * (1 - rock) + np.array([.085, .08, .07]) * rock
sand = np.clip((Y - (SH - 42)) / 14, 0, 1)[..., None]
colg = colg * (1 - sand) + np.array([.62, .54, .4]) * sand
nx_, ny_ = len(xs), len(ys)
verts = np.stack([X.ravel(), Y.ravel(), H.ravel()], -1)
idx = np.arange(nx_ * ny_).reshape(ny_, nx_)
quads = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], -1)
me = bpy.data.meshes.new("terrain"); me.from_pydata(verts.tolist(), [], quads.tolist())
ca = me.color_attributes.new("col", "FLOAT_COLOR", "POINT")
ca.data.foreach_set("color", np.concatenate([colg.reshape(-1, 3), np.ones((nx_ * ny_, 1))], -1).ravel().tolist())
sa = me.color_attributes.new("sol", "FLOAT_COLOR", "POINT")          # R = roche (pentes), G = sable : pour les textures photo
sa.data.foreach_set("color", np.concatenate([(rock / .7).reshape(-1, 1), sand.reshape(-1, 1), np.zeros((nx_ * ny_, 1)), np.ones((nx_ * ny_, 1))], -1).ravel().tolist())
for p in me.polygons: p.use_smooth = True
me.materials.append(MAT["terrain"])
COL.objects.link(bpy.data.objects.new("terrain", me))
# la mer
A.face("water", [(-3000, -1500, -1.2), (3000, -1500, -1.2), (3000, 3000, -1.2), (-3000, 3000, -1.2)], [(0, 0), (1, 0), (1, 1), (0, 1)])
# rochers : sur les crêtes et les pentes fortes (affleurements)
n_rock = 0
for k in range(12000):
    x, y = R.uniform(-1000, 1000), R.uniform(-1180, 700)
    j, i = int((y - GY0) / GS), int((x - GX0) / GS)
    if slope[j, i] < .45 or H[j, i] < 8 or zone_at(x, y, 8) or on_road(x, y) or (int(x // CELL), int(y // CELL)) in BUSY: continue
    for kk in range(R.randint(1, 4)):
        px, py = x + R.uniform(-8, 8), y + R.uniform(-8, 8); sc = R.uniform(2.5, 8)
        inst(R.choice(ROCKS), px, py, height(px, py) - sc * .25, R.uniform(0, 6.3), sc, sz=sc * R.uniform(.6, 1.3)); n_rock += 1
n_tree = 0
for k in range(2600):   # forêt dense sur le massif
    a = R.uniform(0, 6.3); r = R.uniform(0, 150) ** 1
    x, y = NATURE[0] + math.cos(a) * r * 1.2, NATURE[1] + math.sin(a) * r * .9
    if zone_at(x, y, 4) or on_road(x, y): continue
    h = height(x, y)
    inst(R.choice(PINES) if h > 25 or R.random() < .4 else R.choice(TREES), x, y, h - .3, R.uniform(0, 6), R.uniform(.9, 1.7))
for k in range(34000):
    x, y = R.uniform(-1000, 1000), R.uniform(-1180, 700)
    j, i = int((y - GY0) / GS), int((x - GX0) / GS)
    if y > SHORE(x) - 38 or on_road(x, y) or zone_at(x, y, 3): continue
    if (int(x // CELL), int(y // CELL)) in BUSY: continue
    r = math.hypot(x, y * 1.2)
    dens = (.55 if r < 600 else .95) * (.7 + .3 * math.sin(x / 61 + 2) * math.cos(y / 47))
    if R.random() > dens: continue
    h = height(x, y)
    if h > 16 or R.random() < .25: inst(R.choice(PINES), x, y, h - .2, R.uniform(0, 6), R.uniform(1, 1.8))
    else: inst(R.choice(TREES), x, y, h - .2, R.uniform(0, 6), R.uniform(.9, 1.5))
    n_tree += 1
# la plage : parasols et transats
for k in range(90):
    x = R.uniform(-200, 1000); y = SHORE(x) - R.uniform(6, 26)
    if on_road(x, y): continue
    A.cyl("metal", x, y, height(x, y), 2.3, .05, 4, top=False)
    A.cyl("fabric", x, y, height(x, y) + 2.1, .5, 1.6, 10, r2=.1, col=R.choice([(.9, .3, .2), (.1, .4, .8), (.95, .85, .2), (.9, .9, .9)]))
print("relief ok, arbres", n_tree)

# ═══════════════════════════════════════ la nuit : halos des lampadaires, phares
if NIGHT > 0:
    for x, y in LAMPS: A.disc_decal("lightpool", x, y, .3, 16)
    for x, y, ang, truck in CARS:
        c, s = math.cos(ang), math.sin(ang)
        fl = 6.9 if truck else 2.25; rl = -8.5 if truck else -2.25
        for side in (-.62, .62):
            hx, hy = x + c * fl - s * side, y + s * fl + c * side
            A.box("headlight", hx, hy, .6, .12, .32, .22, ang, top="headlight")
            tx, ty = x + c * rl - s * side, y + s * rl + c * side
            A.box("taillight", tx, ty, .7, .1, .3, .18, ang, top="taillight")
        A.beam_decal("beam", x + c * (fl + .1), y + s * (fl + .1), .12, ang, 18, 1.8, 8)

A.box = _box0
nf = A.flush(COL)
print("faces fusionnées :", nf, " objets :", len(bpy.data.objects))

# ═══════════════════════════════════════ lumière, caméra, rendu
world = bpy.data.worlds.new("sky"); scene.world = world; world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
sky = wn.new("ShaderNodeTexSky")
for st in ("MULTIPLE_SCATTERING", "NISHITA"):      # selon la version de Blender
    try: sky.sky_type = st; break
    except Exception: pass
sky.sun_elevation = math.radians(L_EL); sky.sun_rotation = math.radians(L_ROT); sky.sun_disc = False
sky.air_density = L_AIR; sky.aerosol_density = L_DUST
try: sky.ozone_density = 1.0
except Exception: pass
bg = wn["Background"]; bg.inputs["Strength"].default_value = L_SKY; wl.new(sky.outputs[0], bg.inputs[0])
if LOOK == "night":
    for lk in list(bg.inputs[0].links): wl.remove(lk)
    bg.inputs[0].default_value = (.006, .010, .022, 1); bg.inputs["Strength"].default_value = 1
sun = bpy.data.lights.new("sun", "SUN"); sun.energy = L_SUNE; sun.angle = math.radians(L_ANG); sun.color = L_SUNC
so = bpy.data.objects.new("sun", sun); COL.objects.link(so)
so.rotation_euler = (math.pi / 2 - math.radians(L_EL), 0, math.radians(L_ROT) + math.pi / 2)

cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; cam.ortho_scale = VIEW_W
cam.clip_start = 10; cam.clip_end = 6000
co = bpy.data.objects.new("cam", cam); COL.objects.link(co); scene.camera = co
EL = math.radians(45); target = Vector((0, -212, 0)); dist = 2500
co.location = target + Vector((0, -math.cos(EL), math.sin(EL))) * dist
co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()

scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"
try:   # carte graphique si possible (Metal sur Mac, OptiX/CUDA sur PC) : 10 à 30 fois plus rapide
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type != "CPU"]
            if gpus:
                for d in prefs.devices: d.use = d.type != "CPU"
                scene.cycles.device = "GPU"; print("rendu sur", kind, [d.name for d in gpus]); break
        except Exception: pass
except Exception as e: print("GPU :", e)
scene.cycles.samples = SAMPLES; scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4; scene.cycles.diffuse_bounces = 2; scene.cycles.glossy_bounces = 2
scene.cycles.transparent_max_bounces = 12
scene.render.resolution_x, scene.render.resolution_y = RES; scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
try: scene.view_settings.look = "AgX - Medium High Contrast"
except Exception: pass
scene.view_settings.exposure = L_EXPO
scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_mode = "RGB"
if CROP:   # un morceau de l'image à pleine résolution (pour vérifier les détails)
    scene.render.use_border = True; scene.render.use_crop_to_border = True
    scene.render.border_min_x, scene.render.border_min_y, scene.render.border_max_x, scene.render.border_max_y = CROP

bpy.context.view_layer.update()
out = []
for sid, nom, p in SLOTS:
    ndc = world_to_camera_view(scene, co, Vector(p))
    if 0 < ndc.x < 1 and 0 < ndc.y < 1: out.append({"id": sid, "nom": nom, "uv": [round(ndc.x, 5), round(ndc.y, 5)]})
# identifiants uniques (usine, usine-2…)
seen = {}
for e in out:
    k = e["id"]; seen[k] = seen.get(k, 0) + 1
    if seen[k] > 1: e["id"] = f"{k}-{seen[k]}"; e["nom"] = f"{e['nom']} {seen[k]}"
FEN = []
if LOOK == "night" and not CROP:
    dg = bpy.context.evaluated_depsgraph_get()
    fwd = (co.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
    cand = R_WIN.sample(WINDOWS, min(len(WINDOWS), 16000))
    for (x, y, z, tx, ty, ww, hh) in cand:
        p = Vector((x, y, z)) - Vector((tx, ty, 0)).cross(Vector((0, 0, 1))).normalized() * .0   # centre de la vitre
        o = p - fwd * 2000
        hit, loc, *_ = scene.ray_cast(dg, o, fwd, distance=2100)
        if not hit or (loc - p).length > 1.2: continue                 # cachée par un autre bâtiment (ou un arbre)
        c0 = world_to_camera_view(scene, co, p)
        if not (0 < c0.x < 1 and 0 < c0.y < 1): continue
        a0 = world_to_camera_view(scene, co, p + Vector((tx, ty, 0)) * ww / 2); a1 = world_to_camera_view(scene, co, p - Vector((tx, ty, 0)) * ww / 2)
        b0 = world_to_camera_view(scene, co, p + Vector((0, 0, hh / 2))); b1 = world_to_camera_view(scene, co, p - Vector((0, 0, hh / 2)))
        FEN.append([c0.x, c0.y, a0.x - a1.x, a0.y - a1.y, b0.x - b1.x, b0.y - b1.y])
        if len(FEN) >= 7000: break
    print("fenêtres animables :", len(FEN), "sur", len(WINDOWS))
if LOOK == "day":
    with open(os.path.join(OUT, "emplacements_preview.json" if PREVIEW else "emplacements.json"), "w") as f:
        json.dump({"image": list(RES), "largeur_m": VIEW_W, "emplacements": out}, f, ensure_ascii=False, indent=2)
print("emplacements :", [(e["id"], e["uv"]) for e in out])
print("biseaux :", [[round(v, 3) for v in world_to_camera_view(scene, co, Vector((p[0][0][0], p[0][0][1], HWY_H)))[:2]] for p in RAMPS])
print("parcs :", [(k, [round(v, 3) for v in world_to_camera_view(scene, co, Vector((x, y, 0)))[:2]]) for k, x, y in PARKS_DBG])
scene.render.filepath = os.path.join(OUT, ("crop" if CROP else "preview" if PREVIEW else "city") + ("" if LOOK == "day" else "_" + LOOK) + ".png")
WEB = os.path.normpath(os.path.join(HERE, "..", "public", "city"))
if SOLEIL and os.path.isdir(WEB):
    # la course du soleil : même ville, seuls le ciel, le soleil et l'exposition changent d'une image à l'autre
    DOSSIER = os.path.join(WEB, "soleil"); os.makedirs(DOSSIER, exist_ok=True)
    s_ = scene.render.image_settings; s_.file_format = "WEBP"; s_.quality = 80; s_.color_mode = "RGB"
    manifeste = {"largeur": RES[0], "segments": {}}
    for a, b in SEGMENTS:
        noms = []
        for k in range(1, SOLEIL + 1):
            el, rot, sc, se, sk, ex, _n, ang, du, air = soleil_params(a, b, k / (SOLEIL + 1))
            sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
            sky.air_density = air; sky.aerosol_density = du; bg.inputs["Strength"].default_value = sk
            sun.energy = se; sun.angle = math.radians(ang); sun.color = sc
            so.rotation_euler = (math.pi / 2 - math.radians(el), 0, math.radians(rot) + math.pi / 2)
            scene.view_settings.exposure = ex
            nom = f"{a}-{b}-{k}.webp"; scene.render.filepath = os.path.join(DOSSIER, nom)
            bpy.ops.render.render(write_still=True); noms.append("soleil/" + nom)
            print(f"rendu : soleil {a} → {b}  {k}/{SOLEIL}")
        manifeste["segments"][f"{a}-{b}"] = noms
    with open(os.path.join(WEB, "soleil.json"), "w") as f: json.dump(manifeste, f)
    print("site mis à jour :", DOSSIER, "(course du soleil)")
elif "--no-render" not in ARGS:
    bpy.ops.render.render(write_still=True); print("rendu :", scene.render.filepath)
    if not PREVIEW and not CROP and os.path.isdir(WEB):
        # directement pour le site : WebP 8K + WebP 4K (téléphones) + les emplacements
        name = "city" + ("" if LOOK == "day" else "_" + LOOK)
        img = bpy.data.images.load(scene.render.filepath)
        s_ = scene.render.image_settings; s_.file_format = "WEBP"; s_.quality = 84; s_.color_mode = "RGB"
        img.save_render(os.path.join(WEB, name + ".webp"), scene=scene)
        img.scale(RES[0] // 2, RES[1] // 2)
        if FEN:
            Wp, Hp = img.size; px = np.empty(Wp * Hp * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(Hp, Wp, 4)
            out_f = []
            for (u, v, ax, ay, bx, by) in FEN:
                i_, j_ = int(u * Wp), int(v * Hp)
                if not (1 <= i_ < Wp - 1 and 1 <= j_ < Hp - 1): continue
                r_, g_, b_ = px[j_ - 1:j_ + 2, i_ - 1:i_ + 2, :3].reshape(-1, 3).max(0)
                lit = int(r_ > .45 and r_ > b_ * 1.2)
                out_f.append([round(u, 5), round(v, 5), round(ax, 6), round(ay, 6), round(bx, 6), round(by, 6), lit])
            with open(os.path.join(WEB, "fenetres.json"), "w") as f: json.dump({"fenetres": out_f}, f, separators=(",", ":"))
            print("fenetres.json :", len(out_f), "fenêtres,", sum(o[6] for o in out_f), "allumées")
        img.save_render(os.path.join(WEB, name + "_4k.webp"), scene=scene)
        if LOOK == "day":
            import shutil; shutil.copy(os.path.join(OUT, "emplacements.json"), os.path.join(WEB, "emplacements.json"))
        print("site mis à jour :", WEB, name)
if "--save" in ARGS: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "city.blend"))
