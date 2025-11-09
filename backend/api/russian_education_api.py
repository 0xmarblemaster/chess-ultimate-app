"""
Russian Education API

API endpoints for processing Russian chess educational materials.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional
import logging
import json
import os
import tempfile
from pathlib import Path
import uuid

# Import the specialized pipeline
from backend.etl.russian_education_pipeline import RussianEducationPipeline
from backend.database.lesson_repository import LessonRepository

# Create router
router = APIRouter(
    prefix="/russian-education",
    tags=["russian-education"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

# Global storage for processing jobs
processing_jobs = {}

class ProcessingJob:
    """Track background processing jobs"""
    def __init__(self, job_id: str, total_files: int):
        self.job_id = job_id
        self.total_files = total_files
        self.processed_files = 0
        self.status = "running"
        self.results = None
        self.errors = []
        
# Dependency for repository
def get_lesson_repository():
    """Dependency to get the lesson repository."""
    return LessonRepository()

@router.post("/upload-batch")
async def upload_batch_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    enable_translation: bool = Form(False),
    batch_size: int = Form(5),
    lesson_repository: LessonRepository = Depends(get_lesson_repository)
):
    """
    Upload and process a batch of Russian educational documents.
    
    Args:
        files: List of document files (PDF or DOCX)
        enable_translation: Whether to enable translation features
        batch_size: Number of documents to process in parallel
        
    Returns:
        Job ID for tracking progress
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
            
        # Validate file types
        supported_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        for file in files:
            if file.content_type not in supported_types:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type: {file.content_type}. Only PDF and DOCX files are supported."
                )
        
        # Create temporary directory for uploaded files
        temp_dir = Path(tempfile.mkdtemp(prefix="russian_education_"))
        
        # Save uploaded files
        saved_files = []
        for file in files:
            file_path = temp_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_files.append(file_path)
            
        # Create processing job
        job_id = str(uuid.uuid4())
        processing_jobs[job_id] = ProcessingJob(job_id, len(files))
        
        # Start background processing
        background_tasks.add_task(
            process_documents_background,
            job_id=job_id,
            file_paths=saved_files,
            enable_translation=enable_translation,
            batch_size=batch_size,
            temp_dir=temp_dir
        )
        
        return {
            "job_id": job_id,
            "status": "started",
            "total_files": len(files),
            "message": f"Processing {len(files)} Russian educational documents"
        }
        
    except Exception as e:
        logger.error(f"Error in upload_batch_documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_documents_background(
    job_id: str,
    file_paths: List[Path],
    enable_translation: bool,
    batch_size: int,
    temp_dir: Path
):
    """
    Background task to process documents
    """
    try:
        job = processing_jobs[job_id]
        
        # Initialize pipeline
        pipeline = RussianEducationPipeline(
            input_dir=None,  # We'll process specific files
            enable_translation=enable_translation,
            batch_size=batch_size
        )
        
        # Process the uploaded files
        results = pipeline.batch_process_documents(file_paths)
        
        # Update job status
        job.status = "completed"
        job.results = results
        job.processed_files = len(file_paths)
        
        # Cleanup temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        job = processing_jobs.get(job_id)
        if job:
            job.status = "failed"
            job.errors.append(str(e))
        logger.error(f"Background processing failed for job {job_id}: {e}")

@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Get the status of a processing job.
    
    Args:
        job_id: ID of the processing job
        
    Returns:
        Job status and progress information
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = processing_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job.status,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "progress_percent": (job.processed_files / job.total_files * 100) if job.total_files > 0 else 0
    }
    
    if job.status == "completed" and job.results:
        response["results"] = {
            "successful_files": job.results.get("successful_files", 0),
            "failed_files": job.results.get("failed_files", 0),
            "total_chunks": job.results.get("total_chunks", 0),
            "total_fen_conversions": job.results.get("total_fen_conversions", 0),
            "stored_chunks": job.results.get("stored_chunks", 0)
        }
        
    if job.errors:
        response["errors"] = job.errors
        
    return response

@router.get("/job/{job_id}/results")
async def get_job_results(job_id: str):
    """
    Get the detailed results of a completed processing job.
    
    Args:
        job_id: ID of the processing job
        
    Returns:
        Detailed processing results
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = processing_jobs[job_id]
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job is not completed. Current status: {job.status}")
        
    if not job.results:
        raise HTTPException(status_code=404, detail="No results available")
        
    return job.results

@router.post("/process-directory")
async def process_directory(
    background_tasks: BackgroundTasks,
    directory_path: str = Form(...),
    enable_translation: bool = Form(False),
    batch_size: int = Form(5)
):
    """
    Process all Russian educational documents in a directory.
    
    Args:
        directory_path: Path to directory containing documents
        enable_translation: Whether to enable translation features
        batch_size: Number of documents to process in parallel
        
    Returns:
        Job ID for tracking progress
    """
    try:
        dir_path = Path(directory_path)
        if not dir_path.exists():
            raise HTTPException(status_code=400, detail=f"Directory does not exist: {directory_path}")
            
        if not dir_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {directory_path}")
            
        # Find all supported documents
        supported_extensions = ['.pdf', '.docx', '.doc']
        file_paths = []
        
        for ext in supported_extensions:
            file_paths.extend(dir_path.glob(f"**/*{ext}"))
            
        if not file_paths:
            raise HTTPException(status_code=400, detail="No supported documents found in directory")
            
        # Create processing job
        job_id = str(uuid.uuid4())
        processing_jobs[job_id] = ProcessingJob(job_id, len(file_paths))
        
        # Start background processing
        background_tasks.add_task(
            process_directory_background,
            job_id=job_id,
            directory_path=directory_path,
            enable_translation=enable_translation,
            batch_size=batch_size
        )
        
        return {
            "job_id": job_id,
            "status": "started",
            "total_files": len(file_paths),
            "message": f"Processing {len(file_paths)} documents from directory"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process_directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_directory_background(
    job_id: str,
    directory_path: str,
    enable_translation: bool,
    batch_size: int
):
    """
    Background task to process directory
    """
    try:
        job = processing_jobs[job_id]
        
        # Initialize pipeline
        pipeline = RussianEducationPipeline(
            input_dir=directory_path,
            enable_translation=enable_translation,
            batch_size=batch_size
        )
        
        # Process the directory
        results = pipeline.process_directory()
        
        # Update job status
        job.status = "completed"
        job.results = results
        job.processed_files = results.get("total_files", 0)
        
    except Exception as e:
        job = processing_jobs.get(job_id)
        if job:
            job.status = "failed"
            job.errors.append(str(e))
        logger.error(f"Background directory processing failed for job {job_id}: {e}")

@router.get("/search-russian-content")
async def search_russian_content(
    query: str,
    limit: int = 10,
    difficulty_level: Optional[str] = None,
    content_type: Optional[str] = None,
    lesson_repository: LessonRepository = Depends(get_lesson_repository)
):
    """
    Search for Russian chess educational content.
    
    Args:
        query: Search query in Russian or English
        limit: Maximum number of results
        difficulty_level: Filter by difficulty (beginner, intermediate, advanced)
        content_type: Filter by content type (explanation, task, etc.)
        
    Returns:
        List of matching content chunks
    """
    try:
        # Build filters
        filters = {"language": "ru"}
        
        if difficulty_level:
            filters["difficulty_level"] = difficulty_level
            
        if content_type:
            filters["type"] = content_type
            
        # Search for content
        results = lesson_repository.search_lessons(
            query=query,
            limit=limit,
            filters=filters
        )
        
        return {
            "query": query,
            "filters": filters,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error searching Russian content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/russian-books")
async def get_russian_books(
    lesson_repository: LessonRepository = Depends(get_lesson_repository)
):
    """
    Get list of all Russian chess books in the database.
    
    Returns:
        List of Russian books with metadata
    """
    try:
        # Get all chunks with Russian language
        all_chunks = lesson_repository.search_lessons(
            query="",
            limit=1000,
            filters={"language": "ru"}
        )
        
        # Group by book
        books = {}
        for chunk in all_chunks:
            book_title = chunk.get("book", "Unknown Book")
            if book_title not in books:
                books[book_title] = {
                    "title": book_title,
                    "lesson_count": 0,
                    "chunk_count": 0,
                    "difficulty_levels": set(),
                    "content_types": set()
                }
            
            books[book_title]["chunk_count"] += 1
            
            if chunk.get("lessonNumber"):
                books[book_title]["lesson_count"] = max(
                    books[book_title]["lesson_count"], 
                    int(chunk.get("lessonNumber", 0))
                )
                
            if chunk.get("difficulty_level"):
                books[book_title]["difficulty_levels"].add(chunk["difficulty_level"])
                
            if chunk.get("type"):
                books[book_title]["content_types"].add(chunk["type"])
        
        # Convert sets to lists for JSON serialization
        for book in books.values():
            book["difficulty_levels"] = list(book["difficulty_levels"])
            book["content_types"] = list(book["content_types"])
            
        return {
            "books": list(books.values()),
            "total_books": len(books)
        }
        
    except Exception as e:
        logger.error(f"Error getting Russian books: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/job/{job_id}")
async def cleanup_job(job_id: str):
    """
    Clean up a completed or failed processing job.
    
    Args:
        job_id: ID of the job to clean up
        
    Returns:
        Cleanup confirmation
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    del processing_jobs[job_id]
    
    return {
        "job_id": job_id,
        "status": "cleaned_up",
        "message": "Job data has been removed"
    }

@router.get("/jobs")
async def list_active_jobs():
    """
    List all active processing jobs.
    
    Returns:
        List of active jobs with their status
    """
    jobs_list = []
    for job_id, job in processing_jobs.items():
        jobs_list.append({
            "job_id": job_id,
            "status": job.status,
            "total_files": job.total_files,
            "processed_files": job.processed_files,
            "progress_percent": (job.processed_files / job.total_files * 100) if job.total_files > 0 else 0,
            "has_errors": len(job.errors) > 0
        })
    
    return {
        "active_jobs": jobs_list,
        "total_jobs": len(jobs_list)
    }

@router.get("/health")
async def health_check():
    """
    Health check for the Russian education processing system.
    
    Returns:
        System health status
    """
    try:
        # Test pipeline initialization
        pipeline = RussianEducationPipeline()
        
        # Test repository connection
        repo = LessonRepository()
        repo_health = repo.healthcheck()
        
        return {
            "status": "healthy",
            "pipeline_initialized": True,
            "repository_connected": repo_health,
            "active_jobs": len(processing_jobs),
            "services": {
                "extract_service": "available",
                "fen_converter": "available",
                "vector_store": "connected" if repo_health else "disconnected"
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "active_jobs": len(processing_jobs)
        } 