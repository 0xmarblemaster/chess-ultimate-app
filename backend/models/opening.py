"""
Opening Models

This module provides Pydantic models for chess openings.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union


class OpeningBase(BaseModel):
    """Base model for chess openings."""
    eco: str = Field(..., description="ECO code for the opening (e.g., 'B01')")
    name: str = Field(..., description="Name of the opening")
    moves: str = Field(..., description="Opening moves in SAN notation")
    
    @validator('eco')
    def validate_eco(cls, v):
        """Validate the ECO code format."""
        if not (len(v) == 3 and v[0] in "ABCDE" and v[1:].isdigit()):
            raise ValueError("ECO code must be in format 'X00' where X is A-E and 00 is 00-99")
        return v


class OpeningCreate(OpeningBase):
    """Model for creating a new chess opening."""
    pgn: Optional[str] = Field(None, description="PGN notation for the opening moves")
    fen: Optional[str] = Field(None, description="FEN string for the position after the opening moves")
    category: Optional[str] = Field(None, description="Category of the opening (e.g., 'Open Game', 'Semi-Open')")
    description: Optional[str] = Field(None, description="Description of the opening and its key ideas")
    parent_eco: Optional[str] = Field(None, description="ECO code of the parent opening (if this is a variation)")
    variations: Optional[List[str]] = Field(None, description="ECO codes of known variations of this opening")
    popularity: Optional[float] = Field(None, ge=0, le=100, description="Relative popularity of the opening (0-100)")
    evaluation: Optional[float] = Field(None, description="Approximate engine evaluation of the position")
    tags: Optional[List[str]] = Field(None, description="Tags describing the opening (e.g., 'tactical', 'positional')")


class OpeningResponse(OpeningBase):
    """Model for returning a chess opening."""
    id: str = Field(..., description="Unique identifier of the opening")
    pgn: Optional[str] = Field(None, description="PGN notation for the opening moves")
    fen: Optional[str] = Field(None, description="FEN string for the position after the opening moves")
    category: Optional[str] = Field(None, description="Category of the opening")
    description: Optional[str] = Field(None, description="Description of the opening")
    parent_eco: Optional[str] = Field(None, description="ECO code of the parent opening")
    variations: Optional[List[str]] = Field(None, description="ECO codes of known variations")
    popularity: Optional[float] = Field(None, description="Relative popularity of the opening")
    evaluation: Optional[float] = Field(None, description="Approximate engine evaluation")
    tags: Optional[List[str]] = Field(None, description="Tags describing the opening")


class OpeningSearchParams(BaseModel):
    """Parameters for searching openings."""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Maximum number of results to return")
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validate the limit parameter."""
        if v < 1:
            raise ValueError('Limit must be at least 1')
        if v > 50:
            return 50  # Cap at 50 to prevent resource exhaustion
        return v


class OpeningFilterParams(BaseModel):
    """Parameters for filtering openings."""
    category: Optional[str] = Field(None, description="Filter by opening category")
    min_popularity: Optional[float] = Field(None, ge=0, le=100, description="Filter by minimum popularity")
    tags: Optional[str] = Field(None, description="Comma-separated list of tags to filter by")
    limit: int = Field(20, description="Maximum number of results to return")
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validate the limit parameter."""
        if v < 1:
            raise ValueError('Limit must be at least 1')
        if v > 100:
            return 100  # Cap at 100 to prevent resource exhaustion
        return v


class OpeningSearchResponse(BaseModel):
    """Response model for opening search."""
    results: List[OpeningResponse] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results returned")


class OpeningImportResponse(BaseModel):
    """Response model for opening import."""
    success: bool = Field(..., description="Whether the import was successful")
    total_count: int = Field(..., description="Number of openings processed")
    success_count: int = Field(..., description="Number of openings successfully stored")
    message: str = Field(..., description="Status message") 