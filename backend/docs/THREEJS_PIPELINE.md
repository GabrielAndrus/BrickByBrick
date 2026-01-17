# Three.js Pipeline Integration

## Overview

The entire pipeline now uses **Three.js as the primary data exchange format**. This enables seamless visualization, interactive instructions, and timeline scrubbing.

## Architecture Flow

```
1. Scan Object (Video)
   ↓
2. Pegasus Analyzer → Three.js Mesh JSON (vertices + faces)
   ↓
3. Frontend: Mesh Voxelizer → Voxel Grid
   ↓
4. MasterBuilder → LEGO Bricks
   ↓
5. Backboard → Scene Deltas (History of Creation)
   ↓
6. Frontend: Timeline Scrubber → Interactive Instructions
```

## Components

### 1. Scene Conversion (Pegasus Analyzer)

**File**: `app/services/twelve_labs.py`

**Updated Prompt**: Now requests Three.js-compatible JSON format:
- `vertices`: Array of `[x, y, z]` coordinates in millimeters
- `faces`: Array of `[i, j, k]` triangular face indices
- `normals`: Optional vertex normals for lighting
- `colors`: Optional vertex colors (hex codes)

**Output Format**:
```json
{
  "dimensions_mm": {...},
  "dominant_colors": [...],
  "complexity": {...},
  "threejs_mesh": {
    "vertices": [[x, y, z], ...],
    "faces": [[i, j, k], ...],
    "normals": [[nx, ny, nz], ...],
    "colors": ["#FF0000", ...]
  }
}
```

### 2. Mesh Voxelizer

**File**: `frontend/lib/voxelizer.ts`

**Function**: `voxelizeMesh(mesh, resolution)`

**Algorithm**: 
- Uses raycasting (inside/outside detection)
- Möller–Trumbore ray-triangle intersection
- Generates voxel grid for MasterBuilder

**Usage**:
```typescript
import { voxelizeMesh, threejsJsonToMesh } from '@/lib/voxelizer';

// Convert Three.js JSON to Mesh
const mesh = threejsJsonToMesh(threejsData);

// Voxelize the mesh
const voxelGrid = voxelizeMesh(mesh, 8.0); // 8mm = 1 stud

// Send to backend
await fetch('/master-builder/process', {
  method: 'POST',
  body: JSON.stringify({ voxels: voxelGrid.voxels })
});
```

### 3. Scene Deltas (Memory-to-Manual)

**File**: `app/services/backboard_service.py`

**What are Scene Deltas?**
Each brick placement is recorded as a "Scene Delta" - a change to the Three.js scene that tells the frontend which objects to show/hide.

**Delta Format**:
```json
{
  "timestamp": 0,
  "action": "add_brick",
  "threejs_object_id": "brick_3001_0",
  "visible": true,
  "part_id": "3001",
  "color_id": 14,
  "position": [10, 5, 2],
  "dimensions": [4, 2, 1],
  "is_ai_filled": false,
  "model_switch": "gemini-3-pro"
}
```

**Model Switch Deltas**:
```json
{
  "timestamp": 5,
  "action": "model_switch",
  "from_model": "gemini-3-pro",
  "to_model": "gemini-3-flash",
  "description": "Switched from Gemini 3 Pro to Gemini 3 Flash"
}
```

### 4. Interactive Instructions

**Function**: `get_interactive_instructions(thread_id)`

**Returns**: List of Scene Deltas in chronological order

**API Endpoint**: `GET /backboard/{thread_id}/instructions`

**Response**:
```json
{
  "thread_id": "thread_123",
  "total_deltas": 150,
  "action_counts": {
    "add_brick": 145,
    "model_switch": 2,
    "step_marker": 3
  },
  "deltas": [...],
  "metadata": {
    "description": "History of Creation",
    "format": "threejs_scene_deltas",
    "version": "1.0"
  }
}
```

## Frontend Integration

### Timeline Scrubber

The frontend can now scrub through the "History of Creation":

```typescript
// Fetch instructions
const timeline = await fetch(`/backboard/${threadId}/instructions`).then(r => r.json());

// Scrub to timestamp
function scrubToTimestamp(timestamp: number) {
  const deltasUpToNow = timeline.deltas.filter(d => d.timestamp <= timestamp);
  
  // Apply all deltas up to this point
  deltasUpToNow.forEach(delta => {
    if (delta.action === "add_brick") {
      const brickObject = scene.getObjectByName(delta.threejs_object_id);
      if (brickObject) {
        brickObject.visible = delta.visible;
      }
    }
  });
}
```

### Three.js Scene Management

Each brick gets a Three.js object with a unique ID:

```typescript
// Create brick object
const brickGeometry = new THREE.BoxGeometry(
  delta.dimensions[0] * 8, // Convert studs to mm
  delta.dimensions[1] * 8,
  delta.dimensions[2] * 8
);
const brickMaterial = new THREE.MeshStandardMaterial({
  color: delta.color_id
});
const brickMesh = new THREE.Mesh(brickGeometry, brickMaterial);
brickMesh.name = delta.threejs_object_id;
brickMesh.position.set(
  delta.position[0] * 8,
  delta.position[1] * 8,
  delta.position[2] * 8
);
brickMesh.visible = false; // Start hidden
scene.add(brickMesh);
```

## The Complete Experience

### For Judges

1. **The Scan**: User scans an object with video
2. **The Translation**: Beautiful translucent 3D Three.js model appears
3. **The Assembly**: AI "reaches into" the model and fills it with bricks
4. **The Manual**: User scrubs timeline to see:
   - Every brick choice
   - Every model switch (Gemini → Claude)
   - Every structural fix
   - All saved in Backboard's Memory

### Timeline Features

- **Play/Pause**: Step through build process
- **Scrub**: Jump to any point in time
- **Model Indicators**: See when AI switches models
- **Step Markers**: Navigate to specific assembly steps
- **Visual Feedback**: See exactly which bricks are visible at each timestamp

## API Endpoints

### Process Three.js Mesh
```
POST /threejs/voxelize
Body: { vertices: [...], faces: [...] }
```

### Get Interactive Instructions
```
GET /backboard/{thread_id}/instructions
Returns: Timeline with all Scene Deltas
```

### Get Raw Deltas
```
GET /backboard/{thread_id}/deltas
Returns: List of Scene Deltas
```

## Data Flow Example

```
1. Video → Pegasus Analyzer
   → Returns: { threejs_mesh: { vertices: [...], faces: [...] } }

2. Frontend: threejsJsonToMesh(threejsData)
   → Creates: THREE.Mesh object

3. Frontend: voxelizeMesh(mesh, 8.0)
   → Returns: { voxels: [{x, y, z, hex_color}, ...] }

4. Backend: MasterBuilder.process_voxels(voxels)
   → Returns: MasterManifest with bricks

5. Backend: BackboardService.add_object_to_world()
   → Records: Scene Deltas for each brick

6. Frontend: GET /backboard/{thread_id}/instructions
   → Returns: Timeline of all changes

7. Frontend: Timeline Scrubber
   → Shows/Hides Three.js objects based on deltas
```

## Benefits

✅ **Unified Format**: Three.js throughout the entire pipeline  
✅ **Interactive**: Timeline scrubbing for build visualization  
✅ **Transparent**: See every AI decision and model switch  
✅ **Visual**: Beautiful 3D representation from start to finish  
✅ **Debuggable**: Complete history of creation in Backboard memory  
