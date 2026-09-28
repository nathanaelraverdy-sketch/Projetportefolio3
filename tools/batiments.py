# -*- coding: utf-8 -*-
"""Bâtiments détaillés, exécuté dans build.py (il en utilise les outils : A, R, inst, TREES, car_at, lamp…).

  • îlots de maisons de ville : rangées tout autour de l'îlot, bâtiments d'angle, arrière-cours
    (jardins privatifs séparés par des murets, ou parking commun sous porche)
  • bâtiments uniques et équipements : ils occupent TOUT leur îlot (parvis, jardins, parkings compris)

Repère local d'un îlot : u le long de l'îlot, v vers le fond ; le devant (v < 0) regarde la caméra."""

class Site:
    """un îlot vu en coordonnées locales (u, v), sol au-dessus du trottoir de l'îlot"""
    def __init__(s, x, y, rot, W, D, z0=.18):
        s.x, s.y, s.rot, s.W, s.D, s.z0 = x, y, rot, W, D, z0
        s.c, s.s = math.cos(rot), math.sin(rot)
    def P(s, u, v): return (s.x + u * s.c - v * s.s, s.y + u * s.s + v * s.c)
    def box(s, mat, u, v, z, w, d, h, col=(.5, .5, .5), top=None, r=0., **kw):
        A.box(mat, *s.P(u, v), s.z0 + z, w, d, h, s.rot + r, col=col, top=top, **kw)
    def flat(s, mat, u, v, z, w, d, col=(.5, .5, .5), r=0., h=.03):
        A.box(mat, *s.P(u, v), s.z0 + z, w, d, h, s.rot + r, col=col, sides=False)
    def cyl(s, mat, u, v, z, h, r, seg=16, col=(.5, .5, .5), **kw):
        A.cyl(mat, *s.P(u, v), s.z0 + z, h, r, seg, col=col, **kw)
    def dome(s, mat, u, v, z, r, h, seg=28, rings=7, col=(.5, .5, .5)):
        A.dome(mat, *s.P(u, v), s.z0 + z, r, h, seg, rings, col=col)
    def gable(s, mat, u, v, z, w, d, rh, col, r=0., over=.3, ends=None):
        A.gable(mat, *s.P(u, v), s.z0 + z, w, d, rh, s.rot + r, col, over=over)
        if ends: A.gable_ends("wall", *s.P(u, v), s.z0 + z, w, d, rh, s.rot + r, ends)
    def hip(s, u, v, z, w, d, rh, col, r=0., over=.3, mat="roof"):
        x, y = s.P(u, v); z0 = s.z0 + z; c, s_ = math.cos(s.rot + r), math.sin(s.rot + r)
        P = lambda lx, ly, zz: (x + lx * c - ly * s_, y + lx * s_ + ly * c, zz)
        hw, hd = w / 2 + over, d / 2 + over; k = max(0., hw - hd)
        a, b, cc, dd = P(-hw, -hd, z0), P(hw, -hd, z0), P(hw, hd, z0), P(-hw, hd, z0)
        r0, r1 = P(-k, 0, z0 + rh), P(k, 0, z0 + rh)
        for q in ([a, b, r1, r0], [cc, dd, r0, r1]): A.face(mat, q, None, col)
        A.face(mat, [b, cc, r1], None, col); A.face(mat, [dd, a, r0], None, col)
        if mat != "cuivre":      # faîtages et arêtiers en zinc
            for p0, p1 in ((r0, r1), (a, r0), (b, r1), (cc, r1), (dd, r0)):
                mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2; L_ = math.dist(p0[:2], p1[:2])
                if L_ > .3: A.box("metal", mx, my, (p0[2] + p1[2]) / 2 - .05, L_, .22, .12, math.atan2(p1[1] - p0[1], p1[0] - p0[0]), col=(.5, .52, .55))
    def face(s, mat, pts, col=(.5, .5, .5)):
        A.face(mat, [(*s.P(u, v), s.z0 + z) for u, v, z in pts], None, col)
    def tree(s, u, v, sc=1., pine=False):
        inst(R.choice(PINES if pine else TREES), *s.P(u, v), s.z0, R.uniform(0, 6.3), sc * R.uniform(.85, 1.1))
    def row_trees(s, u0, u1, v, n, sc=.9):
        for k in range(n): s.tree(u0 + (u1 - u0) * (k + .5) / n, v, sc)
    def lamp(s, u, v, a=0.): lamp(*s.P(u, v), s.rot + a)
    def bench(s, u, v, a=0.): bench(*s.P(u, v), s.rot + a)
    def columns(s, u0, u1, v, n, z, h, r=.55, mat="pierre", col=(.9, .88, .84)):
        """colonnes avec base et chapiteau"""
        for k in range(n):
            u = u0 + (u1 - u0) * k / max(1, n - 1)
            s.box("pierre", u, v, z, r * 2.6, r * 2.6, .45, col=col, top="pierre")
            s.cyl(mat, u, v, z + .45, h - 1.05, r, 14, col=col, r2=r * .88)
            s.cyl("pierre", u, v, z + h - .6, .3, r * 1.15, 14, col=col, r2=r * 1.35)
            s.box("pierre", u, v, z + h - .3, r * 2.8, r * 2.8, .3, col=col, top="pierre")
    def steps(s, u, v, w, d, n, rise=.18, mat="white", col=(.85, .83, .78)):
        """un emmarchement qui monte vers le fond (v croissant)"""
        for k in range(n):
            s.box(mat, u, v + d * k / (2 * n), rise * k, w - k * .3, d * (1 - k / n) + .01 * k, rise, col=col, top=mat)
    def pediment(s, u, v, w, z, h, depth, col):
        """fronton : tympan en retrait avec un bas-relief, corniches rampantes, acrotères"""
        a0, b0 = u - w / 2, u + w / 2
        s.face("pierre", [(a0, v + .35, z), (b0, v + .35, z), (u, v + .35, z + h)], tuple(c_ * .92 for c_ in col))
        s.face("ardoise", [(a0 - .3, v - .2, z), (u, v - .2, z + h + .3), (u, v + depth, z + h + .3), (a0 - .3, v + depth, z)], (.5, .5, .5))
        s.face("ardoise", [(u, v - .2, z + h + .3), (b0 + .3, v - .2, z), (b0 + .3, v + depth, z), (u, v + depth, z + h + .3)], (.5, .5, .5))
        for sd in (-1, 1):   # corniches rampantes (bandes claires le long des deux pentes)
            s.face("pierre", [(u + sd * (w / 2 + .3), v - .25, z - .05), (u, v - .25, z + h + .25), (u, v - .25, z + h - .35), (u + sd * (w / 2 - .5), v - .25, z - .05)], col)
        s.box("pierre", u, v - .1, z - .5, w + .8, .8, .5, col=col, top="pierre")                           # corniche horizontale
        s.box("pierre", u, v + .2, z + .6, w * .3, .3, h * .45, col=tuple(c_ * 1.05 for c_ in col))           # bas-relief
        for du in (-w / 2, 0, w / 2): s.box("or" if du == 0 else "pierre", u + du, v, z + (h + .3 if du == 0 else 0), .9, .9, 1.8, col=col)   # acrotères

    def classic(s, u, v, w, d, h, fh=4.2, col=None, bay=3.1, r=0., balustrade=True, pilasters=True, arcades=True):
        """façade classique en pierre de taille : rez-de-chaussée à bossages et arcades, fenêtres en creux, bandeaux,
        pilastres, corniche à denticules, balustrade"""
        col = col or STONE
        x, y = s.P(u, v); z0 = s.z0
        gridded(x, y, s.rot + r, w, d, z0 + fh, h - fh, fh, bay, (col, (.06, .08, .1), 1.2, 1.5, .55), "pierre")
        dark = tuple(c_ * .86 for c_ in col); light = tuple(min(1, c_ * 1.06) for c_ in col)
        s.box("pierre", u, v, 0, w + .5, d + .5, fh, col=dark, top="pierre", r=r)
        for k in range(1, int((h - fh) / fh) + 1):
            s.box("pierre", u, v, fh * k - .1 if k > 1 else fh - .02, w + .35, d + .35, .22, col=light, top="pierre", r=r)
        s.box("pierre", u, v, h, w + 1.3, d + 1.3, .75, col=light, top="pierre", r=r)
        rb = s.rot + r
        for fr, L_, off in ((0, w, d / 2), (math.pi / 2, d, w / 2), (math.pi, w, d / 2), (-math.pi / 2, d, w / 2)):
            th = rb + fr
            if math.cos(th) < .08: continue          # face que la caméra ne voit pas
            ct, st_ = math.cos(th), math.sin(th)
            F = lambda t, e: (x + ct * t + st_ * e, y + st_ * t - ct * e)
            nb = max(1, round(L_ / bay))
            for k in range(nb):
                t = -L_ / 2 + L_ * (k + .5) / nb
                if arcades: A.box("dark", *F(t, off + .27), z0 + .25, bay * .55, .08, fh * .68, th, col=(.05, .05, .05))
                if pilasters and k % 2 == 0 and h - fh > 4: A.box("pierre", *F(-L_ / 2 + L_ * k / nb, off + .2), z0 + fh, .75, .4, h - fh, th, col=light, top="pierre")
            for k in range(int(L_ / .75)):
                A.box("pierre", *F(-L_ / 2 + .4 + k * .75, off + .55), z0 + h - .3, .32, .3, .3, th, col=light)
            if balustrade:
                A.box("pierre", *F(0, off + .3), z0 + h + .75, L_ + 1, .45, .18, th, col=light, top="pierre")
                A.box("pierre", *F(0, off + .3), z0 + h + 1.7, L_ + 1, .5, .18, th, col=light, top="pierre")
                for k in range(int(L_ / .6)):
                    A.box("pierre", *F(-L_ / 2 + .3 + k * .6, off + .3), z0 + h + .93, .2, .2, .77, th, col=light)

    def rib_dome(s, u, v, z, r, h, ribs=12, rib_mat="or", lantern=True):
        """coupole à côtes : tambour, calotte en cuivre patiné, nervures, lanterne à colonnettes, épi doré"""
        x, y = s.P(u, v); z0 = s.z0 + z
        A.cyl("pierre", x, y, z0 - .6, .6, r + .5, 36, col=STONE2)
        A.dome("cuivre", x, y, z0, r, h, 40, 9)
        for k in range(ribs):
            a = 2 * math.pi * k / ribs; ca, sa = math.cos(a), math.sin(a); prev = None
            for j in range(10):
                t = j / 9 * math.pi / 2 * .93; rr, zz = r * math.cos(t) + .07, z0 + h * math.sin(t) + .07
                wv = .22 * (1 - .6 * j / 9)
                p = [(x + ca * rr - sa * wv, y + sa * rr + ca * wv, zz), (x + ca * rr + sa * wv, y + sa * rr - ca * wv, zz)]
                if prev: A.face(rib_mat, [prev[0], prev[1], p[1], p[0]], None, (.8, .6, .2))
                prev = p
        if lantern:
            lr = max(.9, r * .17); lz = z0 + h * .97
            A.cyl("pierre", x, y, lz, .4, lr + .3, 16, col=STONE2)
            for k in range(8): A.cyl("pierre", x + math.cos(k * .785) * lr, y + math.sin(k * .785) * lr, lz + .4, lr * 1.6, .12, 6, col=STONE)
            A.cyl("pierre", x, y, lz + .4 + lr * 1.6, .3, lr + .2, 16, col=STONE2)
            A.dome("cuivre", x, y, lz + .7 + lr * 1.6, lr, lr * .8, 16, 4)
            A.cyl("or", x, y, lz + .7 + lr * 2.4, lr * 1.3, .1, 6, r2=.02)
    def mansard(s, u, v, z, w, d, h, col=(.2, .22, .26), r=0.):
        """toit à la Mansart : pentes raides en ardoise, terrasson presque plat"""
        s.box("ardoise", u, v, z, w, d, h * .75, col=(.5, .5, .5), top=None, r=r)
        s.hip(u, v, z + h * .75, w - .4, d - .4, h * .35, col, r=r, over=0, mat="ardoise")
        for k in range(int(w / 3.2)):                  # lucarnes en façade avant
            du = -w / 2 + 1.6 + k * 3.2
            cu, cv = u + du * math.cos(r), v + du * math.sin(r)
            lx_, ly_ = cu - math.sin(r) * (-d / 2 - .2), cv + math.cos(r) * (-d / 2 - .2)
            s.box("pierre", lx_, ly_, z + .4, 1.2, .9, 1.7, col=(.85, .82, .76), top="pierre", r=r)
            s.box("dark", lx_ - math.sin(r) * -.46, ly_ + math.cos(r) * -.46, z + .6, .6, .04, 1.1, r=r)
            s.gable("ardoise", lx_, ly_, z + 2.1, 1.2, 1.1, .6, (.5, .5, .5), r=r + math.pi / 2, over=.1)
        for k in range(int(w / 9)):                     # souches de cheminée
            du = -w / 2 + 4 + k * 9; s.box("pierre", u + du * math.cos(r), v + du * math.sin(r), z + h * .6, 1.4, .8, h * .75, col=(.7, .62, .52), top="pierre", r=r)
    def parking(s, u0, u1, v0, v1, fill=.75, trees=True):
        """parking : enrobé, places peintes en épi droit, voitures, arbres d'alignement"""
        s.flat("asphalt", (u0 + u1) / 2, (v0 + v1) / 2, .005, u1 - u0, v1 - v0, h=.03)
        rows = max(1, int((v1 - v0) / 16.5))
        for r_ in range(rows):
            va = v0 + (v1 - v0) * (r_ + .5) / rows              # allée centrale de la double rangée
            for side in (-1, 1):
                vr = va + side * 5.8
                n = int((u1 - u0 - 2) / 2.6)
                for k in range(n + 1):
                    uu = u0 + 1 + k * 2.6
                    s.flat("paint_w", uu, vr, .04, .12, 5, h=.005)
                    if k < n and R.random() < fill:
                        car_at(*s.P(uu + 1.3, vr), s.rot + math.pi / 2 * side, parked=True)
            if trees and rows > 1 and r_ < rows - 1:
                vb = v0 + (v1 - v0) * (r_ + 1) / rows
                s.box("sidewalk", (u0 + u1) / 2, vb, 0, u1 - u0 - 4, 1.6, .15, top="grass")
                for k in range(int((u1 - u0) / 10)): s.tree(u0 + 5 + k * 10, vb, .75)


# ═══════════════════════════════════════ îlots de maisons de ville, tout autour de l'îlot
def perimeter_block(z, b, gardens=None, station=False):
    """maisons mitoyennes sur les 4 côtés, bâtiments d'angle plus hauts, arrière-cours au milieu
    (station=True : une station-service occupe l'angle sud-ouest de l'îlot)"""
    u0, u1, v0, v1 = b
    block_pad(z, b)
    block_props(z, b, inset=1.4, kinds=("tree", "lamp", "bin"))
    WK = 2.8                                             # trottoir de l'îlot
    iu0, iu1, iv0, iv1 = u0 + WK, u1 - WK, v0 + WK, v1 - WK
    DD = R.uniform(10, 12)                               # profondeur des maisons
    cx, cy = z.w((u0 + u1) / 2, (v0 + v1) / 2)
    S = Site(cx, cy, z.rot, u1 - u0, v1 - v0)
    ou, ov = (u0 + u1) / 2, (v0 + v1) / 2                 # centre de l'îlot en coordonnées de zone
    L = lambda uu, vv: (uu - ou, vv - ov)                 # zone → site
    fl = R.choice([2, 2, 3, 3, 4])                        # étages de la rangée
    mode = gardens if gardens is not None else R.choices(["jardins", "parking", "mixte"], [5, 2, 3])[0]
    SU, SV = 36., 28.                                     # emprise de la station (angle sud-ouest)
    if station: mode = "jardins"
    # les 4 côtés : (origine, direction le long, normale vers la rue, longueur)
    sides = [((iu0, iv0), (1, 0), (0, -1), iu1 - iu0), ((iu1, iv0), (0, 1), (1, 0), iv1 - iv0),
             ((iu1, iv1), (-1, 0), (0, 1), iu1 - iu0), ((iu0, iv1), (0, -1), (-1, 0), iv1 - iv0)]
    passage = (2 if mode == "mixte" else R.randrange(4)) if mode != "jardins" else -1  # porche vers la cour (parking)
    yards = []
    for si, ((ox_, oy_), (du, dv), (nu, nv), Ls) in enumerate(sides):
        rot_side = z.rot + math.atan2(dv, du)             # axe x du bâtiment le long de la rue, façade vers la rue (−y local)
        # bâtiment d'angle au début de chaque côté (le coin appartient à ce côté)
        ch = fl * 3.2 + R.choice([3.2, 3.2, 6.4]) + .6
        skip_corner = station and si == 0
        cu_, cv_ = ox_ + du * DD / 2 - nu * DD / 2, oy_ + dv * DD / 2 - nv * DD / 2
        x_, y_ = z.w(cu_, cv_)
        st = R.choice(["brick", "brick2", "stone", "stucco", "office"])
        if not skip_corner:
            A.box("facade", x_, y_, .18, DD, DD, ch, rot_side, col=STYLES[st][0], top="roof", fh=3.2, bay=2.4)
            A.box("wall", x_, y_, .18 + ch - .1, DD + .4, DD + .4, .6, rot_side, col=tuple(c_ * .88 for c_ in STYLES[st][0]), top="roof")
            roof_clutter(x_, y_, rot_side, DD - .8, DD - .8, .18 + ch + .5, "std")
            # rez-de-chaussée commerçant sur l'angle : vitrine et store
            fx, fy = z.w(cu_ + nu * (DD / 2 + .25), cv_ + nv * (DD / 2 + .25))
            A.box("painted", fx, fy, .18 + 2.7, DD * .8, 1.1, .12, rot_side, col=R.choice([(.6, .1, .08), (.1, .3, .2), (.15, .2, .45), (.7, .5, .1)]))
            if R.random() < .45:     # terrasse de café sur le trottoir
                tx_, ty_ = z.w(cu_ + nu * (DD / 2 + 1.5), cv_ + nv * (DD / 2 + 1.5)); terrace(tx_, ty_, rot_side, 3)
        # les maisons entre les angles
        pos = DD; end = Ls - DD * 0          # le coin de fin appartient au côté suivant
        units = []
        while pos < end - DD - 3.5:
            w_ = R.uniform(5.5, 8.)
            if end - DD - pos - w_ < 5.5: w_ = end - DD - pos
            units.append((pos, w_)); pos += w_
        if pos < end - DD - .1 and units: units[-1] = (units[-1][0], end - DD - units[-1][0])
        pk = len(units) // 2 if si == passage and units else -1
        for k_, (p0, w_) in enumerate(units):
            mu = p0 + w_ / 2
            if station and ((si == 0 and p0 < SU) or (si == 3 and p0 + w_ > Ls - SV)): continue
            uu, vv = ox_ + du * mu - nu * DD / 2, oy_ + dv * mu - nv * DD / 2
            x_, y_ = z.w(uu, vv)
            h_ = fl * 3.1 + R.choice([0, 0, 0, 3.1]) * (1 if fl < 4 else 0) + .3
            colw = R.choice(WALLS_H)
            if k_ == pk:          # porche : le passage vers la cour, les étages au-dessus
                A.box("facade", x_, y_, .18 + 3.4, w_, DD, h_ - 3.4, rot_side, col=colw, top="roof", fh=3.1, bay=2.2)
                A.box("dark", x_, y_, .18 + 3.3, w_, DD, .1, rot_side)
                for sd in (-1, 1):
                    px_, py_ = z.w(uu + du * sd * (w_ / 2 - .25), vv + dv * sd * (w_ / 2 - .25)); A.box("wall", px_, py_, .18, .5, DD, 3.4, rot_side, col=colw)
                yards.append(("porche", si, mu, w_))
            else:
                A.box("facade", x_, y_, .18, w_ - .05, DD, h_, rot_side, col=colw, top="roof", fh=3.1, bay=2.2, uoff=R.random())
            if R.random() < .72:
                A.gable("roof", x_, y_, .18 + h_, w_, DD, DD * R.uniform(.28, .38), rot_side, R.choice(ROOFS_H), over=.15)
                A.gable_ends("wall", x_, y_, .18 + h_, w_, DD, DD * .28, rot_side, colw)
                if R.random() < .5:   # cheminée
                    kx, ky = z.w(uu + du * R.uniform(-w_ / 3, w_ / 3), vv); A.box("wall", kx, ky, .18 + h_, .7, .7, DD * .38 + .8, rot_side, col=(.5, .3, .22))
            else:
                A.box("wall", x_, y_, .18 + h_ - .05, w_, DD, .5, rot_side, col=tuple(c_ * .9 for c_ in colw), top="roof")
            yards.append(("maison", si, mu, w_))
        claim(*z.w(ox_ + du * Ls / 2 - nu * DD / 2, oy_ + dv * Ls / 2 - nv * DD / 2), Ls, DD, rot_side)
    if station:   # la station-service : auvent et pompes, boutique, totem des prix, dalle béton
        su0, sv0 = iu0, iv0
        a_, b_ = L(su0 + SU / 2, sv0 + SV / 2)
        S.flat("concrete", a_, b_, .01, SU + 2.6, SV + 2.6, h=.04)
        pu, pv = L(su0 + SU * .42, sv0 + SV * .38)
        S.box("painted", pu, pv, 5.2, 20, 12, .9, col=(.85, .1, .08), top="white")
        S.box("white", pu, pv - 6.05, 5.35, 20, .1, .6, top="white")
        for k in (-6.5, 0, 6.5):
            S.box("concrete", pu + k, pv, 0, 1.2, 7, .2, top="concrete")
            for r_ in (-2.2, 2.2): S.box("white", pu + k, pv + r_, .2, .7, 1.2, 1.8, top="white"); S.cyl("metal", pu + k, pv + r_, 2, 3.2, .1, 6)
            if R.random() < .7: car_at(*S.P(pu + k + 2, pv - 4), S.rot, parked=True)
        S.box("sign", pu, pv - 6.12, 5.5, 8, .1, .5, top="sign")
        bu, bv = L(su0 + SU - 6, sv0 + SV - 5)
        S.box("facade", bu, bv, 0, 11, 7, 4.2, col=(.92, .92, .9), top="roof", fh=4.2, bay=3)
        S.box("signred", bu, bv - 3.6, 3.2, 8, .2, .8, top="signred")
        roof_clutter(*S.P(bu, bv), S.rot, 10, 6, S.z0 + 4.3, "std")
        tu, tv = L(su0 + 1.5, sv0 + 1.5)
        S.cyl("metal", tu, tv, 0, 7, .15, 6); S.box("signred", tu, tv, 7, 2.6, .35, 3.4, top="signred")
        claim(*S.P(a_, b_), SU, SV, S.rot)
    # ─── la cour : jardins privatifs derrière chaque maison, ou parking commun
    cu0, cu1, cv0, cv1 = iu0 + DD, iu1 - DD, iv0 + DD, iv1 - DD
    if cu1 - cu0 < 6 or cv1 - cv0 < 6: return
    midv = (cv0 + cv1) / 2
    if mode == "parking" or mode == "mixte":
        # parking commun : toute la cour (parking) ou sa moitié arrière (mixte)
        pv0 = cv0 if mode == "parking" else midv
        a_, b_ = L(cu0 + 1, pv0 + (0 if mode == "parking" else .6)); c_, d_ = L(cu1 - 1, cv1 - 1)
        S.parking(a_, c_, b_, d_, fill=.7, trees=False)
        for k in range(3): S.tree(*L(cu0 + 3 + k * (cu1 - cu0 - 6) / 2, cv1 - 1.5), .7)
    if mode == "jardins" or mode == "mixte":
        # jardins des maisons côté rue avant (sud) et, si pas de parking, côté nord ; murets entre voisins
        gv1 = midv if mode == "mixte" else midv
        for (kind, si, mu, w_) in yards:
            if kind != "maison": continue
            if si == 0: ua, ub, va, vb = iu0 + mu - w_ / 2, iu0 + mu + w_ / 2, cv0, midv
            elif si == 2 and mode == "jardins": ua, ub, va, vb = iu1 - mu - w_ / 2, iu1 - mu + w_ / 2, midv, cv1
            elif si == 1: ua, ub, va, vb = cu1 - min(8, (cu1 - cu0) / 2), cu1, iv0 + mu - w_ / 2, iv0 + mu + w_ / 2
            elif si == 3: ua, ub, va, vb = cu0, cu0 + min(8, (cu1 - cu0) / 2), iv1 - mu - w_ / 2, iv1 - mu + w_ / 2
            else: continue
            ua, ub = max(ua, cu0), min(ub, cu1); va, vb = max(va, cv0), min(vb, cv1)
            if si in (0, 2) and (ua < cu0 + min(8, (cu1 - cu0) / 2) - .5 or ub > cu1 - min(8, (cu1 - cu0) / 2) + .5): continue
            if mode == "mixte" and si in (1, 3) and (va + vb) / 2 > midv: continue
            if ub - ua < 2 or vb - va < 2: continue
            gu, gv = L((ua + ub) / 2, (va + vb) / 2); gw, gd = ub - ua, vb - va
            r_ = R.random()
            S.flat("grass" if r_ < .7 else "plaza", gu, gv, .01, gw - .2, gd - .2, h=.04)
            # muret de brique sur le côté et au fond du jardin
            wc = R.choice([(.45, .22, .14), (.6, .56, .5), (.36, .18, .11)])
            if si in (0, 2):
                S.box("wall", *L(ub, (va + vb) / 2), 0, .25, gd, 1.4, col=wc)
                S.box("wall", *L((ua + ub) / 2, vb if si == 0 else va), 0, gw, .25, 1.4, col=wc)
            else:
                S.box("wall", *L((ua + ub) / 2, vb), 0, gw, .25, 1.4, col=wc)
                S.box("wall", *L(ua if si == 1 else ub, (va + vb) / 2), 0, .25, gd, 1.4, col=wc)
            # terrasse contre la maison, et un élément de jardin
            if si == 0: S.flat("wood", *L((ua + ub) / 2, va + 1.2), .05, gw - .6, 2.2, h=.05)
            x_ = R.random()
            pu, pv = L(R.uniform(ua + 1.2, ub - 1.2), R.uniform(va + (3 if si == 0 else 1.2), vb - 1.2))
            if x_ < .35 and gw * gd > 30: S.tree(pu, pv, .6)
            elif x_ < .5: S.box("wood", pu, pv, 0, 1.8, 1.5, 2.0, top="roof", col=(.3, .2, .12))           # abri
            elif x_ < .62: S.flat("dirt", pu, pv, .05, min(3, gw - 1), min(2.4, gd - 1), h=.1)             # potager
            elif x_ < .72: S.cyl("painted", pu, pv, 0, .5, 1.2, 12, col=(.1, .4, .2))                    # trampoline
            elif x_ < .82 and gd > 5: S.flat("pool", pu, pv, .05, min(3.5, gw - 1.2), 2.2, h=.07)        # petit bassin
            else:
                S.cyl("painted", pu, pv, 0, .08, .6, 8, col=(.85, .85, .85)); S.cyl("white", pu, pv, .08, 2, .04, 4)  # table et parasol
                S.cyl("painted", pu, pv, 1.9, .35, 1.2, 8, r2=.05, col=R.choice([(.75, .2, .12), (.12, .3, .55), (.9, .7, .15)]))


# ═══════════════════════════════════════ bâtiments uniques : tout l'îlot
STONE = (.8, .75, .64); STONE2 = (.74, .68, .57); SLATE = (.2, .22, .26); COPPER = (.16, .33, .27)

def forecourt(S, depth, trees=True, fountain=False):
    """parvis devant (v < 0) : dallage, alignement d'arbres, lampadaires, bancs, fontaine"""
    W, D = S.W, S.D
    S.flat("plaza", 0, -D / 2 + depth / 2, .005, W - .5, depth, h=.02)
    if trees:
        for sd in (-1, 1):
            for k in range(3): S.tree(sd * (W / 2 - 4 - k * 6), -D / 2 + depth * .5, .85)
    for sd in (-1, 1): S.lamp(sd * W * .2, -D / 2 + 1.2, math.pi / 2); S.bench(sd * W * .28, -D / 2 + depth * .7, 0)
    if fountain:
        S.cyl("concrete", 0, -D / 2 + depth * .5, 0, .5, 4, 28); S.cyl("water", 0, -D / 2 + depth * .5, 0, .55, 3.5, 28)
        S.cyl("white", 0, -D / 2 + depth * .5, .5, 2.2, .35, 10)

def lm_theatre(S):
    W, D = S.W, S.D; fc = 12
    forecourt(S, fc, fountain=True)
    v0 = -D / 2 + fc
    bw, bd = W * .76, D - fc - 5; bv = v0 + bd / 2
    for sd in (-1, 1):                                                                             # ailes basses
        S.classic(sd * (bw / 2 + (W - bw) / 4 - .4), bv + 3, (W - bw) / 2 - 1.6, bd - 10, 10.5, fh=3.8, bay=2.8, balustrade=False)
        S.hip(sd * (bw / 2 + (W - bw) / 4 - .4), bv + 3, 11.3, (W - bw) / 2 - 1.2, bd - 9.6, 2.5, (.5, .5, .5), mat="ardoise")
    S.classic(0, bv, bw, bd, 17, fh=4.6, bay=3.3)
    S.hip(0, bv + 3, 18.7, bw - 5, bd - 12, 5.5, (.5, .5, .5), mat="cuivre")
    fv = v0 + bd - 8                                                                               # cage de scène
    S.box("pierre", 0, fv, 17, bw * .56, 12, 13, col=STONE2, top="pierre")
    S.box("pierre", 0, fv, 29.9, bw * .56 + .6, 12.6, .5, col=STONE, top="pierre")
    S.gable("ardoise", 0, fv, 30.4, bw * .56, 12, 3, (.5, .5, .5), ends=STONE2)
    # portique : emmarchement, colonnes à chapiteaux, entablement, fronton, statues
    S.steps(0, v0 - 6, bw * .64, 6, 6)
    S.box("pierre", 0, v0 - 2.7, 1.05, bw * .62, 5.4, .25, col=STONE2, top="plaza")
    S.columns(-bw * .28, bw * .28, v0 - 4.8, 8, 1.3, 11.5, .62)
    S.columns(-bw * .28, bw * .28, v0 - 1.4, 8, 1.3, 11.5, .5)
    S.box("pierre", 0, v0 - 2.7, 12.8, bw * .62, 6, 2.2, col=STONE, top="pierre")
    S.box("pierre", 0, v0 - 2.7, 15, bw * .64, 6.2, .5, col=STONE2, top="pierre")
    S.pediment(0, v0 - 5.6, bw * .62, 15.5, 4.6, 6, STONE)
    for k in range(7): S.box("or", -bw * .42 + k * bw * .14, v0 - .6, 18.5, .7, .7, 2.3)           # statues dorées sur la balustrade
    for sd in (-1, 1): S.box("painted", sd * bw * .37, v0 - .35, 5, 2.4, .2, 9, col=(.62, .08, .08))  # bannières
    S.box("sign", 0, v0 - .3, 4.3, bw * .3, .3, 1.1, top="sign")
    for sd in (-1, 1): S.lamp(sd * bw * .35, v0 - 7.5, math.pi / 2)
    return 34

def lm_opera(S):
    W, D = S.W, S.D; fc = 11
    forecourt(S, fc)
    v0 = -D / 2 + fc
    S.box("pierre", 0, v0 + (D - fc - 2) / 2, 0, W * .92, D - fc - 2, 3.2, col=STONE2, top="plaza")   # soubassement
    S.steps(0, v0 - 5.5, W * .72, 5.5, 8, .4)
    fw = W * .82
    # grande façade : arcades, loggia de colonnes jumelées, attique, groupes dorés
    S.classic(0, v0 + 6, fw, 12, 18, fh=5.2, bay=3.7, balustrade=False, pilasters=False)
    for k in range(8):
        uu = -fw * .42 + k * fw * .84 / 7
        S.columns(uu - .75, uu + .75, v0 - .8, 2, 5.4, 9.2, .42)
    S.box("pierre", 0, v0 + 6, 21.5, fw + .2, 12.2, 3, col=STONE2, top="pierre")                     # attique
    for sd in (-1, 1):
        S.box("pierre", sd * fw * .44, v0 + 6, 24.5, 5.6, 10, 2.6, col=STONE, top="pierre")
        S.rib_dome(sd * fw * .44, v0 + 6, 27.8, 2.8, 3.2, ribs=8, lantern=False)
        S.box("or", sd * fw * .44, v0 - .8, 24.6, 2.6, 1.4, 3.2)                                    # groupes sculptés dorés
        S.box("or", sd * fw * .3, v0 - .7, 21.6, 1, 1, 2.2)
    # salle : tambour à oculi, coupole de cuivre à côtes dorées
    rr = min(W, D) * .21; cv = v0 + 13 + rr
    S.cyl("pierre", 0, cv, 3.2, 18.6, rr, 40, col=STONE)
    for k in range(16):
        a = k / 16 * 6.283
        A.box("dark", *S.P(math.cos(a) * (rr + .02), cv + math.sin(a) * (rr + .02)), S.z0 + 14, 1.4, .1, 2, S.rot + a + math.pi / 2, col=(.05, .05, .05))
    S.cyl("pierre", 0, cv, 21.8, .8, rr + .6, 40, col=STONE2)
    S.rib_dome(0, cv, 23.2, rr, rr * .55, ribs=16)
    # cage de scène, pignon, Apollon doré
    sv = D / 2 - 8.5
    S.classic(0, sv, W * .58, 13, 31, fh=6, bay=4.2, balustrade=False, arcades=False)
    S.gable("cuivre", 0, sv, 31.8, W * .58, 13, 5, (.5, .5, .5), ends=STONE2)
    S.box("or", 0, sv - 6.6, 34, 1.4, 1.4, 4)
    for sd in (-1, 1):                                                                            # pavillons latéraux en rotonde
        S.cyl("pierre", sd * (W * .4), v0 + 21, 3.2, 12, 6, 28, col=STONE)
        S.cyl("pierre", sd * (W * .4), v0 + 21, 15.2, .6, 6.5, 28, col=STONE2)
        S.rib_dome(sd * (W * .4), v0 + 21, 16.4, 6, 3.8, ribs=10)
    return 38

def lm_musee(S):
    W, D = S.W, S.D; wing = 13; fc = 6
    S.flat("plaza", 0, 0, .004, W - .5, D - .5, h=.02)
    # palais en U autour de la cour, ouvert vers l'avant
    S.classic(0, D / 2 - wing / 2 - 1, W - 2, wing, 14, fh=4.6, bay=3.2)
    for sd in (-1, 1):
        S.classic(sd * (W / 2 - wing / 2 - 1), -fc / 2 - 1, wing, D - wing - fc - 4, 13.6, fh=4.6, bay=3.2)
    S.mansard(0, D / 2 - wing / 2 - 1, 15.6, W - 2.4, wing - .4, 6)
    S.mansard(-W / 2 + wing / 2 + 1, -fc / 2 - 1, 15.2, D - wing - fc - 4.4, wing - .4, 6, r=math.pi / 2)
    S.mansard(W / 2 - wing / 2 - 1, -fc / 2 - 1, 15.2, D - wing - fc - 4.4, wing - .4, 6, r=-math.pi / 2)
    for sd in (-1, 1):   # pavillons d'angle à dôme carré
        pu = sd * (W / 2 - wing / 2 - 1); pv = -D / 2 + fc + 5
        S.classic(pu, pv, wing + 1.5, 10, 16, fh=4.6, bay=3.2, balustrade=False)
        S.hip(pu, pv, 16.8, wing + 1.5, 10, 7, (.5, .5, .5), mat="ardoise")
        S.box("or", pu, pv, 23.6, .3, .3, 2)
    # la cour : pyramide de verre à résille, bassins, pyramidions
    cv = (-D / 2 + fc + D / 2 - wing - 1) / 2; pw = min(W - 2 * wing - 10, 22); ph = pw * .64
    base = [(-pw / 2, cv - pw / 2), (pw / 2, cv - pw / 2), (pw / 2, cv + pw / 2), (-pw / 2, cv + pw / 2)]
    for i in range(4):
        a, b = base[i], base[(i + 1) % 4]
        S.face("glass", [(a[0], a[1], .05), (b[0], b[1], .05), (0, cv, ph)], (.45, .55, .6))
        for k in range(1, 8):   # la résille métallique (horizontales et obliques)
            t = k / 8
            S.face("metal", [(a[0] * (1 - t), cv + (a[1] - cv) * (1 - t), ph * t + .05), (b[0] * (1 - t), cv + (b[1] - cv) * (1 - t), ph * t + .05),
                             (b[0] * (1 - t), cv + (b[1] - cv) * (1 - t), ph * t + .15), (a[0] * (1 - t), cv + (a[1] - cv) * (1 - t), ph * t + .15)], (.3, .3, .32))
            q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            S.face("metal", [(q[0], q[1], .06), (q[0] + .12, q[1] + .12, .06), (0, cv, ph + .02), (0, cv, ph + .06)], (.3, .3, .32))
    for sd in (-1, 1):
        S.box("pierre", sd * (pw / 2 + 6), cv, 0, 8.6, pw * .9 + .6, .45, col=STONE2, top="pierre")
        S.flat("water", sd * (pw / 2 + 6), cv, .38, 8, pw * .9, h=.1)
        for sv in (-1, 1):
            q = 2.5; uu, vv = sd * (pw / 2 + 6), cv + sv * pw * .25
            for (a_, b_) in (((-q, -q), (q, -q)), ((q, -q), (q, q)), ((q, q), (-q, q)), ((-q, q), (-q, -q))):
                S.face("glass", [(uu + a_[0], vv + a_[1], .5), (uu + b_[0], vv + b_[1], .5), (uu, vv, 3.4)], (.45, .55, .6))
    for k in range(4): S.bench(-W * .2 + k * W * .13, -D / 2 + 2.5, 0)
    S.box("sign", 0, -D / 2 + fc + 1.3, 11, 10, .3, 1.2, top="sign")
    return 22

def lm_cinema(S):
    W, D = S.W, S.D; fc = 9
    forecourt(S, fc, trees=True)
    v0 = -D / 2 + fc; bw, bd = W * .9, D - fc - 2; bv = v0 + bd / 2
    S.box("painted", 0, bv, 0, bw, bd, 17, col=(.14, .14, .16), top="roof")
    for k in range(3): S.box("painted", 0, v0 - .06, 12 + k * 1.2, bw + .1, .12, .45, col=((.8, .15, .1), (.95, .6, .1), (.8, .15, .1))[k])   # bandeaux colorés
    for k in range(int(bw / 3)):
        S.box("painted", -bw / 2 + 1.5 + k * 3, v0 - .12, 9.2, .25, .25, 7.8, col=(.3, .3, .33))        # joints du bardage
    S.box("glass", 0, v0 - .5, 0, bw * .6, 1, 9, col=(.2, .3, .35), top="glass")                     # hall vitré
    for k in range(9): S.box("metal", -bw * .3 + k * bw * .6 / 8, v0 - 1.05, 0, .2, .2, 9, col=(.4, .4, .42))
    S.box("dark", 0, v0 - 4, 5.2, bw * .64, 7, .6, col=(.1, .1, .1), top="painted")                 # marquise
    for sd in (-1, 1): S.cyl("metal", sd * bw * .3, v0 - 7, 0, 5.2, .18, 8)
    S.box("sign", 0, v0 - .25, 9.6, bw * .5, .4, 2.2, top="sign")                                  # enseigne
    S.box("signred", bw * .38, v0 - 1.4, 3, 1.2, 2.6, 17, top="signred")                           # enseigne verticale
    for k in range(6): S.box("sign", -bw * .44 + k * 3.2 if k < 3 else bw * .15 + (k - 3) * 3.2, v0 - .12, 1.2, 2.2, .15, 3.2, top="sign")   # affiches
    for sd in (-1, 1): S.box("painted", sd * bw * .2, bv + 4, 17, bw * .3, bd * .5, 3, col=(.2, .2, .22), top="roof")  # salles hautes
    roof_clutter(*S.P(0, bv + 4), S.rot, bw * .35, bd * .5, S.z0 + 17.2, "std")
    S.box("white", -W * .3, v0 - 5, 0, 3, 2, 2.6, top="roof")                                        # billetterie
    return 20

def lm_bibliotheque(S):
    W, D = S.W, S.D; fc = 10
    forecourt(S, fc, trees=False)
    for k in range(6): S.tree(-W / 2 + 4 + k * (W - 8) / 5, -D / 2 + 3, .8)
    v0 = -D / 2 + fc
    # trois volumes vitrés empilés et décalés (porte-à-faux), toit-jardin sur le dernier
    vols = [(0, v0 + 14, W * .82, 26, 0, 8), (-W * .08, v0 + 17, W * .7, 24, 8, 7), (W * .1, v0 + 20, W * .56, 22, 15, 7)]
    for (u, v, w, d, z_, h_) in vols:
        gridded(*S.P(u, v), S.rot, w, d, S.z0 + z_, h_, 3.5, 2.2, STYLES["glass" if z_ else "office"])
    for (u, v, w, d, z_, h_) in vols:
        for k in range(int(w / 1.2)):
            S.box("wood", u - w / 2 + .6 + k * 1.2, v - d / 2 - .45, z_ + .1, .18, .7, h_ - .3, top="wood")
    tu, tv, tw, td, tz, th = vols[-1]
    S.flat("grass", tu, tv, tz + th + .02, tw - 2, td - 2, h=.2)
    for k in range(6): S.tree(tu - tw / 2 + 4 + k * (tw - 8) / 5, tv + R.uniform(-td / 3, td / 3), .55)
    S.box("concrete", 0, v0 - 1, 3.6, 14, 4, .4, top="concrete")                                   # auvent d'entrée
    S.box("sign", 0, v0 + .8, 4.3, 12, .3, 1, top="sign")
    # jardin de lecture à l'arrière
    for k in range(5): S.tree(-W / 2 + 5 + k * (W - 10) / 4, D / 2 - 4, .9)
    for k in range(4): S.bench(-W * .3 + k * W * .2, D / 2 - 7, math.pi)
    for k in range(8): S.box("metal", W * .32 + k * .8, v0 - 3, 0, .08, 1.6, .8, col=(.2, .2, .22))   # arceaux vélos
    return 24

def lm_hotel_de_ville(S, small=False):
    W, D = S.W, S.D; fc = 12 if not small else 9
    h1 = 15 if not small else 11
    S.flat("plaza", 0, 0, .004, W - .5, D - .5, h=.02)
    wing = 12 if not small else 10
    back_v = D / 2 - wing / 2 - 2
    # corps principal au fond, deux ailes en avant : la cour d'honneur au milieu
    S.classic(0, back_v, W - 4, wing, h1, fh=4.6 if not small else 3.8, bay=3.1)
    S.mansard(0, back_v, h1 + 1.6, W - 4.4, wing - .4, 6 if not small else 4.5)
    wl = D - wing - fc - 2
    for sd in (-1, 1):
        wu = sd * (W / 2 - wing / 2 - 2)
        S.classic(wu, back_v - wing / 2 - wl / 2 - .4, wing, wl - .8, h1 - 1, fh=4.6 if not small else 3.8, bay=3.1, balustrade=False)
        S.mansard(wu, back_v - wing / 2 - wl / 2 - .4, h1 - .2, wl - 1.2, wing - .4, 5 if not small else 4, r=math.pi / 2)
        S.classic(wu, -D / 2 + fc + 2.8, wing + 1.8, 5.6, h1 + 2, fh=4.6 if not small else 3.8, bay=3.1, balustrade=False)   # pavillons de tête
        S.hip(wu, -D / 2 + fc + 2.8, h1 + 2.75, wing + 2.4, 6.2, 3.5, (.5, .5, .5), mat="ardoise")
    # avant-corps central : colonnes, fronton, horloge, beffroi, campanile
    bv = back_v - wing / 2 - 2
    S.classic(0, bv + 1, 15, 5, h1 + 3, fh=4.6 if not small else 3.8, bay=3.1, balustrade=False)
    S.columns(-6, 6, bv - 2, 6, .2, h1 - 1, .5)
    S.pediment(0, bv - 1.8, 15, h1 + 3.75, 3.8, 4.5, STONE)
    S.box("pierre", 0, back_v, h1 + .75, 8.5, 8.5, 9, col=STONE, top="pierre")
    ck = S.P(0, back_v - 4.3)
    A.cyl("white", ck[0], ck[1], S.z0 + h1 + 5.2, .05, 1.7, 24); A.cyl("or", ck[0], ck[1], S.z0 + h1 + 5.25, .05, .25, 8)
    S.box("pierre", 0, back_v, h1 + 9.75, 5.6, 5.6, .6, col=STONE2, top="pierre")
    for a in range(4): 
        for b_ in range(2): S.cyl("pierre", -2.2 + b_ * 4.4, back_v - 2.2 + a * 4.4 / 3, h1 + 10.35, 3.2, .22, 6, col=STONE)
    S.rib_dome(0, back_v, h1 + 14.2, 3, 4, ribs=8)
    # cour d'honneur : parterres de broderie, fontaine, mâts et drapeaux, grille dorée sur la rue
    cv = (-D / 2 + fc + bv - 2) / 2
    for sd in (-1, 1):
        pu = sd * (W / 2 - wing - 8); pd = (bv - 2 - (-D / 2 + fc)) * .6
        S.box("pierre", pu, cv, 0, 7.4, pd + .4, .15, col=STONE2, top="grass")
        for k in range(3): S.box("painted", pu, cv - pd / 3 + k * pd / 3, .15, 5, .5, .5, col=(.06, .16, .05))
    S.cyl("pierre", 0, cv, 0, .5, 3.6, 28, col=STONE2); S.cyl("water", 0, cv, 0, .55, 3.1, 28); S.cyl("pierre", 0, cv, .55, 1.4, .5, 10, col=STONE); S.cyl("or", 0, cv, 1.95, .8, .3, 8)
    for k, colf in enumerate(((.1, .2, .6), (.9, .9, .9), (.75, .1, .1), (.12, .25, .55))):
        uu = -6 + k * 4; S.cyl("metal", uu, -D / 2 + fc - 1, 0, 10, .08, 6); S.box("painted", uu + .9, -D / 2 + fc - 1, 8.4, 1.8, .05, 1.2, col=colf)
    for sd in (-1, 1):
        S.box("dark", sd * (W / 4 + 2.5), -D / 2 + fc, 0, W / 2 - 9, .12, 2, col=(.06, .06, .06))
        for k in range(int((W / 2 - 9) / 1.5)): S.box("or", sd * (9 + k * 1.5), -D / 2 + fc - .05, 2, .12, .15, .35)
        S.box("pierre", sd * 4.5, -D / 2 + fc, 0, 1.2, 1.2, 3.2, col=STONE, top="pierre"); S.box("or", sd * 4.5, -D / 2 + fc, 3.2, .6, .6, .8)
    forecourt(S, fc - 1, trees=True)
    return h1 + 18

def lm_eglise(S):
    W, D = S.W, S.D
    S.flat("grass", 0, 0, .002, W - 1, D - 1, h=.02)                                              # l'enclos : pelouse
    S.flat("plaza", 0, -D / 2 + 6, .03, W * .6, 12, h=.02)
    nw, nl = min(15, W * .26), D * .64
    nv = -D / 2 + 12 + nl / 2
    S.flat("path", 0, nv, .05, nw + 16, nl + 6, h=.02)
    S.box("pierre", 0, nv, 0, nw, nl, 15, col=STONE2, top="pierre")
    S.gable("ardoise", 0, nv, 15, nl, nw, 7, (.5, .5, .5), r=math.pi / 2, over=.4)
    A.gable_ends("pierre", *S.P(0, nv), S.z0 + 15, nl, nw, 7, S.rot + math.pi / 2, STONE2)
    for sd in (-1, 1):                                                                            # bas-côtés, contreforts, arcs-boutants
        S.box("pierre", sd * (nw / 2 + 2.6), nv, 0, 5, nl - 6, 8, col=STONE2, top="pierre")
        S.gable("ardoise", sd * (nw / 2 + 2.6), nv, 8, nl - 6, 5, 1.6, (.5, .5, .5), r=math.pi / 2)
        for k in range(7):
            vk = nv - nl / 2 + 5 + k * (nl - 10) / 6
            S.box("pierre", sd * (nw / 2 + 5.5), vk, 0, 1.2, 1.6, 10, col=STONE, top="pierre")
            S.cyl("pierre", sd * (nw / 2 + 5.5), vk, 10, 1.8, .5, 4, col=STONE, r2=.05)             # pinacles
            S.box("pierre", sd * (nw / 2 + 3), vk, 11.5, 5, .5, .5, col=STONE, r=0)                 # arc-boutant
    tv = nv + nl * .12                                                                            # transept, pignon et rosace
    S.box("pierre", 0, tv, 0, nw * 2.4, 11, 14, col=STONE2, top="pierre")
    S.gable("ardoise", 0, tv, 14, nw * 2.4, 11, 6.2, (.5, .5, .5), over=.4)
    A.gable_ends("pierre", *S.P(0, tv), S.z0 + 14, nw * 2.4, 11, 6.2, S.rot, STONE2)
    S.cyl("pierre", 0, tv, 20, 5, .8, 8, col=STONE); S.cyl("ardoise", 0, tv, 25, 6, .9, 8, r2=.05)      # flèche de la croisée
    S.cyl("pierre", 0, nv + nl / 2, 0, 13, nw / 2, 24, col=STONE2)                                    # abside
    S.cyl("ardoise", 0, nv + nl / 2, 13, 5, nw / 2 + .4, 24, r2=.1)
    # façade : clocher-porche, portail, flèche en ardoise, clochetons, horloge
    fv = nv - nl / 2 - 3
    S.box("pierre", 0, fv, 0, 9, 7.5, 27, col=STONE, top="pierre")
    for a in (-1, 1):
        for b in (-1, 1): S.box("pierre", a * 4.7, fv + b * 3.9, 0, 1.4, 1.4, 24, col=STONE2, top="pierre")
    S.box("dark", 0, fv - 3.8, 0, 3, .12, 5.2, col=(.05, .05, .05))                                  # portail
    S.box("pierre", 0, fv - 3.9, 5.2, 4, .3, 1.2, col=STONE2)
    for k in (-1, 1): S.box("dark", k * 2.2, fv - 3.8, 18, 1, .1, 4.5, col=(.05, .05, .05))           # abat-sons
    A.box("white", *S.P(0, fv - 3.8), S.z0 + 12.5, 2.2, .06, 2.2, S.rot)                               # horloge
    S.cyl("ardoise", 0, fv, 27, 18, 5.4, 8, r2=.05)
    for a in (-1, 1):
        for b in (-1, 1): S.cyl("ardoise", a * 4.2, fv + b * 3.4, 27, 4, .8, 6, r2=.05)
    S.cyl("or", 0, fv, 45, 2.6, .1, 4)
    # enclos paroissial : arbres, allées, petit cimetière au fond
    for k in range(5): S.tree(-W / 2 + 4, -D / 2 + 8 + k * (D - 12) / 4, .9); S.tree(W / 2 - 4, -D / 2 + 8 + k * (D - 12) / 4, .9)
    for i in range(6):
        for j in range(3):
            S.box("pierre", W * .28 + (i - 2.5) * 2.2 * (1 if W > 60 else .7), D / 2 - 5 - j * 2.6, 0, .9, .3, 1 + R.uniform(0, .5), col=(.7, .7, .68))
    for sd in (-1, 1): S.bench(sd * 6, -D / 2 + 4, 0)
    return 44

def lm_ecole(S):
    W, D = S.W, S.D
    colw = R.choice([(.85, .62, .4), (.72, .78, .8), (.9, .82, .6)])
    wing = 12; h = 10.2
    for k_, (u, v, w, d) in enumerate(((0, -D / 2 + wing / 2 + 2, W - 4, wing), (-W / 2 + wing / 2 + 2, 0, wing, D - 4), (W / 2 - wing / 2 - 2, -D / 4, wing, D / 2))):
        S.box("facade", u, v, 0, w, d, h + .07 * k_, col=colw, top="roof", fh=3.4, bay=3.0)
        S.box("wall", u, v, h + .07 * k_ - .1, w + .3, d + .3, .6, col=tuple(c * .85 for c in colw), top="roof")
    S.box("solar", 0, -D / 2 + wing / 2 + 2, h + .6, W * .6, wing * .6, .12, top="solar", sides=False)
    for k in range(4): S.box("painted", -W * .3 + k * W * .2, -D / 2 + 1.7, 3.4, 3.4, .12, 1.2, col=((.8, .2, .1), (.1, .4, .8), (.9, .7, .1), (.2, .6, .3))[k])   # panneaux colorés
    # cour de récréation : enrobé, marquages, préau, arbres, jeux
    cu0, cu1, cv0, cv1 = -W / 2 + wing + 3, W / 2 - 2, -D / 2 + wing + 3, D / 2 - 2
    S.flat("asphalt", (cu0 + cu1) / 2, (cv0 + cv1) / 2, .005, cu1 - cu0, cv1 - cv0, col=(.3, .3, .3), h=.03)
    bu, bv = (cu0 + cu1) / 2 - 4, (cv0 + cv1) / 2 + 2
    S.box("pitch", bu, bv, .04, 26, 14, .01, top="pitch", sides=False)
    S.flat("paint_w", bu, bv, .06, .15, 14, h=.005)
    for sd in (-1, 1): S.cyl("metal", bu + sd * 12.5, bv, 0, 3, .08, 6); S.box("white", bu + sd * 12.3, bv, 2.8, .1, 1.6, 1, top="white")
    S.box("roof", cu0 + 6, cv1 - 5, 3.3, 11, 8, .25, col=(.3, .35, .4))                           # préau
    for a in (-1, 1):
        for b in (-1, 1): S.cyl("metal", cu0 + 6 + a * 5, cv1 - 5 + b * 3.5, 0, 3.3, .12, 6)
    for k in range(4): S.tree(cu1 - 3, cv0 + 4 + k * (cv1 - cv0 - 8) / 3, .85)
    S.box("sand", cu1 - 12, cv1 - 5, .04, 9, 6, .08, top="sand", sides=False)
    for k in range(4): S.box("painted", cu1 - 15 + k * 2.2, cv1 - 5 + R.uniform(-1.5, 1.5), .1, 1.2, 1.2, R.uniform(.8, 2), col=R.choice([(.8, .2, .1), (.1, .4, .8), (.9, .7, .1)]))
    for sd in (-1, 1): S.box("dark", sd * (W / 2 - .3), 0, 0, .1, D - 2, 1.8, col=(.1, .3, .15))    # grillage
    return 12

def lm_clinique(S):
    W, D = S.W, S.D
    # parking visiteurs devant, bâtiment en H au fond, urgences sur le côté, hélistation sur le toit
    pd = D * .34
    S.parking(-W / 2 + 2, W / 2 - 16, -D / 2 + 1, -D / 2 + pd, fill=.8)
    bw, bd = W - 6, D - pd - 4; bv = -D / 2 + pd + 2 + bd / 2; t = 12
    for k_, (u, v, w, d) in enumerate(((-bw / 2 + t / 2, bv, t, bd), (bw / 2 - t / 2, bv, t, bd), (0, bv, bw - 2 * t + .2, t))):
        h = 22 if k_ < 2 else 25
        gridded(*S.P(u, v), S.rot + (0 if k_ < 2 else 0), w, d, S.z0, h, 3.6, 2.4, STYLES["stucco"])
        S.box("wall", u, v, h - .2, w + .4, d + .4, .8, col=(.8, .8, .78), top="roof")
    S.cyl("concrete", 0, bv, 25.6, .3, 5.4, 24); S.flat("signred", 0, bv, 25.92, 5, 1.2, h=.02); S.flat("signred", 0, bv, 25.92, 1.2, 5, h=.02)
    S.box("white", W / 2 - 8, -D / 2 + pd * .55, 3.6, 12, 9, .4, top="white")                        # auvent des urgences
    for a in (-1, 1): S.cyl("metal", W / 2 - 8 + a * 5.5, -D / 2 + pd * .55 - 4, 0, 3.6, .15, 6)
    S.box("signred", W / 2 - 8, -D / 2 + pd * .55 - 4.55, 4.05, 8, .2, .9, top="signred")
    for k in range(2): car_at(*S.P(W / 2 - 10 + k * 4, -D / 2 + pd * .55), S.rot + math.pi / 2, parked=True)
    for k in range(4): S.tree(-W / 2 + 4 + k * 6, bv, .8)
    return 28

def lm_gymnase(S):
    W, D = S.W, S.D
    hw, hd = W * .55, D - 6; hu = -W / 2 + hw / 2 + 2
    S.box("facade", hu, 0, 0, hw, hd, 9, col=(.55, .62, .7), top=None, fh=9, bay=5)
    for k in range(12):                                                                            # toit en berceau
        t = -hw / 2 + (k + .5) * hw / 12
        S.box("roof", hu + t, 0, 9, hw / 12 + .05, hd + .4, .5 + 3.2 * math.sin(math.pi * (k + .5) / 12), col=(.6, .64, .66))
    S.box("glass", hu, -hd / 2 - .3, 0, hw * .5, .6, 6, col=(.2, .3, .35), top="glass")
    S.box("sign", hu, -hd / 2 - .7, 6.5, hw * .4, .2, 1, top="sign")
    # terrains extérieurs : tennis, basket, et un petit parking
    ou0 = hu + hw / 2 + 3; ou1 = W / 2 - 2
    for k, colc in enumerate(((.2, .35, .55), (.55, .25, .15))):
        cv = -D / 4 + k * D / 2 - (2 if k == 0 else -2); cw = min(ou1 - ou0, 24)
        S.flat("painted", (ou0 + ou1) / 2, cv, .01, ou1 - ou0, D / 2 - 5, col=colc, h=.04)
        S.flat("paint_w", (ou0 + ou1) / 2, cv, .06, cw * .8, .1, h=.005); S.flat("paint_w", (ou0 + ou1) / 2, cv, .06, .1, D / 2 - 9, h=.005)
        for sd in (-1, 1): S.box("dark", (ou0 + ou1) / 2, cv + sd * (D / 4 - 2.5), 0, ou1 - ou0, .08, 3, col=(.1, .25, .12))   # grillage
    for k in range(5): S.tree(hu - hw / 2 + 3 + k * (hw - 6) / 4, -D / 2 + 1.5, .8)
    return 12

def lm_supermarche(S):
    W, D = S.W, S.D
    bd = D * .48; bv = D / 2 - bd / 2 - 1
    S.box("facade", 0, bv, 0, W - 4, bd, 8, col=(.86, .85, .8), top=None, fh=8, bay=6)
    S.box("roof", 0, bv, 8, W - 4, bd, .02, col=(.55, .55, .55), sides=False)
    for k in range(int((W - 12) / 8)):
        S.box("solar", -W / 2 + 8 + k * 8, bv, 8.1, 6, bd - 6, .12, top="solar", sides=False)
    S.box("glass", 0, bv - bd / 2 - .2, 0, W * .5, .4, 4.2, col=(.2, .3, .35), top="glass")
    S.box("white", 0, bv - bd / 2 - 2.5, 4.4, W - 8, 5, .4, top="white")                             # auvent
    S.box("signred", 0, bv - bd / 2 - .3, 5.6, W * .3, .5, 2, top="signred")
    # parking : places, caddies, îlots plantés
    S.parking(-W / 2 + 2, W / 2 - 2, -D / 2 + 1, bv - bd / 2 - 5.5, fill=.7)
    for k in range(3): S.box("metal", -W / 2 + 10 + k * (W - 20) / 2, bv - bd / 2 - 8, 0, 4, 2.4, 2.2, col=(.5, .52, .55), top="roof")
    # quai de livraison à l'arrière (côté droit)
    for k in range(2): inst(TRUCK, *S.P(W / 2 - 3.5, bv - 6 + k * 8), S.z0, S.rot, 1, (.9, .9, .9))
    return 10

def lm_station(S):
    W, D = S.W, S.D
    S.flat("concrete", 0, 0, .004, W - 1, D - 1, h=.03)
    cu, cv = -W * .18, -D * .12
    S.box("painted", cu, cv, 5.2, 24, 14, .9, col=(.85, .1, .08), top="white")                      # auvent des pompes
    for k in (-8, 0, 8):
        for r_ in (-3.5, 3.5): S.box("white", cu + k, cv + r_, 0, .7, 1.4, 5.2, top="white")
        car_at(*S.P(cu + k + 2, cv), S.rot, parked=True)
    S.box("sign", cu, cv - 7.1, 5.5, 10, .2, .6, top="sign")
    S.box("facade", W * .22, cv, 0, 16, 10, 4.5, col=(.9, .9, .88), top="roof", fh=4.5, bay=3)     # boutique
    S.box("signred", W * .22, cv - 5.1, 3.4, 10, .2, .9, top="signred")
    S.cyl("metal", -W / 2 + 3, -D / 2 + 3, 0, 9, .2, 6); S.box("signred", -W / 2 + 3, -D / 2 + 3, 9, 3, .4, 4, top="signred")   # totem des prix
    # lavage auto et garage au fond
    S.box("painted", -W * .25, D / 2 - 8, 0, 18, 7, 4.5, col=(.2, .45, .75), top="roof")
    S.box("facade", W * .2, D / 2 - 9, 0, 24, 14, 6, col=(.7, .72, .74), top="roof", fh=6, bay=4)
    for k in range(5): car_at(*S.P(W * .06 + k * 3, D / 2 - 18), S.rot + math.pi / 2, parked=True)
    for k in range(4): S.tree(-W / 2 + 2.5, -D / 2 + 8 + k * 7, .8)
    S.parking(W * .02, W / 2 - 1.5, -D / 2 + 1, -D / 2 + 13, fill=.6, trees=False)                # parking de la boutique
    for k in range(4): S.tree(-W * .45 + k * 4, D / 2 - 3, .8)
    return 8

LANDMARKS = {"theatre": lm_theatre, "opera": lm_opera, "musee": lm_musee, "cinema": lm_cinema, "bibliotheque": lm_bibliotheque,
             "hotel_de_ville": lm_hotel_de_ville, "mairie": lambda S: lm_hotel_de_ville(S, small=True), "eglise": lm_eglise,
             "ecole": lm_ecole, "clinique": lm_clinique, "gymnase": lm_gymnase, "supermarche": lm_supermarche, "station": lm_station}

def landmark_block(z, b, kind, pad="plaza"):
    """un bâtiment unique ou un équipement sur TOUT son îlot"""
    u0, u1, v0, v1 = b
    block_pad(z, b, pad)
    x, y = z.w((u0 + u1) / 2, (v0 + v1) / 2)
    S = Site(x, y, z.rot, u1 - u0 - 3, v1 - v0 - 3)
    for k in range(int((u1 - u0) / 11)):          # arbres de trottoir le long de l'îlot
        inst(R.choice(TREES), *z.w(u0 + 5 + k * 11, v0 + 1.4), .18, R.uniform(0, 6), .8)
    h = LANDMARKS[kind](S)
    claim(x, y, u1 - u0 - 2, v1 - v0 - 2, z.rot)
    SLOTS.append((kind, NOMS.get(kind, kind), (x, y, h * .6)))


# ═══════════════════════════════════════ usines : tout l'îlot, avec leurs équipements
def tube(p0, p1, r, mat="metal", col=(.5, .5, .5), seg=8):
    """un tube entre deux points 3D (tuyauterie, convoyeur, grume, citerne couchée)"""
    ax = [p1[i] - p0[i] for i in range(3)]; L_ = math.sqrt(sum(a * a for a in ax)) or 1
    t = [a / L_ for a in ax]
    up = (0, 0, 1) if abs(t[2]) < .9 else (1, 0, 0)
    n1 = [t[1] * up[2] - t[2] * up[1], t[2] * up[0] - t[0] * up[2], t[0] * up[1] - t[1] * up[0]]
    l1 = math.sqrt(sum(a * a for a in n1)); n1 = [a / l1 for a in n1]
    n2 = [t[1] * n1[2] - t[2] * n1[1], t[2] * n1[0] - t[0] * n1[2], t[0] * n1[1] - t[1] * n1[0]]
    ring = lambda p, k: tuple(p[i] + r * (math.cos(2 * math.pi * k / seg) * n1[i] + math.sin(2 * math.pi * k / seg) * n2[i]) for i in range(3))
    for k in range(seg):
        A.face(mat, [ring(p0, k), ring(p0, k + 1), ring(p1, k + 1), ring(p1, k)], None, col)

def S_tube(S, u0, v0, z0, u1, v1, z1, r, mat="metal", col=(.5, .5, .5), seg=8):
    a, b = S.P(u0, v0), S.P(u1, v1)
    tube((a[0], a[1], S.z0 + z0), (b[0], b[1], S.z0 + z1), r, mat, col, seg)

PIPE_COLS = [(.55, .56, .58), (.75, .6, .1), (.15, .3, .55), (.6, .15, .1), (.2, .45, .25), (.85, .85, .82)]

def pipe_rack(S, u0, v0, u1, v1, levels=(5, 7.5), npipes=5, width=4.):
    """rack à tuyauteries : portiques en acier tous les 6 m, poutres, tuyaux de couleurs"""
    L_ = math.hypot(u1 - u0, v1 - v0); du, dv = (u1 - u0) / L_, (v1 - v0) / L_; nu, nv = -dv, du
    r_ = math.atan2(dv, du)
    for k in range(int(L_ / 6) + 1):
        cu, cv = u0 + du * k * 6, v0 + dv * k * 6
        for sd in (-1, 1): S.box("metal", cu + nu * sd * width / 2, cv + nv * sd * width / 2, 0, .35, .35, levels[-1] + .3, col=(.4, .42, .45), r=r_)
        for z_ in levels: S.box("metal", cu, cv, z_, .3, width + .4, .3, col=(.4, .42, .45), r=r_)
    for i, z_ in enumerate(levels):
        for p in range(npipes):
            o = -width / 2 + .5 + p * (width - 1) / max(1, npipes - 1)
            S_tube(S, u0 + nu * o, v0 + nv * o, z_ + .55, u1 + nu * o, v1 + nv * o, z_ + .55, .22 + .08 * (p % 2), "metalattr", PIPE_COLS[(p + i) % len(PIPE_COLS)], 6)

def tank(S, u, v, r, h, col=(.85, .85, .83), roof="cone", bund=True):
    """cuve verticale : robe, toit conique ou flottant, garde-corps, escalier hélicoïdal, cuvette de rétention"""
    S.cyl("metalattr", u, v, 0, h, r, 32, col=col, top=(roof != "cone"))
    for k in range(int(h / 2.4)): S.cyl("metalattr", u, v, k * 2.4 + 2.3, .12, r + .04, 32, col=tuple(c_ * .9 for c_ in col), top=False)   # viroles
    if roof == "cone": S.cyl("metalattr", u, v, h, r * .18, r, 32, r2=.6, col=col)
    S.cyl("metal", u, v, h + (r * .18 if roof == "cone" else 0), .9, r + .05, 32, col=(.3, .3, .32), top=False)          # garde-corps
    for k in range(10):                                                                                                 # escalier
        a = k / 10 * math.pi * .9; zz = h * k / 10
        x_, y_ = S.P(u + math.cos(a) * (r + .5), v + math.sin(a) * (r + .5))
        A.box("metal", x_, y_, S.z0 + zz, 1.8, .9, .15, S.rot + a + math.pi / 2, col=(.35, .35, .37))
    if bund:
        for sd in (-1, 1):
            S.box("concrete", u + sd * (r + 3), v, 0, .4, 2 * r + 6.4, 1.2, top="concrete")
            S.box("concrete", u, v + sd * (r + 3), 0, 2 * r + 6, .4, 1.2, top="concrete")

def column(S, u, v, r, h, col=(.8, .8, .78)):
    """colonne de distillation : fût, plateformes annulaires, échelle, calotte"""
    S.cyl("metalattr", u, v, 0, h, r, 20, col=col, top=False)
    S.dome("metalattr", u, v, h, r, r * .6, 20, 4, col=col)
    for z_ in range(6, int(h), 7):
        S.cyl("metal", u, v, z_, .15, r + 1.3, 20, col=(.35, .35, .37))
        S.cyl("metal", u, v, z_ + .15, 1, r + 1.3, 20, col=(.35, .35, .37), top=False)
    S.box("metal", u + r + .4, v, 0, .5, .3, h, col=(.3, .3, .32))

def sphere(S, u, v, r):
    zc = r + 2.5
    S.dome("metalattr", u, v, zc, r, r, 24, 6, col=(.88, .88, .86)); S.dome("metalattr", u, v, zc, r, -r, 24, 6, col=(.88, .88, .86))
    for k in range(8):
        a = k / 8 * 6.283; S.cyl("metal", u + math.cos(a) * r * .8, v + math.sin(a) * r * .8, 0, zc, .25, 6)
    S.cyl("metal", u, v, zc - .1, .8, r + .05, 24, col=(.3, .3, .32), top=False)

def stack(S, u, v, h, r0=2.2, bands=True):
    """cheminée : fût conique, bandes rouges et blanches en haut, plateforme, échelle"""
    n = 8
    for k in range(n):
        rr0 = r0 * (1 - .35 * k / n); rr1 = r0 * (1 - .35 * (k + 1) / n)
        top_band = k >= n - 3
        S.cyl("painted", u, v, h * k / n, h / n, rr0, 20, r2=rr1, top=False,
              col=((.8, .12, .08) if k % 2 else (.9, .9, .88)) if (bands and top_band) else (.62, .6, .58))
    S.cyl("dark", u, v, h - .05, .1, r0 * .6, 20)
    S.cyl("metal", u, v, h * .72, .15, r0 + 1.1, 20, col=(.3, .3, .32)); S.cyl("metal", u, v, h * .72 + .15, 1, r0 + 1.1, 20, top=False, col=(.3, .3, .32))
    S.box("metal", u + r0 * .85, v, 0, .35, .3, h * .75, col=(.3, .3, .32))

def cooling_tower(S, u, v, R0, h):
    """tour aéroréfrigérante hyperboloïde"""
    n = 12; zt = h * .72
    rad = lambda z_: R0 * .8 * math.sqrt(1 + ((z_ - zt) / (h * .6)) ** 2)
    for k in range(n):
        z0, z1 = h * k / n, h * (k + 1) / n
        S.cyl("concrete", u, v, z0, z1 - z0, rad(z0), 40, r2=rad(z1), top=False)
    for k in range(20):   # pieds en V à la base
        a = k / 20 * 6.283; S.box("concrete", u + math.cos(a) * rad(0), v + math.sin(a) * rad(0), 0, .6, .6, 3, r=a)
    S.cyl("water", u, v, .4, .05, rad(0) - .3, 40)
    S.cyl("dark", u, v, h * .55, .05, rad(h * .55) - .2, 40)       # l'intérieur sombre vu d'en haut

def sawtooth(S, u, v, w, d, h, n, col):
    """halle à toit en sheds : murs, dents de scie vitrées tournées vers la caméra"""
    S.box("facade", u, v, 0, w, d, h, col=col, top=None, fh=h / 2, bay=6)
    dt = d / n; ht = 3.2
    for k in range(n):
        va = v - d / 2 + k * dt; vb = va + dt
        a0, a1 = u - w / 2, u + w / 2
        S.face("glass", [(a0, va, h), (a1, va, h), (a1, va, h + ht), (a0, va, h + ht)], (.35, .45, .5))
        S.face("roof", [(a0, va, h + ht), (a1, va, h + ht), (a1, vb, h), (a0, vb, h)], (.55, .56, .57))
        for uu in (a0, a1): S.face("wall", [(uu, va, h), (uu, vb, h), (uu, va, h + ht)], col)
        for kk in range(int(w / 5)): S.box("metal", a0 + 2.5 + kk * 5, va + .1, h, .15, .25, ht, col=(.3, .3, .32))

def containers(S, u0, v0, n, rot=0.):
    for k in range(n):
        cu, cv = u0 + (k % 4) * 12.6, v0 + (k // 4) * 2.7
        for st in range(R.randint(1, 3)):
            colc = R.choice([(.6, .12, .08), (.1, .25, .5), (.1, .4, .25), (.8, .55, .1), (.5, .5, .52), (.85, .85, .82)])
            S.box("painted", cu, cv, st * 2.62, 12.2, 2.45, 2.6, col=colc, r=rot)
            for rb in range(6): S.box("painted", cu - 5.4 + rb * 2.16, cv - 1.24, st * 2.62 + .1, .12, .06, 2.4, col=tuple(c_ * .8 for c_ in colc), r=rot)

def fence(S, gate_u=0.):
    """clôture grillagée autour du site, portail et loge de gardien sur la rue sud"""
    W, D = S.W, S.D; colf = (.12, .25, .14)
    for sd in (-1, 1):
        S.box("dark", sd * (W / 2 - .3), 0, 0, .08, D - .6, 2.2, col=colf)
    S.box("dark", 0, D / 2 - .3, 0, W - .6, .08, 2.2, col=colf)
    for a_, b_ in ((-W / 2 + .3, gate_u - 5), (gate_u + 5, W / 2 - .3)):
        S.box("dark", (a_ + b_) / 2, -D / 2 + .3, 0, b_ - a_, .08, 2.2, col=colf)
    S.box("facade", gate_u + 7.5, -D / 2 + 3, 0, 4, 3, 3, col=(.85, .85, .82), top="roof", fh=3, bay=2)
    S.box("painted", gate_u, -D / 2 + .6, .9, 9, .15, .15, col=(.85, .1, .08))

def parking_lot(S, u0, u1, v0, v1): S.parking(u0, u1, v0, v1, fill=.65, trees=False)

def ind_usine(S):
    """usine de fabrication : bureaux vitrés, grande halle en sheds, quais, chaufferie et cheminée, rack, parking"""
    W, D = S.W, S.D
    ow = min(34, W * .32)
    gridded(*S.P(-W / 2 + ow / 2 + 3, -D / 2 + 11), S.rot, ow, 13, S.z0, 11.5, 3.8, 2.4, STYLES["glass"])
    S.box("wall", -W / 2 + ow / 2 + 3, -D / 2 + 11, 11.3, ow + .4, 13.4, .6, col=(.5, .52, .55), top="roof")
    S.box("sign", -W / 2 + ow / 2 + 3, -D / 2 + 4.4, 8.8, ow * .6, .2, 1.4, top="sign")
    hw, hd = W * .62, D * .58; hu, hv = W / 2 - hw / 2 - 3, D / 2 - hd / 2 - 3
    sawtooth(S, hu, hv, hw, hd, 10, int(hd / 7), R.choice([(.55, .6, .66), (.66, .64, .6), (.5, .55, .5)]))
    for k in range(int(hw / 5.5)):                                             # quais de chargement (façade sud de la halle)
        du = hu - hw / 2 + 3 + k * 5.5
        S.box("dark", du, hv - hd / 2 - .15, .9, 3.4, .3, 3.8, col=(.08, .08, .08))
        S.box("painted", du, hv - hd / 2 - .3, 4.9, 4.4, .4, .2, col=(.85, .65, .1))
        if R.random() < .55: inst(TRUCK, *S.P(du, hv - hd / 2 - 9.5), S.z0, S.rot + math.pi / 2, 1, R.choice([(.9, .9, .9), (.1, .2, .5), (.7, .1, .08)]))
    S.flat("asphalt", hu, hv - hd / 2 - 9, .01, hw, 17, h=.03)
    bu, bv = -W / 2 + 12, D / 2 - 14                                          # chaufferie + cheminée + cuves
    S.box("facade", bu, bv, 0, 16, 14, 13, col=(.5, .35, .25), top="roof", fh=4.3, bay=3)
    roof_clutter(*S.P(bu, bv), S.rot, 15, 13, S.z0 + 13, "std")
    stack(S, bu + 5, bv + 9, 34, 1.8)
    tank(S, bu - 5, bv - 13, 3.5, 8, (.3, .45, .6), bund=False); tank(S, bu + 4, bv - 13, 3.5, 8, (.3, .45, .6), bund=False)
    pipe_rack(S, bu + 9, bv, hu - hw / 2, bv, levels=(5,), npipes=4)
    roof_clutter(*S.P(hu, hv), S.rot, hw - 4, hd - 4, S.z0 + 13.3, "logi")
    parking_lot(S, -W / 2 + 3, -W / 2 + ow + 3, -D / 2 + 20, -D / 2 + 20 + min(22, D * .25))
    containers(S, W / 2 - 52, -D / 2 + 3.5, 8)
    fence(S, gate_u=W * .05)
    SLOTS.append(("usine", NOMS["usine"], (*S.P(hu, hv), 14)))
    return 14

def ind_chimie(S):
    """site chimique : parc de cuves en cuvettes, colonnes de distillation, sphères, racks, torchère, salle de contrôle"""
    W, D = S.W, S.D
    for i in range(3):
        for j in range(2):
            tank(S, -W / 2 + 12 + i * 17, D / 2 - 12 - j * 17, R.uniform(5, 6.5), R.uniform(9, 13), R.choice([(.86, .86, .84), (.82, .84, .86)]))
    for k, (du, h) in enumerate(((0, 38), (7, 30), (13, 44), (19, 26))):
        column(S, W * .05 + du, D * .1, 1.6 + .3 * (k % 2), h)
    S.box("metal", W * .05 + 9, D * .1 - 5, 0, 24, 6, .3, col=(.35, .35, .37))           # structure d'échangeurs
    for lv in (6, 12, 18):
        S.box("metal", W * .05 + 9, D * .1 - 5, lv, 24, 6, .25, col=(.35, .35, .37))
        for c in range(5): S.box("metal", W * .05 - 3 + c * 6, D * .1 - 8, 0, .3, .3, 18, col=(.35, .35, .37))
    sphere(S, W / 2 - 12, D / 2 - 12, 6); sphere(S, W / 2 - 12, D / 2 - 28, 6)
    pipe_rack(S, -W / 2 + 6, -D * .08, W / 2 - 6, -D * .08, levels=(5, 8), npipes=6, width=5)
    pipe_rack(S, W * .2, -D * .08, W * .2, D / 2 - 8, levels=(5, 8), npipes=4)
    S.cyl("metal", W / 2 - 6, -D / 2 + 10, 0, 45, .5, 8); S.cyl("painted", W / 2 - 6, -D / 2 + 10, 45, 1.2, .8, 8, col=(.85, .1, .08))   # torchère
    gridded(*S.P(-W * .25, -D / 2 + 9), S.rot, 24, 11, S.z0, 7.6, 3.8, 2.4, STYLES["office"])
    S.box("wall", -W * .25, -D / 2 + 9, 7.4, 24.4, 11.4, .5, col=(.5, .5, .5), top="roof")
    parking_lot(S, -W / 2 + 3, -W * .25 - 14, -D / 2 + 2, -D / 2 + 16)
    for k in range(4): inst(TRUCK, *S.P(W * .02 + k * 5, -D / 2 + 8), S.z0, S.rot + math.pi / 2, 1, (.85, .85, .85))
    fence(S, gate_u=W * .1)
    SLOTS.append(("usine", NOMS["usine"], (*S.P(W * .05, D * .1), 30)))
    return 30

def ind_agro(S):
    """usine agroalimentaire : batterie de silos avec galerie, tour d'élévation, convoyeur, hall de conditionnement"""
    W, D = S.W, S.D
    su0, sv0, rs = -W / 2 + 10, D / 2 - 22, 4.6
    for i in range(5):
        for j in range(2):
            S.cyl("concrete", su0 + i * 9.4, sv0 + j * 9.4, 0, 30, rs, 28, col=(.8, .78, .74))
    S.box("wall", su0 + 18.8, sv0 + 4.7, 30, 42, 5, 3.5, col=(.72, .7, .66), top="roof")               # galerie au-dessus
    S.box("wall", su0 + 44, sv0 + 4.7, 0, 8, 8, 42, col=(.7, .68, .64), top="roof")                   # tour d'élévation
    S.box("wall", su0 + 44, sv0 + 4.7, 42, 5, 5, 3, col=(.6, .58, .55), top="roof")
    S_tube(S, su0 + 44, sv0 + .5, 36, su0 + 62, -D / 2 + 22, 5, .9, "metalattr", (.7, .7, .68), 4)   # convoyeur incliné
    S.box("facade", su0 + 64, -D / 2 + 20, 0, 18, 14, 8, col=(.75, .72, .66), top="roof", fh=8, bay=5)   # fosse de réception
    for k in range(3): inst(TRUCK, *S.P(su0 + 58 + k * 6, -D / 2 + 8), S.z0, S.rot + math.pi / 2, 1, R.choice([(.8, .6, .1), (.9, .9, .9)]))
    hw, hd = W * .42, D * .38
    S.box("facade", -W / 2 + hw / 2 + 4, -D / 2 + hd / 2 + 4, 0, hw, hd, 12, col=(.86, .86, .84), top=None, fh=12, bay=6)
    S.gable("roof", -W / 2 + hw / 2 + 4, -D / 2 + hd / 2 + 4, 12, hw, hd, 3, (.6, .62, .64), over=.3)
    A.gable_ends("wall", *S.P(-W / 2 + hw / 2 + 4, -D / 2 + hd / 2 + 4), S.z0 + 12, hw, hd, 3, S.rot, (.86, .86, .84))
    S.box("sign", -W / 2 + hw / 2 + 4, -D / 2 + 3.8, 9, hw * .5, .2, 1.6, top="sign")
    tank(S, W / 2 - 10, -D / 2 + 30, 3.2, 12, (.9, .9, .9), roof="flat", bund=False); tank(S, W / 2 - 18, -D / 2 + 30, 3.2, 12, (.9, .9, .9), roof="flat", bund=False)
    pipe_rack(S, -W / 2 + hw + 4, -D / 2 + 24, W / 2 - 22, -D / 2 + 24, levels=(5,), npipes=3)
    fence(S, gate_u=W * .15)
    return 30

def ind_centrale(S):
    """centrale thermique : salle des machines, chaudière, cheminée, deux aéroréfrigérants, poste électrique"""
    W, D = S.W, S.D
    tw, td = W * .45, 18
    S.box("facade", -W / 2 + tw / 2 + 4, -D / 2 + td / 2 + 5, 0, tw, td, 20, col=(.62, .66, .7), top=None, fh=5, bay=4)   # salle des machines
    S.gable("roof", -W / 2 + tw / 2 + 4, -D / 2 + td / 2 + 5, 20, tw, td, 2, (.55, .57, .6), over=.2)
    bu, bv = -W / 2 + tw * .3 + 4, -D / 2 + td + 14
    S.box("facade", bu, bv, 0, 20, 16, 40, col=(.5, .45, .4), top="roof", fh=5, bay=4)        # chaudière
    roof_clutter(*S.P(bu, bv), S.rot, 19, 15, S.z0 + 40, "std")
    stack(S, bu + 15, bv + 2, 72, 3.2)
    R0 = min(D * .17, 14.)                                  # rayon au col ; à la base ≈ 1,2 × R0
    cooling_tower(S, W / 2 - R0 * 1.25 - 3, D / 2 - R0 * 1.25 - 3, R0, 40)
    cooling_tower(S, W / 2 - R0 * 1.25 - 3, -D / 2 + R0 * 1.25 + 3, R0 * .95, 38)
    yu, yv = -W * .03, -D / 2 + 14                                                             # poste électrique
    S.flat("sand", yu, yv, .01, 30, 18, h=.05)
    for i in range(4):
        for j in range(2):
            S.box("painted", yu - 11 + i * 7, yv - 3 + j * 7, 0, 3, 2.2, 3, col=(.42, .45, .4), top="painted")
            S.cyl("white", yu - 11 + i * 7, yv - 3 + j * 7, 3, 1.6, .25, 6)
    for i in range(5):
        for sd in (-1, 1): S.box("metal", yu - 14 + i * 7, yv + sd * 8, 0, .3, .3, 12, col=(.45, .47, .5))
        S.box("metal", yu - 14 + i * 7, yv, 11.7, .3, 16.3, .3, col=(.45, .47, .5))
    S_tube(S, bu - 6, bv + 8, 18, bu - 6, D / 2 - 11, 6, 1., "metalattr", (.7, .7, .68), 4)          # convoyeur à combustible
    S.cyl("dirt", bu - 6, D / 2 - 11, 0, 6, 8, 24, r2=.5, col=(.3, .25, .2))                          # stock de biomasse
    fence(S, gate_u=W * .2)
    SLOTS.append(("centrale", "Centrale", (*S.P(bu, bv), 40)))
    return 44

def ind_metal(S):
    """aciérie / chaudronnerie : longues halles à lanterneau, parc à ferrailles sous portique roulant, bobines"""
    W, D = S.W, S.D
    for k in range(2):
        hv = D / 2 - 11 - k * 22; hw = W * .72
        S.box("facade", -W / 2 + hw / 2 + 3, hv, 0, hw, 20, 16 - k * 2, col=R.choice([(.55, .35, .25), (.5, .52, .55)]), top=None, fh=5, bay=5)
        S.gable("roof", -W / 2 + hw / 2 + 3, hv, 16 - k * 2, hw, 20, 3, (.45, .46, .48), over=.2)
        A.gable_ends("wall", *S.P(-W / 2 + hw / 2 + 3, hv), S.z0 + 16 - k * 2, hw, 20, 3, S.rot, (.5, .5, .5))
        S.box("glass", -W / 2 + hw / 2 + 3, hv, 16 - k * 2 + 2.6, hw - 4, 2.2, .9, col=(.4, .5, .55), top="glass")   # lanterneau
        for e in range(3): S.cyl("metal", -W / 2 + 12 + e * hw / 3, hv + 4, 16 - k * 2 + 2.5, 3, .6, 8)
    gu = W / 2 - 16                                                                            # portique roulant
    for sd in (-1, 1):
        S.box("painted", gu + sd * 12, -D / 2 + 22, 0, 1, 1, 14, col=(.9, .7, .1)); S.box("painted", gu + sd * 12, -D / 2 + 6, 0, 1, 1, 14, col=(.9, .7, .1))
        S.box("painted", gu + sd * 12, -D / 2 + 14, 13, 1, 17, 1.2, col=(.9, .7, .1))
    S.box("painted", gu, -D / 2 + 14, 14.2, 26, 1.6, 1.4, col=(.9, .7, .1)); S.box("painted", gu + 3, -D / 2 + 14, 12.6, 3, 2.6, 1.6, col=(.2, .2, .22))
    for k in range(10):                                                                        # poutrelles et bobines
        S.box("metal", gu - 9 + (k % 5) * 4.5, -D / 2 + 9 + (k // 5) * 8, 0, 3.2, 7, R.uniform(.6, 1.6), col=(.45, .3, .22))
    for k in range(8):
        cu, cv = -W / 2 + 10 + k * 5, -D / 2 + 10
        S_tube(S, cu, cv - 1, 1.1, cu, cv + 1, 1.1, 1.1, "metalattr", (.6, .6, .62), 12)
    containers(S, -W / 2 + 50, -D / 2 + 4, 4)
    for k in range(3): inst(TRUCK, *S.P(-W / 2 + 12 + k * 6, -D / 2 + 20), S.z0, S.rot + math.pi / 2, 1, (.2, .3, .6))
    fence(S, gate_u=0)
    return 18

def ind_scierie(S):
    """scierie : parc à grumes, hall de sciage ouvert, convoyeur, silo à copeaux, piles de bois séché"""
    W, D = S.W, S.D
    for j in range(4):                                                                         # grumes en piles
        for k in range(14):
            cu, cv = -W / 2 + 8 + k * 2.4, D / 2 - 8 - j * 7
            for st in range(3 - (k % 2)):
                S_tube(S, cu + st * 1.2, cv - 3, .6 + st * 1.05, cu + st * 1.2, cv + 3, .6 + st * 1.05, .55, "wood", (.4, .26, .15), 7)
    hw = W * .38
    S.box("wood", hw / 2 - W * .05, 0, 0, hw, 22, 9, top=None, col=(.4, .25, .15))
    S.gable("roof", hw / 2 - W * .05, 0, 9, hw, 22, 3, (.35, .36, .38), over=.4)
    S.box("dark", hw / 2 - W * .05, -11.05, 0, hw * .8, .1, 7, col=(.05, .05, .05))
    S_tube(S, W * .32, 2, 2, W * .42, 14, 18, .9, "metalattr", (.7, .7, .68), 4)
    S.cyl("metalattr", W * .42, 16, 0, 20, 4, 20, col=(.75, .75, .72)); S.cyl("metalattr", W * .42, 16, 20, 3, 4, 20, r2=.8, col=(.75, .75, .72))
    S.cyl("sand", W * .38, -D / 2 + 16, 0, 5, 8, 24, r2=.4, col=(.7, .55, .35))                    # tas de copeaux
    for k in range(12):                                                                        # bois séché en paquets
        S.box("wood", -W / 2 + 8 + (k % 6) * 7, -D / 2 + 8 + (k // 6) * 6, 0, 5.5, 3.6, R.uniform(1.8, 3.2), col=(.75, .6, .4), top="wood")
    for k in range(3): inst(TRUCK, *S.P(W * .1 + k * 6, -D / 2 + 8), S.z0, S.rot + math.pi / 2, 1, (.3, .45, .25))
    fence(S, gate_u=W * .25)
    return 12

INDUSTRIES = {"usine": ind_usine, "chimie": ind_chimie, "agro": ind_agro, "centrale": ind_centrale, "metal": ind_metal, "scierie": ind_scierie}

def industrial_block(z, b, kind):
    u0, u1, v0, v1 = b
    block_pad(z, b, "concrete", .1)
    x, y = z.w((u0 + u1) / 2, (v0 + v1) / 2)
    S = Site(x, y, z.rot, u1 - u0 - 2, v1 - v0 - 2, z0=.1)
    S.flat("concrete", 0, 0, .002, S.W, S.D, h=.02)
    # on note l'emprise de tout ce qui est construit, pour mettre de la verdure dans ce qui reste
    fps = []; ob, oc, oi = A.box, A.cyl, inst
    def rbox(mat, x_, y_, z0, w, d, h, rot=0., *a, **k): fps.append((x_, y_, w, d, rot)); return ob(mat, x_, y_, z0, w, d, h, rot, *a, **k)
    def rcyl(mat, x_, y_, z0, h, r, *a, **k): fps.append((x_, y_, 2 * r, 2 * r, 0.)); return oc(mat, x_, y_, z0, h, r, *a, **k)
    def rinst(mesh, x_, y_, *a, **k): fps.append((x_, y_, 9, 4, a[1] if len(a) > 1 else 0.)); return oi(mesh, x_, y_, *a, **k)
    A.box, A.cyl = rbox, rcyl; globals()["inst"] = rinst
    try: h = INDUSTRIES[kind](S)
    finally:
        del A.box, A.cyl; globals()["inst"] = oi
    factory_greenery(S, fps)
    claim(x, y, u1 - u0 - 2, v1 - v0 - 2, z.rot)
    return h


# ═══════════════════════════════════════ parcs : amphithéâtre, stade, équipements de parc
def arc_quad(mat, x, y, a0, a1, r0, r1, z0, z1, col, n):
    """portion d'anneau (horizontale si z0 == z1, sinon rampe) entre les angles a0 et a1"""
    for k in range(n):
        t0, t1 = a0 + (a1 - a0) * k / n, a0 + (a1 - a0) * (k + 1) / n
        A.face(mat, [(x + r0 * math.cos(t0), y + r0 * math.sin(t0), z0), (x + r0 * math.cos(t1), y + r0 * math.sin(t1), z0),
                     (x + r1 * math.cos(t1), y + r1 * math.sin(t1), z1), (x + r1 * math.cos(t0), y + r1 * math.sin(t0), z1)], None, col)

def arc_wall(mat, x, y, a0, a1, r, z0, z1, col, n):
    for k in range(n):
        t0, t1 = a0 + (a1 - a0) * k / n, a0 + (a1 - a0) * (k + 1) / n
        A.face(mat, [(x + r * math.cos(t0), y + r * math.sin(t0), z0), (x + r * math.cos(t1), y + r * math.sin(t1), z0),
                     (x + r * math.cos(t1), y + r * math.sin(t1), z1), (x + r * math.cos(t0), y + r * math.sin(t0), z1)], None, col)

def amphitheatre(x, y, rot, r):
    """théâtre antique : gradins en pierre en demi-cercle (5 travées, 4 escaliers, un palier), portique en haut,
    orchestre, scène et mur de scène à deux ordres de colonnes"""
    n, ri = 12, r * .34; dr = (r - ri) / n; rs = .45
    a0, a1 = rot, rot + math.pi
    cols = STONE; dark = tuple(c_ * .8 for c_ in STONE)
    wedges = 5; gap = .06
    for k in range(n):
        r0, r1 = ri + k * dr, ri + (k + 1) * dr; z_ = .3 + (k + 1) * rs + (.3 if k >= 6 else 0)
        for w_ in range(wedges):
            b0 = a0 + (a1 - a0) * w_ / wedges + (gap / 2 if w_ else 0); b1 = a0 + (a1 - a0) * (w_ + 1) / wedges - (gap / 2 if w_ < wedges - 1 else 0)
            arc_quad("pierre", x, y, b0, b1, r0, r1, z_, z_, cols if k != 6 else dark, 8)
            arc_wall("pierre", x, y, b0, b1, r0, z_ - rs - (.3 if k == 6 else 0), z_, dark, 8)
        for w_ in range(1, wedges):                                          # escaliers rayonnants
            c = a0 + (a1 - a0) * w_ / wedges
            arc_quad("pierre", x, y, c - gap / 2, c + gap / 2, r0, r1, z_ - rs / 2, z_ - rs / 2, dark, 1)
    ztop = .3 + n * rs + .3
    arc_wall("pierre", x, y, a0, a1, r + 2.6, 0, ztop, dark, 36)                   # mur extérieur
    arc_quad("pierre", x, y, a0, a1, r, r + 2.6, ztop, ztop, cols, 36)             # promenade
    for ang in (a0, a1):                                                            # murs d'about
        ca, sa = math.cos(ang), math.sin(ang)
        A.face("pierre", [(x + ri * ca, y + ri * sa, 0), (x + (r + 2.6) * ca, y + (r + 2.6) * sa, 0),
                          (x + (r + 2.6) * ca, y + (r + 2.6) * sa, ztop), (x + ri * ca, y + ri * sa, .3 + rs)], None, dark)
    for k in range(16):                                                             # portique au sommet
        t = a0 + (a1 - a0) * (k + .5) / 16
        A.cyl("pierre", x + (r + 1.8) * math.cos(t), y + (r + 1.8) * math.sin(t), ztop, 4.2, .32, 10, col=cols)
    arc_quad("pierre", x, y, a0, a1, r + 1.1, r + 2.6, ztop + 4.2, ztop + 4.2, cols, 36)
    arc_wall("pierre", x, y, a0, a1, r + 2.6, ztop + 3.7, ztop + 4.2, dark, 36)
    # orchestre et scène
    A.cyl("plaza", x, y, 0, .3, ri, 32)
    A.cyl("pierre", x, y, .3, .05, ri * .55, 32, col=(.7, .55, .45))
    back = rot - math.pi / 2; bx, by = math.cos(back), math.sin(back); tx, ty = math.cos(rot), math.sin(rot)
    sw_ = 2 * ri + 8
    A.box("wood", x + bx * 3.5, y + by * 3.5, 0, sw_, 6, 1.3, rot, col=(.45, .3, .18), top="wood")                # plateau
    fx, fy = x + bx * 8, y + by * 8
    A.box("pierre", fx, fy, 0, sw_ + 4, 2.4, 11.5, rot, col=dark, top="pierre")                                    # mur de scène
    for lvl, (z0, hh) in enumerate(((1.3, 4.6), (6.4, 4.2))):
        for k in range(10):
            cx_, cy_ = fx - bx * 1.9 + tx * (-sw_ / 2 + 1 + k * (sw_ - 2) / 9), fy - by * 1.9 + ty * (-sw_ / 2 + 1 + k * (sw_ - 2) / 9)
            A.cyl("pierre", cx_, cy_, z0, hh, .3, 10, col=cols)
        A.box("pierre", fx - bx * 1.7, fy - by * 1.7, z0 + hh, sw_, 1.4, .5, rot, col=cols, top="pierre")
    for k in (-1, 0, 1):
        A.box("dark", fx - bx * 1.25 + tx * k * sw_ * .3, fy - by * 1.25 + ty * k * sw_ * .3, 1.3, 2.4 if k else 3.2, .1, 3.6 if k else 4.4, rot, col=(.05, .05, .05))
    for sd in (-1, 1):                                                             # ailes de scène
        A.box("pierre", fx + tx * sd * (sw_ / 2 + 4), fy + ty * sd * (sw_ / 2 + 4), 0, 6, 7, 8.5, rot, col=dark, top="pierre")
    for k in range(10):                                                            # cyprès autour
        t = a0 - .25 + (a1 - a0 + .5) * k / 9
        inst(R.choice(PINES), x + (r + 6.5) * math.cos(t), y + (r + 6.5) * math.sin(t), 0, 0, .75)

def stadium(x, y, rot, a, b):
    """stade : gradins en travées colorées, vomitoires, toiture annulaire sur mâts haubanés, piste d'athlétisme,
    pelouse rayée, tribune d'honneur vitrée, écran géant, projecteurs"""
    seg = 64; ry = b / a
    E = lambda r_, t, z_: (x + r_ * math.cos(t), y + r_ * ry * math.sin(t), z_)
    A.cyl("concrete", x, y, 0, 3, a + 6, seg, rx=1, ry=ry, top=False)
    seats = [(.12, .25, .55), (.62, .1, .08)]
    for ring in range(7):
        r0 = a + ring * 2.2; z0 = 3 + ring * 2.2
        for k in range(seg):
            t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
            colk = seats[(k // 8) % 2] if ring != 3 else (.3, .3, .32)
            A.face("painted", [E(r0, t0, z0 - 2.2), E(r0, t1, z0 - 2.2), E(r0, t1, z0), E(r0, t0, z0)], None, (.55, .55, .55))
            A.face("painted", [E(r0, t0, z0), E(r0, t1, z0), E(r0 + 2.2, t1, z0), E(r0 + 2.2, t0, z0)], None, colk)
            if ring == 3 and k % 8 == 4:
                A.face("dark", [E(r0 - .05, t0, z0 - 2), E(r0 - .05, t1, z0 - 2), E(r0 - .05, t1, z0), E(r0 - .05, t0, z0)], None, (.05, .05, .05))
    zt = 3 + 7 * 2.2
    for k in range(seg):                                                      # enveloppe extérieure à claire-voie
        t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        A.face("white", [E(a + 15.6, t0, 0), E(a + 15.6, t1, 0), E(a + 15.6, t1, zt + 1), E(a + 15.6, t0, zt + 1)], None)
        if k % 2 == 0: A.face("dark", [E(a + 15.7, t0, 3), E(a + 15.7, t1, 3), E(a + 15.7, t1, zt - 2), E(a + 15.7, t0, zt - 2)], None, (.1, .1, .12))
    zr = zt + 5                                                               # toiture annulaire
    for k in range(seg):
        t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        A.face("white", [E(a + 7, t0, zr - 1), E(a + 7, t1, zr - 1), E(a + 16.5, t1, zr), E(a + 16.5, t0, zr)], None)
    for k in range(12):                                                       # mâts et haubans
        t = 2 * math.pi * (k + .5) / 12
        mx, my, _ = E(a + 19, t, 0); A.cyl("metal", mx, my, 0, zr + 14, .45, 8)
        ex, ey, _ = E(a + 8, t, 0); tube((mx, my, zr + 14), (ex, ey, zr - .8), .08, "metal", (.4, .4, .42), 4)
    # piste et pelouse
    for i, (ri_, ro_) in enumerate(((a * .71, a * .93),)):
        for k in range(seg):
            t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
            A.face("painted", [E(ri_, t0, .19), E(ri_, t1, .19), E(ro_, t1, .19), E(ro_, t0, .19)], None, (.62, .2, .12))
    for ln in range(1, 6):
        rr = a * .71 + ln * (a * .22) / 6
        for k in range(seg):
            t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
            A.face("paint_w", [E(rr, t0, .205), E(rr, t1, .205), E(rr + .12, t1, .205), E(rr + .12, t0, .205)], None)
    A.cyl("grass", x, y, 0, .17, a * .71, seg, rx=1, ry=ry)
    pw, pd = a * .96, b * .86
    for k in range(8):                                                        # pelouse rayée
        A.box("pitch", x + math.cos(rot) * (-pw / 2 + pw * (k + .5) / 8), y + math.sin(rot) * (-pw / 2 + pw * (k + .5) / 8), .17, pw / 8 + .01 * (k % 2), pd, .02 + .004 * (k % 2), rot, top="pitch", sides=False)
    for dx in (-pw / 2, 0, pw / 2): A.box("paint_w", x + dx * math.cos(rot), y + dx * math.sin(rot), .2, .2, pd, .01, rot, sides=False)
    for dy in (-pd / 2, pd / 2): A.box("paint_w", x - dy * math.sin(rot), y + dy * math.cos(rot), .2, pw, .2, .01, rot, sides=False)
    A.cyl("paint_w", x, y, .2, .01, 6, 32, top=False)
    for sd in (-1, 1):   # buts
        gx, gy = x + math.cos(rot) * sd * pw / 2, y + math.sin(rot) * sd * pw / 2
        A.box("white", gx, gy, .2, .2, 7.3, 2.4, rot, top="white")
    vx, vy, _ = E(a + 6, -math.pi / 2, 0)                                    # tribune d'honneur vitrée
    A.box("glass", vx, vy, 9, 30, 2, 3, rot, col=(.25, .35, .4), top="glass")
    sx_, sy_, _ = E(a + 12, math.pi / 2, 0)                                  # écran géant
    A.box("dark", sx_, sy_, zt + 1, 18, 1.2, 7, rot, col=(.05, .05, .05)); A.box("sign", sx_, sy_ - .65, zt + 1.6, 16.5, .1, 5.8, rot, top="sign")
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):   # projecteurs
        px, py = x + sx * (a + 17), y + sy * (b + 11)
        A.cyl("metal", px, py, 0, zr + 18, .6, 8)
        A.box("flood", px, py, zr + 18, 6, 1.2, 3.2, math.atan2(-sy, -sx) + 1.57, top="flood")
        if NIGHT > 0: A.disc_decal("floodpool", x + sx * a * .4, y + sy * b * .4, .35, a * 1.3)

# ─── petits aménagements qui rendent les parcs vivants
def park_extras(kind, P, W, D, x, y, rot, z0=.18):
    def box(mat, a_, b_, z_, w_, d_, h_, col=(.5, .5, .5), top=None, r=0.): A.box(mat, *P(a_, b_), z0 + z_, w_, d_, h_, rot + r, col=col, top=top)
    def cyl(mat, a_, b_, z_, h_, r_, seg=12, col=(.5, .5, .5), **kw): A.cyl(mat, *P(a_, b_), z0 + z_, h_, r_, seg, col=col, **kw)
    def tb(a0, b0, za, a1, b1, zb, r_, mat="metal", col=(.5, .5, .5), seg=6):
        p, q = P(a0, b0), P(a1, b1); tube((p[0], p[1], z0 + za), (q[0], q[1], z0 + zb), r_, mat, col, seg)
    if kind == "jeux":
        # tour à toboggan, balançoires, dôme à grimper, tourniquet
        box("painted", -4, 2, 0, .15, .15, 3.2, (.9, .7, .1)); box("painted", -2, 2, 0, .15, .15, 3.2, (.9, .7, .1))
        box("painted", -4, 4, 0, .15, .15, 3.2, (.9, .7, .1)); box("painted", -2, 4, 0, .15, .15, 3.2, (.9, .7, .1))
        box("wood", -3, 3, 1.6, 2.4, 2.4, .15, top="wood"); cyl("painted", -3, 3, 3.2, 1.2, 1.8, 4, (.8, .2, .1), r2=.05)
        tb(-1.8, 3, 1.7, 2.5, 3, .3, .45, "painted", (.1, .4, .8), 8)
        for k in (-1, 1): tb(4 + k * 2.2, -3, 0, 4 + k * 2.2, -2, 2.6, .08, "painted", (.1, .5, .3), 5); tb(4 + k * 2.2, -4, 0, 4 + k * 2.2, -3, 2.6, .08, "painted", (.1, .5, .3), 5)
        tb(1.6, -3, 2.6, 6.4, -3, 2.6, .1, "painted", (.1, .5, .3), 6)
        for k in (-1, 1): box("dark", 4 + k * 1, -3, .5, .5, .2, .06, (.1, .1, .1))
        A.dome("painted", *P(-6, -4), z0, 2, 1.8, 10, 3, col=(.8, .2, .1))
        cyl("painted", 7, 4, 0, .5, 1.3, 12, (.9, .7, .1))
    elif kind == "fontaine":
        cyl("concrete", 0, 0, .6, 1.4, 1.2, 16); cyl("concrete", 0, 0, 2, .4, 2.6, 24); cyl("water", 0, 0, 2.05, .4, 2.3, 24)
        cyl("concrete", 0, 0, 2.4, 1.3, .5, 12); cyl("concrete", 0, 0, 3.7, .3, 1.3, 16); cyl("water", 0, 0, 3.72, .3, 1.1, 16)
        cyl("white", 0, 0, 4, 1.4, .12, 6, r2=.02)
    elif kind == "japonais":
        pu, pv = W * .32, D * .3                                           # pagode à trois toits
        for k in range(3):
            box("wood", pu, pv, k * 3, 5 - k * 1.1, 5 - k * 1.1, 2.4, (.55, .15, .08), top="wood")
            cyl("roof", pu, pv, k * 3 + 2.4, .9, (7 - k * 1.4) * .75, 4, (.15, .15, .17), r2=(5 - k * 1.1) * .5)
        cyl("metal", pu, pv, 9.3, 2.5, .08, 4)
        box("wood", -W * .3, D * .3, 0, 7, 5, 2.6, (.45, .32, .2), top=None)             # pavillon de thé
        A.gable("roof", *P(-W * .3, D * .3), z0 + 2.6, 7, 5, 1.6, rot, (.18, .18, .2), over=.6)
        for k in range(4):                                                                 # lanternes de pierre
            a_, b_ = R.uniform(-W * .35, W * .35), -D * .38
            cyl("concrete", a_, b_, 0, .9, .2, 6); box("concrete", a_, b_, .9, .8, .8, .5); cyl("concrete", a_, b_, 1.4, .4, .6, 4, r2=.05)
    elif kind == "etang":
        box("wood", 0, -D * .25 + 1, .02, 2, 7, .25, (.4, .28, .16), top="wood")             # ponton
        for k in range(2):
            bx_, by_ = P(-3 + k * 6, -D * .1)
            A.box("white", bx_, by_, .2, 3.2, 1.3, .45, rot + .4 * k, col=(.9, .9, .88), top="wood")
    elif kind == "sport":
        for k in range(4): box("concrete", 0, D * .36 + k * .8, k * .45, W * .5, .8, .45, top="wood")     # gradins
        for sd in (-1, 1):
            for e in (-1, 1): cyl("metal", sd * W * .4, e * D * .3, 0, 9, .12, 6); box("flood", sd * W * .4, e * D * .3, 9, 1.4, .3, .8)
    elif kind == "roseraie":
        for k in range(12):                                                                 # pergola circulaire
            t = k / 12 * 6.283
            cyl("wood", math.cos(t) * 5.5, math.sin(t) * 5.5, 0, 2.6, .12, 6, (.4, .28, .16))
            t2 = (k + 1) / 12 * 6.283
            tb(math.cos(t) * 5.5, math.sin(t) * 5.5, 2.6, math.cos(t2) * 5.5, math.sin(t2) * 5.5, 2.6, .1, "wood", (.4, .28, .16), 4)
            cyl("painted", math.cos(t + .26) * 5.5, math.sin(t + .26) * 5.5, 2.3, .6, .7, 6, R.choice(FLOWERS))
    elif kind == "francais":
        for sa in (-1, 1):
            for sb in (-1, 1):
                for e in (-1, 1): cyl("painted", sa * (W * .25 + e * 5), sb * (D * .25 + e * 4), 0, 2.4, .7, 8, (.05, .15, .05), r2=.05)   # ifs taillés
        for k in range(4): cyl("pierre", (k - 1.5) * 5, D * .12, 0, 2.2, .35, 8, STONE)                              # statues
    elif kind == "bosquet":
        for k in range(4):
            a_, b_ = R.uniform(-W * .3, W * .3), R.uniform(-D * .3, D * .3)
            box("wood", a_, b_, .7, 2, .8, .08, top="wood"); box("wood", a_, b_ - .8, .4, 2, .3, .08, top="wood"); box("wood", a_, b_ + .8, .4, 2, .3, .08, top="wood")


# ═══════════════════════════════════════ mobilier urbain : feux, arrêts de bus, colonnes Morris, terrasses
def traffic_light(x, y, ang, arm=4.2, green=False):
    """feu tricolore sur mât à potence ; ang = direction de la potence (au-dessus des voies)"""
    c, s_ = math.cos(ang), math.sin(ang)
    A.cyl("dark", x, y, .18, 5.8, .17, 8, col=(.14, .14, .15))
    A.box("dark", x + c * arm / 2, y + s_ * arm / 2, 5.6, arm, .22, .22, ang, col=(.14, .14, .15))
    for k, d_ in enumerate((arm, 1.3)):
        hx, hy = x + c * d_, y + s_ * d_; zh = 4.5 if k == 0 else 2.9
        A.box("dark", hx, hy, zh, .5, .5, 1.3, ang, col=(.06, .06, .06), top="dark")
        A.box("painted", hx, hy, zh + 1.3, .62, .62, .06, ang, col=(.85, .7, .1))              # visière jaune (visible d'en haut)
        A.box("feu_v" if green else "feu_r", hx, hy, zh + (.15 if green else .95), .52, .52, .25, ang, top="feu_v" if green else "feu_r")
    A.box("white", x, y, 2.2, .12, .5, .5, ang + math.pi / 2)                # bouton piéton

def bus(x, y, ang):
    c, s_ = math.cos(ang), math.sin(ang)
    A.box("painted", x, y, .35, 12, 2.55, 2.6, ang, col=(.92, .92, .9), top="painted")
    A.box("carglass", x, y, 1.35, 12.05, 2.6, 1.1, ang, col=(.1, .12, .14))
    A.box("painted", x, y, .6, 12.1, 2.62, .35, ang, col=(.1, .35, .7))
    A.box("metal", x - c * 2, y - s_ * 2, 2.95, 4, 1.8, .35, ang, col=(.6, .6, .62))

def bus_stop(x, y, ang, with_bus=False, road_side=None):
    """abribus : toit, paroi vitrée, banc, poteau et panneau ; ang = le long de la rue ; road_side = vecteur vers la chaussée"""
    c, s_ = math.cos(ang), math.sin(ang); nx, ny = road_side
    bx, by = x - nx * .6, y - ny * .6
    A.box("glass", bx, by, .18, 3.8, .08, 2.3, ang, col=(.5, .6, .65), top="glass")                  # paroi du fond
    for sd in (-1, 1): A.box("glass", x + c * sd * 1.9, y + s_ * sd * 1.9, .18, .08, 1.3, 2.3, ang, col=(.5, .6, .65))
    A.box("white", x, y, 2.5, 4.1, 1.6, .12, ang, col=(.85, .85, .85), top="white")                  # toit
    A.box("wood", bx + nx * .35, by + ny * .35, .6, 3, .4, .08, ang, top="wood")                        # banc
    A.box("sign", bx + c * 1.4, by + s_ * 1.4, 1, 1.1, .1, 1.6, ang, top="sign")                        # affiche éclairée
    px, py = x + nx * .6 + c * 2.6, y + ny * .6 + s_ * 2.6
    A.cyl("metal", px, py, .18, 2.8, .05, 6); A.box("painted", px, py, 2.5, .6, .06, .6, ang, col=(.1, .3, .7))
    if with_bus: bus(x + nx * 3.2, y + ny * 3.2, ang)

def morris(x, y):
    A.cyl("painted", x, y, .18, 3, .62, 16, col=(.1, .28, .18)); A.cyl("sign", x, y, .6, 1.9, .64, 16, top=False)
    A.dome("painted", x, y, 3.18, .72, .55, 16, 3, col=(.1, .28, .18))

def terrace(x, y, ang, n=3):
    c, s_ = math.cos(ang), math.sin(ang)
    colp = R.choice([(.75, .15, .1), (.12, .3, .2), (.9, .85, .75), (.15, .2, .45)])
    for k in range(n):
        tx, ty = x + c * (k - (n - 1) / 2) * 2.4, y + s_ * (k - (n - 1) / 2) * 2.4
        A.cyl("painted", tx, ty, .18, .75, .35, 8, col=(.3, .3, .32))
        A.cyl("painted", tx, ty, 2.25, .35, 1.15, 8, r2=.08, col=colp); A.cyl("metal", tx, ty, .18, 2.2, .03, 4)

def junction_props(p, info, k):
    """carrefour du réseau (≥ 3 branches, grandes rues) : un feu sur chaque branche, côté droit de l'arrivée"""
    if k < 3 or not any(a["cls"] in ("arterial", "avenue") for a in info): return
    for i, a in enumerate(info):
        if a["walk"] <= 1 or a["cls"] == "ramp": continue
        E, t, n = a["E"], a["t"], a["n"]
        off = a["h"] + .8
        x, y = E[0] + n[0] * off + t[0] * 1.2, E[1] + n[1] * off + t[1] * 1.2
        traffic_light(x, y, math.atan2(-n[1], -n[0]), arm=min(4.5, a["h"] * .9), green=(i % 2 == 0))

def edge_props(pts, e):
    """le long des grandes rues : arrêts de bus tous les 200 à 300 m"""
    if e["cls"] not in ("arterial", "avenue") or e["walk"] < 2: return
    L_ = length(pts); s_ = R.uniform(60, 140); side = R.choice([-1, 1])
    while s_ < L_ - 40:
        p, t, _ = at(pts, s_); n = (-t[1] * side, t[0] * side)
        H = e["w"] / 2 + e["walk"] / 2 + .1
        x, y = p[0] + n[0] * H, p[1] + n[1] * H
        if cell_of(x, y) not in BUSY:
            bus_stop(x, y, math.atan2(t[1], t[0]), R.random() < .4, (-n[0], -n[1]))
        s_ += R.uniform(200, 300); side = -side


# ═══════════════════════════════════════ verdure dans les usines : pelouses et arbres dans tous les espaces libres
def factory_greenery(S, fps):
    W, D = S.W, S.D; cs = S.c; sn = S.s
    rects = []
    for (x, y, w, d, r) in fps:
        if w * d > .6 * W * D: continue
        du, dv = x - S.x, y - S.y; u = du * cs + dv * sn; v = -du * sn + dv * cs
        rects.append((u, v, w / 2 + 1.6, d / 2 + 1.6, r - S.rot))
    def occupied(u, v):
        for (cu, cv, hw, hd, r) in rects:
            dx, dy = u - cu, v - cv; c_, s2 = math.cos(r), math.sin(r)
            lx, ly = dx * c_ + dy * s2, -dx * s2 + dy * c_
            if abs(lx) < hw and abs(ly) < hd: return True
        return False
    st = 4.
    for i in range(int((W - 4) / st)):
        for j in range(int((D - 8) / st)):
            u, v = -W / 2 + 2 + (i + .5) * st, -D / 2 + 6 + (j + .5) * st
            if occupied(u, v): continue
            S.flat("grass", u, v, .015, st + .02, st + .02, h=.03)
            if R.random() < .3: S.tree(u + R.uniform(-1, 1), v + R.uniform(-1, 1), R.uniform(.7, 1.))
            elif R.random() < .1: S.box("painted", u, v, 0, 1.6, 1.6, .9, col=(.07, .18, .06))
