"""
Rebrickable API Integration
Provides color mapping and part availability verification for LEGO bricks.
"""
import os
import logging
import httpx
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RebrickableAPI:
    """
    Client for Rebrickable API integration.
    
    Features:
    - Color mapping: Convert hex codes to closest LEGO color
    - Part verification: Check if a part is available in a specific color
    """
    
    BASE_URL = "https://rebrickable.com/api/v3"
    
    def __init__(self):
        """Initialize the Rebrickable API client."""
        self.api_key = os.getenv("REBRICKABLE_API_KEY")
        if not self.api_key:
            logger.warning(
                "REBRICKABLE_API_KEY not set. Color mapping will use fallback values."
            )
            self.api_key = None
        
        # Cache for colors (fetched once)
        self._colors_cache: Optional[List[Dict]] = None
        
        # Cache for part availability checks
        self._availability_cache: Dict[Tuple[str, int], bool] = {}
        
        # Cache for parts list (fetched dynamically)
        self._parts_cache: Optional[List[Dict]] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "MasterBuilder/1.0"
        }
        if self.api_key:
            headers["Authorization"] = f"key {self.api_key}"
        return headers
    
    async def _fetch_colors(self) -> List[Dict]:
        """
        Fetch all LEGO colors from Rebrickable API.
        Caches the result for subsequent calls.
        """
        if self._colors_cache is not None:
            return self._colors_cache
        
        if not self.api_key:
            logger.warning("No API key, using fallback color mapping")
            self._colors_cache = self._get_fallback_colors()
            return self._colors_cache
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.BASE_URL}/lego/colors/"
                headers = self._get_headers()
                
                logger.info("Fetching LEGO colors from Rebrickable API...")
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                colors = data.get("results", [])
                
                # Handle pagination if needed
                while data.get("next"):
                    next_url = data["next"]
                    response = await client.get(next_url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    colors.extend(data.get("results", []))
                
                self._colors_cache = colors
                logger.info(f"Fetched {len(colors)} LEGO colors from Rebrickable")
                return colors
                
        except httpx.HTTPError as e:
            logger.error(f"Error fetching colors from Rebrickable: {e}")
            logger.warning("Using fallback color mapping")
            self._colors_cache = self._get_fallback_colors()
            return self._colors_cache
        except Exception as e:
            logger.error(f"Unexpected error fetching colors: {e}")
            self._colors_cache = self._get_fallback_colors()
            return self._colors_cache
    
    def _get_fallback_colors(self) -> List[Dict]:
        """Fallback color mapping when API is unavailable."""
        return [
            {"id": 0, "name": "Black", "rgb": "05131D"},
            {"id": 1, "name": "White", "rgb": "FFFFFF"},
            {"id": 2, "name": "Green", "rgb": "237841"},
            {"id": 3, "name": "Yellow", "rgb": "F2CD37"},
            {"id": 4, "name": "Red", "rgb": "C91A09"},
            {"id": 5, "name": "Red", "rgb": "C91A09"},
            {"id": 6, "name": "Blue", "rgb": "0055BF"},
            {"id": 7, "name": "Blue", "rgb": "0055BF"},
            {"id": 8, "name": "Orange", "rgb": "FF6B00"},
            {"id": 9, "name": "Light Gray", "rgb": "9CA3A8"},
            {"id": 10, "name": "Dark Gray", "rgb": "6B5A5A"},
            {"id": 11, "name": "Pink", "rgb": "FF69B4"},
            {"id": 12, "name": "Brown", "rgb": "583927"},
            {"id": 13, "name": "Magenta", "rgb": "C870A0"},
            {"id": 14, "name": "Yellow", "rgb": "F2CD37"},
            {"id": 15, "name": "White", "rgb": "FFFFFF"},
        ]
    
    def _hex_to_rgb(self, hex_code: str) -> Tuple[int, int, int]:
        """Convert hex color code to RGB tuple."""
        hex_code = hex_code.lstrip("#")
        if len(hex_code) == 3:
            hex_code = "".join([c * 2 for c in hex_code])
        try:
            return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            logger.warning(f"Invalid hex code: {hex_code}, using white")
            return (255, 255, 255)
    
    def _rgb_distance(self, rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
        """
        Calculate RGB color distance using Euclidean distance in RGB space.
        Lower values indicate closer colors.
        """
        r1, g1, b1 = rgb1
        r2, g2, b2 = rgb2
        return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
    
    async def get_closest_lego_color(self, hex_code: str) -> int:
        """
        Find the closest LEGO color to a given hex code.
        
        Args:
            hex_code: Hex color code (e.g., "#FFD700")
            
        Returns:
            Rebrickable color ID of the closest match
        """
        colors = await self._fetch_colors()
        target_rgb = self._hex_to_rgb(hex_code)
        
        best_match = None
        best_distance = float('inf')
        
        for color in colors:
            color_rgb_str = color.get("rgb", "FFFFFF")
            color_rgb = self._hex_to_rgb(color_rgb_str)
            distance = self._rgb_distance(target_rgb, color_rgb)
            
            if distance < best_distance:
                best_distance = distance
                best_match = color
        
        if best_match:
            color_id = best_match.get("id")
            color_name = best_match.get("name", "Unknown")
            logger.debug(
                f"Hex {hex_code} -> Color ID {color_id} ({color_name}), "
                f"distance: {best_distance:.2f}"
            )
            return color_id
        
        # Fallback to white if no match found
        logger.warning(f"No color match found for {hex_code}, using white (ID: 1)")
        return 1
    
    async def verify_part_availability(self, part_id: str, color_id: int) -> bool:
        """
        Verify if a LEGO part is available in a specific color.
        
        Args:
            part_id: LEGO part number (e.g., "3001")
            color_id: Rebrickable color ID
            
        Returns:
            True if the part is available in the specified color, False otherwise
        """
        # Check cache first
        cache_key = (part_id, color_id)
        if cache_key in self._availability_cache:
            return self._availability_cache[cache_key]
        
        if not self.api_key:
            logger.warning(
                f"No API key, assuming part {part_id} is available in color {color_id}"
            )
            # Default to available when API key is missing
            self._availability_cache[cache_key] = True
            return True
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.BASE_URL}/lego/parts/{part_id}/colors/{color_id}/"
                headers = self._get_headers()
                
                response = await client.get(url, headers=headers)
                
                # 200 means available, 404 means not available
                is_available = response.status_code == 200
                
                self._availability_cache[cache_key] = is_available
                
                if is_available:
                    logger.debug(f"✅ Part {part_id} available in color {color_id}")
                else:
                    logger.debug(f"❌ Part {part_id} NOT available in color {color_id}")
                return is_available
                    
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Part not available in this color
                self._availability_cache[cache_key] = False
                logger.debug(f"❌ Part {part_id} NOT available in color {color_id} (404)")
                return False
            else:
                logger.error(f"HTTP error checking part availability: {e}")
                # On error, assume available to avoid blocking
                self._availability_cache[cache_key] = True
                return True
        except Exception as e:
            logger.error(f"Error verifying part availability: {e}")
            # On error, assume available to avoid blocking
            self._availability_cache[cache_key] = True
            return True
    
    async def fetch_parts(
        self,
        part_category: Optional[str] = None,
        search_term: Optional[str] = None,
        min_area: Optional[int] = None,
        max_results: int = 200
    ) -> List[Dict]:
        """
        Fetch LEGO parts from Rebrickable API with filtering.
        
        Args:
            part_category: Filter by category (e.g., "Bricks", "Plates", "Tiles")
            search_term: Search term to filter parts by name/description
            min_area: Minimum area (width * height) for rectangular parts
            max_results: Maximum number of results to return
            
        Returns:
            List of part dictionaries with part_num, name, dimensions, etc.
        """
        if not self.api_key:
            logger.warning("No API key, using fallback parts list")
            return self._get_fallback_parts()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.BASE_URL}/lego/parts/"
                headers = self._get_headers()
                params = {
                    "page_size": min(max_results, 1000),  # API limit
                }
                
                if search_term:
                    params["search"] = search_term
                
                logger.info(f"Fetching parts from Rebrickable API (search: {search_term})...")
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                parts = data.get("results", [])
                
                # Handle pagination
                while data.get("next") and len(parts) < max_results:
                    next_url = data["next"]
                    response = await client.get(next_url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    parts.extend(data.get("results", []))
                
                # Filter by category if specified
                if part_category:
                    parts = [
                        p for p in parts
                        if part_category.lower() in p.get("part_cat_id", {}).get("name", "").lower()
                    ]
                
                # Limit results
                parts = parts[:max_results]
                
                logger.info(f"Fetched {len(parts)} parts from Rebrickable")
                return parts
                
        except Exception as e:
            logger.error(f"Error fetching parts from Rebrickable: {e}")
            return self._get_fallback_parts()
    
    def _get_fallback_parts(self) -> List[Dict]:
        """Fallback parts list when API is unavailable."""
        # Return basic rectangular bricks as fallback
        return [
            {"part_num": "3001", "name": "Brick 2 x 4", "width": 4, "height": 2},
            {"part_num": "3003", "name": "Brick 2 x 2", "width": 2, "height": 2},
            {"part_num": "3004", "name": "Brick 1 x 2", "width": 2, "height": 1},
            {"part_num": "3005", "name": "Brick 1 x 1", "width": 1, "height": 1},
        ]


# Global instance for reuse
_rebrickable_client: Optional[RebrickableAPI] = None


def get_rebrickable_client() -> RebrickableAPI:
    """Get or create the global Rebrickable API client instance."""
    global _rebrickable_client
    if _rebrickable_client is None:
        _rebrickable_client = RebrickableAPI()
    return _rebrickable_client
