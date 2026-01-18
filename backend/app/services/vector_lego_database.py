"""
Vector Database for LEGO Component Memory & Intelligence
Stores and retrieves similar LEGO components to minimize variety and reuse solutions.
Integrates with Backboard.io for persistent cross-session memory.
"""

import logging
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn not available. Install with: pip install scikit-learn numpy")


@dataclass
class LegoComponentMemory:
    """Stored memory of a LEGO component"""
    component_id: str  # Unique ID
    component_type: str  # desk, bed, chair, door, etc.
    brick_composition: Dict[str, int]  # part_id -> quantity
    signature: str  # Hash of normalized composition
    dimensions: Tuple[int, int, int]  # width, depth, height
    typical_colors: List[int]  # color IDs used
    room_contexts: List[str] = field(default_factory=list)  # bedroom, office, living room
    creation_date: str = field(default_factory=lambda: datetime.now().isoformat())
    usage_count: int = 0  # How many times reused
    confirmed: bool = False  # User-confirmed good design
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "brick_composition": self.brick_composition,
            "signature": self.signature,
            "dimensions": self.dimensions,
            "typical_colors": self.typical_colors,
            "room_contexts": self.room_contexts,
            "creation_date": self.creation_date,
            "usage_count": self.usage_count,
            "confirmed": self.confirmed,
            "metadata": self.metadata
        }


class VectorLegoDatabase:
    """
    Vector database for semantic similarity search of LEGO components.
    Uses TF-IDF vectorization to find similar designs.
    """
    
    def __init__(self):
        """Initialize vector database"""
        self.memories: Dict[str, LegoComponentMemory] = {}
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.vectors: Optional[np.ndarray] = None
        self.memory_ids: List[str] = []
        
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn required for vector search. Falling back to basic matching.")
    
    def add_memory(self, component: LegoComponentMemory) -> str:
        """
        Add a component to memory.
        
        Args:
            component: LegoComponentMemory to store
            
        Returns:
            Component ID
        """
        try:
            self.memories[component.component_id] = component
            self.memory_ids.append(component.component_id)
            
            # Rebuild vectors if we have sklearn
            if SKLEARN_AVAILABLE and len(self.memories) > 1:
                self._rebuild_vectors()
            
            logger.info(f"Added memory: {component.component_id} ({component.component_type})")
            return component.component_id
        
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return None
    
    def find_similar(
        self,
        component_type: str,
        brick_composition: Dict[str, int],
        threshold: float = 0.7,
        top_k: int = 5
    ) -> List[Tuple[LegoComponentMemory, float]]:
        """
        Find similar components using vector similarity.
        
        Args:
            component_type: Type of component (desk, chair, etc.)
            brick_composition: Target brick composition
            threshold: Minimum similarity score (0-1)
            top_k: Maximum results to return
            
        Returns:
            List of (component, similarity_score) tuples
        """
        try:
            if not SKLEARN_AVAILABLE:
                # Fallback: basic type matching
                return self._find_similar_basic(component_type, threshold, top_k)
            
            # Filter by type first
            same_type = [
                (cid, mem) for cid, mem in self.memories.items()
                if mem.component_type == component_type
            ]
            
            if not same_type:
                logger.debug(f"No memories found for type: {component_type}")
                return []
            
            # Convert target composition to text vector
            target_text = self._composition_to_text(brick_composition)
            
            # Compare to similar type memories
            results = []
            for cid, memory in same_type:
                memory_text = self._composition_to_text(memory.brick_composition)
                
                # Simple similarity: matching parts
                similarity = self._compute_similarity(target_text, memory_text)
                
                if similarity >= threshold:
                    results.append((memory, similarity))
            
            # Sort by similarity and return top k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
        
        except Exception as e:
            logger.error(f"Error finding similar components: {e}")
            return []
    
    def _find_similar_basic(
        self,
        component_type: str,
        threshold: float,
        top_k: int
    ) -> List[Tuple[LegoComponentMemory, float]]:
        """Basic similarity matching without sklearn"""
        results = []
        
        for cid, memory in self.memories.items():
            if memory.component_type == component_type:
                # Simple score: prefer confirmed and frequently used
                score = (memory.usage_count / 10.0) * 0.5
                score += (1.0 if memory.confirmed else 0.0) * 0.5
                
                if score >= threshold:
                    results.append((memory, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def _composition_to_text(self, brick_composition: Dict[str, int]) -> str:
        """Convert brick composition to text for vectorization"""
        parts = []
        for part_id, qty in sorted(brick_composition.items()):
            parts.extend([part_id] * qty)
        return " ".join(parts)
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity between two text representations"""
        if not text1 or not text2:
            return 0.0
        
        # Simple Jaccard similarity
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _rebuild_vectors(self):
        """Rebuild vector representation of all memories"""
        if not SKLEARN_AVAILABLE or len(self.memories) < 2:
            return
        
        try:
            # Convert all compositions to text
            texts = []
            for cid in self.memory_ids:
                if cid in self.memories:
                    memory = self.memories[cid]
                    text = self._composition_to_text(memory.brick_composition)
                    texts.append(text)
            
            if texts:
                self.vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(1, 2))
                self.vectors = self.vectorizer.fit_transform(texts).toarray()
                logger.debug(f"Rebuilt vectors for {len(texts)} memories")
        
        except Exception as e:
            logger.error(f"Error rebuilding vectors: {e}")
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        by_type = {}
        total_usage = 0
        
        for memory in self.memories.values():
            if memory.component_type not in by_type:
                by_type[memory.component_type] = 0
            by_type[memory.component_type] += 1
            total_usage += memory.usage_count
        
        return {
            "total_components": len(self.memories),
            "by_type": by_type,
            "total_reuses": total_usage,
            "confirmed_count": sum(1 for m in self.memories.values() if m.confirmed),
            "sklearn_available": SKLEARN_AVAILABLE
        }
    
    def save_to_file(self, filepath: str) -> bool:
        """Save database to JSON file"""
        try:
            data = {
                "total_components": len(self.memories),
                "memories": [mem.to_dict() for mem in self.memories.values()]
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.memories)} components to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            return False
    
    def load_from_file(self, filepath: str) -> bool:
        """Load database from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.memories.clear()
            self.memory_ids.clear()
            
            for mem_data in data.get("memories", []):
                memory = LegoComponentMemory(
                    component_id=mem_data.get("component_id"),
                    component_type=mem_data.get("component_type"),
                    brick_composition=mem_data.get("brick_composition", {}),
                    signature=mem_data.get("signature"),
                    dimensions=tuple(mem_data.get("dimensions", [0, 0, 0])),
                    typical_colors=mem_data.get("typical_colors", []),
                    room_contexts=mem_data.get("room_contexts", []),
                    creation_date=mem_data.get("creation_date"),
                    usage_count=mem_data.get("usage_count", 0),
                    confirmed=mem_data.get("confirmed", False),
                    metadata=mem_data.get("metadata", {})
                )
                self.add_memory(memory)
            
            logger.info(f"Loaded {len(self.memories)} components from {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            return False


class ComponentRecommender:
    """
    Recommends similar LEGO components based on current build.
    Uses vector database to suggest reusable solutions.
    """
    
    def __init__(self, vector_db: VectorLegoDatabase):
        """
        Initialize recommender.
        
        Args:
            vector_db: VectorLegoDatabase instance
        """
        self.vector_db = vector_db
    
    def recommend_component(
        self,
        component_type: str,
        target_dimensions: Tuple[int, int, int],
        room_context: str = None,
        max_recommendations: int = 3
    ) -> List[Dict]:
        """
        Get component recommendations.
        
        Args:
            component_type: Type of component (desk, chair, etc.)
            target_dimensions: Target (width, depth, height)
            room_context: Room type (bedroom, office, etc.)
            max_recommendations: Max results
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        try:
            # Get all memories of this type
            same_type = [
                (cid, mem) for cid, mem in self.vector_db.memories.items()
                if mem.component_type == component_type
            ]
            
            if not same_type:
                return []
            
            # Score by various factors
            scored = []
            for cid, memory in same_type:
                score = 0.0
                
                # Dimension similarity (prefer exact or close matches)
                dim_diff = sum(abs(a - b) for a, b in zip(target_dimensions, memory.dimensions))
                dim_score = max(0, 1.0 - (dim_diff / 20.0))  # Normalize to 0-1
                score += dim_score * 0.4
                
                # Confirmation bonus
                score += (1.0 if memory.confirmed else 0.0) * 0.3
                
                # Usage/popularity
                usage_score = min(1.0, memory.usage_count / 10.0)
                score += usage_score * 0.2
                
                # Room context match
                if room_context and room_context in memory.room_contexts:
                    score += 0.1
                
                scored.append((memory, score))
            
            # Sort and return top k
            scored.sort(key=lambda x: x[1], reverse=True)
            
            for memory, score in scored[:max_recommendations]:
                recommendations.append({
                    "component_id": memory.component_id,
                    "component_type": memory.component_type,
                    "dimensions": memory.dimensions,
                    "brick_count": sum(memory.brick_composition.values()),
                    "score": round(score, 2),
                    "confirmed": memory.confirmed,
                    "usage_count": memory.usage_count,
                    "brick_composition": memory.brick_composition
                })
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def track_usage(self, component_id: str, context: str = None) -> bool:
        """
        Track usage of a component.
        
        Args:
            component_id: Component to track
            context: Room or build context
            
        Returns:
            True if successful
        """
        try:
            if component_id in self.vector_db.memories:
                memory = self.vector_db.memories[component_id]
                memory.usage_count += 1
                
                if context and context not in memory.room_contexts:
                    memory.room_contexts.append(context)
                
                logger.debug(f"Tracked usage: {component_id} (now {memory.usage_count}x)")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
            return False
    
    def confirm_component(self, component_id: str) -> bool:
        """
        Mark component as user-confirmed (good design).
        
        Args:
            component_id: Component to confirm
            
        Returns:
            True if successful
        """
        try:
            if component_id in self.vector_db.memories:
                self.vector_db.memories[component_id].confirmed = True
                logger.info(f"Confirmed component: {component_id}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error confirming component: {e}")
            return False
