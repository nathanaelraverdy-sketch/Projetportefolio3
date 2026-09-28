"""Matériaux Cycles de la ville (v2).
Les géométries fusionnées portent une couleur par sommet « col » (attribut de coin) :
un seul matériau sert à des centaines de bâtiments de couleurs différentes."""
import bpy, os
TEXDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")

MAT = {}
NIGHT = 0.0          # 0 = jour, 1 = nuit (fenêtres allumées, lampes, phares) — fixé par build.py


def mat_new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes, nt.links, nt.nodes["Principled BSDF"]


def mn(N, L, op, a, b=None, c=None):
    n = N.new("ShaderNodeMath"); n.operation = op
    for i, v in enumerate((a, b, c)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: L.new(v, n.inputs[i])
    return n.outputs[0]


def band(N, L, x, lo, hi):
    return mn(N, L, "MULTIPLY", mn(N, L, "GREATER_THAN", x, lo), mn(N, L, "LESS_THAN", x, hi))


def mul(N, L, *xs):
    o = xs[0]
    for x in xs[1:]: o = mn(N, L, "MULTIPLY", o, x)
    return o


def mixc(N, L, fac, a, b, blend="MIX"):
    n = N.new("ShaderNodeMix"); n.data_type = "RGBA"; n.blend_type = blend
    if isinstance(fac, (int, float)): n.inputs["Factor"].default_value = fac
    else: L.new(fac, n.inputs["Factor"])
    for s, v in ((n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, tuple): s.default_value = (*v, 1) if len(v) == 3 else v
        else: L.new(v, s)
    return n.outputs[2]


def noise(N, L, scale, detail=4, coord=None, rough=.5):
    n = N.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    if coord is not None: L.new(coord, n.inputs["Vector"])
    return n.outputs["Fac"]


def maprange(N, L, x, a, b):
    r = N.new("ShaderNodeMapRange"); L.new(x, r.inputs[0])
    r.inputs[3].default_value = a; r.inputs[4].default_value = b
    return r.outputs[0]


def colattr(N):
    a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"
    return a.outputs["Color"]


def grainy(N, L, base, scale=14, amt=(.8, 1.12)):
    return mixc(N, L, 1, base, maprange(N, L, noise(N, L, scale, 6), *amt), "MULTIPLY")


# ─────────────────────────────── pierre de taille, ardoise, cuivre patiné, or (bâtiments uniques)
def _wallcoord(N, L, sx=1., sz=1.):
    """coordonnées pour un appareil de pierre ou des rangs d'ardoise : (le long du mur, hauteur)"""
    g = N.new("ShaderNodeNewGeometry"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(g.outputs["Position"], sep.inputs[0])
    u = mn(N, L, "ADD", mn(N, L, "MULTIPLY", sep.outputs[0], .72 * sx), mn(N, L, "MULTIPLY", sep.outputs[1], .69 * sx))
    cmb = N.new("ShaderNodeCombineXYZ"); L.new(u, cmb.inputs[0]); L.new(mn(N, L, "MULTIPLY", sep.outputs[2], sz), cmb.inputs[1])
    return cmb.outputs[0]

def m_brickish(name, brick_w, row_h, mortar, c1, c2, mortar_col, rough, bump, attr=True, metal=0.):
    m, nt, N, L, P = mat_new(name)
    b = N.new("ShaderNodeTexBrick")
    L.new(_wallcoord(N, L), b.inputs["Vector"])
    b.inputs["Scale"].default_value = 1.; b.inputs["Mortar Size"].default_value = mortar
    b.inputs["Brick Width"].default_value = brick_w; b.inputs["Row Height"].default_value = row_h
    b.offset = .5; b.inputs["Bias"].default_value = 0.
    b.inputs["Color1"].default_value = (*c1, 1); b.inputs["Color2"].default_value = (*c2, 1); b.inputs["Mortar"].default_value = (*mortar_col, 1)
    col = b.outputs["Color"]
    if attr: col = mixc(N, L, 1, colattr(N), col, "MULTIPLY")
    col = grainy(N, L, col, 9, (.9, 1.08))
    L.new(col, P.inputs["Base Color"])
    bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = bump; bm.inputs["Distance"].default_value = .05
    L.new(b.outputs["Fac"], bm.inputs["Height"]); L.new(bm.outputs[0], P.inputs["Normal"])
    P.inputs["Roughness"].default_value = rough; P.inputs["Metallic"].default_value = metal
    MAT[name] = m

def m_patina():
    """cuivre vert-de-gris : taches et coulures, mat"""
    m, nt, N, L, P = mat_new("cuivre")
    g = N.new("ShaderNodeNewGeometry")
    streak = N.new("ShaderNodeMapping"); streak.inputs["Scale"].default_value = (3., 3., .4)
    L.new(g.outputs["Position"], streak.inputs[0])
    n1 = noise(N, L, 1.2, 8, streak.outputs[0], .6)
    c = mixc(N, L, maprange(N, L, n1, 0., 1.), (.05, .15, .11), (.13, .27, .21))
    c = mixc(N, L, maprange(N, L, noise(N, L, 5, 4), -.6, .5), c, (.2, .14, .08))
    L.new(c, P.inputs["Base Color"]); P.inputs["Roughness"].default_value = .62
    MAT["cuivre"] = m

# ─────────────────────────────── murs, façades, verre
def m_wall():
    m, nt, N, L, P = mat_new("wall")
    L.new(grainy(N, L, colattr(N)), P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = .85
    MAT["wall"] = m


def lit_windows(N, L, P, cellvec, mask, amount, strength):
    """fenêtres allumées la nuit : une cellule sur « amount », couleur chaude ou froide"""
    if NIGHT <= 0: return
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"; L.new(cellvec, wn.inputs["Vector"])
    lit = mul(N, L, mask, mn(N, L, "GREATER_THAN", wn.outputs["Value"], 1 - amount * NIGHT))
    w2 = N.new("ShaderNodeTexWhiteNoise"); w2.noise_dimensions = "4D"; L.new(cellvec, w2.inputs["Vector"])
    w2.inputs["W"].default_value = 3.1
    ec = mixc(N, L, w2.outputs["Value"], (1.0, .58, .26), (1.0, .86, .62))
    ec = mixc(N, L, mn(N, L, "GREATER_THAN", w2.outputs["Value"], .9), ec, (.75, .85, 1.0))
    L.new(ec, P.inputs["Emission Color"])
    L.new(mn(N, L, "MULTIPLY", lit, strength * NIGHT), P.inputs["Emission Strength"])


def m_facade():
    """petits bâtiments : fenêtres peintes (u = travées, v = étages)"""
    m, nt, N, L, P = mat_new("facade")
    uv = N.new("ShaderNodeUVMap").outputs[0]
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(uv, sep.inputs[0])
    u, v = sep.outputs[0], sep.outputs[1]
    fu, fv = mn(N, L, "FRACT", u), mn(N, L, "FRACT", v)
    above = mn(N, L, "GREATER_THAN", v, 1.0)
    win = mul(N, L, band(N, L, fu, .26, .74), band(N, L, fv, .3, .78), above)
    shop = mul(N, L, band(N, L, fu, .06, .94), band(N, L, fv, .08, .72), mn(N, L, "LESS_THAN", v, 1.0))
    glass = mn(N, L, "MAXIMUM", win, shop)
    cell = N.new("ShaderNodeVectorMath"); cell.operation = "FLOOR"; L.new(uv, cell.inputs[0])
    wn = N.new("ShaderNodeTexWhiteNoise"); L.new(cell.outputs[0], wn.inputs["Vector"])
    wall = grainy(N, L, colattr(N))
    ledge = mul(N, L, mn(N, L, "LESS_THAN", fv, .08), above)
    wall = mixc(N, L, mn(N, L, "MULTIPLY", ledge, .3), wall, (.42, .4, .36))
    gcol = mixc(N, L, mn(N, L, "MULTIPLY", wn.outputs["Value"], .6), (.02, .03, .04), (.09, .11, .13))
    L.new(mixc(N, L, glass, wall, gcol), P.inputs["Base Color"])
    L.new(mn(N, L, "MULTIPLY_ADD", glass, -.84, .88), P.inputs["Roughness"])
    L.new(mn(N, L, "MULTIPLY", glass, .65), P.inputs["Metallic"])                      # reflet dans les vitres
    try: L.new(mn(N, L, "MULTIPLY", glass, .7), P.inputs["Coat Weight"]); P.inputs["Coat Roughness"].default_value = .03
    except Exception: pass
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = .9; b.inputs["Distance"].default_value = .2
    L.new(mn(N, L, "SUBTRACT", 1.0, glass), b.inputs["Height"]); L.new(b.outputs[0], P.inputs["Normal"])
    lit_windows(N, L, P, cell.outputs[0], glass, .3, 2.4)
    MAT["facade"] = m


def m_glass():
    """le verre au fond des fenêtres en creux (u = travée, v = étage) : reflets variés, allumé la nuit"""
    m, nt, N, L, P = mat_new("glass")
    uv = N.new("ShaderNodeUVMap").outputs[0]
    cell = N.new("ShaderNodeVectorMath"); cell.operation = "FLOOR"; L.new(uv, cell.inputs[0])
    wn = N.new("ShaderNodeTexWhiteNoise"); L.new(cell.outputs[0], wn.inputs["Vector"])
    tint = colattr(N)
    base = mixc(N, L, mn(N, L, "MULTIPLY", wn.outputs["Value"], .5), tint, (.16, .23, .31))
    L.new(base, P.inputs["Base Color"])
    L.new(maprange(N, L, wn.outputs["Value"], .01, .07), P.inputs["Roughness"])     # vitrages lisses : ils reflètent le ciel et les voisins
    P.inputs["Metallic"].default_value = .75
    P.inputs["Specular IOR Level"].default_value = 1.
    try:
        P.inputs["Coat Weight"].default_value = .4; P.inputs["Coat Roughness"].default_value = .02
    except Exception: pass
    one = N.new("ShaderNodeValue"); one.outputs[0].default_value = 1
    lit_windows(N, L, P, cell.outputs[0], one.outputs[0], .34, 2.0)
    MAT["glass"] = m


def m_simple(name, color, rough=.8, metal=0., ns=None, amt=.2, bump=0., spec=.5, attr=False):
    m, nt, N, L, P = mat_new(name)
    base = colattr(N) if attr else None
    if ns:
        c = mixc(N, L, 1, base if attr else (*color, 1), maprange(N, L, noise(N, L, ns, 8), 1 - amt, 1 + amt), "MULTIPLY")
        L.new(c, P.inputs["Base Color"])
        if bump:
            b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump
            L.new(noise(N, L, ns * 3, 8), b.inputs["Height"]); L.new(b.outputs[0], P.inputs["Normal"])
    elif attr: L.new(base, P.inputs["Base Color"])
    else: P.inputs["Base Color"].default_value = (*color, 1)
    P.inputs["Roughness"].default_value = rough; P.inputs["Metallic"].default_value = metal
    P.inputs["Specular IOR Level"].default_value = spec
    MAT[name] = m
    return m, N, L, P


def m_emit(name, color, strength, base=(.8, .8, .75)):
    m, N, L, P = m_simple(name, base, .4)[0:4]
    P.inputs["Emission Color"].default_value = (*color, 1)
    P.inputs["Emission Strength"].default_value = strength
    return m


def m_decal(name, color, strength, kind):
    """halo de lumière posé au sol (lampadaire : disque ; phare : faisceau), purement additif"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    uv = N.new("ShaderNodeUVMap").outputs[0]
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(uv, sep.inputs[0])
    if kind == "pool":
        dx = mn(N, L, "SUBTRACT", sep.outputs[0], .5); dy = mn(N, L, "SUBTRACT", sep.outputs[1], .5)
        r = mn(N, L, "MULTIPLY", mn(N, L, "SQRT", mn(N, L, "ADD", mn(N, L, "MULTIPLY", dx, dx), mn(N, L, "MULTIPLY", dy, dy))), 2)
        fac = mn(N, L, "POWER", mn(N, L, "MAXIMUM", mn(N, L, "SUBTRACT", 1.0, r), 0.0), 2.2)
    else:   # faisceau : u = distance au phare (0 → 1), v = travers (0 → 1)
        along = mn(N, L, "POWER", mn(N, L, "SUBTRACT", 1.0, sep.outputs[0]), 1.6)
        across = mn(N, L, "POWER", mn(N, L, "MAXIMUM", mn(N, L, "SUBTRACT", 1.0, mn(N, L, "ABSOLUTE", mn(N, L, "MULTIPLY_ADD", sep.outputs[1], 2, -1))), 0.0), 1.3)
        fac = mul(N, L, along, across, mn(N, L, "MINIMUM", mn(N, L, "MULTIPLY", sep.outputs[0], 12), 1.0))
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    L.new(mn(N, L, "MULTIPLY", fac, strength), em.inputs["Strength"])
    tr = N.new("ShaderNodeBsdfTransparent")
    add = N.new("ShaderNodeAddShader"); L.new(tr.outputs[0], add.inputs[0]); L.new(em.outputs[0], add.inputs[1])
    L.new(add.outputs[0], out.inputs["Surface"])
    MAT[name] = m


def m_objcolor(name, rough=.5, coat=0., var=None, metal=0.):
    m, nt, N, L, P = mat_new(name)
    oi = N.new("ShaderNodeObjectInfo")
    if var:
        ramp = N.new("ShaderNodeValToRGB"); L.new(oi.outputs["Random"], ramp.inputs[0])
        ramp.color_ramp.elements[0].color = (*var[0], 1); ramp.color_ramp.elements[1].color = (*var[1], 1)
        L.new(mixc(N, L, 1, ramp.outputs[0], maprange(N, L, noise(N, L, 1.1, 3), .55, 1.3), "MULTIPLY"), P.inputs["Base Color"])
        b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = .6
        L.new(noise(N, L, 3, 6), b.inputs["Height"]); L.new(b.outputs[0], P.inputs["Normal"])
    else: L.new(oi.outputs["Color"], P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = rough; P.inputs["Coat Weight"].default_value = coat
    P.inputs["Metallic"].default_value = metal
    MAT[name] = m


def m_foliage(name, c0, c1, core=False):
    """feuillage : des feuilles découpées (cellules de Voronoï) sur les cartes, translucides, teinte variable par arbre"""
    m, nt, N, L, P = mat_new(name)
    oi = N.new("ShaderNodeObjectInfo")
    ramp = N.new("ShaderNodeValToRGB"); L.new(oi.outputs["Random"], ramp.inputs[0])
    ramp.color_ramp.elements[0].color = (*c0, 1); ramp.color_ramp.elements[1].color = (*c1, 1)
    tc = N.new("ShaderNodeTexCoord")
    base = mixc(N, L, 1, ramp.outputs[0], maprange(N, L, noise(N, L, 2.5, 4, tc.outputs["Object"]), .55, 1.35), "MULTIPLY")
    if core:   # le cœur du houppier, dans l'ombre
        base = mixc(N, L, 1, base, (.55, .6, .5), "MULTIPLY")
        L.new(base, P.inputs["Base Color"]); P.inputs["Roughness"].default_value = .9
        b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 1
        L.new(noise(N, L, 6, 6, tc.outputs["Object"]), b.inputs["Height"]); L.new(b.outputs[0], P.inputs["Normal"])
        MAT[name] = m; return
    uv = N.new("ShaderNodeUVMap").outputs[0]
    vor = N.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 3.2
    L.new(uv, vor.inputs["Vector"])
    # une feuille par cellule : pointue vers le bord (distance), disque central coupé en deux par la nervure
    leaf = mn(N, L, "LESS_THAN", vor.outputs["Distance"], .36)
    ctr = N.new("ShaderNodeVectorMath"); ctr.operation = "DISTANCE"; L.new(uv, ctr.inputs[0]); ctr.inputs[1].default_value = (.5, .5, 0)
    round_ = mn(N, L, "LESS_THAN", ctr.outputs["Value"], .5)
    alpha = mul(N, L, leaf, round_)
    per = mixc(N, L, mn(N, L, "MULTIPLY", vor.outputs["Color"] if False else vor.outputs["Distance"], .8), base, (.2, .3, .08), "MIX")
    L.new(mixc(N, L, .25, base, per), P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = .55; P.inputs["Specular IOR Level"].default_value = .35
    P.inputs["Subsurface Weight"].default_value = 0
    # un peu de lumière qui traverse les feuilles
    tr = N.new("ShaderNodeBsdfTranslucent"); L.new(base, tr.inputs["Color"])
    mix = N.new("ShaderNodeMixShader"); mix.inputs[0].default_value = .22
    out = nt.nodes["Material Output"]
    L.new(P.outputs[0], mix.inputs[1]); L.new(tr.outputs[0], mix.inputs[2])
    tp = N.new("ShaderNodeBsdfTransparent"); cut = N.new("ShaderNodeMixShader")
    L.new(alpha, cut.inputs[0]); L.new(tp.outputs[0], cut.inputs[1]); L.new(mix.outputs[0], cut.inputs[2])
    L.new(cut.outputs[0], out.inputs["Surface"])
    MAT[name] = m


def m_water():
    m, nt, N, L, P = mat_new("water")
    P.inputs["Base Color"].default_value = (.012, .07, .10, 1)
    P.inputs["Roughness"].default_value = .05; P.inputs["Specular IOR Level"].default_value = .9
    tc = N.new("ShaderNodeTexCoord").outputs["Object"]
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 3, 1); L.new(tc, mp.inputs[0])
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = .22
    L.new(noise(N, L, .7, 8, mp.outputs[0]), b.inputs["Height"]); L.new(b.outputs[0], P.inputs["Normal"])
    MAT["water"] = m


# ─────────────────────────────── vraies textures photo (herbe, roche), sans répétition visible
# La photo n'apporte que son grain (et un peu de relief) : la teinte reste celle choisie (couleur de base / couleur par sommet).
# Anti-répétition (méthode d'I. Quilez, comme sur Projet Carte) : la texture est décalée par grandes zones irrégulières
# (un bruit découpé en paliers), et deux décalages voisins se fondent en douceur : on ne voit plus la grille des carreaux.
PHOTOS = {  # nom : (fichier, taille d'un carreau en mètres, teinte moyenne de la photo, occlusion moyenne)
    "herbe": ("forrest_ground_01", 9.0, (.2918, .2482, .1198), .477),
    "roche": ("rocks_ground_04", 6.0, (.2501, .2176, .1752), .756),
}

def _img(N, fname, colorspace="sRGB", box=False):
    img = bpy.data.images.load(os.path.join(TEXDIR, fname), check_existing=True)
    img.colorspace_settings.name = colorspace
    t = N.new("ShaderNodeTexImage"); t.image = img; t.interpolation = "Linear"
    if box: t.projection = "BOX"; t.projection_blend = .35
    return t

def photo(N, L, key, mc=.1, box=False, ao=.55, contraste=1.):
    """facteur de détail (couleur, autour de 1) + hauteur pour le relief, d'après la photo « key »"""
    fname, size, mean, mao = PHOTOS[key]
    if box:   # rochers et pentes : projection sur trois axes (chaque rocher a son morceau de photo)
        g = N.new("ShaderNodeNewGeometry"); P = g.outputs["Position"]          # (position dans le monde : la même échelle sur tous les rochers)
        oi = N.new("ShaderNodeObjectInfo"); dv = N.new("ShaderNodeVectorMath"); dv.operation = "MULTIPLY_ADD"   # chaque rocher prend un autre morceau de la photo
        L.new(oi.outputs["Random"], dv.inputs[0]); dv.inputs[1].default_value = (371., 913., 537.); L.new(P, dv.inputs[2]); P = dv.outputs[0]
    else:     # sol : position dans le monde, vue du dessus
        g = N.new("ShaderNodeNewGeometry"); P = g.outputs["Position"]
    q = N.new("ShaderNodeVectorMath"); q.operation = "SCALE"; L.new(P, q.inputs[0]); q.inputs["Scale"].default_value = 1 / size
    # Anti-répétition : la photo est « semée » par cellules (Voronoï, environ une cellule par carreau).
    # Chaque cellule prend un morceau et une orientation au hasard ; trois semis décalés se relaient près des bords
    # des cellules (là où l'un change de morceau, les autres sont au milieu d'une cellule) : ni grille, ni couture.
    cols, arms, poids = [], [], []
    for sh in ((0., 0., 0.), (.37, .61, .13), (.71, .23, .53)):
        qs = N.new("ShaderNodeVectorMath"); qs.operation = "ADD"; L.new(q.outputs[0], qs.inputs[0]); qs.inputs[1].default_value = sh
        vc = N.new("ShaderNodeTexVoronoi"); vc.voronoi_dimensions = "3D"; vc.feature = "F1"; vc.inputs["Scale"].default_value = .8
        L.new(qs.outputs[0], vc.inputs["Vector"])
        ve = N.new("ShaderNodeTexVoronoi"); ve.voronoi_dimensions = "3D"; ve.feature = "DISTANCE_TO_EDGE"; ve.inputs["Scale"].default_value = .8
        L.new(qs.outputs[0], ve.inputs["Vector"])
        rv = N.new("ShaderNodeSeparateColor"); L.new(vc.outputs["Color"], rv.inputs[0])
        rot = N.new("ShaderNodeVectorRotate"); rot.rotation_type = "Z_AXIS"; L.new(q.outputs[0], rot.inputs["Vector"])
        L.new(mn(N, L, "MULTIPLY", rv.outputs[0], 6.2832), rot.inputs["Angle"])
        off = N.new("ShaderNodeVectorMath"); off.operation = "MULTIPLY_ADD"; L.new(vc.outputs["Color"], off.inputs[0])
        off.inputs[1].default_value = (53., 97., 71.); L.new(rot.outputs[0], off.inputs[2])
        tc, ta = _img(N, fname + "_diff_1k.jpg", box=box), _img(N, fname + "_arm_1k.jpg", "Non-Color", box)
        L.new(off.outputs[0], tc.inputs["Vector"]); L.new(off.outputs[0], ta.inputs["Vector"])
        w = N.new("ShaderNodeMapRange"); w.interpolation_type = "SMOOTHSTEP"; L.new(ve.outputs["Distance"], w.inputs[0])
        w.inputs[1].default_value = 0.; w.inputs[2].default_value = .18
        cols.append(tc.outputs["Color"]); arms.append(ta.outputs["Color"]); poids.append(mn(N, L, "ADD", w.outputs[0], .001))
    tot = mn(N, L, "ADD", mn(N, L, "ADD", poids[0], poids[1]), poids[2])
    def moyenne(xs):
        acc = None
        for x, pw in zip(xs, poids):
            t = N.new("ShaderNodeVectorMath"); t.operation = "SCALE"; L.new(x, t.inputs[0]); L.new(mn(N, L, "DIVIDE", pw, tot), t.inputs["Scale"])
            if acc is None: acc = t.outputs[0]
            else: s_ = N.new("ShaderNodeVectorMath"); s_.operation = "ADD"; L.new(acc, s_.inputs[0]); L.new(t.outputs[0], s_.inputs[1]); acc = s_.outputs[0]
        return acc
    col, arm = moyenne(cols), moyenne(arms)
    # d = photo / teinte moyenne → autour de 1 ; on garde surtout sa luminosité (mc = part de sa couleur propre)
    d = N.new("ShaderNodeVectorMath"); d.operation = "DIVIDE"; L.new(col, d.inputs[0]); d.inputs[1].default_value = mean
    bw = N.new("ShaderNodeRGBToBW"); L.new(d.outputs[0], bw.inputs[0])
    det = mixc(N, L, mc, bw.outputs[0], d.outputs[0])
    if contraste != 1:   # vue de haut, le grain de la photo doit rester lisible : on accentue ses écarts autour de 1
        k_ = contraste; ma = N.new("ShaderNodeVectorMath"); ma.operation = "MULTIPLY_ADD"                # 1 + (det − 1) × k
        L.new(det, ma.inputs[0]); ma.inputs[1].default_value = (k_, k_, k_); ma.inputs[2].default_value = (1 - k_, 1 - k_, 1 - k_)
        det = ma.outputs[0]                                                  # (en vecteur : une couleur ne peut pas être négative)
    sep = N.new("ShaderNodeSeparateColor"); L.new(arm, sep.inputs[0])
    nrm = 1 - ao + ao * mao                                                 # (divisée par sa moyenne : la teinte d'ensemble ne change pas)
    occ = maprange(N, L, sep.outputs[0], (1 - ao) / nrm, 1. / nrm)          # l'occlusion de la photo (creux plus sombres)
    det = mixc(N, L, 1, det, occ, "MULTIPLY")
    h = N.new("ShaderNodeRGBToBW"); L.new(col, h.inputs[0])
    return det, h.outputs[0]

def relief(N, L, P, height, strength, dist=.03, avant=None):
    """le relief de la photo, par-dessus le relief d'avant (avant = (échelle du bruit, force)) : la lumière reste la même qu'avant"""
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = strength; b.inputs["Distance"].default_value = dist
    L.new(height, b.inputs["Height"]); out = b.outputs[0]
    if avant:
        b2 = N.new("ShaderNodeBump"); b2.inputs["Strength"].default_value = avant[1]
        L.new(noise(N, L, avant[0], 8), b2.inputs["Height"]); L.new(out, b2.inputs["Normal"]); out = b2.outputs[0]
    L.new(out, P.inputs["Normal"])
    return b


def m_grass():
    """pelouses, parcs, jardins : même vert qu'avant, grain d'une vraie photo d'herbe"""
    m, nt, N, L, P = mat_new("grass")
    c = mixc(N, L, 1, (.06, .15, .035, 1), maprange(N, L, noise(N, L, .2, 8), .55, 1.45), "MULTIPLY")   # les grandes nuances d'avant
    det, h = photo(N, L, "herbe", mc=.15, ao=.4, contraste=1.8)
    L.new(mixc(N, L, 1, c, det, "MULTIPLY"), P.inputs["Base Color"])
    relief(N, L, P, h, .25, avant=(.6, .2))
    P.inputs["Roughness"].default_value = .95; P.inputs["Specular IOR Level"].default_value = .5
    MAT["grass"] = m


def m_rock():
    """rochers : même gris qu'avant, texture photo de roche projetée sur trois axes (elle ne s'étire jamais)"""
    m, nt, N, L, P = mat_new("rock")
    c = mixc(N, L, 1, (.11, .105, .095, 1), maprange(N, L, noise(N, L, .9, 8), .65, 1.35), "MULTIPLY")
    det, h = photo(N, L, "roche", mc=.6, box=True)
    L.new(mixc(N, L, 1, c, det, "MULTIPLY"), P.inputs["Base Color"])
    relief(N, L, P, h, .5, .08, avant=(2.7, .8))
    P.inputs["Roughness"].default_value = .85
    MAT["rock"] = m


def m_terrain():
    """le sol hors des quartiers : herbe / terre / roche selon la couleur par sommet, plus des variations"""
    m, nt, N, L, P = mat_new("terrain")
    c = mixc(N, L, 1, colattr(N), maprange(N, L, noise(N, L, .08, 6), .7, 1.25), "MULTIPLY")
    c = mixc(N, L, 1, c, maprange(N, L, noise(N, L, 1.5, 8), .82, 1.12), "MULTIPLY")
    # le grain des vraies photos : herbe partout, roche sur les pentes, rien sur le sable (attribut « sol » : R = roche, G = sable)
    sol = N.new("ShaderNodeAttribute"); sol.attribute_name = "sol"
    sp = N.new("ShaderNodeSeparateColor"); L.new(sol.outputs["Color"], sp.inputs[0])
    dg, hg = photo(N, L, "herbe", mc=.15, ao=.4, contraste=1.8, box=True); dr, hr = photo(N, L, "roche", mc=.4, box=True)   # (projetées sur trois axes : rien ne s'étire sur les pentes)
    det = mixc(N, L, sp.outputs[0], dg, dr)
    det = mixc(N, L, sp.outputs[1], det, (1., 1., 1., 1))
    L.new(mixc(N, L, 1, c, det, "MULTIPLY"), P.inputs["Base Color"]); P.inputs["Roughness"].default_value = .95
    h = mn(N, L, "MULTIPLY", mn(N, L, "ADD", mul(N, L, hg, mn(N, L, "SUBTRACT", 1., sp.outputs[0])), mul(N, L, hr, sp.outputs[0])), mn(N, L, "SUBTRACT", 1., sp.outputs[1]))
    relief(N, L, P, h, .3, .05, avant=(2.5, .35))
    MAT["terrain"] = m


def m_solar():
    m, nt, N, L, P = mat_new("solar")
    uv = N.new("ShaderNodeUVMap").outputs[0]
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(uv, sep.inputs[0])
    lines = mn(N, L, "MAXIMUM", mn(N, L, "LESS_THAN", mn(N, L, "FRACT", mn(N, L, "MULTIPLY", sep.outputs[0], 6)), .06),
               mn(N, L, "LESS_THAN", mn(N, L, "FRACT", mn(N, L, "MULTIPLY", sep.outputs[1], 10)), .06))
    L.new(mixc(N, L, lines, (.02, .04, .1), (.6, .62, .65)), P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = .15; P.inputs["Specular IOR Level"].default_value = .8
    MAT["solar"] = m


def m_pitch():
    m, nt, N, L, P = mat_new("pitch")
    uv = N.new("ShaderNodeUVMap").outputs[0]
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(uv, sep.inputs[0])
    stripe = mn(N, L, "LESS_THAN", mn(N, L, "FRACT", mn(N, L, "MULTIPLY", sep.outputs[0], 7)), .5)
    L.new(mixc(N, L, stripe, (.06, .2, .04), (.09, .26, .05)), P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = .9
    MAT["pitch"] = m


def build_all(night):
    global NIGHT
    NIGHT = night
    m_wall(); m_facade(); m_glass(); m_water(); m_terrain(); m_solar(); m_pitch()
    m_simple("roof", (0, 0, 0), .9, ns=.35, amt=.3, attr=True)
    m_brickish("pierre", 1.1, .42, .012, (1., 1., 1.), (.9, .88, .84), (.72, .7, .66), .85, .35)            # pierre de taille (teinte = col)
    m_brickish("ardoise", .42, .22, .015, (.17, .19, .22), (.13, .14, .17), (.08, .09, .1), .55, .5, attr=False)
    m_patina()
    m_simple("or", (.85, .62, .2), .28, metal=1.)
    m_simple("painted", (0, 0, 0), .45, attr=True)
    m_simple("metalattr", (0, 0, 0), .35, metal=.7, attr=True)
    m_simple("asphalt", (.05, .05, .055), .85, ns=1.2, amt=.35, bump=.04)
    m_simple("sidewalk", (.36, .35, .33), .9, ns=2, amt=.14)
    m_simple("plaza", (.46, .43, .39), .85, ns=1.5, amt=.15)
    m_grass()
    m_simple("path", (.47, .42, .34), .95, ns=3, amt=.15)
    m_simple("dirt", (.30, .21, .13), .95, ns=.6, amt=.35, bump=.3)
    m_simple("sand", (.62, .53, .38), .95, ns=.8, amt=.12, bump=.1)
    m_rock()
    m_simple("concrete", (.42, .41, .39), .9, ns=1.2, amt=.18)
    m_simple("paint_w", (.8, .8, .78), .7)
    m_simple("paint_y", (.78, .58, .08), .7)
    m_simple("metal", (.34, .35, .37), .4, metal=.8)
    m_simple("dark", (.04, .04, .045), .6)
    m_simple("white", (.8, .79, .76), .55, ns=4, amt=.05)
    m_simple("trunk", (.11, .075, .045), .9)
    m_simple("wood", (.25, .14, .07), .85, ns=12, amt=.25)
    m_simple("carglass", (.015, .02, .025), .05, spec=1)
    m_simple("pool", (.05, .35, .45), .05, spec=.9)
    m_objcolor("paint", rough=.25, coat=.8)
    m_objcolor("leaves", rough=.8, var=((.045, .13, .03), (.15, .25, .06)))
    m_objcolor("conifer", rough=.8, var=((.02, .08, .03), (.05, .13, .05)))
    m_foliage("foliage", (.05, .14, .03), (.2, .3, .06))
    m_foliage("foliage_core", (.03, .09, .02), (.1, .17, .04), core=True)
    m_foliage("foliage_c", (.02, .07, .03), (.06, .14, .05))
    m_foliage("foliage_core_c", (.015, .05, .02), (.04, .09, .035), core=True)
    m_objcolor("fabric", rough=.9)
    # lumières (éteintes le jour)
    m_emit("lamphead", (1, .78, .45), 40 * NIGHT, base=(.9, .88, .8))
    m_emit("headlight", (1, .95, .82), 60 * NIGHT, base=(.9, .9, .85))
    m_emit("taillight", (1, .05, .02), 25 * NIGHT, base=(.5, .02, .02))
    m_emit("sign", (1, .75, .3), 12 * NIGHT + .0, base=(.85, .7, .35))
    m_emit("signred", (1, .1, .08), 14 * NIGHT, base=(.6, .05, .04))
    m_emit("feu_r", (1, .08, .05), 6 + 20 * NIGHT, base=(.8, .05, .03))       # feux de circulation
    m_emit("feu_v", (.1, 1, .35), 6 + 20 * NIGHT, base=(.05, .6, .2))
    m_emit("flood", (1, .97, .9), 80 * NIGHT, base=(.85, .85, .85))
    m_decal("lightpool", (1, .7, .4), 2.4 * NIGHT, "pool")
    m_decal("beam", (1, .92, .75), 3.2 * NIGHT, "beam")
    m_decal("floodpool", (1, .97, .9), 1.6 * NIGHT, "pool")


def m_foliage_img(name, img_path, var):
    """feuillage en cartes : la texture donne la forme des feuilles (transparence) ; chaque arbre a sa teinte"""
    m, nt, N, L, P = mat_new(name)
    img = bpy.data.images.load(img_path, check_existing=True); img.alpha_mode = "STRAIGHT"
    tex = N.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Linear"
    L.new(N.new("ShaderNodeUVMap").outputs[0], tex.inputs["Vector"])
    oi = N.new("ShaderNodeObjectInfo")
    ramp = N.new("ShaderNodeValToRGB"); L.new(oi.outputs["Random"], ramp.inputs[0])
    ramp.color_ramp.elements[0].color = (*var[0], 1); ramp.color_ramp.elements[1].color = (*var[1], 1)
    col = mixc(N, L, 1, tex.outputs["Color"], ramp.outputs[0], "MULTIPLY")
    col = mixc(N, L, 1, col, (2.2, 2.2, 2.2), "MULTIPLY")
    L.new(col, P.inputs["Base Color"]); P.inputs["Roughness"].default_value = .7
    P.inputs["Specular IOR Level"].default_value = .35
    tr = N.new("ShaderNodeBsdfTranslucent"); L.new(col, tr.inputs["Color"])
    mix1 = N.new("ShaderNodeMixShader"); mix1.inputs[0].default_value = .25
    out = N["Material Output"]
    L.new(P.outputs[0], mix1.inputs[1]); L.new(tr.outputs[0], mix1.inputs[2])
    tp = N.new("ShaderNodeBsdfTransparent")
    mix2 = N.new("ShaderNodeMixShader"); L.new(tex.outputs["Alpha"], mix2.inputs[0])
    L.new(tp.outputs[0], mix2.inputs[1]); L.new(mix1.outputs[0], mix2.inputs[2])
    L.new(mix2.outputs[0], out.inputs["Surface"])
    MAT[name] = m
