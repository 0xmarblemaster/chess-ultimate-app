"""
Lesson Models

This module provides Pydantic models for chess lessons.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union


class ChunkBase(BaseModel):
    """Base model for lesson chunks."""
    content: str = Field(..., description="The text content of the lesson chunk")
    book: str = Field(..., description="Title of the book or source")
    lesson_number: int = Field(..., description="Lesson number within the book")
    lesson_title: str = Field(..., description="Title of the lesson")
    chunk_type: str = Field("explanation", description="Type of chunk (e.g., 'explanation', 'task', 'example')")
    
    @validator('chunk_type')
    def validate_chunk_type(cls, v):
        """Validate the chunk type."""
        valid_types = ['explanation', 'task', 'example', 'introduction', 'conclusion', 'diagram']
        if v not in valid_types:
            raise ValueError(f'Chunk type must be one of {valid_types}')
        return v


class ChunkCreate(ChunkBase):
    """Model for creating a new lesson chunk."""
    chunk_id: Optional[str] = Field(None, description="Unique ID for this chunk")
    diagram_reference: Optional[str] = Field(None, description="Reference to a diagram image if any")
    diagram_number: Optional[int] = Field(None, description="Number of the diagram if any")
    fen: Optional[str] = Field(None, description="FEN string for the position if any")
    pgn: Optional[str] = Field(None, description="PGN notation for moves if any")
    difficulty: Optional[str] = Field(None, description="Difficulty level of the chunk")
    tags: Optional[List[str]] = Field(None, description="Tags describing the content")
    topics: Optional[List[str]] = Field(None, description="Chess topics covered in the chunk")
    source: Optional[str] = Field(None, description="Source file of the lesson")
    source_type: Optional[str] = Field(None, description="Type of source (e.g., 'pdf', 'docx')")


class ChunkResponse(ChunkBase):
    """Model for returning a lesson chunk."""
    id: str = Field(..., description="Unique identifier of the chunk")
    chunk_id: str = Field(..., description="Unique ID for this chunk")
    diagram_reference: Optional[str] = Field(None, description="Reference to a diagram image if any")
    diagram_number: Optional[int] = Field(None, description="Number of the diagram if any")
    fen: Optional[str] = Field(None, description="FEN string for the position if any")
    pgn: Optional[str] = Field(None, description="PGN notation for moves if any")
    difficulty: Optional[str] = Field(None, description="Difficulty level of the chunk")
    tags: Optional[List[str]] = Field(None, description="Tags describing the content")
    topics: Optional[List[str]] = Field(None, description="Chess topics covered in the chunk")
    source: Optional[str] = Field(None, description="Source file of the lesson")
    source_type: Optional[str] = Field(None, description="Type of source (e.g., 'pdf', 'docx')")


class LessonSearchParams(BaseModel):
    """Parameters for searching lessons."""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Maximum number of results to return")
    book: Optional[str] = Field(None, description="Filter by book title")
    lesson_number: Optional[int] = Field(None, description="Filter by lesson number")
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validate the limit parameter."""
        if v < 1:
            raise ValueError('Limit must be at least 1')
        if v > 50:
            return 50  # Cap at 50 to prevent resource exhaustion
        return v


class LessonSearchResponse(BaseModel):
    """Response model for lesson search."""
    results: List[ChunkResponse] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results returned")


class LessonMetadata(BaseModel):
    """Metadata for a lesson."""
    number: int = Field(..., description="Lesson number")
    title: str = Field(..., description="Lesson title")
    chunk_count: int = Field(..., description="Number of chunks in the lesson")


class BookResponse(BaseModel):
    """Response model for book information."""
    book: str = Field(..., description="Title of the book")
    lessons: List[LessonMetadata] = Field(..., description="List of lessons in the book")
    count: int = Field(..., description="Number of lessons in the book")


class LessonResponse(BaseModel):
    """Response model for a complete lesson."""
    book: str = Field(..., description="Title of the book")
    number: int = Field(..., description="Lesson number")
    title: str = Field(..., description="Lesson title")
    chunks: List[ChunkResponse] = Field(..., description="All chunks in the lesson")
    chunk_types: Dict[str, List[ChunkResponse]] = Field(..., description="Chunks grouped by type")


class DocumentImportResponse(BaseModel):
    """Response model for document import."""
    success: bool = Field(..., description="Whether the import was successful")
    book_title: str = Field(..., description="Title of the imported book")
    lesson_count: int = Field(..., description="Number of lessons extracted")
    chunk_count: int = Field(..., description="Number of chunks stored")
    message: str = Field(..., description="Status message") 