"""
Enhanced Diagram Processor for Chess Educational Documents

This module provides sophisticated diagram-text association that works with
unordered diagram numbering by using spatial context, text proximity analysis,
and chess-specific pattern matching.

Key Features:
- Context-aware diagram-text association 
- Handles non-sequential diagram numbering
- Spatial analysis for diagram placement
- Semantic analysis of surrounding text
- Chess pattern recognition for better matching
"""

import re
import os
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class DiagramContext:
    """Contextual information about a diagram's location and surroundings"""
    diagram_number: int
    image_filename: str
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    preceding_text: str = ""
    following_text: str = ""
    nearby_text: str = ""
    extracted_position: int = 0  # Order in which diagram was extracted
    confidence_score: float = 0.0

@dataclass
class TaskContext:
    """Contextual information about a task or explanation"""
    content: str
    task_number: Optional[int] = None
    lesson_number: Optional[int] = None
    content_type: str = "task"  # task, explanation, etc.
    paragraph_index: Optional[int] = None
    contains_chess_terms: bool = False
    difficulty_indicators: List[str] = None

class EnhancedDiagramProcessor:
    """Enhanced processor for associating diagrams with text in unordered documents"""
    
    def __init__(self):
        # Chess-specific terms for semantic analysis
        self.chess_terms = {
            'russian': [
                'мат', 'шах', 'ход', 'фигура', 'пешка', 'ладья', 'слон', 'конь', 'ферзь', 'король',
                'позиция', 'партия', 'дебют', 'эндшпиль', 'миттельшпиль', 'тактика', 'стратегия',
                'диаграмма', 'доска', 'поле', 'белые', 'чёрные', 'нападение', 'защита'
            ],
            'english': [
                'mate', 'check', 'move', 'piece', 'pawn', 'rook', 'bishop', 'knight', 'queen', 'king',
                'position', 'game', 'opening', 'endgame', 'middlegame', 'tactics', 'strategy',
                'diagram', 'board', 'square', 'white', 'black', 'attack', 'defense'
            ]
        }
        
        # Patterns for different types of chess content
        self.task_patterns = {
            'mate_in_n': re.compile(r'мат\s+в\s+(\d+)\s+ход', re.IGNORECASE),
            'find_best_move': re.compile(r'найдите?\s+лучший\s+ход|лучший\s+ход|best\s+move', re.IGNORECASE),
            'white_to_move': re.compile(r'белые\s+начинают|ход\s+белых|white\s+to\s+move', re.IGNORECASE),
            'black_to_move': re.compile(r'чёрные\s+начинают|ход\s+чёрных|black\s+to\s+move', re.IGNORECASE),
            'evaluate': re.compile(r'оценит|оценка|evaluate|assessment', re.IGNORECASE)
        }
        
        # Common diagram reference patterns
        self.diagram_ref_patterns = [
            re.compile(r'диаграмм[аеы]\s*№?\s*(\d+)', re.IGNORECASE),
            re.compile(r'diagram\s*#?\s*(\d+)', re.IGNORECASE),
            re.compile(r'см\.\s*диаграмм[ау]\s*(\d+)', re.IGNORECASE),
            re.compile(r'see\s+diagram\s+(\d+)', re.IGNORECASE),
            re.compile(r'позиция\s*(\d+)', re.IGNORECASE),
            re.compile(r'position\s*(\d+)', re.IGNORECASE)
        ]
    
    def extract_diagram_contexts(self, extracted_data: Dict[str, Any], images_info: List[Dict[str, Any]]) -> List[DiagramContext]:
        """
        Extract contextual information for all diagrams in the document
        
        Args:
            extracted_data: Document data with lessons and content
            images_info: Information about extracted images
            
        Returns:
            List of DiagramContext objects with detailed context information
        """
        diagram_contexts = []
        
        for img_info in images_info:
            img_filename = img_info.get('filename', '')
            page_num = img_info.get('page_number')
            
            # Extract diagram number from filename with multiple strategies
            diagram_number = self._extract_diagram_number(img_filename)
            if diagram_number is None:
                logger.warning(f"Could not extract diagram number from {img_filename}")
                continue
            
            # Extract contextual text around the diagram
            context = self._extract_spatial_context(extracted_data, img_info, diagram_number)
            
            diagram_context = DiagramContext(
                diagram_number=diagram_number,
                image_filename=img_filename,
                page_number=page_num,
                preceding_text=context.get('preceding', ''),
                following_text=context.get('following', ''),
                nearby_text=context.get('nearby', ''),
                extracted_position=len(diagram_contexts)
            )
            
            diagram_contexts.append(diagram_context)
        
        return diagram_contexts
    
    def extract_task_contexts(self, extracted_data: Dict[str, Any]) -> List[TaskContext]:
        """
        Extract contextual information for all tasks and explanations
        
        Args:
            extracted_data: Document data with lessons and content
            
        Returns:
            List of TaskContext objects
        """
        task_contexts = []
        
        for lesson in extracted_data.get('lessons', []):
            lesson_number = lesson.get('lesson_number')
            
            for idx, content_item in enumerate(lesson.get('content', [])):
                content_text = content_item.get('text', '')
                content_type = content_item.get('type', 'explanation')
                
                # Extract task number if present
                task_number = self._extract_task_number(content_text)
                
                # Analyze chess content
                contains_chess = self._contains_chess_terms(content_text)
                difficulty_indicators = self._extract_difficulty_indicators(content_text)
                
                task_context = TaskContext(
                    content=content_text,
                    task_number=task_number,
                    lesson_number=lesson_number,
                    content_type=content_type,
                    paragraph_index=idx,
                    contains_chess_terms=contains_chess,
                    difficulty_indicators=difficulty_indicators
                )
                
                task_contexts.append(task_context)
        
        return task_contexts
    
    def associate_diagrams_with_tasks(self, diagram_contexts: List[DiagramContext], 
                                    task_contexts: List[TaskContext]) -> Dict[str, Dict[str, Any]]:
        """
        Use multiple strategies to associate diagrams with their corresponding tasks
        
        Args:
            diagram_contexts: List of diagram contexts
            task_contexts: List of task contexts
            
        Returns:
            Dictionary mapping image filenames to associated task information
        """
        associations = {}
        used_tasks = set()  # Track which tasks have been used
        
        for diagram_ctx in diagram_contexts:
            # Strategy 1: Direct number matching with confidence scoring
            best_match = self._find_best_match_by_number(diagram_ctx, task_contexts, used_tasks)
            
            if best_match and best_match['confidence'] > 0.8:
                associations[diagram_ctx.image_filename] = best_match
                used_tasks.add(id(best_match['task_context']))
                logger.info(f"High confidence match for {diagram_ctx.image_filename}: task {best_match['task_context'].task_number}")
                continue
            
            # Strategy 2: Semantic similarity analysis
            semantic_match = self._find_semantic_match(diagram_ctx, task_contexts, used_tasks)
            
            if semantic_match and semantic_match['confidence'] > 0.6:
                associations[diagram_ctx.image_filename] = semantic_match
                used_tasks.add(id(semantic_match['task_context']))
                logger.info(f"Semantic match for {diagram_ctx.image_filename}: confidence {semantic_match['confidence']:.2f}")
                continue
            
            # Strategy 3: Proximity and context analysis
            proximity_match = self._find_proximity_match(diagram_ctx, task_contexts, used_tasks)
            
            if proximity_match:
                associations[diagram_ctx.image_filename] = proximity_match
                used_tasks.add(id(proximity_match['task_context']))
                logger.info(f"Proximity match for {diagram_ctx.image_filename}")
                continue
            
            # Strategy 4: Fallback to best available task
            fallback_match = self._find_fallback_match(diagram_ctx, task_contexts, used_tasks)
            if fallback_match:
                associations[diagram_ctx.image_filename] = fallback_match
                used_tasks.add(id(fallback_match['task_context']))
                logger.warning(f"Fallback match for {diagram_ctx.image_filename}")
        
        return associations
    
    def _extract_diagram_number(self, filename: str) -> Optional[int]:
        """Extract diagram number from filename using multiple patterns"""
        # Pattern 1: Standard diagram_N format
        patterns = [
            re.compile(r'diagram[_]?(\d+)', re.IGNORECASE),
            re.compile(r'img[_]?(\d+)', re.IGNORECASE),
            re.compile(r'fig[ure]*[_]?(\d+)', re.IGNORECASE),
            re.compile(r'диаграмма[_]?(\d+)', re.IGNORECASE),
            re.compile(r'(\d+)\.(?:png|jpg|jpeg|gif|bmp)', re.IGNORECASE),
            re.compile(r'[_](\d+)[_]', re.IGNORECASE),
            re.compile(r'(\d+)', re.IGNORECASE)  # Any number as fallback
        ]
        
        for pattern in patterns:
            match = pattern.search(filename)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_spatial_context(self, extracted_data: Dict[str, Any], 
                                img_info: Dict[str, Any], diagram_number: int) -> Dict[str, str]:
        """Extract text that appears spatially near the diagram"""
        context = {'preceding': '', 'following': '', 'nearby': ''}
        
        # This is a simplified version - in a real implementation, you'd use
        # document structure information to find text near the diagram
        page_number = img_info.get('page_number', 0)
        
        # Collect text from the same lesson/section
        all_text_items = []
        for lesson in extracted_data.get('lessons', []):
            for content_item in lesson.get('content', []):
                text = content_item.get('text', '')
                if text.strip():
                    all_text_items.append(text)
        
        # Look for references to this diagram number in the text
        for text in all_text_items:
            for pattern in self.diagram_ref_patterns:
                if pattern.search(text):
                    ref_match = pattern.search(text)
                    if ref_match and int(ref_match.group(1)) == diagram_number:
                        context['nearby'] += f" {text}"
        
        return context
    
    def _extract_task_number(self, text: str) -> Optional[int]:
        """Extract task number from text content"""
        # Pattern for numbered tasks: "42. ", "42)", "42 ___", etc.
        patterns = [
            re.compile(r'^(\d+)\.', re.MULTILINE),
            re.compile(r'^(\d+)\)', re.MULTILINE),
            re.compile(r'^(\d+)\s+[_\-]{3,}', re.MULTILINE),
            re.compile(r'задача\s*№?\s*(\d+)', re.IGNORECASE),
            re.compile(r'task\s*#?\s*(\d+)', re.IGNORECASE)
        ]
        
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _contains_chess_terms(self, text: str, language: str = 'russian') -> bool:
        """Check if text contains chess-specific terminology"""
        text_lower = text.lower()
        chess_terms = self.chess_terms.get(language, [])
        
        return any(term in text_lower for term in chess_terms)
    
    def _extract_difficulty_indicators(self, text: str) -> List[str]:
        """Extract difficulty indicators from text"""
        indicators = []
        
        for pattern_name, pattern in self.task_patterns.items():
            if pattern.search(text):
                indicators.append(pattern_name)
        
        return indicators
    
    def _find_best_match_by_number(self, diagram_ctx: DiagramContext, 
                                  task_contexts: List[TaskContext], 
                                  used_tasks: Set) -> Optional[Dict[str, Any]]:
        """Find best matching task based on number similarity"""
        best_match = None
        best_confidence = 0.0
        
        for task_ctx in task_contexts:
            if id(task_ctx) in used_tasks:
                continue
            
            if task_ctx.task_number is None:
                continue
            
            # Exact number match
            if task_ctx.task_number == diagram_ctx.diagram_number:
                return {
                    'task_context': task_ctx,
                    'confidence': 1.0,
                    'match_type': 'exact_number'
                }
            
            # Close number match (within reasonable range)
            number_diff = abs(task_ctx.task_number - diagram_ctx.diagram_number)
            if number_diff <= 5:  # Configurable tolerance
                confidence = max(0.5, 1.0 - (number_diff * 0.1))
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        'task_context': task_ctx,
                        'confidence': confidence,
                        'match_type': 'close_number'
                    }
        
        return best_match
    
    def _find_semantic_match(self, diagram_ctx: DiagramContext, 
                           task_contexts: List[TaskContext], 
                           used_tasks: Set) -> Optional[Dict[str, Any]]:
        """Find matching task based on semantic similarity"""
        # Look for explicit references to the diagram number in task text
        for task_ctx in task_contexts:
            if id(task_ctx) in used_tasks:
                continue
            
            # Check if task text references this diagram number
            for pattern in self.diagram_ref_patterns:
                match = pattern.search(task_ctx.content)
                if match:
                    try:
                        referenced_num = int(match.group(1))
                        if referenced_num == diagram_ctx.diagram_number:
                            return {
                                'task_context': task_ctx,
                                'confidence': 0.9,
                                'match_type': 'explicit_reference'
                            }
                    except (ValueError, IndexError):
                        continue
        
        return None
    
    def _find_proximity_match(self, diagram_ctx: DiagramContext, 
                            task_contexts: List[TaskContext], 
                            used_tasks: Set) -> Optional[Dict[str, Any]]:
        """Find matching task based on proximity and context"""
        # Simplified proximity matching - look for tasks with chess content
        # that haven't been used yet
        for task_ctx in task_contexts:
            if id(task_ctx) in used_tasks:
                continue
            
            # Prefer tasks with chess terms and difficulty indicators
            if (task_ctx.contains_chess_terms and 
                task_ctx.content_type in ['task', 'general_task'] and
                task_ctx.difficulty_indicators):
                
                return {
                    'task_context': task_ctx,
                    'confidence': 0.6,
                    'match_type': 'proximity'
                }
        
        return None
    
    def _find_fallback_match(self, diagram_ctx: DiagramContext, 
                           task_contexts: List[TaskContext], 
                           used_tasks: Set) -> Optional[Dict[str, Any]]:
        """Fallback matching strategy"""
        # Find any unused task
        for task_ctx in task_contexts:
            if (id(task_ctx) in used_tasks or 
                task_ctx.content_type not in ['task', 'general_task']):
                continue
            
            return {
                'task_context': task_ctx,
                'confidence': 0.3,
                'match_type': 'fallback'
            }
        
        return None

def apply_enhanced_diagram_associations(extracted_data: Dict[str, Any], 
                                      images_info: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply enhanced diagram processing to extracted data
    
    Args:
        extracted_data: Document data with lessons and content
        images_info: Information about extracted images
        
    Returns:
        Updated extracted_data with improved diagram associations
    """
    processor = EnhancedDiagramProcessor()
    
    # Extract contexts
    diagram_contexts = processor.extract_diagram_contexts(extracted_data, images_info)
    task_contexts = processor.extract_task_contexts(extracted_data)
    
    # Find associations
    associations = processor.associate_diagrams_with_tasks(diagram_contexts, task_contexts)
    
    # Apply associations to the extracted data
    for lesson in extracted_data.get('lessons', []):
        for content_item in lesson.get('content', []):
            # Find if any image should be associated with this content item
            for img_filename, association in associations.items():
                if id(association['task_context']) == id(content_item):
                    content_item['image'] = img_filename
                    content_item['diagram_number'] = next(
                        (ctx.diagram_number for ctx in diagram_contexts 
                         if ctx.image_filename == img_filename), None
                    )
                    content_item['association_confidence'] = association['confidence']
                    content_item['match_type'] = association['match_type']
                    logger.info(f"Associated {img_filename} with task in lesson {lesson.get('lesson_number')} "
                              f"(confidence: {association['confidence']:.2f})")
                    break
    
    return extracted_data 