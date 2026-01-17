#!/usr/bin/env python3
"""
Test script for Rebrickable API integration with MasterBuilder.

Tests the complete data flow:
1. Voxel Input with hex color
2. Color mapping via Rebrickable API
3. Part availability verification
4. Fallback logic for unavailable parts
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.master_builder import MasterBuilder
from app.services.rebrickable_api import get_rebrickable_client


async def test_color_mapping():
    """Test color mapping from hex to Rebrickable color ID"""
    print("="*70)
    print("TEST 1: Color Mapping")
    print("="*70)
    
    rebrickable = get_rebrickable_client()
    
    # Test known colors
    test_cases = [
        ("#FFD700", "Yellow (Gold)"),
        ("#FF0000", "Red"),
        ("#0000FF", "Blue"),
        ("#00FF00", "Green"),
        ("#FFFFFF", "White"),
        ("#000000", "Black"),
    ]
    
    print("\nTesting color mapping:")
    for hex_color, expected_name in test_cases:
        color_id = await rebrickable.get_closest_lego_color(hex_color)
        print(f"  {hex_color} -> Color ID {color_id} ({expected_name})")
    
    print("\n✅ Color mapping test completed")


async def test_part_verification():
    """Test part availability verification"""
    print("\n" + "="*70)
    print("TEST 2: Part Availability Verification")
    print("="*70)
    
    rebrickable = get_rebrickable_client()
    
    # Test common parts
    test_cases = [
        ("3001", 14, "2x4 brick in Yellow"),
        ("3001", 5, "2x4 brick in Red"),
        ("3003", 1, "2x2 brick in White"),
        ("3004", 0, "1x2 brick in Black"),
    ]
    
    print("\nTesting part availability:")
    for part_id, color_id, description in test_cases:
        is_available = await rebrickable.verify_part_availability(part_id, color_id)
        status = "✅ Available" if is_available else "❌ Not Available"
        print(f"  {description} ({part_id}, color {color_id}): {status}")
    
    print("\n✅ Part verification test completed")


async def test_full_pipeline():
    """Test the complete pipeline with Rebrickable integration"""
    print("\n" + "="*70)
    print("TEST 3: Full Pipeline with Rebrickable Integration")
    print("="*70)
    
    builder = MasterBuilder()
    
    # Create a simple 4x4x2 structure with gold color
    voxel_data = [
        {"x": 0, "y": 0, "z": 0, "hex_color": "#FFD700"},  # Gold
        {"x": 1, "y": 0, "z": 0, "hex_color": "#FFD700"},
        {"x": 2, "y": 0, "z": 0, "hex_color": "#FFD700"},
        {"x": 3, "y": 0, "z": 0, "hex_color": "#FFD700"},
        {"x": 0, "y": 1, "z": 0, "hex_color": "#FFD700"},
        {"x": 1, "y": 1, "z": 0, "hex_color": "#FFD700"},
        {"x": 2, "y": 1, "z": 0, "hex_color": "#FFD700"},
        {"x": 3, "y": 1, "z": 0, "hex_color": "#FFD700"},
        # Second layer
        {"x": 0, "y": 0, "z": 1, "hex_color": "#FFD700"},
        {"x": 1, "y": 0, "z": 1, "hex_color": "#FFD700"},
        {"x": 2, "y": 0, "z": 1, "hex_color": "#FFD700"},
        {"x": 3, "y": 0, "z": 1, "hex_color": "#FFD700"},
        {"x": 0, "y": 1, "z": 1, "hex_color": "#FFD700"},
        {"x": 1, "y": 1, "z": 1, "hex_color": "#FFD700"},
        {"x": 2, "y": 1, "z": 1, "hex_color": "#FFD700"},
        {"x": 3, "y": 1, "z": 1, "hex_color": "#FFD700"},
    ]
    
    print(f"\nInput: {len(voxel_data)} voxels with hex color #FFD700 (Gold)")
    print("Expected: Should map to Yellow (Color ID 14) and verify part availability")
    
    manifest = await builder.process_voxels(voxel_data)
    
    print(f"\n✅ Output: MasterManifest generated!")
    print(f"   Total bricks: {manifest['total_bricks']}")
    
    # Check verification status
    verified_count = sum(1 for b in manifest['bricks'] if b.get('is_verified', False))
    print(f"   Verified bricks: {verified_count}/{manifest['total_bricks']}")
    
    # Show first few bricks
    print(f"\n📦 First 5 bricks:")
    for i, brick in enumerate(manifest['bricks'][:5], 1):
        verified = "✅" if brick.get('is_verified', False) else "❌"
        print(f"   {i}. {brick['part_id']} at {brick['position']} "
              f"(color {brick['color_id']}) {verified}")
    
    # Check color mapping
    if manifest['bricks']:
        first_color = manifest['bricks'][0]['color_id']
        print(f"\n🎨 Color mapping: #FFD700 -> Color ID {first_color}")
        if first_color == 14:
            print("   ✅ Correctly mapped to Yellow (14)")
        else:
            print(f"   ⚠️  Mapped to Color ID {first_color} (expected 14)")
    
    return manifest


async def test_fallback_logic():
    """Test fallback logic when a part is unavailable"""
    print("\n" + "="*70)
    print("TEST 4: Fallback Logic (Unavailable Parts)")
    print("="*70)
    
    print("\nNote: This test demonstrates fallback behavior.")
    print("If a 2x4 brick is unavailable, the system will try 2x2, then 1x2, then 1x1.")
    
    builder = MasterBuilder()
    
    # Small structure that could use different brick sizes
    voxel_data = [
        {"x": 0, "y": 0, "z": 0, "hex_color": "#FF0000"},
        {"x": 1, "y": 0, "z": 0, "hex_color": "#FF0000"},
        {"x": 0, "y": 1, "z": 0, "hex_color": "#FF0000"},
        {"x": 1, "y": 1, "z": 0, "hex_color": "#FF0000"},
    ]
    
    print(f"\nInput: {len(voxel_data)} voxels (2x2 square)")
    print("Expected: Should try 2x4 (fail), then 2x2 (succeed)")
    
    manifest = await builder.process_voxels(voxel_data)
    
    print(f"\n✅ Output: {manifest['total_bricks']} bricks placed")
    print(f"   Brick types used:")
    brick_types = {}
    for brick in manifest['bricks']:
        part_id = brick['part_id']
        brick_types[part_id] = brick_types.get(part_id, 0) + 1
    
    for part_id, count in sorted(brick_types.items()):
        print(f"     - {part_id}: {count}x")
    
    return manifest


if __name__ == "__main__":
    print("\n" + "="*70)
    print("REBRICKABLE API INTEGRATION TEST SUITE")
    print("="*70)
    
    async def run_all_tests():
        try:
            await test_color_mapping()
            await test_part_verification()
            await test_full_pipeline()
            await test_fallback_logic()
            
            print("\n" + "="*70)
            print("✅ ALL TESTS COMPLETED")
            print("="*70)
            print("\nData Flow Summary:")
            print("1. ✅ Voxel Input: (x, y, z, hex_color)")
            print("2. ✅ Color Mapping: Hex -> Rebrickable Color ID")
            print("3. ✅ Part Verification: Check availability via API")
            print("4. ✅ Fallback Logic: Try next smaller brick if unavailable")
            print("5. ✅ Output: MasterManifest with is_verified flag")
            
        except Exception as e:
            print(f"\n❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    asyncio.run(run_all_tests())
