"""
Database Layer for Chess Companion

This module provides database abstractions for the application:
- GameRepository: For storing and retrieving chess games
- OpeningRepository: For storing and retrieving chess openings
- LessonRepository: For storing and retrieving lesson chunks
"""

from backend.database.game_repository import GameRepository
from backend.database.opening_repository import OpeningRepository
from backend.database.lesson_repository import LessonRepository 