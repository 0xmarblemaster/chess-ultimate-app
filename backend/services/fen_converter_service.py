"""
FEN Converter Service

Service for converting between chess board images and FEN notation.
"""

import logging
import os
import subprocess
import tempfile
from typing import Dict, Any, Optional, Union, Tuple
from pathlib import Path
import chess
import cv2
import numpy as np

# Import config
from backend.config import FEN_MODEL_PATH, PYTHON_EXECUTABLE

logger = logging.getLogger(__name__)

class FENConverterService:
    """
    Service for converting between chess board images and FEN notation.
    
    This service handles:
    1. Converting chess board images to FEN notation
    2. Validating FEN strings
    3. Converting FEN notation back to chess board images
    """
    
    def __init__(self, model_path=None, python_executable=None):
        """
        Initialize the FEN Converter service.
        
        Args:
            model_path: Path to the chess board recognition model.
            python_executable: Path to Python executable for running external scripts.
        """
        self.logger = logger
        self.model_path = model_path or FEN_MODEL_PATH
        self.python_executable = python_executable or PYTHON_EXECUTABLE
        
        # Initialize validation status
        self._is_initialized = False
        self._initialization_error = None
        
        # Try to initialize and validate components
        try:
            self._validate_initialization()
            self._is_initialized = True
        except Exception as e:
            self._initialization_error = str(e)
            self.logger.error(f"FEN Converter initialization failed: {e}")
    
    def healthcheck(self) -> bool:
        """
        Check if the service is operational.
        
        Returns:
            True if the service is healthy, False otherwise.
        """
        try:
            # Check if initialization was successful
            if not self._is_initialized:
                self.logger.warning(f"Health check failed: Service not initialized. Error: {self._initialization_error}")
                return False
                
            # Validate that we can access the model or external tools
            if self.model_path and not os.path.exists(self.model_path):
                self.logger.warning(f"Health check failed: Model path not found: {self.model_path}")
                return False
                
            # Verify Python executable is available
            result = subprocess.run([self.python_executable, "--version"], 
                                    capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                self.logger.warning(f"Health check failed: Python executable check failed: {result.stderr}")
                return False
                
            # Basic chess module test
            test_board = chess.Board()
            if test_board.fen() != chess.STARTING_FEN:
                self.logger.warning("Health check failed: Chess library validation failed")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False    
    def _validate_initialization(self) -> None:
        """
        Validate that required components are available.
        
        Raises:
            ValueError: If required components are missing or invalid
        """
        # Verify python chess library is available
        try:
            import chess
        except ImportError:
            raise ValueError("Python chess library not available. Install with 'pip install chess'")
            
        # If model path is specified, verify it exists
        if self.model_path and not os.path.exists(self.model_path):
            raise ValueError(f"Model path not found: {self.model_path}")
    
    def convert_image_to_fen(self, image_path: Union[str, Path, np.ndarray], 
                           perspective_correction: bool = True) -> str:
        """
        Convert a chess board image to FEN notation.
        
        Args:
            image_path: Path to the image file or the image array directly
            perspective_correction: Whether to apply perspective correction
            
        Returns:
            FEN string representation of the board position
            
        Raises:
            ValueError: If the image cannot be processed
            RuntimeError: If the conversion fails
        """
        try:
            # Check if service is initialized
            if not self._is_initialized:
                raise ValueError(f"Service not properly initialized: {self._initialization_error}")
            
            # Process the image - this is a placeholder that would integrate with a real CV model
            # In a real implementation, this would:
            # 1. Use a CV model to detect the board
            # 2. Apply perspective correction if requested
            # 3. Detect pieces on the board
            # 4. Convert to FEN notation
            
            # For the MVP, we're using a simplified approach
            if isinstance(image_path, (str, Path)):
                if not os.path.exists(image_path):
                    raise ValueError(f"Image file not found: {image_path}")
                
                # Read image
                img = cv2.imread(str(image_path))
                if img is None:
                    raise ValueError(f"Failed to read image: {image_path}")
            elif isinstance(image_path, np.ndarray):
                img = image_path
            else:
                raise ValueError(f"Unsupported image type: {type(image_path)}")
            
            # TODO: Implement actual board recognition logic
            # For now, return a placeholder FEN representing the starting position
            fen = chess.STARTING_FEN
            
            # Log the conversion
            self.logger.info(f"Converted image to FEN: {fen}")
            return fen
            
        except Exception as e:
            self.logger.error(f"Error in convert_image_to_fen: {e}")
            raise

    def validate_fen(self, fen: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a FEN string is well-formed and represents a legal position.
        
        Args:
            fen: The FEN string to validate
            
        Returns:
            A tuple (is_valid, error_message) where:
              - is_valid is True if the FEN is valid, False otherwise
              - error_message contains details if invalid, None otherwise
        """
        try:
            # Check if service is initialized
            if not self._is_initialized:
                raise ValueError(f"Service not properly initialized: {self._initialization_error}")
            
            # Use the chess library to validate the FEN
            try:
                chess.Board(fen)
                return True, None
            except ValueError as e:
                return False, str(e)
            
        except Exception as e:
            self.logger.error(f"Error in validate_fen: {e}")
            return False, f"Internal error: {str(e)}"
    
    def convert_fen_to_image(self, fen: str, output_path: Optional[Union[str, Path]] = None,
                           size: int = 600, with_coordinates: bool = True) -> Union[str, np.ndarray]:
        """
        Convert a FEN string to a chess board image.
        
        Args:
            fen: FEN string to convert
            output_path: Path to save the output image. If None, the image is returned as an array.
            size: Size of the output image in pixels (width = height)
            with_coordinates: Whether to include coordinates (a-h, 1-8) in the image
            
        Returns:
            If output_path is provided, returns the path to the saved image.
            Otherwise, returns the image as a numpy array.
            
        Raises:
            ValueError: If the FEN is invalid
            RuntimeError: If the conversion fails
        """
        try:
            # Check if service is initialized
            if not self._is_initialized:
                raise ValueError(f"Service not properly initialized: {self._initialization_error}")
            
            # Validate FEN
            is_valid, error = self.validate_fen(fen)
            if not is_valid:
                raise ValueError(f"Invalid FEN: {error}")
            
            # Create a chess board from the FEN
            board = chess.Board(fen)
            
            # TODO: Implement actual board rendering logic
            # For a proper implementation, this would:
            # 1. Create an empty board image
            # 2. Draw squares in alternating colors
            # 3. Draw coordinates if requested
            # 4. Draw pieces based on the FEN
            
            # For the MVP, we'll create a simple visual representation
            # (this is a placeholder - in a real implementation you'd use a proper rendering library)
            square_size = size // 8
            img = np.zeros((size, size, 3), dtype=np.uint8)
            
            # Draw alternating squares
            for row in range(8):
                for col in range(8):
                    color = (240, 240, 240) if (row + col) % 2 == 0 else (100, 100, 100)
                    x1, y1 = col * square_size, row * square_size
                    x2, y2 = x1 + square_size, y1 + square_size
                    cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)            # Add coordinates if requested
            if with_coordinates:
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                font_thickness = 1
                font_color = (0, 0, 0)
                
                # Add column labels (a-h)
                for col in range(8):
                    label = chr(ord('a') + col)
                    x = col * square_size + square_size // 2
                    y = size - 10
                    cv2.putText(img, label, (x, y), font, font_scale, font_color, font_thickness)
                
                # Add row labels (1-8)
                for row in range(8):
                    label = str(8 - row)
                    x = 10
                    y = row * square_size + square_size // 2
                    cv2.putText(img, label, (x, y), font, font_scale, font_color, font_thickness)
            
            # TODO: Draw pieces on the board
            # For a real implementation, you'd place piece images on each square
            
            # Save or return the image
            if output_path:
                cv2.imwrite(str(output_path), img)
                self.logger.info(f"Saved board image to {output_path}")
                return str(output_path)
            else:
                return img
                
        except Exception as e:
            self.logger.error(f"Error in convert_fen_to_image: {e}")
            raise
        
        
# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # Create service instance
        service = FENConverterService()
        logger.info("FEN Converter service initialized")
        
        # Test health check
        is_healthy = service.healthcheck()
        logger.info(f"Health check {'passed' if is_healthy else 'failed'}")
        
        # Example service usage
        starting_position = chess.STARTING_FEN
        is_valid, error = service.validate_fen(starting_position)
        logger.info(f"FEN valid: {is_valid}, Error: {error}")
        
        # Create and save a test image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
            output_path = temp.name
        
        service.convert_fen_to_image(starting_position, output_path)
        logger.info(f"Test image saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error in FEN Converter service example: {e}", exc_info=True)