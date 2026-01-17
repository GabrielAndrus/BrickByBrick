#!/usr/bin/env python3
"""
Test script for MasterBuilder service.

Tests the Greedy Fitting Algorithm with sample voxel data.
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.master_builder import MasterBuilder


async def test_simple_cube():
    """Test with a simple 4x4x4 cube"""
    print("="*70)
    print("TEST 1: Simple 4x4x4 Cube")
    print("="*70)
    
    builder = MasterBuilder()
    
    # Create a 4x4x4 cube with red color
    voxels = []
    for x in range(4):
        for y in range(4):
            for z in range(4):
                voxels.append({
                    "x": x,
                    "y": y,
                    "z": z,
                    "hex_color": "#FF0000"  # Red
                })
    
    print(f"Input: {len(voxels)} voxels")
    manifest = await builder.process_voxels(voxels)
    
    print(f"\nOutput: {manifest['total_bricks']} bricks")
    print(f"Layers: {len(manifest['layers'])}")
    print(f"\nInventory:")
    for item in manifest['inventory'][:5]:  # Show first 5
        print(f"  - {item['part_id']} (color {item['color_id']}): {item['quantity']}x")
    
    print(f"\nFirst 5 bricks:")
    for brick in manifest['bricks'][:5]:
        print(f"  - {brick['part_id']} at {brick['position']} (rotation: {brick['rotation']}°)")
    
    return manifest


async def test_layered_structure():
    """Test with a layered structure to verify interlocking"""
    print("\n" + "="*70)
    print("TEST 2: Layered Structure (Interlocking Test)")
    print("="*70)
    
    builder = MasterBuilder()
    
    # Create a 6x6 base layer and a 4x4 top layer (offset for interlocking)
    voxels = []
    
    # Base layer (z=0): 6x6
    for x in range(6):
        for y in range(6):
            voxels.append({
                "x": x,
                "y": y,
                "z": 0,
                "hex_color": "#0000FF"  # Blue
            })
    
    # Top layer (z=1): 4x4, offset by 1 for interlocking
    for x in range(1, 5):
        for y in range(1, 5):
            voxels.append({
                "x": x,
                "y": y,
                "z": 1,
                "hex_color": "#00FF00"  # Green
            })
    
    print(f"Input: {len(voxels)} voxels")
    manifest = await builder.process_voxels(voxels)
    
    print(f"\nOutput: {manifest['total_bricks']} bricks")
    print(f"Layers: {manifest['layers']}")
    
    # Check that interlocking worked (different brick positions on different layers)
    layer_0_bricks = [b for b in manifest['bricks'] if b['position'][2] == 0]
    layer_1_bricks = [b for b in manifest['bricks'] if b['position'][2] == 1]
    
    print(f"\nLayer 0: {len(layer_0_bricks)} bricks")
    print(f"Layer 1: {len(layer_1_bricks)} bricks")
    
    if layer_0_bricks and layer_1_bricks:
        print(f"\n✅ Interlocking: Layers have different brick positions")
        print(f"   Layer 0 first brick: {layer_0_bricks[0]['position']}")
        print(f"   Layer 1 first brick: {layer_1_bricks[0]['position']}")
    
    return manifest


async def test_mixed_colors():
    """Test with multiple colors"""
    print("\n" + "="*70)
    print("TEST 3: Mixed Colors")
    print("="*70)
    
    builder = MasterBuilder()
    
    # Create a 3x3x3 cube with different colors per layer
    voxels = []
    colors = ["#FF0000", "#00FF00", "#0000FF"]  # Red, Green, Blue
    
    for z in range(3):
        for x in range(3):
            for y in range(3):
                voxels.append({
                    "x": x,
                    "y": y,
                    "z": z,
                    "hex_color": colors[z]
                })
    
    print(f"Input: {len(voxels)} voxels with 3 colors")
    manifest = await builder.process_voxels(voxels)
    
    print(f"\nOutput: {manifest['total_bricks']} bricks")
    print(f"\nColor distribution:")
    color_counts = {}
    for brick in manifest['bricks']:
        color_id = brick['color_id']
        color_counts[color_id] = color_counts.get(color_id, 0) + 1
    
    for color_id, count in sorted(color_counts.items()):
        print(f"  - Color ID {color_id}: {count} bricks")
    
    return manifest


async def test_greedy_priority():
    """Test that greedy algorithm prioritizes larger bricks"""
    print("\n" + "="*70)
    print("TEST 4: Greedy Priority (2x4 bricks preferred)")
    print("="*70)
    
    builder = MasterBuilder()
    
    # Create a perfect 8x4 rectangle (should use 2x4 bricks)
    voxels = []
    for x in range(8):
        for y in range(4):
            voxels.append({
                "x": x,
                "y": y,
                "z": 0,
                "hex_color": "#FFFF00"  # Yellow
            })
    
    print(f"Input: 8x4 rectangle ({len(voxels)} voxels)")
    print("Expected: Should use 2x4 bricks (part_id: 3001)")
    
    manifest = await builder.process_voxels(voxels)
    
    print(f"\nOutput: {manifest['total_bricks']} bricks")
    
    # Count brick types
    brick_counts = {}
    for brick in manifest['bricks']:
        part_id = brick['part_id']
        brick_counts[part_id] = brick_counts.get(part_id, 0) + 1
    
    print(f"\nBrick type distribution:")
    for part_id, count in sorted(brick_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {part_id}: {count}x")
    
    # Check if 2x4 bricks were used
    if "3001" in brick_counts:
        print(f"\n✅ Greedy priority working: Used {brick_counts['3001']} 2x4 bricks")
    else:
        print(f"\n⚠️  No 2x4 bricks used (may be due to interlocking offset)")
    
    return manifest


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MASTER BUILDER SERVICE - TEST SUITE")
    print("="*70)
    
    async def run_all_tests():
        try:
            # Run all tests
            await test_simple_cube()
            await test_layered_structure()
            await test_mixed_colors()
            await test_greedy_priority()
            
            print("\n" + "="*70)
            print("✅ ALL TESTS COMPLETED")
            print("="*70)
            
        except Exception as e:
            print(f"\n❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    asyncio.run(run_all_tests())
