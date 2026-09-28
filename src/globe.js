/* ═════════════ La Terre en points, tournée vers Bruxelles (section « About us ») ═════════════
   Les couleurs de la version sombre, inversées : une sphère claire, les continents en petits points noirs
   (données Natural Earth via world-atlas, domaine public), une ombre douce autour, Bruxelles marquée d'un point
   qui pulse, quelques arcs vers d'autres villes parcourus par une lueur.
   - à l'apparition, les points naissent depuis Bruxelles et s'étendent sur tout le globe
   - la Terre se balance lentement autour de la Belgique (elle reste toujours en vue), on peut la faire tourner
   - elle ne se dessine que quand elle est à l'écran */
import * as THREE from 'three';

const BXL = [50.85, 4.35];
const VILLES = [['London', 51.51, -.13], ['Paris', 48.86, 2.35], ['Amsterdam', 52.37, 4.9], ['Berlin', 52.52, 13.4],
  ['Lisbon', 38.72, -9.14], ['Rome', 41.9, 12.5], ['New York', 40.71, -74.0], ['Dubai', 25.2, 55.27]];
const CENTRE = [50, 12];                          // le point de la Terre au milieu du disque
const RAD = Math.PI / 180;
const CALME = matchMedia('(prefers-reduced-motion: reduce)').matches;
const NOIR = new THREE.Color('#2a2222'), BLANC = new THREE.Color('#eff6f8');

const sph = (lat, lon, r = 1) => { const a = lat * RAD, b = lon * RAD; return new THREE.Vector3(Math.cos(a) * Math.sin(b) * r, Math.sin(a) * r, Math.cos(a) * Math.cos(b) * r); };
const ease = t => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

export async function creerGlobe(boite, etiquette, { petit = false, sombre = false } = {}) {
  const cv = document.createElement('canvas'); cv.className = 'globe-cv'; boite.prepend(cv);
  const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });   // (alpha prémultiplié, par défaut : sinon le halo clair devient gris et opaque sur fond sombre)
  renderer.setPixelRatio(Math.min(devicePixelRatio, petit ? 1.5 : 2)); renderer.setClearColor(0xffffff, 0);
  const scene = new THREE.Scene(), cam = new THREE.OrthographicCamera(-1.3, 1.3, 1.3, -1.3, -10, 10);
  const terre = new THREE.Group(); scene.add(terre);
  const U = { uTemps: { value: 0 }, uNaissance: { value: 0 }, uBxl: { value: sph(...BXL) }, uTaille: { value: 2 }, uSombre: { value: sombre ? 1 : 0 }, uEncre: { value: new THREE.Color() } };   // uSombre : 0 = clair, 1 = sombre

  // l'ombre douce autour du disque (derrière la Terre)
  const ombre = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 2.6), new THREE.ShaderMaterial({
    uniforms: U, transparent: true, depthWrite: false,
    vertexShader: 'varying vec2 vP; void main(){ vP = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
    fragmentShader: `uniform float uNaissance, uSombre; uniform vec3 uEncre; varying vec2 vP;
      void main(){ float r = length(vP); float a = smoothstep(1.28, 1., r) * .16 * smoothstep(.95, 1.02, r) + smoothstep(1.12, .99, r) * .06;
        gl_FragColor = vec4(uEncre, a * uNaissance * (1. - uSombre * .35)); }`,
  }));
  ombre.position.z = -5; scene.add(ombre);

  // la sphère claire : un peu plus foncée sur le bord, éclairée du haut à gauche
  terre.add(new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), new THREE.ShaderMaterial({
    uniforms: U, transparent: true,
    vertexShader: 'varying vec3 vN; void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
    fragmentShader: `uniform float uNaissance, uSombre; varying vec3 vN;
      void main(){ float f = 1. - max(vN.z, 0.), l = max(dot(vN, normalize(vec3(-.5, .6, .65))), 0.);
        vec3 c = mix(mix(vec3(.875, .905, .915), vec3(.77, .8, .815), pow(f, 1.6)), mix(vec3(.15, .125, .125), vec3(.25, .22, .22), pow(f, 1.6)), uSombre) + vec3(.04) * l;
        gl_FragColor = vec4(c, uNaissance); }`,
  })));

  // les continents : des points, qui naissent depuis Bruxelles
  const ll = new Int16Array(await fetch('/apropos/terre.bin').then(r => r.arrayBuffer())), n = ll.length / 2;
  const pos = new Float32Array(n * 3), al = new Float32Array(n);
  for (let i = 0; i < n; i++) { const p = sph(ll[2 * i] / 100, ll[2 * i + 1] / 100, 1.003); pos.set([p.x, p.y, p.z], i * 3); al[i] = Math.random(); }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); pg.setAttribute('aR', new THREE.BufferAttribute(al, 1));
  const points = new THREE.Points(pg, new THREE.ShaderMaterial({
    uniforms: U, transparent: true, depthWrite: false,
    vertexShader: `uniform float uTaille, uTemps, uNaissance; uniform vec3 uBxl; attribute float aR; varying float vA;
      void main(){ vec3 n = normalize(normalMatrix * position);
        float d = acos(clamp(dot(normalize(position), uBxl), -1., 1.)) / 3.1416;          // distance à Bruxelles (0 à 1)
        float nee = smoothstep(d - .02, d + .02 + aR * .05, uNaissance * 1.15);
        vA = smoothstep(-.02, .3, n.z) * (.5 + .5 * aR) * nee;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.);
        gl_PointSize = uTaille * (.75 + .35 * n.z) * (.4 + .6 * nee); }`,
    fragmentShader: `uniform vec3 uEncre; varying float vA; void main(){ float r = length(gl_PointCoord - .5); if (r > .5) discard;
      gl_FragColor = vec4(uEncre, smoothstep(.5, .2, r) * vA); }`,
  }));
  points.renderOrder = 2; terre.add(points);

  // Bruxelles : un point et un anneau qui pulse
  const marque = new THREE.Group(), pB = sph(...BXL, 1.004); marque.position.copy(pB); marque.lookAt(pB.clone().multiplyScalar(2)); terre.add(marque);
  const point = new THREE.Mesh(new THREE.CircleGeometry(.013, 24), new THREE.MeshBasicMaterial({ color: NOIR, transparent: true, depthTest: false })); point.renderOrder = 6; marque.add(point);
  const anneau = new THREE.Mesh(new THREE.RingGeometry(.9, 1, 48), new THREE.MeshBasicMaterial({ color: NOIR, transparent: true, depthTest: false })); anneau.renderOrder = 5; marque.add(anneau);

  // les arcs vers d'autres villes, parcourus par une lueur ; ils se tracent après la naissance des points
  const arcs = [];
  VILLES.forEach(([, la, lo], k) => {
    const A = sph(...BXL), B = sph(la, lo), ang = A.angleTo(B), h = .04 + ang * .22, N = 64, pts = [], t = new Float32Array(N + 1);
    for (let i = 0; i <= N; i++) { const s = i / N; pts.push(A.clone().lerp(B, s).normalize().multiplyScalar(1 + Math.sin(Math.PI * s) * h)); t[i] = s; }
    const g = new THREE.BufferGeometry().setFromPoints(pts); g.setAttribute('aT', new THREE.BufferAttribute(t, 1));
    const u = { uTemps: U.uTemps, uDecal: { value: Math.random() }, uTrace: { value: 0 }, uEncre: U.uEncre };
    const l = new THREE.Line(g, new THREE.ShaderMaterial({
      uniforms: u, transparent: true, depthWrite: false,
      vertexShader: 'attribute float aT; varying float vT; varying float vF; void main(){ vT = aT; vF = normalize(normalMatrix * position).z; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
      fragmentShader: `uniform float uTemps, uDecal, uTrace; uniform vec3 uEncre; varying float vT; varying float vF;
        void main(){ if (vT > uTrace) discard; float p = fract(uTemps * .18 + uDecal), lueur = exp(-pow((vT - p) * 9., 2.));
          float a = (.3 + .7 * lueur) * smoothstep(0., .06, vT) * smoothstep(-.15, .2, vF);
          gl_FragColor = vec4(uEncre, a); }`,
    }));
    l.renderOrder = 4; terre.add(l);
    const d = new THREE.Mesh(new THREE.CircleGeometry(.006, 16), new THREE.MeshBasicMaterial({ color: NOIR, transparent: true, opacity: 0 }));
    const pb = sph(la, lo, 1.004); d.position.copy(pb); d.lookAt(pb.clone().multiplyScalar(2)); d.renderOrder = 5; terre.add(d);
    arcs.push({ u, d, retard: .55 + k * .07 });
  });

  const G = { sombre: sombre ? 1 : 0, t: 0, naissance: -1, glisse: 0, vit: 0, drag: null, vu: false, raf: 0, avant: 0, taille: 1 };
  const taille = () => { const r = boite.getBoundingClientRect(); G.taille = r.width; renderer.setSize(r.width, r.height, false); U.uTaille.value = Math.max(1.5, r.width / 520) * renderer.getPixelRatio(); };
  taille(); addEventListener('resize', taille);
  cv.addEventListener('pointerdown', e => { G.drag = { x: e.clientX, g: G.glisse }; cv.setPointerCapture(e.pointerId); boite.classList.add('tire'); });
  cv.addEventListener('pointermove', e => { if (!G.drag) return; const v = G.drag.g + (e.clientX - G.drag.x) / (G.taille / 2.6) * 1.2; G.vit = v - G.glisse; G.glisse = v; });
  const lache = () => { G.drag = null; boite.classList.remove('tire'); };
  cv.addEventListener('pointerup', lache); cv.addEventListener('pointercancel', lache);

  const qA = new THREE.Quaternion(), qB = new THREE.Quaternion(), X = new THREE.Vector3(1, 0, 0), Y = new THREE.Vector3(0, 1, 0), v = new THREE.Vector3();
  function image(now) {
    G.raf = G.vu ? requestAnimationFrame(image) : 0;
    const dt = Math.min(.05, (now - (G.avant || now)) / 1000); G.avant = now; G.t += dt;
    if (G.naissance >= 0) G.naissance += dt;
    const nai = CALME ? 1 : ease(G.naissance / 2.4);
    U.uNaissance.value = Math.max(0, nai); U.uTemps.value = G.t;
    U.uSombre.value += (G.sombre - U.uSombre.value) * Math.min(1, dt * 4); U.uEncre.value.copy(NOIR).lerp(BLANC, U.uSombre.value);   // le thème change en douceur
    point.material.color.copy(U.uEncre.value); anneau.material.color.copy(U.uEncre.value); arcs.forEach(a => a.d.material.color.copy(U.uEncre.value));
    if (!G.drag) { G.glisse += G.vit; G.vit *= .92; G.glisse *= Math.pow(.35, dt); }
    const lon = CENTRE[1] + (CALME ? 0 : Math.sin(G.t * .16) * 14 - (1 - nai) * 40) - G.glisse / RAD;   // (à la naissance, elle arrive en tournant)
    qA.setFromAxisAngle(X, CENTRE[0] * RAD); qB.setFromAxisAngle(Y, -lon * RAD); terre.quaternion.copy(qA).multiply(qB);
    const k = (G.t * .7) % 1; anneau.scale.setScalar(.013 + k * .05); anneau.material.opacity = (1 - k) * .8 * nai; point.material.opacity = nai;
    arcs.forEach(a => { const s = CALME ? 1 : ease((G.naissance - 1.2 - a.retard) / 1.4); a.u.uTrace.value = s; a.d.material.opacity = s > .98 ? .8 : 0; });
    renderer.render(scene, cam);
    if (etiquette) {
      v.copy(pB).applyMatrix4(terre.matrixWorld);
      etiquette.style.transform = `translate(${((v.x / 2.6 + .5) * G.taille).toFixed(1)}px, ${((-v.y / 2.6 + .5) * G.taille).toFixed(1)}px)`;
      etiquette.style.opacity = v.z > .15 && nai > .6 ? 1 : 0;
    }
  }
  addEventListener('theme', e => { G.sombre = e.detail ? 1 : 0; if (G.vu && !G.raf) G.raf = requestAnimationFrame(image); });
  new IntersectionObserver(([e]) => {
    G.vu = e.isIntersecting;
    if (G.vu) { if (G.naissance < 0) G.naissance = 0; if (!G.raf) { G.avant = 0; G.raf = requestAnimationFrame(image); } }
  }, { threshold: .15 }).observe(boite);
  return G;
}
