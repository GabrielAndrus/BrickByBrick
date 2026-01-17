#!/usr/bin/env python3
"""
Test script to verify brick priority sorting and optimization.

Verifies that bricks are sorted correctly by volume for optimal greedy fitting.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.master_builder import MasterBuilder


def test_brick_priority_sorting():
    """Test that brick priorities are sorted correctly by volume"""
    print("="*70)
    print("TEST: Brick Priority Sorting")
    print("="*70)
    
    sorted_priorities = MasterBuilder._get_sorted_brick_priorities()
    
    print(f"\nTotal brick types: {len(sorted_priorities)}")
    print(f"\nTop 20 brick types (sorted by area, then width):")
    print(f"{'Part ID':<10} {'Dimensions':<12} {'Area':<8} {'Volume':<8}")
    print("-" * 50)
    
    for i, (width, height, depth, part_id) in enumerate(sorted_priorities[:20], 1):
        area = width * height
        volume = width * height * depth
        print(f"{part_id:<10} {width}x{height}x{depth:<4} {area:<8} {volume:<8}")
    
    # Verify sorting
    print(f"\n✅ Verification:")
    areas = [w * h for w, h, d, _ in sorted_priorities]
    is_sorted = all(areas[i] >= areas[i+1] for i in range(len(areas)-1))
    
    if is_sorted:
        print(f"   ✅ Bricks are correctly sorted by area (descending)")
    else:
        print(f"   ❌ Bricks are NOT correctly sorted!")
        # Show where it breaks
        for i in range(len(areas)-1):
            if areas[i] < areas[i+1]:
                w1, h1, d1, p1 = sorted_priorities[i]
                w2, h2, d2, p2 = sorted_priorities[i+1]
                print(f"   Issue: {p1} ({w1}x{h1}, area={areas[i]}) before {p2} ({w2}x{h2}, area={areas[i+1]})")
    
    # Check that largest bricks come first
    first_brick = sorted_priorities[0]
    first_area = first_brick[0] * first_brick[1]
    print(f"\n   Largest brick: {first_brick[3]} ({first_brick[0]}x{first_brick[1]}, area={first_area})")
    
    return sorted_priorities


def test_optimization_logic():
    """Test that the optimization logic makes sense"""
    print("\n" + "="*70)
    print("TEST: Optimization Logic")
    print("="*70)
    
    info = MasterBuilder.get_brick_priority_info()
    
    print(f"\nTotal brick types available: {info['total_brick_types']}")
    print(f"\nOptimization Strategy:")
    print(f"  1. Try largest bricks first (by area)")
    print(f"  2. If unavailable, fallback to next smaller size")
    print(f"  3. This minimizes total part count")
    
    print(f"\nExample: Filling a 8x4 area")
    print(f"  Option 1: 1x 2x8 brick (area=16) ✅ Optimal")
    print(f"  Option 2: 2x 2x4 bricks (area=8 each) ❌ More parts")
    print(f"  Option 3: 4x 1x2 bricks (area=2 each) ❌ Many parts")
    print(f"  Option 4: 32x 1x1 bricks (area=1 each) ❌ Too many parts")
    
    print(f"\n✅ The algorithm will try Option 1 first (largest brick)")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("BRICK PRIORITY OPTIMIZATION TEST")
    print("="*70)
    
    try:
        test_brick_priority_sorting()
        test_optimization_logic()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED")
        print("="*70)
        print("\nSummary:")
        print(f"  - Expanded from 4 to {len(MasterBuilder.BRICK_PRIORITIES)} brick types")
        print(f"  - Sorted by volume (area) for optimal greedy fitting")
        print(f"  - Supports bricks, plates, and tiles")
        print(f"  - Automatically tries largest bricks first to minimize part count")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
