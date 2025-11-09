import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ProgressStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ProgressStep:
    name: str
    description: str
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ProgressTracker:
    """Track progress of RAG pipeline steps for real-time user feedback"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.steps: List[ProgressStep] = []
        self.current_step_index = -1
        self.overall_start_time = time.time()
        self.overall_end_time = None
        self.lock = threading.Lock()
        
        # Define standard RAG pipeline steps
        self._initialize_standard_steps()
    
    def _initialize_standard_steps(self):
        """Initialize the standard steps for RAG pipeline"""
        standard_steps = [
            ("query_validation", "Validating query"),
            ("router_classification", "Analyzing query type"),
            ("document_retrieval", "Searching knowledge base"),
            ("stockfish_analysis", "Running chess engine analysis"),
            ("answer_generation", "Generating response"),
            ("response_formatting", "Finalizing response")
        ]
        
        with self.lock:
            self.steps = [
                ProgressStep(name=name, description=desc) 
                for name, desc in standard_steps
            ]
    
    def start_step(self, step_name: str, description: Optional[str] = None) -> bool:
        """
        Start a specific step in the pipeline
        
        Args:
            step_name: Name of the step to start
            description: Optional custom description
            
        Returns:
            True if step was found and started, False otherwise
        """
        with self.lock:
            for i, step in enumerate(self.steps):
                if step.name == step_name:
                    step.status = ProgressStatus.IN_PROGRESS
                    step.start_time = time.time()
                    if description:
                        step.description = description
                    self.current_step_index = i
                    logger.debug(f"Started step: {step_name} - {step.description}")
                    return True
            
            # If step not found, add it dynamically
            new_step = ProgressStep(
                name=step_name,
                description=description or step_name,
                status=ProgressStatus.IN_PROGRESS,
                start_time=time.time()
            )
            self.steps.append(new_step)
            self.current_step_index = len(self.steps) - 1
            logger.debug(f"Added and started new step: {step_name}")
            return True
    
    def complete_step(self, step_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark a step as completed
        
        Args:
            step_name: Name of the step to complete
            metadata: Optional metadata about the step completion
            
        Returns:
            True if step was found and completed, False otherwise
        """
        with self.lock:
            for step in self.steps:
                if step.name == step_name and step.status == ProgressStatus.IN_PROGRESS:
                    step.status = ProgressStatus.COMPLETED
                    step.end_time = time.time()
                    if step.start_time:
                        step.duration = step.end_time - step.start_time
                    if metadata:
                        step.metadata.update(metadata)
                    logger.debug(f"Completed step: {step_name} in {step.duration:.2f}s")
                    return True
            return False
    
    def fail_step(self, step_name: str, error_message: str) -> bool:
        """
        Mark a step as failed
        
        Args:
            step_name: Name of the step that failed
            error_message: Error message describing the failure
            
        Returns:
            True if step was found and marked as failed, False otherwise
        """
        with self.lock:
            for step in self.steps:
                if step.name == step_name:
                    step.status = ProgressStatus.FAILED
                    step.end_time = time.time()
                    if step.start_time:
                        step.duration = step.end_time - step.start_time
                    step.error_message = error_message
                    logger.debug(f"Failed step: {step_name} - {error_message}")
                    return True
            return False
    
    def skip_step(self, step_name: str, reason: str) -> bool:
        """
        Mark a step as skipped
        
        Args:
            step_name: Name of the step to skip
            reason: Reason for skipping the step
            
        Returns:
            True if step was found and skipped, False otherwise
        """
        with self.lock:
            for step in self.steps:
                if step.name == step_name:
                    step.status = ProgressStatus.SKIPPED
                    step.metadata['skip_reason'] = reason
                    logger.debug(f"Skipped step: {step_name} - {reason}")
                    return True
            return False
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get current progress information
        
        Returns:
            Dict containing progress information
        """
        with self.lock:
            completed_steps = sum(1 for s in self.steps if s.status == ProgressStatus.COMPLETED)
            failed_steps = sum(1 for s in self.steps if s.status == ProgressStatus.FAILED)
            total_steps = len(self.steps)
            
            current_step = None
            if 0 <= self.current_step_index < len(self.steps):
                current_step = self.steps[self.current_step_index]
            
            # Calculate overall duration
            overall_duration = None
            if self.overall_end_time:
                overall_duration = self.overall_end_time - self.overall_start_time
            else:
                overall_duration = time.time() - self.overall_start_time
            
            return {
                'session_id': self.session_id,
                'overall_progress': completed_steps / total_steps if total_steps > 0 else 0,
                'completed_steps': completed_steps,
                'failed_steps': failed_steps,
                'total_steps': total_steps,
                'current_step': {
                    'name': current_step.name if current_step else None,
                    'description': current_step.description if current_step else None,
                    'status': current_step.status.value if current_step else None
                } if current_step else None,
                'steps': [
                    {
                        'name': step.name,
                        'description': step.description,
                        'status': step.status.value,
                        'duration': step.duration,
                        'error_message': step.error_message
                    }
                    for step in self.steps
                ],
                'overall_duration': overall_duration,
                'estimated_remaining': self._estimate_remaining_time()
            }
    
    def _estimate_remaining_time(self) -> Optional[float]:
        """Estimate remaining time based on completed steps"""
        with self.lock:
            completed_durations = [s.duration for s in self.steps if s.duration is not None]
            if not completed_durations:
                return None
            
            avg_duration = sum(completed_durations) / len(completed_durations)
            remaining_steps = sum(1 for s in self.steps if s.status == ProgressStatus.PENDING)
            
            return avg_duration * remaining_steps
    
    def finish(self, success: bool = True):
        """Mark the overall progress as finished"""
        with self.lock:
            self.overall_end_time = time.time()
            
            # Mark any pending steps as skipped if finished unsuccessfully
            if not success:
                for step in self.steps:
                    if step.status == ProgressStatus.PENDING:
                        step.status = ProgressStatus.SKIPPED
                        step.metadata['skip_reason'] = 'Pipeline terminated early'
            
            logger.debug(f"Progress tracking finished for session {self.session_id} (success: {success})")

class ProgressManager:
    """Manage progress trackers for multiple sessions"""
    
    def __init__(self):
        self.active_trackers: Dict[str, ProgressTracker] = {}
        self.lock = threading.Lock()
    
    def create_tracker(self, session_id: str) -> ProgressTracker:
        """Create a new progress tracker for a session"""
        with self.lock:
            tracker = ProgressTracker(session_id)
            self.active_trackers[session_id] = tracker
            logger.debug(f"Created progress tracker for session: {session_id}")
            return tracker
    
    def get_tracker(self, session_id: str) -> Optional[ProgressTracker]:
        """Get existing progress tracker for a session"""
        with self.lock:
            return self.active_trackers.get(session_id)
    
    def get_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a specific session"""
        tracker = self.get_tracker(session_id)
        return tracker.get_progress() if tracker else None
    
    def cleanup_session(self, session_id: str):
        """Clean up progress tracker for a session"""
        with self.lock:
            if session_id in self.active_trackers:
                del self.active_trackers[session_id]
                logger.debug(f"Cleaned up progress tracker for session: {session_id}")
    
    def cleanup_old_trackers(self, max_age: int = 3600):
        """Clean up old progress trackers (older than max_age seconds)"""
        current_time = time.time()
        to_remove = []
        
        with self.lock:
            for session_id, tracker in self.active_trackers.items():
                if current_time - tracker.overall_start_time > max_age:
                    to_remove.append(session_id)
            
            for session_id in to_remove:
                del self.active_trackers[session_id]
                logger.debug(f"Cleaned up old progress tracker for session: {session_id}")

def progress_step(step_name: str, description: Optional[str] = None):
    """
    Decorator to automatically track progress for a function
    
    Args:
        step_name: Name of the step for progress tracking
        description: Optional description of the step
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Try to find session_id in args or kwargs
            session_id = None
            if 'session_id' in kwargs:
                session_id = kwargs['session_id']
            
            if session_id:
                tracker = progress_manager.get_tracker(session_id)
                if tracker:
                    tracker.start_step(step_name, description)
                    try:
                        result = func(*args, **kwargs)
                        tracker.complete_step(step_name)
                        return result
                    except Exception as e:
                        tracker.fail_step(step_name, str(e))
                        raise
                else:
                    # No tracker, execute function normally
                    return func(*args, **kwargs)
            else:
                # No session_id, execute function normally
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global progress manager instance
progress_manager = ProgressManager() 