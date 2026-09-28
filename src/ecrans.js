/* ═════════════ Le Macintosh et l'iPhone en 3D (section « Adaptive design ») ═════════════
   - l'écran affiche l'image ou la vidéo choisie dans l'admin (src/accueil.json), recadrée comme « cover » :
     si elle n'a pas la bonne forme, on zoome dedans (sans jamais la déformer)
   - l'écran garde ses reflets : un verre brillant par-dessus, qui reflète la pièce (environnement)
   - le modèle s'oriente légèrement vers la souris, sans jamais tourner assez pour cacher l'écran
   - il n'est dessiné que quand il est à l'écran ; la vidéo ne joue que quand on la voit */
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

// forme de l'écran (largeur / hauteur) et zone de l'écran dans les coordonnées de texture du modèle
export const ECRANS = {
  iphone: { fichier: '/modeles/iphone.glb', taille: .86, mat: 'Screen', verre: 'Screen_glass', ratio: 1206 / 2622, rot: 0, uv: [.0356, .0125, .9700, .9840], flipU: false, flipV: false },
  mac: { fichier: '/modeles/mac.glb', taille: .74, mat: 'TVScreen', verre: null, ratio: 4 / 3, rot: Math.PI, uv: [-.0048, .1810, .9954, .8190], flipU: false, flipV: true },
};

const chargeur = new GLTFLoader();
const txChargeur = new THREE.TextureLoader();

function recadrer(tex, S, w, h) {                  // la texture remplit la zone de l'écran, recadrée au centre si besoin
  const [u0, v0, u1, v1] = S.uv, ar = w / h;
  let sx = 1, sy = 1;
  if (ar > S.ratio) sx = S.ratio / ar; else sy = ar / S.ratio;          // la partie de l'image qu'on garde
  tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.repeat.set(sx / (u1 - u0) * (S.flipU ? -1 : 1), sy / (v1 - v0) * (S.flipV ? -1 : 1));
  tex.offset.set((S.flipU ? 1 : 0) + (1 - sx) / 2 * (S.flipU ? -1 : 1) - u0 * tex.repeat.x, (S.flipV ? 1 : 0) + (1 - sy) / 2 * (S.flipV ? -1 : 1) - v0 * tex.repeat.y);
  tex.needsUpdate = true;
}

function texteDefaut(nom) {                          // en attendant un média : un écran aux couleurs du site
  const [w, h] = nom === 'iphone' ? [603, 1311] : [1024, 768];
  const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#eff6f8'); gr.addColorStop(1, '#d9e4e8'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
  g.fillStyle = '#2a2222'; g.textAlign = 'center'; g.font = `${Math.round(w * .09)}px "Argesta Display", Georgia, serif`;
  g.fillText('Your project', w / 2, h / 2 - w * .02); g.fillText('here', w / 2, h / 2 + w * .09);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.flipY = false; return [t, w, h];
}

export async function creerEcran(boite, nom, media = {}, { base = [0, 0], amplitude = [.32, .16], echelle = .82, incl = 0 } = {}) {
  const S = ECRANS[nom];
  const cv = document.createElement('canvas'); cv.className = 'ecran-cv'; boite.appendChild(cv);
  const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  const scene = new THREE.Scene();
  const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), .04).texture; pm.dispose();
  const cam = new THREE.PerspectiveCamera(24, 1, .01, 50);
  // le même studio pour les deux : une lumière principale qui porte une ombre douce au sol, un contre-jour qui détache la silhouette
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.VSMShadowMap;   // (ombre floue, comme une lumière de studio diffuse)
  const cle = new THREE.DirectionalLight(0xffffff, 1.5); cle.position.set(-.9, 3.6, 1.5); cle.castShadow = true; scene.add(cle);
  Object.assign(cle.shadow.camera, { left: -.9, right: .9, top: .9, bottom: -.9, near: .5, far: 8 }); cle.shadow.mapSize.set(1024, 1024); cle.shadow.bias = -.0006; cle.shadow.radius = 14; cle.shadow.blurSamples = 20;
  const contre = new THREE.DirectionalLight(0xdfe8ff, .9); contre.position.set(1.8, 1.4, -2.6); scene.add(contre);
  const pivot = new THREE.Group(); scene.add(pivot);

  const gltf = await chargeur.loadAsync(S.fichier), modele = gltf.scene;
  // centrer et mettre à l'échelle (le modèle tient dans une boîte de 1)
  const bb = new THREE.Box3().setFromObject(modele), c = bb.getCenter(new THREE.Vector3()), s = bb.getSize(new THREE.Vector3());
  modele.position.sub(c); const k = (S.taille || echelle) / s.y; const hold = new THREE.Group(); hold.scale.setScalar(k); hold.rotation.y = S.rot; hold.add(modele); pivot.add(hold);   // (même hauteur à l'écran pour les deux ; tourné pour que l'écran nous fasse face)
  cam.position.set(0, .32, 2.6); cam.lookAt(0, -.03, 0);
  // l'ombre au sol, sous l'objet : elle suit ses mouvements
  const sol = new THREE.Mesh(new THREE.PlaneGeometry(3, 3), new THREE.ShadowMaterial({ opacity: .12 })); sol.rotation.x = -Math.PI / 2; sol.position.y = -(S.taille || echelle) / 2 - .06; sol.receiveShadow = true; scene.add(sol);

  // l'écran : l'image ou la vidéo, lumineuse, sous un verre qui reflète la pièce
  let ecran = null, verre = null;
  modele.traverse(o => { if (!o.isMesh) return; if (o.material?.name === S.mat) ecran = o; if (S.verre && o.material?.name === S.verre && o.geometry.boundingBox?.max?.y !== undefined) verre = verre || o; });
  modele.traverse(o => { if (o.isMesh && o.material) { o.material.envMapIntensity = 1; o.castShadow = !/glass/i.test(o.material.name); } });
  if (nom === 'mac') modele.traverse(o => {                                      // le plastique beige du Macintosh : satiné, avec un léger vernis (comme les objets en verre autour)
    if (!o.isMesh || !o.material || o.material.name === S.mat) return;
    const m = o.material, corps = m.name === 'material' || m.name === 'MacMetal';
    o.material = new THREE.MeshPhysicalMaterial({ name: m.name, map: m.map, normalMap: m.normalMap, normalScale: m.normalScale, color: corps ? new THREE.Color('#f6efe0') : m.color,
      roughness: corps ? .42 : .5, metalness: 0, clearcoat: corps ? .5 : .25, clearcoatRoughness: .3, sheen: corps ? .25 : 0, sheenRoughness: .6, sheenColor: new THREE.Color('#fff6e6'), envMapIntensity: 1.2 });
  });
  const matEcran = new THREE.MeshPhysicalMaterial({ color: 0x000000, emissive: 0xffffff, emissiveIntensity: .92, roughness: .08, metalness: 0, clearcoat: 1, clearcoatRoughness: .04, envMapIntensity: 1.1 });
  if (ecran) ecran.material = matEcran;
  // la Dynamic Island de l'iPhone : une pilule noire et brillante en haut de l'écran, par-dessus l'image
  if (nom === 'iphone' && ecran) {
    const [u0, v0, u1, v1] = S.uv;
    const ile = new THREE.Mesh(ecran.geometry, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
      uniforms: { uR: { value: new THREE.Vector4(u0, v0, u1 - u0, v1 - v0) } },
      vertexShader: 'varying vec2 vU; varying vec3 vN; varying vec3 vV; void main(){ vU = uv; vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position, 1.); vV = -mv.xyz; gl_Position = projectionMatrix * mv; }',
      fragmentShader: `uniform vec4 uR; varying vec2 vU; varying vec3 vN; varying vec3 vV;
        void main(){
          vec2 q = (vU - uR.xy) / uR.zw;                                   // 0..1 sur l'écran (haut = 0)
          vec2 p = vec2((q.x - .5) * ${(1206).toFixed(1)}, (q.y - .0355) * ${(2622).toFixed(1)});   // en pixels de l'écran
          vec2 h = vec2(186., 54.);                                        // la pilule : 372 × 108 px (demi-tailles)
          vec2 d = abs(p) - h + vec2(54.); float sd = length(max(d, 0.)) + min(max(d.x, d.y), 0.) - 54.;
          float a = 1. - smoothstep(-1.5, 1.5, sd); if (a < .01) discard;
          float sheen = pow(max(dot(reflect(-normalize(vV), normalize(vN)), normalize(vec3(-.3, .6, .7))), 0.), 24.) * .25;
          gl_FragColor = vec4(vec3(.012) + sheen, a); }`,
    }));
    ile.renderOrder = 2; ecran.add(ile);
  }
  modele.traverse(o => { if (o.isMesh && S.verre && o.material?.name === S.verre) { o.material = o.material.clone(); o.material.envMapIntensity = 1.6; o.material.roughness = .03; o.renderOrder = 3; } });

  let video = null;
  const poser = (tex, w, h) => { tex.flipY = false; tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8; recadrer(tex, S, w, h); matEcran.emissiveMap = tex; matEcran.needsUpdate = true; };
  const [t0, w0, h0] = texteDefaut(nom); poser(t0, w0, h0);
  if (media.video) {
    video = Object.assign(document.createElement('video'), { src: media.video, muted: true, loop: true, playsInline: true, preload: 'auto', crossOrigin: 'anonymous' });
    video.setAttribute('muted', ''); video.setAttribute('playsinline', '');
    video.addEventListener('loadeddata', () => poser(new THREE.VideoTexture(video), video.videoWidth, video.videoHeight), { once: true });
    if (media.image) txChargeur.load(media.image, t => { if (!video.videoWidth) poser(t, t.image.width, t.image.height); });
  } else if (media.image) txChargeur.load(media.image, t => poser(t, t.image.width, t.image.height));

  // la souris : le modèle se tourne un peu vers elle (l'écran reste toujours face à nous)
  const E = { mx: 0, my: 0, rx: 0, ry: 0, vu: false, raf: 0, t: 0, entree: 0, avant: 0, tour: matchMedia('(prefers-reduced-motion: reduce)').matches ? 1 : 0, attente: 0 };
  const sens = nom === 'mac' ? 1 : -1;                                           // (le Mac et l'iPhone se retournent dans des sens opposés)
  addEventListener('pointermove', e => { E.mx = e.clientX / innerWidth * 2 - 1; E.my = e.clientY / innerHeight * 2 - 1; }, { passive: true });
  addEventListener('incline', e => { E.mx = e.detail.nx; E.my = e.detail.ny; });   // (téléphone : l'inclinaison)
  const taille = () => { const r = boite.getBoundingClientRect(); renderer.setSize(r.width, r.height, false); cam.aspect = r.width / Math.max(1, r.height); cam.updateProjectionMatrix(); };
  taille(); addEventListener('resize', taille);

  function image(now) {
    E.raf = E.vu ? requestAnimationFrame(image) : 0;
    if (window.__pause3D && E.rendu) { E.avant = now; return; }                  // (derrière la vitre, et pendant sa chute : on attend)
    const brut = (now - (E.avant || now)) / 1000, dt = Math.min(.05, brut); E.avant = now; E.t += dt;
    const f = 1 - Math.exp(-dt * 4);
    E.ry += (base[1] + E.mx * amplitude[0] - E.ry) * f; E.rx += (base[0] + E.my * amplitude[1] - E.rx) * f;
    // l'arrivée : il est de dos, puis se retourne pour montrer son écran (un léger dépassement, comme un objet qu'on pose)
    if (E.tour < 1 && !window.__pause3D && boite.classList.contains('vu')) E.tour = Math.min(1, E.tour + dt / 1.3);
    const u = E.tour - 1, ret = 1 + 2.1 * u * u * u + 1.1 * u * u, bosse = Math.sin(E.tour * Math.PI);
    pivot.rotation.set(E.rx + bosse * .1, E.ry + sens * (1 - ret) * Math.PI, incl * ret);
    pivot.position.y = Math.sin(E.t * .9) * .015 + bosse * .05;
    renderer.render(scene, cam); E.rendu = true;
  }
  new IntersectionObserver(([e]) => {
    E.vu = e.isIntersecting;
    if (video) E.vu ? video.play().catch(() => {}) : video.pause();
    if (E.vu && !E.raf) { E.avant = 0; E.raf = requestAnimationFrame(image); }
  }, { threshold: .05 }).observe(boite);
  return E;
}
