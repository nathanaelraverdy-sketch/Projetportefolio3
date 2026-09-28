"""Accumulateur de géométrie : tout ce qui partage un matériau finit dans UN seul mesh
(des dizaines de milliers de boîtes → quelques dizaines d'objets). Chaque face garde ses UV
(u = travées, v = étages pour les façades) et une couleur « col »."""
import bpy, bmesh, math
from mathutils import Vector
from mats import MAT


class Acc:
    def __init__(self):
        self.d = {}

    def _g(self, mat):
        if mat not in self.d: self.d[mat] = ([], [], [], [])   # verts, faces, uvs(par coin), cols(par coin)
        return self.d[mat]

    def face(self, mat, pts, uvs=None, col=(.5, .5, .5)):
        V, F, U, C = self._g(mat)
        i0 = len(V); V.extend(pts)
        F.append(tuple(range(i0, i0 + len(pts))))
        U.extend(uvs if uvs else [(0, 0)] * len(pts))
        C.extend([(*col, 1)] * len(pts))

    # ─── boîte orientée : centre (x, y), largeur w (axe local x), profondeur d, rotation rot
    def box(self, mat, x, y, z0, w, d, h, rot=0., col=(.5, .5, .5), top=None, fh=3.4, bay=2.6, uoff=0.,
            sides=True, only_visible=False, bottom=False):
        c, s = math.cos(rot), math.sin(rot)
        P = lambda lx, ly, z: (x + lx * c - ly * s, y + lx * s + ly * c, z)
        hw, hd = w / 2, d / 2
        z1 = z0 + h
        corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
        if sides:
            for i in range(4):
                (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
                nx, ny = (by - ay), -(bx - ax)          # normale locale sortante
                wx, wy = nx * c - ny * s, nx * s + ny * c
                if only_visible and wy >= -0.02 * math.hypot(wx, wy): continue   # face tournée vers le nord : jamais vue
                L = math.hypot(bx - ax, by - ay)
                pa, pb = P(ax, ay, z0), P(bx, by, z0)
                u0 = uoff; u1 = uoff + L / bay
                self.face(mat, [pa, pb, P(bx, by, z1), P(ax, ay, z1)],
                          [(u0, z0 / fh), (u1, z0 / fh), (u1, z1 / fh), (u0, z1 / fh)], col)
        tm = top if top is not None else mat
        if tm:
            pts = [P(ax, ay, z1) for ax, ay in corners]
            self.face(tm, pts, [(p[0] / 10, p[1] / 10) for p in pts], col)
        if bottom:
            pts = [P(ax, ay, z0) for ax, ay in reversed(corners)]
            self.face(mat, pts, None, col)

    def cyl(self, mat, x, y, z0, h, r, seg=16, col=(.5, .5, .5), r2=None, top=True, rx=None, ry=None, cap=None):
        r2 = r if r2 is None else r2
        sx = (rx or 1.); sy = (ry or 1.)
        ring = lambda rr, z: [(x + rr * sx * math.cos(2 * math.pi * k / seg), y + rr * sy * math.sin(2 * math.pi * k / seg), z) for k in range(seg)]
        a, b = ring(r, z0), ring(r2, z0 + h)
        for k in range(seg):
            k2 = (k + 1) % seg
            self.face(mat, [a[k], a[k2], b[k2], b[k]], [(k / seg * 4, 0), ((k + 1) / seg * 4, 0), ((k + 1) / seg * 4, h / 3.4), (k / seg * 4, h / 3.4)], col)
        if top and r2 > 0.001:
            self.face(cap or mat, b, [(p[0] / 10, p[1] / 10) for p in b], col)

    def dome(self, mat, x, y, z0, r, h=None, seg=24, rings=6, col=(.5, .5, .5)):
        h = r if h is None else h
        prev = None
        for j in range(rings + 1):
            t = j / rings * math.pi / 2
            rr, zz = r * math.cos(t), z0 + h * math.sin(t)
            cur = [(x + rr * math.cos(2 * math.pi * k / seg), y + rr * math.sin(2 * math.pi * k / seg), zz) for k in range(seg)]
            if prev:
                for k in range(seg):
                    k2 = (k + 1) % seg
                    self.face(mat, [prev[k], prev[k2], cur[k2], cur[k]], None, col)
            prev = cur

    def gable(self, mat, x, y, z0, w, d, rh, rot, col, over=.4):
        """toit à deux pans (faîtage selon w)"""
        c, s = math.cos(rot), math.sin(rot)
        P = lambda lx, ly, z: (x + lx * c - ly * s, y + lx * s + ly * c, z)
        hw, hd = w / 2 + over, d / 2 + over
        a, b, cc, dd = P(-hw, -hd, z0), P(hw, -hd, z0), P(hw, hd, z0), P(-hw, hd, z0)
        r0, r1 = P(-hw, 0, z0 + rh), P(hw, 0, z0 + rh)
        self.face(mat, [a, b, r1, r0], [(0, 0), (w / 3, 0), (w / 3, 1), (0, 1)], col)
        self.face(mat, [cc, dd, r0, r1], [(0, 0), (w / 3, 0), (w / 3, 1), (0, 1)], col)
        return (a, b, cc, dd, r0, r1)

    def gable_ends(self, mat, x, y, z0, w, d, rh, rot, col):
        c, s = math.cos(rot), math.sin(rot)
        P = lambda lx, ly, z: (x + lx * c - ly * s, y + lx * s + ly * c, z)
        for sx in (-1, 1):
            self.face(mat, [P(sx * w / 2, -d / 2, z0), P(sx * w / 2, d / 2, z0), P(sx * w / 2, 0, z0 + rh)], None, col)

    def ribbon(self, mat, pts, width, z=0., col=(.5, .5, .5), off=0., closed=False, ulen=None):
        """bande qui suit une polyligne 2D (route, allée, marquage)"""
        n = len(pts)
        if n < 2: return
        L = []
        for i in range(n):
            a = pts[max(i - 1, 0)]; b = pts[min(i + 1, n - 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]; tl = math.hypot(tx, ty) or 1
            L.append((-ty / tl, tx / tl))
        dist = 0.
        for i in range(n - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            seg = math.hypot(x1 - x0, y1 - y0)
            n0, n1 = L[i], L[i + 1]
            l0 = off - width / 2; r0 = off + width / 2
            q = [(x0 + n0[0] * l0, y0 + n0[1] * l0, z), (x1 + n1[0] * l0, y1 + n1[1] * l0, z),
                 (x1 + n1[0] * r0, y1 + n1[1] * r0, z), (x0 + n0[0] * r0, y0 + n0[1] * r0, z)]
            ul = ulen or width
            self.face(mat, q, [(dist / ul, 0), ((dist + seg) / ul, 0), ((dist + seg) / ul, 1), (dist / ul, 1)], col)
            dist += seg

    def disc_decal(self, mat, x, y, z, size, rot=0.):
        c, s = math.cos(rot), math.sin(rot); h = size / 2
        P = lambda lx, ly: (x + lx * c - ly * s, y + lx * s + ly * c, z)
        self.face(mat, [P(-h, -h), P(h, -h), P(h, h), P(-h, h)], [(0, 0), (1, 0), (1, 1), (0, 1)])

    def beam_decal(self, mat, x, y, z, rot, length=16., w0=1.6, w1=7.):
        c, s = math.cos(rot), math.sin(rot)
        P = lambda lx, ly: (x + lx * c - ly * s, y + lx * s + ly * c, z)
        self.face(mat, [P(0, -w0 / 2), P(length, -w1 / 2), P(length, w1 / 2), P(0, w0 / 2)], [(0, 0), (1, 0), (1, 1), (0, 1)])

    def poly(self, mat, pts, z=0., col=(.5, .5, .5), uvs=10.):
        """polygone étoilé (lac, pelouse) : triangles depuis le centre"""
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            tri = [(cx, cy, z), (a[0], a[1], z), (b[0], b[1], z)]
            self.face(mat, tri, [(p[0] / uvs, p[1] / uvs) for p in tri], col)

    def flush(self, collection, prefix="acc"):
        n = 0
        for mat, (V, F, U, C) in self.d.items():
            if not F: continue
            me = bpy.data.meshes.new(f"{prefix}_{mat}")
            me.from_pydata(V, [], F)
            uvl = me.uv_layers.new(name="UVMap")
            flat = [c for uv in U for c in uv]
            uvl.data.foreach_set("uv", flat)
            ca = me.color_attributes.new("col", "BYTE_COLOR", "CORNER")
            ca.data.foreach_set("color", [c for col in C for c in col])
            me.materials.append(MAT[mat])
            me.validate(clean_customdata=False)
            ob = bpy.data.objects.new(f"{prefix}_{mat}", me)
            collection.objects.link(ob)
            n += len(F)
        self.d = {}
        return n
