"""
Piece Counter Service
Counts, catalogs, and generates inventories of LEGO pieces from build manifests.
Provides detailed piece tracking for shopping lists and build guides.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PieceCount:
    """Represents a counted piece type"""
    part_id: str
    color_id: int
    color_name: str
    quantity: int
    piece_name: str
    price_estimate: Optional[float] = None  # USD estimate


@dataclass
class PieceSummary:
    """Summary of all pieces in a build"""
    total_unique_pieces: int
    total_pieces: int
    piece_counts: List[PieceCount]
    by_category: Dict[str, int]  # Category -> count
    by_color: Dict[str, int]  # Color name -> count
    estimated_cost: float


class PieceCounter:
    """
    Analyzes LEGO builds and provides detailed piece inventories.
    """
    
    # LEGO Part ID to Name mapping (common pieces)
    PART_NAMES = {
        "3001": "Brick 2x4",
        "3002": "Brick 2x3",
        "3003": "Brick 2x2",
        "3004": "Brick 1x2",
        "3005": "Brick 1x1",
        "3009": "Brick 1x6",
        "3040": "Slope 45° 2x1",
        "3038": "Slope 45° Inverted 2x1",
        "3297": "Slope 33° 2x2",
        "3068": "Tile 2x2",
        "3069": "Tile 1x2",
        "3070": "Tile 1x1",
        "3938": "Hinge Brick 1x2",
        "6134": "Hinge Plate 1x2",
    }
    
    # LEGO Color ID to Name mapping (common colors)
    COLOR_NAMES = {
        1: "White",
        2: "Tan",
        3: "Light Gray",
        4: "Dark Gray",
        5: "Red",
        6: "Dark Red",
        7: "Brown",
        8: "Dark Brown",
        9: "Yellow",
        10: "Light Yellow",
        11: "Green",
        12: "Dark Green",
        13: "Blue",
        14: "Dark Blue",
        15: "Black",
        16: "Orange",
        17: "Light Blue",
        18: "Purple",
        19: "Pink",
        20: "Beige",
    }
    
    # Price estimates per piece (USD, varies by type and size)
    PIECE_PRICES = {
        "3001": 0.10,   # 2x4
        "3002": 0.08,   # 2x3
        "3003": 0.06,   # 2x2
        "3004": 0.04,   # 1x2
        "3005": 0.03,   # 1x1
        "3009": 0.08,   # 1x6
        "3068": 0.05,   # Tile 2x2
        "3069": 0.03,   # Tile 1x2
        "3070": 0.02,   # Tile 1x1
        "3938": 0.12,   # Hinge
        "6134": 0.10,   # Hinge Plate
    }
    
    # Piece categories
    PIECE_CATEGORIES = {
        "3001": "Bricks",
        "3002": "Bricks",
        "3003": "Bricks",
        "3004": "Bricks",
        "3005": "Bricks",
        "3009": "Bricks",
        "3040": "Slopes",
        "3038": "Slopes",
        "3297": "Slopes",
        "3068": "Tiles",
        "3069": "Tiles",
        "3070": "Tiles",
        "3938": "Hinges",
        "6134": "Hinges",
    }
    
    @staticmethod
    def count_pieces(manifest: Dict) -> PieceSummary:
        """
        Count all pieces in a manifest and generate summary.
        
        Args:
            manifest: The build manifest JSON with bricks array
            
        Returns:
            PieceSummary with detailed piece counts and analysis
        """
        piece_counts = defaultdict(int)
        category_counts = defaultdict(int)
        color_counts = defaultdict(int)
        total_cost = 0.0
        
        try:
            # Count pieces from manifest
            for brick in manifest.get("bricks", []):
                part_id = brick.get("part_id")
                color_id = brick.get("color_id", 16)  # Default to black
                
                key = (part_id, color_id)
                piece_counts[key] += 1
                
                # Category counting
                category = PieceCounter.PIECE_CATEGORIES.get(part_id, "Other")
                category_counts[category] += 1
                
                # Color counting
                color_name = PieceCounter.COLOR_NAMES.get(color_id, f"Color_{color_id}")
                color_counts[color_name] += 1
            
            # Build piece count list
            piece_list = []
            for (part_id, color_id), quantity in piece_counts.items():
                piece_name = PieceCounter.PART_NAMES.get(part_id, f"Part_{part_id}")
                color_name = PieceCounter.COLOR_NAMES.get(color_id, f"Color_{color_id}")
                
                # Estimate price
                price_per_piece = PieceCounter.PIECE_PRICES.get(part_id, 0.05)
                total_price = price_per_piece * quantity
                total_cost += total_price
                
                piece_list.append(PieceCount(
                    part_id=part_id,
                    color_id=color_id,
                    color_name=color_name,
                    quantity=quantity,
                    piece_name=piece_name,
                    price_estimate=total_price
                ))
            
            # Sort by quantity descending
            piece_list.sort(key=lambda p: p.quantity, reverse=True)
            
            return PieceSummary(
                total_unique_pieces=len(piece_counts),
                total_pieces=sum(piece_counts.values()),
                piece_counts=piece_list,
                by_category=dict(category_counts),
                by_color=dict(color_counts),
                estimated_cost=round(total_cost, 2)
            )
        
        except Exception as e:
            logger.error(f"Error counting pieces: {e}")
            return PieceSummary(
                total_unique_pieces=0,
                total_pieces=0,
                piece_counts=[],
                by_category={},
                by_color={},
                estimated_cost=0.0
            )
    
    @staticmethod
    def generate_shopping_list(summary: PieceSummary) -> str:
        """
        Generate a human-readable shopping list from piece summary.
        
        Args:
            summary: PieceSummary from count_pieces()
            
        Returns:
            Formatted shopping list string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("LEGO BUILD - SHOPPING LIST")
        lines.append("=" * 60)
        lines.append(f"\nTotal Unique Pieces: {summary.total_unique_pieces}")
        lines.append(f"Total Bricks Needed: {summary.total_pieces}")
        lines.append(f"Estimated Cost: ${summary.estimated_cost:.2f}\n")
        
        lines.append("Breakdown by Category:")
        lines.append("-" * 40)
        for category, count in sorted(summary.by_category.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {category}: {count} pieces")
        
        lines.append("\n\nDetailed Piece List:")
        lines.append("-" * 60)
        lines.append(f"{'Part ID':<10} {'Piece Name':<25} {'Color':<15} {'Qty':<8} {'Cost':<8}")
        lines.append("-" * 60)
        
        for piece in summary.piece_counts:
            lines.append(
                f"{piece.part_id:<10} {piece.piece_name:<25} "
                f"{piece.color_name:<15} {piece.quantity:<8} "
                f"${piece.price_estimate or 0:.2f}"
            )
        
        lines.append("-" * 60)
        lines.append(f"TOTAL ESTIMATED COST: ${summary.estimated_cost:.2f}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_inventory_csv(summary: PieceSummary) -> str:
        """
        Generate CSV format inventory for import into spreadsheets.
        
        Args:
            summary: PieceSummary from count_pieces()
            
        Returns:
            CSV formatted string
        """
        lines = ["Part ID,Piece Name,Color,Color ID,Quantity,Unit Price,Total Price"]
        
        for piece in summary.piece_counts:
            lines.append(
                f"{piece.part_id},"
                f'"{piece.piece_name}",'
                f'"{piece.color_name}",'
                f"{piece.color_id},"
                f"{piece.quantity},"
                f"${piece.price_estimate / piece.quantity if piece.quantity > 0 else 0:.2f},"
                f"${piece.price_estimate or 0:.2f}"
            )
        
        return "\n".join(lines)
    
    @staticmethod
    def get_piece_info(part_id: str, color_id: int = 16) -> Dict:
        """
        Get detailed information about a specific piece.
        
        Args:
            part_id: LEGO part ID
            color_id: LEGO color ID
            
        Returns:
            Dictionary with piece information
        """
        return {
            "part_id": part_id,
            "name": PieceCounter.PART_NAMES.get(part_id, f"Part_{part_id}"),
            "category": PieceCounter.PIECE_CATEGORIES.get(part_id, "Other"),
            "color_id": color_id,
            "color_name": PieceCounter.COLOR_NAMES.get(color_id, f"Color_{color_id}"),
            "unit_price": PieceCounter.PIECE_PRICES.get(part_id, 0.05),
        }
    
    @staticmethod
    def compare_builds(manifest1: Dict, manifest2: Dict) -> Dict:
        """
        Compare two builds and show differences.
        
        Args:
            manifest1: First build manifest
            manifest2: Second build manifest
            
        Returns:
            Dictionary with comparison results
        """
        summary1 = PieceCounter.count_pieces(manifest1)
        summary2 = PieceCounter.count_pieces(manifest2)
        
        # Create piece maps for comparison
        pieces1 = {(p.part_id, p.color_id): p.quantity for p in summary1.piece_counts}
        pieces2 = {(p.part_id, p.color_id): p.quantity for p in summary2.piece_counts}
        
        # Find differences
        added = {}
        removed = {}
        different = {}
        
        for key, qty in pieces2.items():
            if key not in pieces1:
                added[key] = qty
            elif pieces1[key] != qty:
                different[key] = (pieces1[key], qty)
        
        for key, qty in pieces1.items():
            if key not in pieces2:
                removed[key] = qty
        
        return {
            "build1_total": summary1.total_pieces,
            "build2_total": summary2.total_pieces,
            "pieces_added": added,
            "pieces_removed": removed,
            "pieces_different": different,
            "cost_difference": summary2.estimated_cost - summary1.estimated_cost
        }
