/**
 * LEGO-themed Three.js scene builder
 * Transforms manifest / LEGO set data into an interactive 3D LEGO brick scene
 */

import type { ManifestData } from './legoManualGenerator';

// LEGO Color ID → hex for Three.js
const LEGO_COLOR_HEX: Record<number, number> = {
  0: 0x1b1b1b,   // Black
  1: 0x0055bf,   // Blue
  2: 0x237841,   // Green
  3: 0x008f9b,   // Dark Turquoise
  4: 0xc91a09,   // Red
  5: 0xc870a0,   // Dark Pink
  6: 0x583927,   // Brown
  7: 0x9ba19d,   // Light Gray
  8: 0x6d6e5c,   // Dark Gray
  9: 0x4fa3d1,   // Light Blue
  10: 0x4b9f4a,  // Bright Green
  11: 0x55a5af,  // Light Turquoise
  12: 0xf4a8b8,  // Salmon
  13: 0xdf6695,  // Pink
  14: 0xf2cd37,  // Yellow
  15: 0xf4f4f4,  // White
  16: 0xbbd269,  // Light Green
  17: 0xffe166,  // Light Yellow
  19: 0xe4cd9e,  // Tan
  20: 0xc9cade,  // Light Violet
  22: 0x81007b,  // Purple
  25: 0xfe8a18,  // Orange
  26: 0x923978,  // Magenta
  27: 0xbfe90a,  // Lime
  28: 0x958a73,  // Dark Tan
  29: 0xff69b4,  // Bright Pink
  36: 0xc91a09,  // Trans-Red (use red)
  70: 0x582a12,  // Reddish Brown
  71: 0xa0a5a9,  // Light Bluish Gray
  72: 0x6c6e68,  // Dark Bluish Gray
  85: 0x364892,  // Dark Purple
};

// Part ID → [studWidth, studDepth] for brick footprint (studs). Height in brick units.
const PART_DIMS: Record<string, [number, number]> = {
  '3005': [1, 1], '3024': [1, 1], '3070': [1, 1],
  '3004': [1, 2], '3023': [1, 2], '3069': [1, 2],
  '3622': [1, 3], '3010': [1, 4], '3009': [1, 6], '3008': [1, 8],
  '3003': [2, 2], '3022': [2, 2], '3068': [2, 2],
  '3002': [2, 3], '3021': [2, 3],
  '3001': [2, 4], '3020': [2, 4], '3795': [2, 6], '3034': [2, 8],
  '3007': [2, 8], '3006': [2, 10],
  '628': [16, 16], '3811': [32, 32], '10701': [48, 48],
};

// 1 stud in our scene units
const STUD = 0.2;
// 1 brick height (3 plates)
const BRICK_H = 0.96 * STUD;
// 1 plate height
const PLATE_H = 0.32 * STUD;
// Stud cylinder
const STUD_R = 0.24 * STUD;
const STUD_H = 0.17 * STUD;

function getPartDims(partId: string): [number, number] {
  return PART_DIMS[partId] || [1, 1];
}

function isPlateOrTile(partId: string): boolean {
  return /^30(24|23|22|21|20|34|68|69|70)$/.test(partId) || /^3795$/.test(partId);
}

function isBaseplate(partId: string): boolean {
  return /^(628|3811|10701)$/.test(partId);
}

function getColorHex(colorId: number): number {
  return LEGO_COLOR_HEX[colorId] ?? 0x9ba19d;
}

/**
 * Create a single LEGO brick mesh (box + studs on top)
 */
function createLegoBrick(
  THREE: typeof import('three'),
  partId: string,
  colorId: number,
  rotationDeg: number
): THREE.Group {
  const [w, d] = getPartDims(partId);
  const hex = getColorHex(colorId);

  const isPlate = isPlateOrTile(partId);
  const isBase = isBaseplate(partId);

  let bodyH: number;
  if (isBase) bodyH = PLATE_H * 0.8;
  else if (isPlate) bodyH = PLATE_H;
  else bodyH = BRICK_H;

  const group = new THREE.Group();

  // Body
  const bodyW = w * STUD * 0.8;
  const bodyD = d * STUD * 0.8;
  const bodyGeo = new THREE.BoxGeometry(bodyW, bodyH, bodyD);
  const mat = new THREE.MeshStandardMaterial({
    color: hex,
    roughness: 0.35,
    metalness: 0.05,
  });
  const body = new THREE.Mesh(bodyGeo, mat);
  body.castShadow = true;
  body.receiveShadow = true;
  group.add(body);

  // Studs on top (skip for baseplates and very large; limit for perf)
  if (!isBase && w <= 4 && d <= 4) {
    const studGeo = new THREE.CylinderGeometry(STUD_R, STUD_R, STUD_H, 12);
    const studMat = new THREE.MeshStandardMaterial({
      color: hex,
      roughness: 0.3,
      metalness: 0.08,
    });
    for (let ix = 0; ix < w; ix++) {
      for (let iz = 0; iz < d; iz++) {
        const stud = new THREE.Mesh(studGeo, studMat);
        stud.position.set(
          (ix - (w - 1) / 2) * STUD * 0.8,
          bodyH / 2 + STUD_H / 2,
          (iz - (d - 1) / 2) * STUD * 0.8
        );
        stud.castShadow = true;
        group.add(stud);
      }
    }
  }

  // Rotation: 0, 90, 180, 270
  const r = (rotationDeg * Math.PI) / 180;
  group.rotation.y = r;

  return group;
}

/**
 * Build a full LEGO scene from manifest data
 */
export async function buildLegoSceneFromManifest(
  container: HTMLElement,
  manifest: ManifestData,
  options?: {
    showBaseplate?: boolean;
    studScale?: number;
  }
): Promise<{
  scene: import('three').Scene;
  camera: import('three').PerspectiveCamera;
  renderer: import('three').WebGLRenderer;
  controls: import('three/examples/jsm/controls/OrbitControls').OrbitControls;
  cleanup: () => void;
}> {
  const THREE = await import('three');
  const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');

  const width = container.clientWidth || 800;
  const height = container.clientHeight || 600;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf2f2f0);
  scene.fog = new THREE.Fog(0xf2f2f0, 8, 20);

  const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 100);
  camera.position.set(4, 3, 5);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.style.display = 'block';
  renderer.domElement.style.width = '100%';
  renderer.domElement.style.height = '100%';
  renderer.domElement.style.position = 'absolute';
  renderer.domElement.style.top = '0';
  renderer.domElement.style.left = '0';
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1, 0);
  controls.enableDamping = true;

  // Lighting
  const amb = new THREE.AmbientLight(0xffffff, 0.55);
  scene.add(amb);

  const dir = new THREE.DirectionalLight(0xffffff, 0.7);
  dir.position.set(5, 10, 5);
  dir.castShadow = true;
  dir.shadow.mapSize.set(1024, 1024);
  scene.add(dir);

  const fill = new THREE.DirectionalLight(0xccddff, 0.25);
  fill.position.set(-3, 2, -2);
  scene.add(fill);

  // Center and scale: manifest uses stud grid. 1 unit = 1 stud * STUD
  const bricks = manifest.bricks;
  if (bricks.length === 0) {
    const g = createLegoBrick(THREE, '3001', 4, 0);
    scene.add(g);
  } else {
    let minX = Infinity, maxX = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    for (const b of bricks) {
      const [w, d] = getPartDims(b.part_id);
      const rx = b.rotation === 90 || b.rotation === 270 ? d : w;
      const rz = b.rotation === 90 || b.rotation === 270 ? w : d;
      minX = Math.min(minX, b.position[0]);
      maxX = Math.max(maxX, b.position[0] + rx);
      minZ = Math.min(minZ, b.position[2]);
      maxZ = Math.max(maxZ, b.position[2] + rz);
      minY = Math.min(minY, b.position[1]);
      maxY = Math.max(maxY, b.position[1] + 1);
    }
    const centerX = (minX + maxX) / 2;
    const centerZ = (minZ + maxZ) / 2;

    const buildGroup = new THREE.Group();
    for (const b of bricks) {
      const brick = createLegoBrick(THREE, b.part_id, b.color_id, b.rotation || 0);
      const [w, d] = getPartDims(b.part_id);
      const rx = b.rotation === 90 || b.rotation === 270 ? d : w;
      const rz = b.rotation === 90 || b.rotation === 270 ? w : d;
      brick.position.set(
        (b.position[0] + rx / 2 - centerX) * STUD,
        (b.position[1] - minY) * BRICK_H,
        (b.position[2] + rz / 2 - centerZ) * STUD
      );
      buildGroup.add(brick);
    }
    scene.add(buildGroup);
  }

  // Baseplate as ground (optional)
  if (options?.showBaseplate !== false) {
    const baseGeo = new THREE.PlaneGeometry(40, 40);
    const baseMat = new THREE.MeshStandardMaterial({
      color: getColorHex(28), // Dark Tan
      roughness: 0.9,
    });
    const base = new THREE.Mesh(baseGeo, baseMat);
    base.rotation.x = -Math.PI / 2;
    base.position.y = -0.5;
    base.receiveShadow = true;
    scene.add(base);
  }

  const animate = () => {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  };
  animate();

  const handleResize = () => {
    if (!container) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  };
  window.addEventListener('resize', handleResize);
  handleResize();

  const cleanup = () => {
    window.removeEventListener('resize', handleResize);
    if (container && renderer.domElement.parentNode === container) {
      container.removeChild(renderer.domElement);
    }
    renderer.dispose();
  };

  return { scene, camera, renderer, controls, cleanup };
}
