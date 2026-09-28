"""Kit de route : un réseau (nœuds + tronçons) qui connaît tous ses carrefours, et des pièces standard
pour le dessiner au sol.

  • tronçon : chaussée + bordure en béton + trottoir surélevé DES DEUX CÔTÉS (+ marquages)
  • carrefour : la chaussée se prolonge, les trottoirs tournent le coin en arc (raccord tangent),
    passages piétons sur chaque branche
  • impasse : raquette ronde, trottoir tout autour
  • porte : le bout d'une rue de quartier en grille (le quartier dessine lui-même son carrefour)
  • rampe : l'arrivée au sol d'une bretelle d'autoroute (le viaduc est un autre kit)

Règles tenues par le réseau : pas deux routes qui se superposent, un croisement crée un vrai nœud,
toute rue finit sur un carrefour, une porte ou une raquette."""
import math

Z_ROAD, Z_JUNC, Z_WALK = .03, .031, .16


# ═══════════════════════════════════════ polylignes
def cum(pts):
    out = [0.]
    for i in range(len(pts) - 1): out.append(out[-1] + math.dist(pts[i], pts[i + 1]))
    return out

def length(pts): return cum(pts)[-1]

def at(pts, s, C=None):
    """point, tangente (unitaire) et indice de segment à l'abscisse s"""
    C = C or cum(pts)
    s = max(0., min(C[-1], s))
    for i in range(len(pts) - 1):
        if C[i + 1] >= s or i == len(pts) - 2:
            l = C[i + 1] - C[i] or 1e-9; t = (s - C[i]) / l
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), ((x1 - x0) / l, (y1 - y0) / l), i
    return pts[-1], (1., 0.), len(pts) - 2

def cut(pts, s0, s1):
    """la portion de polyligne entre les abscisses s0 et s1"""
    C = cum(pts)
    if s1 - s0 < .05: return []
    p0, _, i0 = at(pts, s0, C); p1, _, i1 = at(pts, s1, C)
    mid = [pts[k] for k in range(i0 + 1, i1 + 1) if s0 + .05 < C[k] < s1 - .05]
    return [p0] + mid + [p1]

def resample(pts, step):
    L = length(pts); n = max(1, int(round(L / step))); C = cum(pts)
    return [at(pts, L * k / n, C)[0] for k in range(n + 1)]

def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]; l2 = ax * ax + ay * ay or 1e-9
    t = max(0., min(1., ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / l2))
    q = (a[0] + ax * t, a[1] + ay * t)
    return math.dist(p, q), t, q

def seg_x(p, p2, q, q2):
    r = (p2[0] - p[0], p2[1] - p[1]); s = (q2[0] - q[0], q2[1] - q[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9: return None
    t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den; u = ((q[0] - p[0]) * r[1] - (q[1] - p[1]) * r[0]) / den
    if 0 <= t <= 1 and 0 <= u <= 1: return t, u
    return None

def normals(pts, closed=False):
    """normale (à gauche) de chaque sommet, avec correction d'onglet : la largeur reste juste dans les virages"""
    n = len(pts); out = []
    for i in range(n):
        if closed: a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        else: a, b, c = pts[max(i - 1, 0)], pts[i], pts[min(i + 1, n - 1)]
        def nn(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]; l = math.hypot(dx, dy)
            return (-dy / l, dx / l) if l > 1e-6 else None
        n0, n1 = nn(a, b), nn(b, c)
        n0 = n0 or n1; n1 = n1 or n0
        mx, my = n0[0] + n1[0], n0[1] + n1[1]; ml = math.hypot(mx, my) or 1
        mx, my = mx / ml, my / ml
        k = 1 / max(.6, mx * n0[0] + my * n0[1])
        out.append((mx * k, my * k))
    return out


# ═══════════════════════════════════════ le réseau
class Net:
    CELLH = 24.

    def __init__(s):
        s.N = []          # nœuds : {"p", "e": [ids], "kind": std|end|gate|ramp}
        s.E = {}          # tronçons : {"a", "b", "pts", "w", "walk", "cls"}
        s.H = {}          # grille de hachage : cellule → ids de tronçons
        s.nid = 0

    # ─── hachage spatial
    def _cells(s, pts, pad=0.):
        out = set()
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            n = int(math.dist(pts[i], pts[i + 1]) / (s.CELLH / 2)) + 1
            for k in range(n + 1):
                x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
                out.add((int(math.floor(x / s.CELLH)), int(math.floor(y / s.CELLH))))
        return out
    def _hadd(s, eid):
        for c in s._cells(s.E[eid]["pts"]): s.H.setdefault(c, set()).add(eid)
    def _hdel(s, eid):
        for c in s._cells(s.E[eid]["pts"]): s.H.get(c, set()).discard(eid)
    def near(s, p, r):
        out = set(); k = int(r / s.CELLH) + 1
        cx, cy = int(math.floor(p[0] / s.CELLH)), int(math.floor(p[1] / s.CELLH))
        for a in range(-k, k + 1):
            for b in range(-k, k + 1): out |= s.H.get((cx + a, cy + b), set())
        return out

    # ─── construction
    def node(s, p, kind="std"):
        s.N.append({"p": (float(p[0]), float(p[1])), "e": [], "kind": kind}); return len(s.N) - 1
    def edge(s, a, b, pts, w, walk, cls="rue"):
        pts = [s.N[a]["p"]] + [tuple(p) for p in pts[1:-1]] + [s.N[b]["p"]]
        clean = [pts[0]]
        for p in pts[1:]:
            if math.dist(p, clean[-1]) > .4: clean.append(p)
        if len(clean) < 2: clean.append(pts[-1])
        clean[-1] = pts[-1]
        eid = s.nid; s.nid += 1
        s.E[eid] = {"a": a, "b": b, "pts": clean, "w": w, "walk": walk, "cls": cls}
        s.N[a]["e"].append(eid); s.N[b]["e"].append(eid); s._hadd(eid)
        return eid
    def split(s, eid, sarc, kind="std"):
        """coupe le tronçon à l'abscisse sarc → un nouveau nœud (ou le nœud d'extrémité s'il est tout près)"""
        e = s.E[eid]; pts = e["pts"]; L = length(pts)
        if sarc < 1.: return e["a"]
        if sarc > L - 1.: return e["b"]
        q, _, i = at(pts, sarc)
        n = s.node(q, kind)
        s._hdel(eid); del s.E[eid]
        s.N[e["a"]]["e"].remove(eid); s.N[e["b"]]["e"].remove(eid)
        s.edge(e["a"], n, pts[:i + 1] + [q], e["w"], e["walk"], e["cls"])
        s.edge(n, e["b"], [q] + pts[i + 1:], e["w"], e["walk"], e["cls"])
        return n

    # ─── requêtes
    def closest(s, p, r, skip=()):
        """(distance, tronçon, abscisse, point) du tronçon le plus proche dans un rayon r"""
        best = None
        for eid in s.near(p, r):
            if eid in skip: continue
            pts = s.E[eid]["pts"]; acc = 0.
            for i in range(len(pts) - 1):
                d, t, q = seg_dist(p, pts[i], pts[i + 1]); l = math.dist(pts[i], pts[i + 1])
                if d < r and (best is None or d < best[0]): best = (d, eid, acc + t * l, q)
                acc += l
        return best
    def clearance(s, p, skip=()):
        """écart libre entre le point p et le bord extérieur (trottoir compris) des routes voisines"""
        best = 1e9
        for eid in s.near(p, 60):
            if eid in skip: continue
            e = s.E[eid]; pts = e["pts"]; H = e["w"] / 2 + e["walk"]
            for i in range(len(pts) - 1):
                d = seg_dist(p, pts[i], pts[i + 1])[0] - H
                if d < best: best = d
        return best
    def ray(s, p, d, L, skip=()):
        """premier tronçon touché par le segment p → p + d·L : (distance, tronçon, abscisse, point, tangente)"""
        q = (p[0] + d[0] * L, p[1] + d[1] * L); best = None
        for eid in s.near(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), L / 2 + 30):
            if eid in skip: continue
            pts = s.E[eid]["pts"]; acc = 0.
            for i in range(len(pts) - 1):
                l = math.dist(pts[i], pts[i + 1]); h = seg_x(p, q, pts[i], pts[i + 1])
                if h and (best is None or h[0] * L < best[0]):
                    tx, ty = (pts[i + 1][0] - pts[i][0]) / (l or 1), (pts[i + 1][1] - pts[i][1]) / (l or 1)
                    best = (h[0] * L, eid, acc + h[1] * l, (p[0] + d[0] * h[0] * L, p[1] + d[1] * h[0] * L), (tx, ty))
                acc += l
        return best
    def crossings(s, pts, skip=()):
        """toutes les intersections d'une polyligne avec le réseau : (abscisse sur pts, tronçon, abscisse sur le tronçon, point, angle)"""
        out = []; C = cum(pts)
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            for eid in s.near(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), math.dist(p, q) / 2 + 30):
                if eid in skip: continue
                ep = s.E[eid]["pts"]; acc = 0.
                for j in range(len(ep) - 1):
                    l = math.dist(ep[j], ep[j + 1]); h = seg_x(p, q, ep[j], ep[j + 1])
                    if h:
                        a1 = math.atan2(q[1] - p[1], q[0] - p[0]); a2 = math.atan2(ep[j + 1][1] - ep[j][1], ep[j + 1][0] - ep[j][0])
                        ang = abs((a1 - a2 + math.pi / 2) % math.pi - math.pi / 2)     # angle aigu entre les deux routes
                        out.append((C[i] + h[0] * math.dist(p, q), eid, acc + h[1] * l,
                                    (p[0] + (q[0] - p[0]) * h[0], p[1] + (q[1] - p[1]) * h[0]), ang))
                    acc += l
        out.sort(key=lambda c: c[0])
        return out
    def junction_dist(s, eid, sarc):
        """distance (le long du tronçon) jusqu'au plus proche carrefour de ses extrémités"""
        e = s.E[eid]; L = length(e["pts"])
        da = sarc if len(s.N[e["a"]]["e"]) > 1 or s.N[e["a"]]["kind"] != "std" else 1e9
        db = L - sarc if len(s.N[e["b"]]["e"]) > 1 or s.N[e["b"]]["kind"] != "std" else 1e9
        return min(da, db)


# ═══════════════════════════════════════ dessin
class Kit:
    def __init__(s, A, net):
        s.A, s.net = A, net
        s.trim = {}        # (nœud, tronçon, côté) → recul
        s.chains = []

    # ─── primitives
    def strip(s, mat, pts, o0, o1, z, closed=False, col=(.5, .5, .5)):
        if len(pts) < 2: return
        N = normals(pts, closed); n = len(pts)
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            j = (i + 1) % n
            a, b = pts[i], pts[j]; na, nb = N[i], N[j]
            s.A.face(mat, [(a[0] + na[0] * o0, a[1] + na[1] * o0, z), (b[0] + nb[0] * o0, b[1] + nb[1] * o0, z),
                           (b[0] + nb[0] * o1, b[1] + nb[1] * o1, z), (a[0] + na[0] * o1, a[1] + na[1] * o1, z)],
                      [(a[0] / 4, a[1] / 4), (b[0] / 4, b[1] / 4), (b[0] / 4, b[1] / 4), (a[0] / 4, a[1] / 4)], col)
    def wall(s, mat, pts, off, z0, z1, closed=False, flip=False, col=(.55, .54, .52)):
        if len(pts) < 2: return
        N = normals(pts, closed); n = len(pts)
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            j = (i + 1) % n
            a = (pts[i][0] + N[i][0] * off, pts[i][1] + N[i][1] * off); b = (pts[j][0] + N[j][0] * off, pts[j][1] + N[j][1] * off)
            q = [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]
            s.A.face(mat, q[::-1] if flip else q, None, col)
    def band(s, inner, outer, walk):
        """trottoir entre deux courbes (même nombre de points) : dessus, bordure côté chaussée, flanc extérieur"""
        for i in range(len(inner) - 1):
            a, b, c, d = inner[i], inner[i + 1], outer[i + 1], outer[i]
            if walk > .05:
                s.A.face("sidewalk", [(a[0], a[1], Z_WALK), (b[0], b[1], Z_WALK), (c[0], c[1], Z_WALK), (d[0], d[1], Z_WALK)])
                s.A.face("concrete", [(d[0], d[1], 0), (c[0], c[1], 0), (c[0], c[1], Z_WALK), (d[0], d[1], Z_WALK)])
            s.A.face("concrete", [(a[0], a[1], Z_ROAD), (b[0], b[1], Z_ROAD), (b[0], b[1], Z_WALK if walk > .05 else .13), (a[0], a[1], Z_WALK if walk > .05 else .13)])
        if walk <= .05:   # simple bordure (bretelle) : un liseré de béton
            for i in range(len(inner) - 1):
                a, b = inner[i], inner[i + 1]
                s.A.face("concrete", [(a[0], a[1], .13), (b[0], b[1], .13), (outer[i + 1][0], outer[i + 1][1], .13), (outer[i][0], outer[i][1], .13)])

    # ─── les bras de chaque nœud
    def arms(s, n):
        out = []
        for eid in s.net.N[n]["e"]:
            e = s.net.E[eid]
            for side in ("a", "b"):
                if e[side] != n: continue
                pts = e["pts"] if side == "a" else e["pts"][::-1]
                out.append((eid, side, pts, e["w"], e["walk"], e["cls"]))
                if e["a"] == e["b"]: break
            if e["a"] == e["b"] == n:
                out.append((eid, "b", e["pts"][::-1], e["w"], e["walk"], e["cls"]))
        return out

    def passthrough(s, n):
        nd = s.net.N[n]; es = nd["e"]
        if nd["kind"] != "std" or len(es) != 2 or es[0] == es[1]: return False
        e0, e1 = s.net.E[es[0]], s.net.E[es[1]]
        return (e0["w"], e0["walk"], e0["cls"]) == (e1["w"], e1["walk"], e1["cls"])

    def radius(s, n):
        nd = s.net.N[n]; arms = s.arms(n)
        if nd["kind"] in ("gate", "ramp"): return 0.
        if len(arms) == 1:
            w = arms[0][3]; return math.sqrt(max(1, s.bulb_r(arms[0]) ** 2 - (w / 2) ** 2))
        Hm = max(a[3] / 2 + a[4] for a in arms)
        angs = sorted(math.atan2(a[2][min(3, len(a[2]) - 1)][1] - nd["p"][1], a[2][min(3, len(a[2]) - 1)][0] - nd["p"][0]) for a in arms)
        r = Hm + 3.5
        for i in range(len(angs)):
            g = (angs[(i + 1) % len(angs)] - angs[i]) % (2 * math.pi) or 2 * math.pi
            if g < math.radians(165): r = max(r, Hm / math.tan(g / 2) + 3.)
        return min(r, 34.)

    @staticmethod
    def bulb_r(arm): return arm[3] / 2 + 6.5

    # ─── dessin de tout le réseau
    def render(s, road_cb=None):
        net = s.net
        R = {n: (0. if s.passthrough(n) else s.radius(n)) for n in range(len(net.N)) if net.N[n]["e"]}
        # 1) chaînes : on fusionne les tronçons à travers les nœuds de passage (pas de joint dans les virages)
        seen = set()
        for eid0 in list(net.E):
            if eid0 in seen: continue
            seen.add(eid0); e0 = net.E[eid0]
            pts = list(e0["pts"]); a, b = e0["a"], e0["b"]
            closed = False
            while s.passthrough(b) and not closed:
                nxt = [x for x in net.N[b]["e"] if x not in seen]
                if not nxt:
                    closed = (b == a); break
                e = net.E[nxt[0]]; seen.add(nxt[0])
                p2 = e["pts"] if e["a"] == b else e["pts"][::-1]
                pts += p2[1:]; b = e["b"] if e["a"] == b else e["a"]
                if b == a: closed = True
            while s.passthrough(a) and not closed:
                nxt = [x for x in net.N[a]["e"] if x not in seen]
                if not nxt: break
                e = net.E[nxt[0]]; seen.add(nxt[0])
                p2 = e["pts"] if e["b"] == a else e["pts"][::-1]
                pts = p2[:-1] + pts; a = e["a"] if e["b"] == a else e["b"]
                if b == a: closed = True
            if closed and s.passthrough(a):
                pts = pts[:-1]; s.chains.append((pts, e0, True)); continue
            L = length(pts); ra, rb = R.get(a, 0), R.get(b, 0)
            if L - ra - rb < .5: continue
            s.chains.append((cut(pts, ra, L - rb), e0, False))
        for pts, e, closed in s.chains:
            s.draw_chain(pts, e, closed)
            if road_cb: road_cb(pts, e, closed)
        # 2) carrefours et raquettes
        for n in range(len(net.N)):
            if not net.N[n]["e"] or s.passthrough(n) or net.N[n]["kind"] in ("gate", "ramp"): continue
            s.draw_node(n, R[n])

    def draw_chain(s, pts, e, closed):
        w, walk = e["w"], e["walk"]; h = w / 2
        s.strip("asphalt", pts, -h - .05, h + .05, Z_ROAD, closed)
        wk = walk if walk > .05 else .45
        for sd in (-1, 1):
            N = normals(pts, closed)
            inner = [(p[0] + n[0] * sd * h, p[1] + n[1] * sd * h) for p, n in zip(pts, N)]
            outer = [(p[0] + n[0] * sd * (h + wk), p[1] + n[1] * sd * (h + wk)) for p, n in zip(pts, N)]
            if closed: inner.append(inner[0]); outer.append(outer[0])
            s.band(inner, outer, walk)
        # marquages
        P = pts + [pts[0]] if closed else pts
        if e["cls"] in ("arterial", "avenue") and w >= 11:
            s.strip("paint_y", P, -.35, -.15, Z_ROAD + .004); s.strip("paint_y", P, .15, .35, Z_ROAD + .004)
            s.dashes(P, w / 4); s.dashes(P, -w / 4)
        elif e["cls"] != "ramp" and w >= 7:
            s.dashes(P, 0)
        elif e["cls"] == "ramp":
            s.strip("paint_w", P, -h + .5, -h + .7, Z_ROAD + .004); s.strip("paint_w", P, h - .7, h - .5, Z_ROAD + .004)

    def dashes(s, pts, off, dash=3., gap=6.):
        L = length(pts); d = gap / 2
        while d + dash < L:
            seg = cut(pts, d, d + dash)
            if len(seg) >= 2: s.strip("paint_w", seg, off - .1, off + .1, Z_ROAD + .004)
            d += dash + gap

    def draw_node(s, n, r):
        net = s.net; p = net.N[n]["p"]; arms = s.arms(n)
        info = []
        for eid, side, apts, w, walk, cls in arms:
            L = length(apts)
            E, t, _ = at(apts, min(r, L - .1))
            nrm = (-t[1], t[0]); h = w / 2; H = h + (walk if walk > .05 else .45)
            ang = math.atan2(E[1] - p[1], E[0] - p[0])
            info.append(dict(E=E, t=t, n=nrm, h=h, H=H, walk=walk, ang=ang, w=w, cls=cls))
        info.sort(key=lambda a: a["ang"])
        k = len(info)
        poly = []                      # contour de la chaussée du carrefour
        for i in range(k):
            a = info[i]; b = info[(i + 1) % k]
            Ra = (a["E"][0] - a["n"][0] * a["h"], a["E"][1] - a["n"][1] * a["h"])
            La = (a["E"][0] + a["n"][0] * a["h"], a["E"][1] + a["n"][1] * a["h"])
            poly += [Ra, a["E"], La]
            gap = (b["ang"] - a["ang"]) % (2 * math.pi) if k > 1 else 2 * math.pi
            if k == 1: gap = 2 * math.pi
            M = max(12, int(gap / .12))
            inner = s.corner(p, a, b, "h", gap, M)
            outer = s.corner(p, a, b, "H", gap, M)
            poly += inner[1:-1]
            s.band(inner, outer, min(a["walk"], b["walk"]) if min(a["walk"], b["walk"]) > .05 else max(a["walk"], b["walk"]) if max(a["walk"], b["walk"]) > .05 else 0)
        for i in range(len(poly)):
            q0, q1 = poly[i], poly[(i + 1) % len(poly)]
            s.A.face("asphalt", [(p[0], p[1], Z_JUNC), (q0[0], q0[1], Z_JUNC), (q1[0], q1[1], Z_JUNC)])
        if k == 1:        # raquette : un îlot planté au milieu
            s.A.cyl("concrete", p[0], p[1], 0, Z_WALK, 3.6, 20, top=False)
            s.A.cyl("grass", p[0], p[1], Z_WALK - .01, .02, 3.6, 20)
        if getattr(s, "node_cb", None): s.node_cb(p, info, k)
        if k >= 3:        # passages piétons sur chaque branche
            for a in info:
                if a["walk"] <= .05 or a["cls"] == "ramp": continue
                c = (a["E"][0] + a["t"][0] * 2.2, a["E"][1] + a["t"][1] * 2.2)
                rot = math.atan2(a["t"][1], a["t"][0])
                m = int((a["w"] - 1) / 1.2)
                for j in range(m):
                    o = -a["h"] + .9 + j * 1.2
                    s.A.box("paint_w", c[0] + a["n"][0] * o, c[1] + a["n"][1] * o, Z_ROAD + .003, 3, .6, .005, rot, sides=False)

    def corner(s, p, a, b, which, gap, M=12):
        """le bord (chaussée « h » ou trottoir « H ») entre le côté gauche du bras a et le côté droit du bras b"""
        ha, hb = a[which], b[which]
        P0 = (a["E"][0] + a["n"][0] * ha, a["E"][1] + a["n"][1] * ha)
        P1 = (b["E"][0] - b["n"][0] * hb, b["E"][1] - b["n"][1] * hb)
        if gap < math.radians(165):
            # raccord tangent : les deux bords prolongés se croisent en X, courbe de Bézier P0 → X → P1
            d0, d1 = a["t"], b["t"]
            den = d0[0] * d1[1] - d0[1] * d1[0]
            if abs(den) > 1e-6:
                wx, wy = P1[0] - P0[0], P1[1] - P0[1]
                u = (wx * d1[1] - wy * d1[0]) / den; v = (wx * d0[1] - wy * d0[0]) / den
                if u < 0 and v < 0:
                    X = (P0[0] + d0[0] * u, P0[1] + d0[1] * u)
                    return [((1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * X[0] + t * t * P1[0],
                             (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * X[1] + t * t * P1[1]) for t in (k / M for k in range(M + 1))]
        if gap < math.radians(190):
            return [(P0[0] + (P1[0] - P0[0]) * k / M, P0[1] + (P1[1] - P0[1]) * k / M) for k in range(M + 1)]
        # grand angle (raquette, virage large) : arc autour du nœud
        a0 = math.atan2(P0[1] - p[1], P0[0] - p[0]); a1 = math.atan2(P1[1] - p[1], P1[0] - p[0])
        da = (a1 - a0) % (2 * math.pi)
        r0, r1 = math.dist(P0, p), math.dist(P1, p)
        return [(p[0] + math.cos(a0 + da * k / M) * (r0 + (r1 - r0) * k / M), p[1] + math.sin(a0 + da * k / M) * (r0 + (r1 - r0) * k / M)) for k in range(M + 1)]
