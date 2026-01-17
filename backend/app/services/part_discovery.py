"""
Intelligent Part Discovery Service
Uses Backboard API to intelligently search for LEGO parts based on shape characteristics.
"""
import os
import logging
from typing import Dict, List, Optional, Tuple, Set
from backboard import BackboardClient
from dotenv import load_dotenv
from app.services.rebrickable_api import get_rebrickable_client

load_dotenv()

logger = logging.getLogger(__name__)


class PartDiscoveryService:
    """
    Service for intelligent LEGO part discovery using Backboard AI.
    
    Analyzes voxel clusters to determine shape characteristics (round, curved, etc.)
    and uses Backboard API to find appropriate LEGO parts.
    """
    
    def __init__(self):
        """Initialize the Part Discovery Service."""
        self.backboard_client = None
        backboard_key = os.getenv("BACKBOARD_API_KEY")
        if backboard_key:
            try:
                self.backboard_client = BackboardClient(api_key=backboard_key)
                logger.info("Backboard client initialized for intelligent part discovery")
            except Exception as e:
                logger.warning(f"Could not initialize Backboard client: {e}")
        
        self.rebrickable = get_rebrickable_client()
        
        # Cache for discovered parts
        self._discovered_parts_cache: Dict[str, List[Dict]] = {}
    
    def analyze_voxel_shape(self, voxels: Set[Tuple[int, int]]) -> Dict[str, any]:
        """
        Analyze a voxel cluster to determine shape characteristics.
        
        Args:
            voxels: Set of (x, y) positions in a 2D layer
            
        Returns:
            Dictionary with shape characteristics:
            - is_round: bool
            - is_curved: bool
            - is_rectangular: bool
            - aspect_ratio: float
            - bounding_box: (min_x, min_y, max_x, max_y)
        """
        if not voxels:
            return {
                "is_round": False,
                "is_curved": False,
                "is_rectangular": True,
                "aspect_ratio": 1.0,
                "bounding_box": (0, 0, 0, 0)
            }
        
        xs = [x for x, y in voxels]
        ys = [y for x, y in voxels]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        area = len(voxels)
        bounding_area = width * height
        
        # Calculate aspect ratio
        aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 1.0
        
        # Check if rectangular (fills bounding box)
        is_rectangular = area == bounding_area
        
        # Check if round (circular shape)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        radius = min(width, height) / 2
        
        round_score = 0
        for x, y in voxels:
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            if abs(distance - radius) < 0.5:  # Within 0.5 studs of circle
                round_score += 1
        
        is_round = round_score / area > 0.7 if area > 0 else False
        
        # Check if curved (has curves but not fully round)
        is_curved = not is_round and not is_rectangular and aspect_ratio > 1.5
        
        return {
            "is_round": is_round,
            "is_curved": is_curved,
            "is_rectangular": is_rectangular,
            "aspect_ratio": aspect_ratio,
            "bounding_box": (min_x, min_y, max_x, max_y),
            "width": width,
            "height": height,
            "area": area
        }
    
    async def discover_parts_for_shape(
        self,
        shape_analysis: Dict,
        color_id: int,
        use_hard_search: bool = False
    ) -> List[Dict]:
        """
        Use Backboard API to discover appropriate LEGO parts for a given shape.
        
        Args:
            shape_analysis: Result from analyze_voxel_shape()
            color_id: Target color ID
            use_hard_search: If True, uses more thorough AI search
            
        Returns:
            List of part candidates with part_num, priority_score, etc.
        """
        cache_key = f"{shape_analysis.get('is_round')}_{shape_analysis.get('is_curved')}_{shape_analysis.get('width')}_{shape_analysis.get('height')}"
        
        if cache_key in self._discovered_parts_cache:
            return self._discovered_parts_cache[cache_key]
        
        # Build search query based on shape characteristics
        search_terms = []
        
        if shape_analysis.get("is_round"):
            search_terms.append("round brick")
            search_terms.append("circular")
        elif shape_analysis.get("is_curved"):
            search_terms.append("curved brick")
            search_terms.append("slope")
        else:
            # Rectangular - use dimensions
            width = shape_analysis.get("width", 1)
            height = shape_analysis.get("height", 1)
            search_terms.append(f"{width}x{height} brick")
        
        # Use Backboard for intelligent search if available
        if self.backboard_client and use_hard_search:
            parts = await self._backboard_intelligent_search(
                shape_analysis, search_terms, color_id
            )
        else:
            # Simple search via Rebrickable
            parts = await self._rebrickable_simple_search(
                shape_analysis, search_terms, color_id
            )
        
        # Sort by priority (area descending for greedy fitting)
        parts.sort(key=lambda p: p.get("area", 0), reverse=True)
        
        self._discovered_parts_cache[cache_key] = parts
        return parts
    
    async def _backboard_intelligent_search(
        self,
        shape_analysis: Dict,
        search_terms: List[str],
        color_id: int
    ) -> List[Dict]:
        """
        Use Backboard AI for intelligent part search.
        This provides more sophisticated matching based on shape descriptions.
        """
        if not self.backboard_client:
            return await self._rebrickable_simple_search(shape_analysis, search_terms, color_id)
        
        try:
            # Create a prompt for Backboard to find appropriate parts
            prompt = f"""
            Find LEGO parts that match these characteristics:
            - Shape: {"Round" if shape_analysis.get("is_round") else "Curved" if shape_analysis.get("is_curved") else "Rectangular"}
            - Dimensions: {shape_analysis.get("width")}x{shape_analysis.get("height")} studs
            - Area: {shape_analysis.get("area")} studs
            - Color ID: {color_id}
            
            Search terms: {', '.join(search_terms)}
            
            Return a list of LEGO part numbers (part_num) that would fit this shape,
            prioritized by how well they match. Focus on parts that:
            1. Match the shape (round/curved/rectangular)
            2. Are close to the target dimensions
            3. Are available in the specified color
            4. Minimize part count (prefer larger parts)
            """
            
            # Use Backboard to generate part suggestions
            # This would use the Backboard API to get AI-generated part recommendations
            # For now, fall back to simple search
            logger.info("Using Backboard intelligent search for part discovery")
            # TODO: Implement actual Backboard API call
            
            return await self._rebrickable_simple_search(shape_analysis, search_terms, color_id)
            
        except Exception as e:
            logger.error(f"Error in Backboard intelligent search: {e}")
            return await self._rebrickable_simple_search(shape_analysis, search_terms, color_id)
    
    async def _rebrickable_simple_search(
        self,
        shape_analysis: Dict,
        search_terms: List[str],
        color_id: int
    ) -> List[Dict]:
        """
        Simple search via Rebrickable API.
        Searches for parts matching the search terms.
        """
        parts = []
        
        for search_term in search_terms:
            try:
                rebrickable_parts = await self.rebrickable.fetch_parts(
                    search_term=search_term,
                    max_results=50
                )
                
                # Convert to our format and filter by availability
                for part in rebrickable_parts:
                    part_num = part.get("part_num", "")
                    if not part_num:
                        continue
                    
                    # Check if available in target color
                    is_available = await self.rebrickable.verify_part_availability(
                        part_num, color_id
                    )
                    
                    if is_available:
                        # Extract dimensions if available
                        width = part.get("width", 1)
                        height = part.get("height", 1)
                        area = width * height
                        
                        parts.append({
                            "part_num": part_num,
                            "name": part.get("name", ""),
                            "width": width,
                            "height": height,
                            "area": area,
                            "color_id": color_id,
                            "is_verified": True,
                            "priority_score": area  # Larger parts = higher priority
                        })
            except Exception as e:
                logger.warning(f"Error searching for '{search_term}': {e}")
                continue
        
        # Remove duplicates
        seen = set()
        unique_parts = []
        for part in parts:
            key = part["part_num"]
            if key not in seen:
                seen.add(key)
                unique_parts.append(part)
        
        return unique_parts


# Global instance
_part_discovery_service: Optional[PartDiscoveryService] = None


def get_part_discovery_service() -> PartDiscoveryService:
    """Get or create the global Part Discovery Service instance."""
    global _part_discovery_service
    if _part_discovery_service is None:
        _part_discovery_service = PartDiscoveryService()
    return _part_discovery_service
