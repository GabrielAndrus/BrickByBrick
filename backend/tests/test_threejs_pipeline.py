"""
Test: Three.js Dorm Room to Backboard Pipeline

This tests the complete workflow:
1. Extract voxels from sample dorm room
2. Process through LEGO generation
3. Save to Backboard
4. Get recommendations
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.threejs_voxelizer import (
    get_sample_dorm_room_voxels,
    ThreeJsVoxelizer,
    VoxelGrid
)
from app.services.master_builder import MasterBuilder
from app.services.backboard_lego_memory import BackboardLegoMemory


def test_dorm_room_voxelization():
    """Test 1: Extract voxels from dorm room"""
    print("\n" + "="*70)
    print("TEST 1: Three.js Dorm Room → Voxel Grid")
    print("="*70)
    
    voxels = get_sample_dorm_room_voxels(resolution=0.15)
    
    print(f"✓ Extracted {len(voxels)} voxels from dorm room")
    print(f"  Voxel resolution: 0.15m (15cm)")
    
    # Show voxel statistics
    colors = {}
    for voxel in voxels:
        color = voxel.get("hex_color", "#888888")
        colors[color] = colors.get(color, 0) + 1
    
    print(f"\n  Color distribution:")
    for color, count in sorted(colors.items(), key=lambda x: -x[1])[:5]:
        print(f"    {color}: {count} voxels")
    
    # Sample voxels
    print(f"\n  Sample voxels (first 5):")
    for i, voxel in enumerate(voxels[:5]):
        print(f"    [{i}] pos=({voxel['x']}, {voxel['y']}, {voxel['z']}), color={voxel['hex_color']}")
    
    return voxels


def test_lego_generation(voxels):
    """Test 2: Generate LEGO manifest from voxels"""
    print("\n" + "="*70)
    print("TEST 2: Voxel Grid → LEGO Manifest (Greedy Algorithm)")
    print("="*70)
    
    try:
        builder = MasterBuilder()
        manifest = builder.process_voxels_sync(voxels)
        
        print(f"✓ Generated LEGO manifest")
        print(f"  Total bricks: {len(manifest.get('bricks', []))}")
        
        # Show brick statistics
        brick_types = {}
        for brick in manifest.get('bricks', []):
            brick_type = brick.get('lego_type', 'unknown')
            brick_types[brick_type] = brick_types.get(brick_type, 0) + 1
        
        print(f"\n  Brick type distribution:")
        for brick_type, count in sorted(brick_types.items(), key=lambda x: -x[1])[:5]:
            print(f"    {brick_type}: {count} bricks")
        
        # Manifest metadata
        print(f"\n  Manifest metadata:")
        print(f"    Version: {manifest.get('version', 'N/A')}")
        print(f"    Algorithm: {manifest.get('algorithm', 'N/A')}")
        print(f"    Dimensions: {manifest.get('dimensions', 'N/A')}")
        
        return manifest
    
    except Exception as e:
        print(f"✗ Error generating manifest: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_backboard_persistence(voxels, manifest):
    """Test 3: Save to Backboard and retrieve"""
    print("\n" + "="*70)
    print("TEST 3: Backboard Memory Persistence & Similarity Matching")
    print("="*70)
    
    try:
        memory = BackboardLegoMemory()
        
        # Save the dorm room build
        saved = memory.save_build(
            project_name="dorm-room-test",
            room_type="bedroom",
            voxels=voxels,
            manifest=manifest
        )
        
        print(f"✓ Saved build to Backboard: {saved}")
        
        # Retrieve similar builds
        similar = memory.get_similar_builds(
            project_name="dorm-room-test",
            room_type="bedroom",
            max_results=5
        )
        
        print(f"✓ Retrieved {len(similar)} similar builds from Backboard")
        
        if similar:
            print(f"\n  Similar builds:")
            for i, build in enumerate(similar[:3]):
                print(f"    [{i+1}] {build.get('project_name', 'Unknown')} " +
                      f"(similarity: {build.get('similarity', 0.0):.2f})")
        
        return memory
    
    except Exception as e:
        print(f"✗ Error with Backboard: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_complete_pipeline():
    """Test 4: Complete pipeline end-to-end"""
    print("\n" + "="*70)
    print("TEST 4: Complete Pipeline (Three.js → Voxels → LEGO → Backboard)")
    print("="*70)
    
    try:
        # Step 1: Voxelization
        voxels = get_sample_dorm_room_voxels(resolution=0.15)
        print(f"✓ Step 1: Voxelized scene → {len(voxels)} voxels")
        
        # Step 2: LEGO Generation
        builder = MasterBuilder()
        manifest = builder.process_voxels_sync(voxels)
        print(f"✓ Step 2: Generated LEGO → {len(manifest.get('bricks', []))} bricks")
        
        # Step 3: Backboard Save
        memory = BackboardLegoMemory()
        saved = memory.save_build(
            project_name="dorm-room-complete",
            room_type="bedroom",
            voxels=voxels,
            manifest=manifest
        )
        print(f"✓ Step 3: Saved to Backboard → {saved}")
        
        # Step 4: Get Recommendations
        similar = memory.get_similar_builds(
            project_name="dorm-room-complete",
            room_type="bedroom",
            max_results=3
        )
        print(f"✓ Step 4: Retrieved recommendations → {len(similar)} similar builds")
        
        # Output summary
        print(f"\n  Pipeline Summary:")
        print(f"    Input: Three.js dorm room scene")
        print(f"    Voxels: {len(voxels)} (0.15m resolution)")
        print(f"    LEGO bricks: {len(manifest.get('bricks', []))}")
        print(f"    Backboard saved: {saved}")
        print(f"    Recommendations: {len(similar)}")
        
        return {
            "status": "success",
            "voxels": len(voxels),
            "bricks": len(manifest.get('bricks', [])),
            "backboard_saved": saved,
            "recommendations": len(similar)
        }
    
    except Exception as e:
        print(f"✗ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_test_results(results_dict):
    """Save test results to JSON file"""
    output_path = Path(__file__).parent / "threejs_pipeline_results.json"
    
    with open(output_path, 'w') as f:
        json.dump(results_dict, f, indent=2)
    
    print(f"\n✓ Test results saved to: {output_path}")


if __name__ == "__main__":
    print("\n" + "█"*70)
    print("█ Three.js Dorm Room to Backboard Pipeline Test Suite")
    print("█"*70)
    
    results = {}
    
    # Test 1: Voxelization
    voxels = test_dorm_room_voxelization()
    results["voxelization"] = {"voxel_count": len(voxels), "status": "passed"}
    
    # Test 2: LEGO Generation
    manifest = test_lego_generation(voxels)
    if manifest:
        results["lego_generation"] = {
            "brick_count": len(manifest.get('bricks', [])),
            "status": "passed"
        }
    else:
        results["lego_generation"] = {"status": "failed"}
    
    # Test 3: Backboard
    if manifest:
        memory = test_backboard_persistence(voxels, manifest)
        if memory:
            results["backboard_persistence"] = {"status": "passed"}
        else:
            results["backboard_persistence"] = {"status": "failed"}
    
    # Test 4: Complete Pipeline
    pipeline_result = test_complete_pipeline()
    if pipeline_result:
        results["complete_pipeline"] = pipeline_result
    else:
        results["complete_pipeline"] = {"status": "failed"}
    
    # Save results
    save_test_results(results)
    
    print("\n" + "█"*70)
    print("█ All Tests Complete!")
    print("█"*70)
    print(f"\nResults Summary:")
    print(json.dumps(results, indent=2))
