"""Vector-based semantic caching system for code analysis results."""

import hashlib
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import openai
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings
from app.utils.redis_client import redis_client, get_cache_key
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Represents a semantic cache entry."""
    content_hash: str
    content_type: str  # function, class, file, project
    embedding_vector: List[float]
    analysis_results: Dict[str, Any]
    language: str
    similarity_threshold: float
    created_at: datetime
    usage_count: int = 1
    last_used_at: Optional[datetime] = None


class VectorCache:
    """Semantic caching system using vector embeddings for code analysis."""
    
    def __init__(self):
        """Initialize the vector cache system."""
        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.embedding_model = settings.embedding_model
        self.vector_dimension = settings.vector_dimension
        self.similarity_threshold = settings.similarity_threshold
        self.logger = get_logger(__name__)
        
        if not self.openai_client:
            self.logger.warning("OpenAI API key not provided, vector caching disabled")
    
    def _generate_content_hash(self, content: str, analysis_type: str) -> str:
        """Generate a hash for the content and analysis type."""
        combined = f"{content}:{analysis_type}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text using OpenAI API."""
        if not self.openai_client:
            return None
        
        try:
            # Truncate text if too long (max ~8000 tokens for text-embedding-3-small)
            if len(text) > 30000:  # Rough character limit
                text = text[:30000] + "..."
            
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def _extract_code_chunks(self, content: str, language: str) -> List[Tuple[str, str]]:
        """
        Extract meaningful code chunks for caching.
        Returns list of (chunk_type, chunk_content) tuples.
        """
        chunks = []
        
        # Simple heuristic-based extraction
        # This could be enhanced with proper AST parsing
        
        lines = content.split('\n')
        current_function = []
        current_class = []
        in_function = False
        in_class = False
        
        for line in lines:
            stripped = line.strip()
            
            # Language-specific patterns
            if language == 'python':
                if stripped.startswith('def '):
                    if current_function:
                        chunks.append(('function', '\n'.join(current_function)))
                    current_function = [line]
                    in_function = True
                elif stripped.startswith('class '):
                    if current_class:
                        chunks.append(('class', '\n'.join(current_class)))
                    current_class = [line]
                    in_class = True
                elif in_function and (not line.startswith(' ') and not line.startswith('\t') and stripped):
                    chunks.append(('function', '\n'.join(current_function)))
                    current_function = []
                    in_function = False
                elif in_class and (not line.startswith(' ') and not line.startswith('\t') and stripped):
                    chunks.append(('class', '\n'.join(current_class)))
                    current_class = []
                    in_class = False
                elif in_function:
                    current_function.append(line)
                elif in_class:
                    current_class.append(line)
            
            elif language in ['javascript', 'typescript']:
                if 'function ' in stripped or '=>' in stripped:
                    if current_function:
                        chunks.append(('function', '\n'.join(current_function)))
                    current_function = [line]
                    in_function = True
                elif stripped.startswith('class '):
                    if current_class:
                        chunks.append(('class', '\n'.join(current_class)))
                    current_class = [line]
                    in_class = True
                elif in_function and stripped == '}':
                    current_function.append(line)
                    chunks.append(('function', '\n'.join(current_function)))
                    current_function = []
                    in_function = False
                elif in_function:
                    current_function.append(line)
        
        # Add remaining chunks
        if current_function:
            chunks.append(('function', '\n'.join(current_function)))
        if current_class:
            chunks.append(('class', '\n'.join(current_class)))
        
        # If no chunks found, use entire file
        if not chunks:
            chunks.append(('file', content))
        
        return chunks
    
    async def find_similar_analysis(
        self,
        content: str,
        analysis_type: str,
        language: str,
        similarity_threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find similar cached analysis results using vector similarity.
        
        Args:
            content: Code content to analyze
            analysis_type: Type of analysis (style, bug, security, performance)
            language: Programming language
            similarity_threshold: Override default similarity threshold
            
        Returns:
            Cached analysis results if similar content found, None otherwise
        """
        if not self.openai_client:
            return None
        
        threshold = similarity_threshold or self.similarity_threshold
        
        try:
            # Generate embedding for input content
            embedding = await self._get_embedding(content)
            if not embedding:
                return None
            
            # Search for similar cached entries
            cache_pattern = get_cache_key("vector", analysis_type, language, "*")
            cached_keys = redis_client.keys(cache_pattern)
            
            best_match = None
            best_similarity = 0.0
            
            for key in cached_keys:
                try:
                    cached_data = redis_client.get_json(key)
                    if not cached_data:
                        continue
                    
                    cached_embedding = cached_data.get('embedding_vector', [])
                    if not cached_embedding:
                        continue
                    
                    # Calculate cosine similarity
                    similarity = cosine_similarity([embedding], [cached_embedding])[0][0]
                    
                    if similarity > threshold and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = cached_data
                        
                except Exception as e:
                    self.logger.warning(f"Failed to process cached entry {key}: {e}")
                    continue
            
            if best_match:
                # Update usage statistics
                best_match['usage_count'] = best_match.get('usage_count', 0) + 1
                best_match['last_used_at'] = datetime.utcnow().isoformat()
                
                # Update cache entry
                content_hash = best_match.get('content_hash', '')
                cache_key = get_cache_key("vector", analysis_type, language, content_hash)
                redis_client.set_json(cache_key, best_match, ex=86400 * 7)  # 7 days TTL
                
                self.logger.info(f"Cache hit for {analysis_type} analysis (similarity: {best_similarity:.3f})")
                return best_match.get('analysis_results')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find similar analysis: {e}")
            return None
    
    async def cache_analysis_result(
        self,
        content: str,
        analysis_type: str,
        language: str,
        analysis_results: Dict[str, Any],
        content_type: str = "file"
    ) -> bool:
        """
        Cache analysis results with vector embedding.
        
        Args:
            content: Code content that was analyzed
            analysis_type: Type of analysis performed
            language: Programming language
            analysis_results: Results to cache
            content_type: Type of content (file, function, class)
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self.openai_client:
            return False
        
        try:
            # Generate content hash and embedding
            content_hash = self._generate_content_hash(content, analysis_type)
            embedding = await self._get_embedding(content)
            
            if not embedding:
                return False
            
            # Create cache entry
            cache_entry = {
                'content_hash': content_hash,
                'content_type': content_type,
                'embedding_vector': embedding,
                'analysis_results': analysis_results,
                'language': language,
                'similarity_threshold': self.similarity_threshold,
                'created_at': datetime.utcnow().isoformat(),
                'usage_count': 1,
                'last_used_at': datetime.utcnow().isoformat()
            }
            
            # Store in Redis with 7-day TTL
            cache_key = get_cache_key("vector", analysis_type, language, content_hash)
            success = redis_client.set_json(cache_key, cache_entry, ex=86400 * 7)
            
            if success:
                self.logger.info(f"Cached {analysis_type} analysis for {language} {content_type}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to cache analysis result: {e}")
            return False
    
    async def cache_file_analysis(
        self,
        file_path: str,
        content: str,
        language: str,
        analysis_results: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Cache analysis results for a file with chunk-level caching.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.openai_client:
            return {'cached_chunks': 0, 'total_chunks': 0}
        
        try:
            # Extract code chunks
            chunks = self._extract_code_chunks(content, language)
            
            cached_count = 0
            
            # Cache each analysis type result for each chunk
            for analysis_type, type_results in analysis_results.items():
                if analysis_type in ['style', 'bug', 'security', 'performance']:
                    # Cache entire file analysis
                    if await self.cache_analysis_result(
                        content, analysis_type, language, type_results, "file"
                    ):
                        cached_count += 1
                    
                    # Cache individual chunks
                    for chunk_type, chunk_content in chunks:
                        if len(chunk_content.strip()) > 50:  # Only cache substantial chunks
                            if await self.cache_analysis_result(
                                chunk_content, analysis_type, language, 
                                type_results, chunk_type
                            ):
                                cached_count += 1
            
            return {
                'cached_chunks': cached_count,
                'total_chunks': len(chunks) * len(analysis_results)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cache file analysis for {file_path}: {e}")
            return {'cached_chunks': 0, 'total_chunks': 0}
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache usage statistics."""
        try:
            # Get all vector cache keys
            all_keys = redis_client.keys(get_cache_key("vector", "*"))
            
            if not all_keys:
                return {
                    'total_entries': 0,
                    'cache_size': '0 MB',
                    'hit_rate': '0%',
                    'languages': {},
                    'analysis_types': {}
                }
            
            total_entries = len(all_keys)
            total_usage = 0
            languages = {}
            analysis_types = {}
            
            # Sample entries for statistics
            sample_size = min(100, len(all_keys))
            sample_keys = all_keys[:sample_size]
            
            for key in sample_keys:
                try:
                    entry = redis_client.get_json(key)
                    if entry:
                        usage_count = entry.get('usage_count', 0)
                        total_usage += usage_count
                        
                        language = entry.get('language', 'unknown')
                        languages[language] = languages.get(language, 0) + 1
                        
                        # Extract analysis type from key
                        key_parts = key.split(':')
                        if len(key_parts) >= 3:
                            analysis_type = key_parts[2]
                            analysis_types[analysis_type] = analysis_types.get(analysis_type, 0) + 1
                            
                except Exception:
                    continue
            
            # Estimate cache hit rate
            avg_usage = total_usage / sample_size if sample_size > 0 else 0
            hit_rate = max(0, (avg_usage - 1) / avg_usage * 100) if avg_usage > 1 else 0
            
            return {
                'total_entries': total_entries,
                'cache_size': f"{total_entries * 50 / 1024:.2f} MB",  # Rough estimate
                'hit_rate': f"{hit_rate:.1f}%",
                'average_usage': f"{avg_usage:.1f}",
                'languages': languages,
                'analysis_types': analysis_types,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cache statistics: {e}")
            return {'error': str(e)}
    
    def cleanup_old_entries(self, days_old: int = 30) -> int:
        """Remove cache entries older than specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            all_keys = redis_client.keys(get_cache_key("vector", "*"))
            
            removed_count = 0
            
            for key in all_keys:
                try:
                    entry = redis_client.get_json(key)
                    if entry:
                        created_at = datetime.fromisoformat(entry.get('created_at', ''))
                        if created_at < cutoff_date:
                            redis_client.delete(key)
                            removed_count += 1
                except Exception:
                    continue
            
            self.logger.info(f"Cleaned up {removed_count} old cache entries")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old entries: {e}")
            return 0


# Global vector cache instance
vector_cache = VectorCache()