/**
 * Three.js Mesh Voxelizer
 * 
 * Converts any Three.js Mesh into a voxel grid using raycasting
 * for inside/outside detection. This generates the voxel data needed
 * for the MasterBuilder service.
 */

import * as THREE from 'three';

export interface Voxel {
  x: number;
  y: number;
  z: number;
  hex_color: string;
}

export interface VoxelGrid {
  voxels: Voxel[];
  bounding_box: {
    min: [number, number, number];
    max: [number, number, number];
  };
  resolution: number; // Voxel size in millimeters
}

/**
 * Voxelize a Three.js mesh using raycasting for inside/outside detection
 * 
 * @param mesh - Three.js Mesh object to voxelize
 * @param resolution - Size of each voxel in millimeters (default: 8mm = 1 LEGO stud)
 * @param colorMap - Function to map mesh position to color (default: uses mesh material)
 * @returns VoxelGrid with all filled voxels
 */
export function voxelizeMesh(
  mesh: THREE.Mesh,
  resolution: number = 8.0, // 8mm = 1 LEGO stud
  colorMap?: (position: THREE.Vector3) => string
): VoxelGrid {
  // Compute bounding box
  const box = new THREE.Box3().setFromObject(mesh);
  const min = box.min;
  const max = box.max;

  // Calculate grid dimensions
  const width = Math.ceil((max.x - min.x) / resolution);
  const height = Math.ceil((max.y - min.y) / resolution);
  const depth = Math.ceil((max.z - min.z) / resolution);

  // Create raycaster for inside/outside detection
  const raycaster = new THREE.Raycaster();
  const direction = new THREE.Vector3(1, 0, 0); // Ray direction (X-axis)
  
  // Get mesh geometry
  const geometry = mesh.geometry;
  if (!geometry.isBufferGeometry) {
    throw new Error('Mesh must use BufferGeometry');
  }

  // Ensure geometry has position attribute
  if (!geometry.attributes.position) {
    throw new Error('Mesh geometry must have position attribute');
  }

  // Compute bounding sphere for optimization
  geometry.computeBoundingSphere();
  const boundingSphere = geometry.boundingSphere;
  if (!boundingSphere) {
    throw new Error('Could not compute bounding sphere');
  }

  // Transform geometry to world space
  const worldMatrix = mesh.matrixWorld;
  const worldGeometry = geometry.clone();
  worldGeometry.applyMatrix4(worldMatrix);

  // Get material for color extraction
  const material = mesh.material;
  const getColor = colorMap || ((pos: THREE.Vector3) => {
    if (material instanceof THREE.MeshStandardMaterial || 
        material instanceof THREE.MeshBasicMaterial) {
      if (material.color) {
        return '#' + material.color.getHexString().padStart(6, '0');
      }
    }
    return '#FFFFFF'; // Default white
  });

  const voxels: Voxel[] = [];
  const voxelSet = new Set<string>(); // For deduplication

  // Sample points in the bounding box
  for (let z = 0; z < depth; z++) {
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        // Calculate world position of voxel center
        const voxelPos = new THREE.Vector3(
          min.x + (x + 0.5) * resolution,
          min.y + (y + 0.5) * resolution,
          min.z + (z + 0.5) * resolution
        );

        // Quick bounding sphere check
        const distanceToCenter = voxelPos.distanceTo(boundingSphere.center);
        if (distanceToCenter > boundingSphere.radius + resolution) {
          continue; // Outside bounding sphere
        }

        // Raycast to determine if point is inside mesh
        const isInside = isPointInsideMesh(voxelPos, worldGeometry, raycaster);

        if (isInside) {
          const key = `${x},${y},${z}`;
          if (!voxelSet.has(key)) {
            voxelSet.add(key);
            
            // Get color for this voxel
            const color = getColor(voxelPos);
            
            voxels.push({
              x: Math.round(voxelPos.x / resolution), // Convert to stud coordinates
              y: Math.round(voxelPos.y / resolution),
              z: Math.round(voxelPos.z / resolution),
              hex_color: color
            });
          }
        }
      }
    }
  }

  return {
    voxels,
    bounding_box: {
      min: [
        Math.floor(min.x / resolution),
        Math.floor(min.y / resolution),
        Math.floor(min.z / resolution)
      ],
      max: [
        Math.ceil(max.x / resolution),
        Math.ceil(max.y / resolution),
        Math.ceil(max.z / resolution)
      ]
    },
    resolution
  };
}

/**
 * Ray-triangle intersection test (Möller–Trumbore algorithm)
 */
function rayIntersectTriangle(
  ray: THREE.Ray,
  v0: THREE.Vector3,
  v1: THREE.Vector3,
  v2: THREE.Vector3
): THREE.Vector3 | null {
  const EPSILON = 0.0000001;
  const edge1 = new THREE.Vector3().subVectors(v1, v0);
  const edge2 = new THREE.Vector3().subVectors(v2, v0);
  const h = new THREE.Vector3().crossVectors(ray.direction, edge2);
  const a = edge1.dot(h);
  
  if (a > -EPSILON && a < EPSILON) {
    return null; // Ray is parallel to triangle
  }
  
  const f = 1.0 / a;
  const s = new THREE.Vector3().subVectors(ray.origin, v0);
  const u = f * s.dot(h);
  
  if (u < 0.0 || u > 1.0) {
    return null;
  }
  
  const q = new THREE.Vector3().crossVectors(s, edge1);
  const v = f * ray.direction.dot(q);
  
  if (v < 0.0 || u + v > 1.0) {
    return null;
  }
  
  const t = f * edge2.dot(q);
  if (t > EPSILON) {
    return ray.at(t);
  }
  
  return null;
}

/**
 * Check if a point is inside a mesh using raycasting
 * Uses the "ray casting" algorithm: cast a ray and count intersections
 * 
 * @param point - Point to test
 * @param geometry - BufferGeometry of the mesh
 * @param raycaster - THREE.Raycaster instance
 * @returns True if point is inside the mesh
 */
function isPointInsideMesh(
  point: THREE.Vector3,
  geometry: THREE.BufferGeometry,
  raycaster: THREE.Raycaster
): boolean {
  // Cast ray from point in positive X direction
  const ray = new THREE.Ray(point, new THREE.Vector3(1, 0, 0));
  raycaster.set(ray.origin, ray.direction);

  // Get position attribute
  const positions = geometry.attributes.position;
  const indices = geometry.index;

  let intersectionCount = 0;

  if (indices) {
    // Indexed geometry
    for (let i = 0; i < indices.count; i += 3) {
      const i0 = indices.getX(i);
      const i1 = indices.getX(i + 1);
      const i2 = indices.getX(i + 2);

      const v0 = new THREE.Vector3(
        positions.getX(i0),
        positions.getY(i0),
        positions.getZ(i0)
      );
      const v1 = new THREE.Vector3(
        positions.getX(i1),
        positions.getY(i1),
        positions.getZ(i1)
      );
      const v2 = new THREE.Vector3(
        positions.getX(i2),
        positions.getY(i2),
        positions.getZ(i2)
      );

      // Check if ray intersects triangle using manual intersection test
      const intersection = rayIntersectTriangle(ray, v0, v1, v2);
      if (intersection) {
        intersectionCount++;
      }
    }
  } else {
    // Non-indexed geometry
    for (let i = 0; i < positions.count; i += 3) {
      const v0 = new THREE.Vector3(
        positions.getX(i),
        positions.getY(i),
        positions.getZ(i)
      );
      const v1 = new THREE.Vector3(
        positions.getX(i + 1),
        positions.getY(i + 1),
        positions.getZ(i + 1)
      );
      const v2 = new THREE.Vector3(
        positions.getX(i + 2),
        positions.getY(i + 2),
        positions.getZ(i + 2)
      );

      const intersection = rayIntersectTriangle(ray, v0, v1, v2);
      if (intersection) {
        intersectionCount++;
      }
    }
  }

  // Odd number of intersections = inside, even = outside
  return intersectionCount % 2 === 1;
}

/**
 * Convert Three.js JSON format to Three.js Mesh
 * 
 * @param threejsData - Three.js JSON object with vertices and faces
 * @returns THREE.Mesh object
 */
export function threejsJsonToMesh(threejsData: {
  vertices: number[][];
  faces: number[][];
  normals?: number[][];
  colors?: string[];
}): THREE.Mesh {
  const geometry = new THREE.BufferGeometry();
  
  // Convert vertices to Float32Array
  const positions: number[] = [];
  threejsData.vertices.forEach(v => {
    positions.push(v[0], v[1], v[2]);
  });
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));

  // Convert faces to indices
  const indices: number[] = [];
  threejsData.faces.forEach(face => {
    indices.push(face[0], face[1], face[2]);
  });
  geometry.setIndex(indices);

  // Add normals if provided
  if (threejsData.normals) {
    const normals: number[] = [];
    threejsData.normals.forEach(n => {
      normals.push(n[0], n[1], n[2]);
    });
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  } else {
    geometry.computeVertexNormals();
  }

  // Create material with colors if provided
  let material: THREE.Material;
  if (threejsData.colors && threejsData.colors.length > 0) {
    const colors: number[] = [];
    threejsData.colors.forEach(colorHex => {
      const color = new THREE.Color(colorHex);
      colors.push(color.r, color.g, color.b);
    });
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    material = new THREE.MeshStandardMaterial({ vertexColors: true });
  } else {
    material = new THREE.MeshStandardMaterial({ color: 0xffffff });
  }

  return new THREE.Mesh(geometry, material);
}
