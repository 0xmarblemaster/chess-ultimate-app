"""
Advanced RAG Strategies Module
Incorporating enhancements from Crawl4AI RAG system for chess domain

Features:
1. Contextual Embeddings - Enhanced chunk context during embedding
2. Hybrid Search - Vector + keyword search combination  
3. Reranking - Cross-encoder based result reordering
4. Agentic RAG - Specialized chess content extraction and storage
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
import numpy as np
# from sentence_transformers import CrossEncoder  # Temporarily disabled due to Keras issue
import openai
from openai import OpenAI
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class AdvancedRAGConfig:
    """Configuration for advanced RAG strategies"""
    use_contextual_embeddings: bool = False
    use_hybrid_search: bool = True
    use_agentic_rag: bool = False
    use_reranking: bool = True
    
    # Model configurations
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    contextual_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    
    # Search configurations
    hybrid_alpha: float = 0.7  # Weight for vector search (0-1, 1 = pure vector)
    rerank_top_k: int = 20     # Results to rerank
    final_top_k: int = 10      # Final results to return
    
    # Contextual embeddings
    context_window: int = 1000  # Characters of context around chunk
    
    # Agentic RAG
    enable_chess_pattern_extraction: bool = True
    min_pattern_length: int = 100  # Minimum length for chess pattern extraction


class ContextualEmbeddingGenerator:
    """Generates enhanced embeddings with document context"""
    
    def __init__(self, config: AdvancedRAGConfig, openai_client: OpenAI):
        self.config = config
        self.openai_client = openai_client
        
    def generate_contextual_embedding(self, 
                                    chunk: str, 
                                    document_context: str,
                                    chunk_metadata: Dict[str, Any] = None) -> List[float]:
        """
        Generate enhanced embedding with document context
        
        Args:
            chunk: Original chunk text
            document_context: Full document or surrounding context
            chunk_metadata: Additional metadata about the chunk
            
        Returns:
            Enhanced embedding vector
        """
        try:
            if not self.config.use_contextual_embeddings:
                # Standard embedding without context
                response = self.openai_client.embeddings.create(
                    model=self.config.embedding_model,
                    input=chunk
                )
                return response.data[0].embedding
            
            # Generate contextual enhancement
            context_prompt = self._create_context_prompt(chunk, document_context, chunk_metadata)
            
            # Get enhanced context from LLM
            enhanced_context = self._get_enhanced_context(context_prompt)
            
            # Combine original chunk with enhanced context
            enriched_text = f"{chunk}\n\nContext: {enhanced_context}"
            
            # Generate embedding for enriched text
            response = self.openai_client.embeddings.create(
                model=self.config.embedding_model,
                input=enriched_text
            )
            
            logger.info(f"Generated contextual embedding for chunk of {len(chunk)} characters")
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Contextual embedding generation failed: {e}")
            # Fallback to standard embedding
            response = self.openai_client.embeddings.create(
                model=self.config.embedding_model,
                input=chunk
            )
            return response.data[0].embedding
    
    def _create_context_prompt(self, chunk: str, document_context: str, metadata: Dict = None) -> str:
        """Create prompt for contextual enhancement"""
        
        # Extract relevant context window around chunk
        context_snippet = self._extract_context_window(chunk, document_context)
        
        prompt = f"""
You are analyzing a chess educational content chunk. Provide enhanced context that captures:
1. The chess concepts being discussed
2. The skill level/audience
3. Related chess patterns or positions
4. Strategic or tactical themes

Original chunk:
{chunk}

Document context:
{context_snippet}

Provide a concise enhanced context summary (max 200 words) that enriches the semantic meaning:
"""
        
        if metadata:
            prompt += f"\nMetadata: {metadata}"
        
        return prompt
    
    def _extract_context_window(self, chunk: str, document: str) -> str:
        """Extract context window around chunk in document"""
        try:
            chunk_position = document.find(chunk)
            if chunk_position == -1:
                # Chunk not found in document, return beginning of document
                return document[:self.config.context_window]
            
            # Extract context before and after chunk
            start = max(0, chunk_position - self.config.context_window // 2)
            end = min(len(document), chunk_position + len(chunk) + self.config.context_window // 2)
            
            return document[start:end]
            
        except Exception as e:
            logger.error(f"Context window extraction failed: {e}")
            return document[:self.config.context_window]
    
    def _get_enhanced_context(self, prompt: str) -> str:
        """Get enhanced context from LLM"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.contextual_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM context enhancement failed: {e}")
            return ""


class HybridSearchEngine:
    """Combines vector search with keyword search"""
    
    def __init__(self, config: AdvancedRAGConfig, weaviate_client):
        self.config = config
        self.weaviate_client = weaviate_client
        
    def hybrid_search(self, 
                     query: str, 
                     collection_name: str = "ChessGame",
                     limit: int = 20,
                     vector_weight: float = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and keyword search
        
        Args:
            query: Search query
            collection_name: Weaviate collection to search
            limit: Number of results to return
            vector_weight: Weight for vector search (overrides config)
            
        Returns:
            Combined search results with enhanced scoring
        """
        
        alpha = vector_weight if vector_weight is not None else self.config.hybrid_alpha
        
        try:
            collection = self.weaviate_client.collections.get(collection_name)
            
            # Perform hybrid search using Weaviate's built-in hybrid search
            results = collection.query.hybrid(
                query=query,
                alpha=alpha,  # 0 = pure keyword, 1 = pure vector
                limit=limit,
                return_metadata=['score', 'distance']
            )
            
            hybrid_results = []
            for i, obj in enumerate(results.objects):
                result = {
                    'document_id': str(obj.uuid),
                    'content': self._extract_content_from_object(obj),
                    'hybrid_score': obj.metadata.score if obj.metadata else 0.5,
                    'vector_distance': obj.metadata.distance if obj.metadata else 1.0,
                    'rank': i + 1,
                    'search_type': 'hybrid',
                    'properties': obj.properties
                }
                hybrid_results.append(result)
            
            logger.info(f"Hybrid search returned {len(hybrid_results)} results with alpha={alpha}")
            return hybrid_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            # Fallback to vector search only
            return self._fallback_vector_search(query, collection_name, limit)
    
    def _extract_content_from_object(self, obj) -> str:
        """Extract searchable content from Weaviate object"""
        props = obj.properties
        
        # For chess games, create descriptive content
        content_parts = []
        
        if props.get('white_player') and props.get('black_player'):
            content_parts.append(f"Game: {props['white_player']} vs {props['black_player']}")
        
        if props.get('opening_name'):
            content_parts.append(f"Opening: {props['opening_name']}")
        
        if props.get('event'):
            content_parts.append(f"Event: {props['event']}")
        
        if props.get('pgn_moves'):
            # Include first few moves for content
            moves = props['pgn_moves'][:200] + "..." if len(props.get('pgn_moves', '')) > 200 else props.get('pgn_moves', '')
            content_parts.append(f"Moves: {moves}")
        
        return " | ".join(content_parts) if content_parts else str(props)
    
    def _fallback_vector_search(self, query: str, collection_name: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback to pure vector search"""
        try:
            collection = self.weaviate_client.collections.get(collection_name)
            
            results = collection.query.near_text(
                query=query,
                limit=limit,
                return_metadata=['distance']
            )
            
            vector_results = []
            for i, obj in enumerate(results.objects):
                result = {
                    'document_id': str(obj.uuid),
                    'content': self._extract_content_from_object(obj),
                    'hybrid_score': 1.0 - (obj.metadata.distance if obj.metadata else 0.5),
                    'vector_distance': obj.metadata.distance if obj.metadata else 1.0,
                    'rank': i + 1,
                    'search_type': 'vector_fallback',
                    'properties': obj.properties
                }
                vector_results.append(result)
            
            return vector_results
            
        except Exception as e:
            logger.error(f"Fallback vector search failed: {e}")
            return []


# Temporarily disabled due to Keras dependency issue
# class CrossEncoderReranker:
#     """Rerank documents using a cross-encoder model for more accurate scoring"""
#     
#     def __init__(self, config: AdvancedRAGConfig):
#         self.config = config
#         
#         # Initialize the cross-encoder model for reranking
#         logger.info(f"Loading CrossEncoder model: {self.config.rerank_model}")
#         self.model = CrossEncoder(self.config.rerank_model)


class ChessAgenticRAG:
    """Specialized chess pattern extraction and storage"""
    
    def __init__(self, config: AdvancedRAGConfig, openai_client: OpenAI, weaviate_client):
        self.config = config
        self.openai_client = openai_client
        self.weaviate_client = weaviate_client
        
    def extract_chess_patterns(self, document: str, document_metadata: Dict = None) -> List[Dict[str, Any]]:
        """
        Extract specialized chess patterns from documents
        
        Args:
            document: Full document text
            document_metadata: Document metadata
            
        Returns:
            List of extracted chess patterns with metadata
        """
        
        if not self.config.use_agentic_rag:
            return []
        
        try:
            patterns = []
            
            # 1. Extract tactical patterns
            tactical_patterns = self._extract_tactical_patterns(document)
            patterns.extend(tactical_patterns)
            
            # 2. Extract opening principles
            opening_patterns = self._extract_opening_patterns(document)
            patterns.extend(opening_patterns)
            
            # 3. Extract endgame techniques
            endgame_patterns = self._extract_endgame_patterns(document)
            patterns.extend(endgame_patterns)
            
            # 4. Extract strategic concepts
            strategic_patterns = self._extract_strategic_patterns(document)
            patterns.extend(strategic_patterns)
            
            # Generate summaries for each pattern
            for pattern in patterns:
                pattern['summary'] = self._generate_pattern_summary(pattern)
                pattern['embedding'] = self._generate_pattern_embedding(pattern)
            
            logger.info(f"Extracted {len(patterns)} chess patterns from document")
            return patterns
            
        except Exception as e:
            logger.error(f"Chess pattern extraction failed: {e}")
            return []
    
    def _extract_tactical_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract tactical patterns and combinations"""
        patterns = []
        
        # Common tactical keywords
        tactical_keywords = [
            'pin', 'fork', 'skewer', 'discovery', 'deflection', 'decoy',
            'sacrifice', 'combination', 'tactic', 'attack', 'puzzle'
        ]
        
        # Find paragraphs containing tactical content
        paragraphs = text.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) < self.config.min_pattern_length:
                continue
                
            # Check for tactical keywords
            keyword_count = sum(1 for keyword in tactical_keywords if keyword.lower() in paragraph.lower())
            
            if keyword_count >= 2:  # At least 2 tactical keywords
                patterns.append({
                    'type': 'tactical_pattern',
                    'content': paragraph.strip(),
                    'keywords': [kw for kw in tactical_keywords if kw.lower() in paragraph.lower()],
                    'position': i,
                    'confidence': min(keyword_count / 5.0, 1.0)  # Normalize confidence
                })
        
        return patterns
    
    def _extract_opening_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract opening principles and variations"""
        patterns = []
        
        opening_keywords = [
            'opening', 'development', 'castle', 'center', 'tempo', 'initiative',
            'principle', 'variation', 'gambit', 'defense', 'system'
        ]
        
        paragraphs = text.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) < self.config.min_pattern_length:
                continue
                
            keyword_count = sum(1 for keyword in opening_keywords if keyword.lower() in paragraph.lower())
            
            if keyword_count >= 2:
                patterns.append({
                    'type': 'opening_pattern',
                    'content': paragraph.strip(),
                    'keywords': [kw for kw in opening_keywords if kw.lower() in paragraph.lower()],
                    'position': i,
                    'confidence': min(keyword_count / 5.0, 1.0)
                })
        
        return patterns
    
    def _extract_endgame_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract endgame techniques and principles"""
        patterns = []
        
        endgame_keywords = [
            'endgame', 'ending', 'technique', 'conversion', 'opposition',
            'promotion', 'king', 'pawn', 'piece', 'activity', 'calculation'
        ]
        
        paragraphs = text.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) < self.config.min_pattern_length:
                continue
                
            keyword_count = sum(1 for keyword in endgame_keywords if keyword.lower() in paragraph.lower())
            
            if keyword_count >= 2:
                patterns.append({
                    'type': 'endgame_pattern',
                    'content': paragraph.strip(),
                    'keywords': [kw for kw in endgame_keywords if kw.lower() in paragraph.lower()],
                    'position': i,
                    'confidence': min(keyword_count / 5.0, 1.0)
                })
        
        return patterns
    
    def _extract_strategic_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract strategic concepts and planning"""
        patterns = []
        
        strategic_keywords = [
            'strategy', 'plan', 'positional', 'structure', 'weakness',
            'strength', 'evaluation', 'assessment', 'advantage', 'compensation'
        ]
        
        paragraphs = text.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) < self.config.min_pattern_length:
                continue
                
            keyword_count = sum(1 for keyword in strategic_keywords if keyword.lower() in paragraph.lower())
            
            if keyword_count >= 2:
                patterns.append({
                    'type': 'strategic_pattern',
                    'content': paragraph.strip(),
                    'keywords': [kw for kw in strategic_keywords if kw.lower() in paragraph.lower()],
                    'position': i,
                    'confidence': min(keyword_count / 5.0, 1.0)
                })
        
        return patterns
    
    def _generate_pattern_summary(self, pattern: Dict[str, Any]) -> str:
        """Generate AI summary for chess pattern"""
        try:
            prompt = f"""
Summarize this chess {pattern['type'].replace('_', ' ')} in 2-3 sentences. Focus on the key concepts and practical application:

{pattern['content']}

Summary:"""
            
            response = self.openai_client.chat.completions.create(
                model=self.config.contextual_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Pattern summary generation failed: {e}")
            return f"Chess {pattern['type'].replace('_', ' ')} focusing on: {', '.join(pattern['keywords'][:3])}"
    
    def _generate_pattern_embedding(self, pattern: Dict[str, Any]) -> List[float]:
        """Generate embedding for chess pattern"""
        try:
            # Combine content and summary for embedding
            embedding_text = f"{pattern['content']}\n\nSummary: {pattern['summary']}"
            
            response = self.openai_client.embeddings.create(
                model=self.config.embedding_model,
                input=embedding_text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Pattern embedding generation failed: {e}")
            return []


class AdvancedRAGOrchestrator:
    """Main orchestrator for advanced RAG strategies"""
    
    def __init__(self, config: AdvancedRAGConfig, openai_client: OpenAI, weaviate_client):
        self.config = config
        self.openai_client = openai_client
        self.weaviate_client = weaviate_client
        
        # Initialize components
        self.contextual_embedder = ContextualEmbeddingGenerator(config, openai_client)
        self.hybrid_searcher = HybridSearchEngine(config, weaviate_client)
        self.reranker = None  # Disabled temporarily
        self.agentic_rag = ChessAgenticRAG(config, openai_client, weaviate_client)
        
        logger.info("Advanced RAG Orchestrator initialized with strategies: " + 
                   f"Contextual={config.use_contextual_embeddings}, " +
                   f"Hybrid={config.use_hybrid_search}, " +
                   f"Agentic={config.use_agentic_rag}, " +
                   f"Reranking={config.use_reranking}")
    
    def enhanced_search(self, 
                       query: str, 
                       collection_name: str = "ChessGame",
                       limit: int = 10,
                       context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Perform enhanced search using all configured strategies
        
        Args:
            query: Search query
            collection_name: Weaviate collection to search
            limit: Final number of results to return
            context: Additional context for search optimization
            
        Returns:
            Enhanced search results
        """
        
        try:
            # Step 1: Hybrid Search (if enabled)
            if self.config.use_hybrid_search:
                search_results = self.hybrid_searcher.hybrid_search(
                    query=query,
                    collection_name=collection_name,
                    limit=self.config.rerank_top_k
                )
                logger.info(f"Hybrid search returned {len(search_results)} results")
            else:
                # Fallback to standard vector search
                search_results = self.hybrid_searcher._fallback_vector_search(
                    query, collection_name, self.config.rerank_top_k
                )
                logger.info(f"Vector search returned {len(search_results)} results")
            
            # Step 2: Reranking (if enabled)
            if self.config.use_reranking and search_results:
                reranked_results = self.reranker.rerank_results(
                    query=query,
                    results=search_results,
                    top_k=limit
                )
                logger.info(f"Reranking returned top {len(reranked_results)} results")
                final_results = reranked_results
            else:
                final_results = search_results[:limit]
            
            # Add strategy metadata
            for result in final_results:
                result['advanced_rag_strategies'] = {
                    'contextual_embeddings': self.config.use_contextual_embeddings,
                    'hybrid_search': self.config.use_hybrid_search,
                    'reranking': self.config.use_reranking,
                    'agentic_rag': self.config.use_agentic_rag
                }
            
            return final_results
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            return []
    
    def process_document_for_storage(self, 
                                   document: str, 
                                   document_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process document for enhanced storage with all strategies
        
        Args:
            document: Document text
            document_metadata: Document metadata
            
        Returns:
            Processed document data with enhancements
        """
        
        processed_data = {
            'original_document': document,
            'metadata': document_metadata or {},
            'enhancements': {}
        }
        
        try:
            # Extract chess patterns (if agentic RAG enabled)
            if self.config.use_agentic_rag:
                patterns = self.agentic_rag.extract_chess_patterns(document, document_metadata)
                processed_data['enhancements']['chess_patterns'] = patterns
                logger.info(f"Extracted {len(patterns)} chess patterns")
            
            # TODO: Add contextual embedding generation for chunks when document is chunked
            # This would be called during the chunking process with document context
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return processed_data 