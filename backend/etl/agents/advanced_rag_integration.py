"""
Advanced RAG Integration Module
Integrates Crawl4AI-inspired RAG strategies with existing chess RAG system

This module bridges the new advanced RAG strategies with your existing
enhanced retriever and context management system.
"""

import logging
import os
from typing import Dict, List, Optional, Any
from openai import OpenAI

try:
    from ...services.advanced_rag_strategies import (
        AdvancedRAGConfig, 
        AdvancedRAGOrchestrator,
        ContextualEmbeddingGenerator,
        HybridSearchEngine,
        # CrossEncoderReranker,  # Temporarily disabled due to Keras issue
        ChessAgenticRAG
    )
except ImportError:
    from backend.services.advanced_rag_strategies import (
        AdvancedRAGConfig, 
        AdvancedRAGOrchestrator,
        ContextualEmbeddingGenerator,
        HybridSearchEngine,
        # CrossEncoderReranker,  # Temporarily disabled due to Keras issue
        ChessAgenticRAG
    )

try:
    from .enhanced_retriever import EnhancedRetriever, RetrievalResult
    from .context_manager import ChessContext, extract_chess_context
except ImportError:
    from enhanced_retriever import EnhancedRetriever, RetrievalResult
    from context_manager import ChessContext, extract_chess_context

logger = logging.getLogger(__name__)


class AdvancedRAGRetriever:
    """
    Enhanced retriever that integrates Crawl4AI-inspired strategies
    with the existing chess RAG system
    """
    
    def __init__(self, weaviate_client, base_retriever, openai_client: OpenAI = None):
        """
        Initialize the advanced RAG retriever
        
        Args:
            weaviate_client: Weaviate client instance
            base_retriever: Existing base retriever for fallback
            openai_client: OpenAI client for advanced features
        """
        self.weaviate_client = weaviate_client
        self.base_retriever = base_retriever
        
        # Initialize OpenAI client if not provided
        if openai_client is None:
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        else:
            self.openai_client = openai_client
        
        # Load configuration from environment
        self.config = self._load_config_from_env()
        
        # Initialize advanced RAG orchestrator
        self.orchestrator = AdvancedRAGOrchestrator(
            config=self.config,
            openai_client=self.openai_client,
            weaviate_client=self.weaviate_client
        )
        
        # Initialize existing enhanced retriever for fallback
        self.enhanced_retriever = EnhancedRetriever(weaviate_client, base_retriever)
        
        logger.info(f"Advanced RAG Retriever initialized with strategies: "
                   f"Contextual={self.config.use_contextual_embeddings}, "
                   f"Hybrid={self.config.use_hybrid_search}, "
                   f"Agentic={self.config.use_agentic_rag}, "
                   f"Reranking={self.config.use_reranking}")
    
    def _load_config_from_env(self) -> AdvancedRAGConfig:
        """Load configuration from environment variables"""
        
        return AdvancedRAGConfig(
            # Strategy flags
            use_contextual_embeddings=os.getenv('USE_CONTEXTUAL_EMBEDDINGS', 'false').lower() == 'true',
            use_hybrid_search=os.getenv('USE_HYBRID_SEARCH', 'true').lower() == 'true',
            use_agentic_rag=os.getenv('USE_AGENTIC_RAG', 'false').lower() == 'true',
            use_reranking=os.getenv('USE_RERANKING', 'true').lower() == 'true',
            
            # Model configurations
            contextual_model=os.getenv('CONTEXTUAL_MODEL', 'gpt-4o-mini'),
            embedding_model=os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small'),
            rerank_model=os.getenv('RERANK_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2'),
            
            # Search configurations
            hybrid_alpha=float(os.getenv('HYBRID_ALPHA', '0.7')),
            rerank_top_k=int(os.getenv('RERANK_TOP_K', '20')),
            final_top_k=int(os.getenv('FINAL_TOP_K', '10')),
            
            # Contextual embeddings
            context_window=int(os.getenv('CONTEXT_WINDOW', '1000')),
            
            # Agentic RAG
            enable_chess_pattern_extraction=os.getenv('ENABLE_CHESS_PATTERN_EXTRACTION', 'true').lower() == 'true',
            min_pattern_length=int(os.getenv('MIN_PATTERN_LENGTH', '100'))
        )
    
    def retrieve_documents(self, 
                         query: str, 
                         context: ChessContext, 
                         limit: int = 10,
                         min_relevance: float = 0.3,
                         collection_name: str = "ChessGame") -> List[RetrievalResult]:
        """
        Enhanced document retrieval using advanced RAG strategies
        
        Args:
            query: User query text
            context: Chess context from context manager
            limit: Maximum number of documents to retrieve
            min_relevance: Minimum relevance score threshold
            collection_name: Weaviate collection to search
            
        Returns:
            List of enhanced retrieval results
        """
        
        try:
            # Determine if we should use advanced strategies or fallback
            use_advanced = any([
                self.config.use_contextual_embeddings,
                self.config.use_hybrid_search,
                self.config.use_agentic_rag,
                self.config.use_reranking
            ])
            
            if not use_advanced:
                logger.info("No advanced strategies enabled, using enhanced retriever")
                return self.enhanced_retriever.retrieve_documents(query, context, limit, min_relevance)
            
            # Convert chess context to additional context for advanced search
            search_context = self._chess_context_to_search_context(context)
            
            # Use advanced RAG orchestrator for search
            advanced_results = self.orchestrator.enhanced_search(
                query=query,
                collection_name=collection_name,
                limit=limit,
                context=search_context
            )
            
            # Convert advanced results to RetrievalResult format
            retrieval_results = []
            for result in advanced_results:
                retrieval_result = self._convert_to_retrieval_result(result, context)
                if retrieval_result.relevance_score >= min_relevance:
                    retrieval_results.append(retrieval_result)
            
            logger.info(f"Advanced RAG returned {len(retrieval_results)} results above threshold {min_relevance}")
            
            # If no results from advanced search, fallback to enhanced retriever
            if not retrieval_results:
                logger.info("Advanced RAG found no results, falling back to enhanced retriever")
                return self.enhanced_retriever.retrieve_documents(query, context, limit, min_relevance)
            
            return retrieval_results[:limit]
            
        except Exception as e:
            logger.error(f"Advanced RAG retrieval failed: {e}")
            # Fallback to enhanced retriever
            logger.info("Falling back to enhanced retriever")
            return self.enhanced_retriever.retrieve_documents(query, context, limit, min_relevance)
    
    def _chess_context_to_search_context(self, chess_context: ChessContext) -> Dict[str, Any]:
        """Convert ChessContext to search context for advanced RAG"""
        
        return {
            'intent_type': chess_context.intent_type,
            'query_complexity': chess_context.query_complexity,
            'requires_position_analysis': chess_context.requires_position_analysis,
            'tactical_patterns': chess_context.tactical_patterns,
            'current_fen': chess_context.current_fen,
            'position_type': chess_context.position_type,
            'confidence': chess_context.confidence
        }
    
    def _convert_to_retrieval_result(self, 
                                   advanced_result: Dict[str, Any], 
                                   context: ChessContext) -> RetrievalResult:
        """Convert advanced search result to RetrievalResult format"""
        
        # Extract scores from advanced result
        relevance_score = advanced_result.get('final_score', 
                         advanced_result.get('rerank_score', 
                         advanced_result.get('hybrid_score', 0.5)))
        
        # Calculate component scores
        context_relevance = self._calculate_context_relevance(advanced_result, context)
        position_relevance = self._calculate_position_relevance(advanced_result, context)
        tactical_relevance = self._calculate_tactical_relevance(advanced_result, context)
        
        # Determine document type
        document_type = self._determine_document_type(advanced_result)
        
        # Extract chess concepts
        chess_concepts = self._extract_chess_concepts_from_result(advanced_result)
        
        retrieval_result = RetrievalResult(
            document_id=advanced_result.get('document_id', ''),
            content=advanced_result.get('content', ''),
            relevance_score=float(relevance_score),
            context_relevance=context_relevance,
            position_relevance=position_relevance,
            tactical_relevance=tactical_relevance,
            document_type=document_type,
            chess_concepts=chess_concepts
        )
        
        # Store original advanced result data
        retrieval_result.advanced_result_data = advanced_result
        
        return retrieval_result
    
    def _calculate_context_relevance(self, result: Dict[str, Any], context: ChessContext) -> float:
        """Calculate context relevance score"""
        
        strategies = result.get('advanced_rag_strategies', {})
        
        # Base score from advanced strategies
        base_score = 0.5
        
        # Boost if reranking was used (indicates better relevance)
        if strategies.get('reranking'):
            base_score += 0.2
        
        # Boost if hybrid search was used (better content matching)
        if strategies.get('hybrid_search'):
            base_score += 0.1
        
        # Boost for intent alignment
        if context.intent_type and context.intent_type in result.get('content', '').lower():
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_position_relevance(self, result: Dict[str, Any], context: ChessContext) -> float:
        """Calculate position relevance score"""
        
        if not context.requires_position_analysis:
            return 0.0
        
        content = result.get('content', '').lower()
        score = 0.0
        
        # Check for position-related terms
        position_terms = ['position', 'fen', 'board', 'placement']
        for term in position_terms:
            if term in content:
                score += 0.2
        
        # Check for position type alignment
        if context.position_type and context.position_type in content:
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_tactical_relevance(self, result: Dict[str, Any], context: ChessContext) -> float:
        """Calculate tactical relevance score"""
        
        if not context.tactical_patterns:
            return 0.0
        
        content = result.get('content', '').lower()
        score = 0.0
        
        # Check for tactical pattern matches
        for pattern in context.tactical_patterns:
            if pattern.lower() in content:
                score += 0.3
        
        # General tactical terms
        tactical_terms = ['tactic', 'combination', 'attack', 'sacrifice']
        for term in tactical_terms:
            if term in content:
                score += 0.1
        
        return min(score, 1.0)
    
    def _determine_document_type(self, result: Dict[str, Any]) -> str:
        """Determine document type from advanced result"""
        
        # Check if it's a chess game result
        properties = result.get('properties', {})
        if properties.get('white_player') and properties.get('black_player'):
            return "game"
        
        # Check content for document type indicators
        content = result.get('content', '').lower()
        
        type_indicators = {
            'opening': ['opening', 'development', 'castle'],
            'tactics': ['tactic', 'combination', 'puzzle'],
            'strategy': ['strategy', 'plan', 'positional'],
            'endgame': ['endgame', 'ending', 'technique']
        }
        
        for doc_type, indicators in type_indicators.items():
            if any(indicator in content for indicator in indicators):
                return doc_type
        
        return "general"
    
    def _extract_chess_concepts_from_result(self, result: Dict[str, Any]) -> List[str]:
        """Extract chess concepts from advanced result"""
        
        content = result.get('content', '').lower()
        concepts = []
        
        # Common chess concepts
        chess_concepts = [
            'development', 'castle', 'center', 'tempo', 'initiative',
            'tactics', 'strategy', 'endgame', 'opening', 'middlegame',
            'attack', 'defense', 'sacrifice', 'combination', 'pin',
            'fork', 'skewer', 'discovery', 'deflection', 'pawn structure'
        ]
        
        for concept in chess_concepts:
            if concept in content:
                concepts.append(concept)
        
        return concepts[:5]  # Limit to top 5 concepts
    
    def process_document_for_storage(self, document: str, document_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process document for enhanced storage using advanced strategies
        
        Args:
            document: Document text to process
            document_metadata: Document metadata
            
        Returns:
            Processed document data with enhancements
        """
        
        try:
            # Use orchestrator to process document
            processed_data = self.orchestrator.process_document_for_storage(document, document_metadata)
            
            logger.info(f"Advanced RAG processed document with {len(processed_data.get('enhancements', {}))} enhancements")
            return processed_data
            
        except Exception as e:
            logger.error(f"Advanced document processing failed: {e}")
            return {
                'original_document': document,
                'metadata': document_metadata or {},
                'enhancements': {}
            }
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy configuration status"""
        
        return {
            'advanced_rag_enabled': True,
            'strategies': {
                'contextual_embeddings': self.config.use_contextual_embeddings,
                'hybrid_search': self.config.use_hybrid_search,
                'agentic_rag': self.config.use_agentic_rag,
                'reranking': self.config.use_reranking
            },
            'models': {
                'contextual_model': self.config.contextual_model,
                'embedding_model': self.config.embedding_model,
                'rerank_model': self.config.rerank_model
            },
            'configuration': {
                'hybrid_alpha': self.config.hybrid_alpha,
                'rerank_top_k': self.config.rerank_top_k,
                'final_top_k': self.config.final_top_k,
                'context_window': self.config.context_window,
                'min_pattern_length': self.config.min_pattern_length
            }
        }


def create_advanced_rag_retriever(weaviate_client, base_retriever, openai_client: OpenAI = None) -> AdvancedRAGRetriever:
    """
    Factory function to create an AdvancedRAGRetriever instance
    
    Args:
        weaviate_client: Weaviate client instance
        base_retriever: Base retriever for fallback
        openai_client: OpenAI client (optional)
        
    Returns:
        Configured AdvancedRAGRetriever instance
    """
    
    return AdvancedRAGRetriever(
        weaviate_client=weaviate_client,
        base_retriever=base_retriever,
        openai_client=openai_client
    ) 