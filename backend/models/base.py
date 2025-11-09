"""
Base Models

This module provides base model classes for the application.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Time of health check")
    version: str = Field(..., description="Service version")
    service_name: str = Field(..., description="Name of the service")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health check details")


class ApiError(BaseModel):
    """API error response model."""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Time of error")


class ApiResponse(BaseModel):
    """Generic API response model."""
    success: bool = Field(..., description="Whether the request was successful")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Time of response")


class PaginatedResponse(BaseModel):
    """Paginated response model."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page") 