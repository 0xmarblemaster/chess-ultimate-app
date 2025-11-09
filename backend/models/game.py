"""
Game Models

This module provides Pydantic models for chess games.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import date


class GameBase(BaseModel):
    """Base model for chess games."""
    pgn: str = Field(..., description="PGN notation of the game")
    white: str = Field(..., description="Name of the white player")
    black: str = Field(..., description="Name of the black player")
    date: str = Field(..., description="Date of the game (YYYY.MM.DD)")
    result: str = Field(..., description="Result of the game (1-0, 0-1, 1/2-1/2, *)")
    event: Optional[str] = Field(None, description="Event/tournament name")
    site: Optional[str] = Field(None, description="Location where the game was played")
    round: Optional[str] = Field(None, description="Round number in the tournament")
    eco: Optional[str] = Field(None, description="ECO code for the opening")
    white_elo: Optional[int] = Field(None, description="ELO rating of white player")
    black_elo: Optional[int] = Field(None, description="ELO rating of black player")
    
    @validator('result')
    def validate_result(cls, v):
        """Validate the game result."""
        valid_results = ['1-0', '0-1', '1/2-1/2', '*']
        if v not in valid_results:
            raise ValueError(f'Result must be one of {valid_results}')
        return v
    
    @validator('date')
    def validate_date_format(cls, v):
        """Validate the date format."""
        # Allow for '????' in date fields but prefer proper dates
        if '?' in v:
            return v
        
        try:
            # Try to parse YYYY.MM.DD format
            year, month, day = v.split('.')
            date(int(year), int(month), int(day))
        except (ValueError, TypeError):
            raise ValueError('Date must be in format YYYY.MM.DD or contain ? for unknown parts')
        return v


class GameCreate(GameBase):
    """Model for creating a new chess game."""
    source: Optional[str] = Field("Manual Import", description="Source of the game data")


class GameResponse(GameBase):
    """Model for returning a chess game."""
    id: str = Field(..., description="Unique identifier of the game")
    move_count: int = Field(..., description="Number of moves in the game")
    opening_moves: str = Field(..., description="Opening moves in SAN notation")
    import_date: str = Field(..., description="Date when the game was imported")
    

class GameSearchParams(BaseModel):
    """Parameters for searching games."""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Maximum number of results to return")
    white: Optional[str] = Field(None, description="Filter by white player name")
    black: Optional[str] = Field(None, description="Filter by black player name")
    result: Optional[str] = Field(None, description="Filter by game result")
    min_elo: Optional[int] = Field(None, description="Filter by minimum player ELO")
    event: Optional[str] = Field(None, description="Filter by event/tournament name")
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validate the limit parameter."""
        if v < 1:
            raise ValueError('Limit must be at least 1')
        if v > 50:
            return 50  # Cap at 50 to prevent resource exhaustion
        return v


class GameSearchResponse(BaseModel):
    """Response model for game search."""
    results: List[GameResponse] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results returned")
    query: str = Field(..., description="Original search query")


class GameImportResponse(BaseModel):
    """Response model for PGN import."""
    success: bool = Field(..., description="Whether the import was successful")
    game_id: Optional[str] = Field(None, description="ID of the stored game if successful")
    message: str = Field(..., description="Status message")


class BatchImportResponse(BaseModel):
    """Response model for batch PGN import."""
    success: bool = Field(..., description="Whether the import was successful")
    processed_count: int = Field(..., description="Number of games processed")
    success_count: int = Field(..., description="Number of games successfully stored")
    message: str = Field(..., description="Status message") 