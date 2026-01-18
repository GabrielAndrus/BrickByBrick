/**
 * Universal LEGO Renderer
 * 
 * Generic component that renders any LEGO manifest following the bricks[] schema.
 * Uses LDraw library to dynamically load and render LEGO parts with InstancedMesh
 * for optimal performance.
 * 
 * Features:
 * - Dynamic cataloging of unique part_ids
 * - LDraw geometry caching
 * - InstancedMesh factory for each part type
 * - Batch transformations with rotation support
 * - Adaptive scenery/environment loading
 */

'use client';

import React, { useRef, useMemo, useEffect, useState } from 'react';
import * as THREE from 'three';

// Types
export interface LegoBrick {
  part_id: string;
  position: [number, number, number];
  rotation: number; // 0, 90, 180, 270 degrees
  color_id: number;
  is_verified?: boolean;
}

export interface LegoManifest {
  manifest_version: string;
  total_bricks: number;
  bricks: LegoBrick[];
  scenery_origin?: [number, number, number];
  room_id?: string;
  layers?: Record<string, number>;
  inventory?: Array<{
    part_id: string;
    color_id: number;
    quantity: number;
  }>;
}

interface PartCache {
  [partId: string]: {
    geometry: THREE.BufferGeometry;
    material: THREE.Material | THREE.Material[];
    boundingBox: THREE.Box3;
    loaded: boolean;
    loading: boolean;
  };
}

interface LegoUniverseProps {
  manifest: LegoManifest;
  showScenery?: boolean;
  wireframeScenery?: boolean;
}

// Official Three.js LDraw library CDN
const LDrawBaseURL = 'https://raw.githubusercontent.com/mrdoob/three.js/master/examples/models/ldraw/officialLibrary/';

// Scale factor to align LDraw meshes with 1-unit voxel grid
const LDrawScale = 0.05;

/**
 * Convert rotation degrees to Three.js Euler rotation
 */
function degreesToEuler(degrees: number): THREE.Euler {
  // LEGO rotations are typically around Y-axis (vertical)
  // 0° = no rotation, 90° = quarter turn, 180° = half turn, 270° = three-quarter turn
  const radians = (degrees * Math.PI) / 180;
  return new THREE.Euler(0, radians, 0, 'XYZ');
}

/**
 * Load LDraw part geometry with proper configuration
 * 
 * Uses LDrawLoader to load official .dat files (e.g., 3004.dat for 1x2 bricks, 3001.dat for 2x4 bricks)
 * Applies scaling (0.05), pivot correction (bottom-center), and material configuration.
 */
async function loadLDrawPart(partId: string): Promise<{ 
  geometry: THREE.BufferGeometry; 
  material: THREE.Material | THREE.Material[]; 
  boundingBox: THREE.Box3;
}> {
  // Dynamically import LDrawLoader and conditional line material to avoid SSR issues
  const { LDrawLoader } = await import('three/examples/jsm/loaders/LDrawLoader.js');
  const { LDrawConditionalLineMaterial } = await import('three/examples/jsm/materials/LDrawConditionalLineMaterial.js');
  
  const loader = new LDrawLoader();
  
  // Configuration: High-quality parts library from gkjohnson/ldraw-parts-library
  const libraryPath = 'https://raw.githubusercontent.com/gkjohnson/ldraw-parts-library/master/complete/ldraw/';
  loader.setPartsLibraryPath(libraryPath);
  
  // Preload materials for realism
  try {
    await loader.preloadMaterials(`${libraryPath}LDConfig.ldr`);
  } catch (e) {
    console.warn('Could not preload LDConfig.ldr:', e);
  }
  
  // Enable conditional lines for professional 'instruction manual' black outlines
  // This creates the characteristic LEGO instruction manual look with black edge lines
  loader.setConditionalLineMaterial(LDrawConditionalLineMaterial);
  
  // Enable smooth normals for realistic stud and curved piece rendering
  loader.smoothNormals = true;
  
  // LDraw part files are in the parts/ subdirectory
  // e.g., "3004" becomes "parts/3004.dat", "3001" becomes "parts/3001.dat"
  const partFileName = `${partId}.dat`;
  const partUrl = `${libraryPath}parts/${partFileName}`;
  
  return new Promise((resolve, reject) => {
    loader.load(
      partUrl,
      (object) => {
        // LDrawLoader returns a Group containing multiple meshes
        // We need to extract all meshes, configure materials, and merge geometries
        const geometries: THREE.BufferGeometry[] = [];
        const materials: THREE.Material[] = [];
        const boundingBox = new THREE.Box3();

        // Traverse the group to extract all meshes
        object.traverse((child: any) => {
          if (child.isMesh && child.geometry) {
            // Clone geometry to avoid sharing references
            const geometry = child.geometry.clone();
            
            // Apply scale factor (0.05) to align with 1-unit voxel grid
            geometry.scale(LDrawScale, LDrawScale, LDrawScale);
            
            geometries.push(geometry);
            
            // Configure material for outlines and prevent flickering
            const material = Array.isArray(child.material) ? child.material[0] : child.material;
            if (material) {
              const clonedMaterial = material.clone();
              
              // Enable conditional lines for black outlines (instruction manual style)
              // LDraw materials already support conditionalLines via LDrawLoader
              if (clonedMaterial.userData) {
                clonedMaterial.userData.conditionalLines = true;
              }
              
              // Enable polygon offset to prevent z-fighting/flickering
              clonedMaterial.polygonOffset = true;
              clonedMaterial.polygonOffsetFactor = 1;
              clonedMaterial.polygonOffsetUnits = 1;
              
              materials.push(clonedMaterial);
            }
            
            // Expand bounding box for overall part bounds
            geometry.computeBoundingBox();
            if (geometry.boundingBox) {
              boundingBox.union(geometry.boundingBox);
            }
          }
        });

        if (geometries.length === 0) {
          reject(new Error(`No meshes found in LDraw part ${partId}`));
          return;
        }

        // Merge geometries if multiple exist
        // For InstancedMesh, we want a single geometry
        let mergedGeometry: THREE.BufferGeometry;
        if (geometries.length === 1) {
          mergedGeometry = geometries[0];
        } else {
          // Try to merge geometries manually or use first geometry
          // Note: BufferGeometryUtils requires async import, so we'll use the first geometry
          // for now. In production, you could pre-load BufferGeometryUtils or handle this differently.
          console.warn(`Multiple geometries for part ${partId}, using first geometry. Consider merging manually.`);
          mergedGeometry = geometries[0];
          
          // Alternative: If you need to merge, you could concatenate attributes manually here
          // For now, using the first geometry is sufficient as LDraw parts typically have one main mesh
        }

        // Use first material or material array (InstancedMesh handles both)
        const finalMaterial = materials.length === 1 ? materials[0] : materials;

        // Calculate bounding box for pivot correction
        mergedGeometry.computeBoundingBox();
        const box = mergedGeometry.boundingBox!;
        const bottomY = box.min.y;
        const centerX = (box.min.x + box.max.x) / 2;
        const centerZ = (box.min.z + box.max.z) / 2;
        
        // Pivot correction: translate so pivot is at bottom-center (prevents clipping into ground)
        // Bottom-center means: Y=0 at the bottom, centered on X and Z axes
        mergedGeometry.translate(-centerX, -bottomY, -centerZ);
        mergedGeometry.computeBoundingBox();

        resolve({
          geometry: mergedGeometry,
          material: finalMaterial,
          boundingBox: mergedGeometry.boundingBox!.clone(),
        });
      },
      undefined,
      (error) => {
        console.warn(`Failed to load LDraw part ${partId}:`, error);
        // Fallback: create a simple box geometry with proper scale and pivot
        // This should rarely happen if LDraw library is accessible
        const fallbackGeometry = new THREE.BoxGeometry(1, 1, 1); // 1-unit voxel
        fallbackGeometry.translate(0, 0.5, 0); // Pivot at bottom-center
        const fallbackMaterial = new THREE.MeshStandardMaterial({ 
          color: 0xcccccc,
          polygonOffset: true,
          polygonOffsetFactor: 1,
          polygonOffsetUnits: 1,
        });
        resolve({
          geometry: fallbackGeometry,
          material: fallbackMaterial,
          boundingBox: new THREE.Box3().setFromObject(new THREE.Mesh(fallbackGeometry)),
        });
      }
    );
  });
}

/**
 * Get LEGO color from Rebrickable color ID
 * This is a simplified mapping - you may want to use a full color database
 */
function getColorFromId(colorId: number): THREE.Color {
  // Common LEGO colors mapping (simplified)
  const colorMap: Record<number, number> = {
    0: 0x05131d, // Black
    1: 0xffffff, // White
    4: 0xe4cd9e, // Tan
    9: 0xe4cd9e, // Light Tan
    12: 0xfcb76d, // Trans-Orange
    13: 0x68abe3, // Trans-Medium Blue
    15: 0xfe8a18, // Trans-Orange
    18: 0x923978, // Trans-Dark Pink
    21: 0xa0a5a9, // Trans-Black
    23: 0x6b5a5a, // Trans-Dark Blue
    25: 0x635f52, // Trans-Brown
    27: 0xfeccb0, // Trans-Red
    28: 0x05131d, // Trans-Black
    29: 0x05131d, // Trans-Dark Blue
    33: 0x05131d, // Trans-Brown
    36: 0x05131d, // Trans-Light Blue
    40: 0x05131d, // Trans-Yellow
    41: 0x05131d, // Trans-Clear
    42: 0x05131d, // Trans-Purple
    46: 0x05131d, // Trans-Neon Green
    47: 0x05131d, // Trans-Neon Orange
    48: 0x05131d, // Trans-Neon Yellow
    49: 0x05131d, // Trans-Neon Red
    50: 0x05131d, // Trans-Neon Blue
    1089: 0xe4cd9e, // Light Tan (common)
  };
  
  const hexColor = colorMap[colorId] || 0xcccccc; // Default gray
  return new THREE.Color(hexColor);
}

export function LegoUniverse({ manifest, showScenery = true, wireframeScenery = true }: LegoUniverseProps) {
  const partCacheRef = useRef<PartCache>({});
  const instancedMeshesRef = useRef<Map<string, THREE.InstancedMesh>>(new Map());
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Extract unique part IDs from manifest
  const uniquePartIds = useMemo(() => {
    const partIds = new Set<string>();
    manifest.bricks.forEach((brick) => {
      partIds.add(brick.part_id);
    });
    return Array.from(partIds);
  }, [manifest]);

  // Group bricks by part_id for instancing
  const bricksByPartId = useMemo(() => {
    const groups: Record<string, LegoBrick[]> = {};
    manifest.bricks.forEach((brick) => {
      if (!groups[brick.part_id]) {
        groups[brick.part_id] = [];
      }
      groups[brick.part_id].push(brick);
    });
    return groups;
  }, [manifest]);

  // Load all unique parts
  useEffect(() => {
    let loadedCount = 0;
    const totalParts = uniquePartIds.length;

    if (totalParts === 0) {
      setIsLoading(false);
      return;
    }

    uniquePartIds.forEach(async (partId) => {
      if (partCacheRef.current[partId]?.loaded) {
        loadedCount++;
        setLoadingProgress((loadedCount / totalParts) * 100);
        if (loadedCount === totalParts) {
          setIsLoading(false);
        }
        return;
      }

      if (partCacheRef.current[partId]?.loading) {
        return; // Already loading
      }

      partCacheRef.current[partId] = {
        geometry: null!,
        material: null!,
        boundingBox: new THREE.Box3(),
        loaded: false,
        loading: true,
      };

      try {
        const { geometry, material, boundingBox } = await loadLDrawPart(partId);
        partCacheRef.current[partId] = {
          geometry,
          material,
          boundingBox,
          loaded: true,
          loading: false,
        };

        loadedCount++;
        setLoadingProgress((loadedCount / totalParts) * 100);

        if (loadedCount === totalParts) {
          setIsLoading(false);
        }
      } catch (error) {
        console.error(`Error loading part ${partId}:`, error);
        partCacheRef.current[partId].loading = false;
        loadedCount++;
        setLoadingProgress((loadedCount / totalParts) * 100);
        if (loadedCount === totalParts) {
          setIsLoading(false);
        }
      }
    });
  }, [uniquePartIds]);

  // Create and update InstancedMeshes when parts are loaded
  useEffect(() => {
    if (isLoading) return;

    uniquePartIds.forEach((partId) => {
      const cache = partCacheRef.current[partId];
      if (!cache?.loaded) return;

      let instancedMesh = instancedMeshesRef.current.get(partId);
      const bricks = bricksByPartId[partId] || [];

      if (!instancedMesh && cache.geometry && cache.material) {
        // Create new InstancedMesh
        // Clone material (handle both single material and material arrays)
        const clonedMaterial = Array.isArray(cache.material)
          ? cache.material.map(mat => mat.clone())
          : cache.material.clone();
        
        instancedMesh = new THREE.InstancedMesh(
          cache.geometry,
          clonedMaterial,
          bricks.length
        );
        instancedMeshesRef.current.set(partId, instancedMesh);
      }

      if (instancedMesh && bricks.length > 0) {
        // Update instance matrices
        const matrix = new THREE.Matrix4();
        bricks.forEach((brick, index) => {
          // Position in voxel grid (1 unit = 1 voxel)
          // Geometry pivot is already at bottom-center, so position directly
          const position = new THREE.Vector3(
            brick.position[0],
            brick.position[1],
            brick.position[2]
          );

          // Rotation
          const euler = degreesToEuler(brick.rotation);
          const quaternion = new THREE.Quaternion().setFromEuler(euler);

          // Scale is already applied to geometry during loading
          const scale = new THREE.Vector3(1, 1, 1);

          // Build transformation matrix
          matrix.compose(position, quaternion, scale);
          instancedMesh.setMatrixAt(index, matrix);
        });

        instancedMesh.instanceMatrix.needsUpdate = true;
      }
    });
  }, [isLoading, uniquePartIds, bricksByPartId]);

  return (
    <group rotation-x={Math.PI}>
      {/* LDraw uses Y-down coordinate system, so we rotate 180° around X-axis to match Three.js Y-up */}
      
      {/* Render all InstancedMeshes */}
      {uniquePartIds.map((partId) => {
        const instancedMesh = instancedMeshesRef.current.get(partId);
        if (!instancedMesh) return null;

        return (
          <InstancedMeshRenderer
            key={partId}
            instancedMesh={instancedMesh}
            partId={partId}
          />
        );
      })}

      {/* Scenery/Environment */}
      {showScenery && manifest.scenery_origin && (
        <Scenery
          origin={manifest.scenery_origin}
          roomId={manifest.room_id}
          wireframe={wireframeScenery}
        />
      )}

      {/* Default grid if no scenery */}
      {showScenery && !manifest.scenery_origin && (
        <gridHelper args={[1000, 100]} />
      )}

      {/* Loading indicator */}
      {isLoading && (
        <mesh position={[0, 10, 0]}>
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial color={0xff0000} />
        </mesh>
      )}
    </group>
  );
}

/**
 * InstancedMesh renderer component
 */
function InstancedMeshRenderer({
  instancedMesh,
  partId,
}: {
  instancedMesh: THREE.InstancedMesh;
  partId: string;
}) {
  return <primitive object={instancedMesh} castShadow receiveShadow />;
}

/**
 * Scenery component for room/environment rendering
 */
function Scenery({
  origin,
  roomId,
  wireframe = true,
}: {
  origin: [number, number, number];
  roomId?: string;
  wireframe?: boolean;
}) {
  // This would load a specific room mesh based on roomId
  // For now, render a simple wireframe box representing the room
  const roomSize = 200; // Default room size in mm

  return (
    <group position={[origin[0] * 8, origin[1] * 9.6, origin[2] * 8]}>
      {/* Floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[roomSize, roomSize]} />
        <meshStandardMaterial
          color={0xcccccc}
          wireframe={wireframe}
          transparent
          opacity={0.3}
        />
      </mesh>

      {/* Walls (simplified) */}
      {wireframe && (
        <>
          {/* Back wall */}
          <lineSegments>
            <edgesGeometry
              args={[
                new THREE.BoxGeometry(roomSize, roomSize * 0.6, 1),
              ]}
            />
            <lineBasicMaterial color={0x888888} />
          </lineSegments>
        </>
      )}
    </group>
  );
}
