"""Main FastAPI application for GitHub PR Analyzer."""

import uuid
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db, create_tables_async
from app.models import AnalysisTask, TaskStatus
from app.schemas import (
    AnalyzeRequest, AnalyzeResponse, TaskStatusResponse, 
    AnalysisResults, ErrorResponse
)
from app.celery_app import analyze_pr_task
from app.utils.logging import get_logger
from app.api.admin import router as admin_router

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GitHub PR Analyzer",
    description="Autonomous code review agent system using AI to analyze GitHub pull requests",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include admin routes
app.include_router(admin_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup."""
    try:
        await create_tables_async()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Application shutting down")


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "message": "GitHub PR Analyzer API",
        "status": "active",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/analyze-pr", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_pr(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a GitHub pull request for analysis.
    
    This endpoint accepts a GitHub repository URL and PR number, then starts
    an asynchronous analysis task using Celery.
    """
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        logger.info(f"Starting PR analysis for {request.repo_url}/pull/{request.pr_number}")
        
        # Create task record in database
        task = AnalysisTask(
            task_id=task_id,
            repo_url=str(request.repo_url),
            pr_number=request.pr_number,
            status=TaskStatus.PENDING,
            metadata={
                "analysis_types": request.analysis_types,
                "priority": request.priority,
                "github_token_provided": request.github_token is not None
            }
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # Start Celery task
        celery_task = analyze_pr_task.delay(
            task_id=task_id,
            repo_url=str(request.repo_url),
            pr_number=request.pr_number,
            github_token=request.github_token,
            analysis_types=request.analysis_types or ["style", "bug", "security", "performance"]
        )
        
        logger.info(f"Celery task {celery_task.id} started for PR analysis {task_id}")
        
        return AnalyzeResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"Analysis started for PR #{request.pr_number}",
            estimated_completion_time="5-10 minutes"
        )
        
    except Exception as e:
        logger.error(f"Failed to start PR analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
        )


@app.get("/status/{task_id}", response_model=TaskStatusResponse, tags=["Analysis"])
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check the status of an analysis task.
    
    Returns current progress, status, and estimated completion time.
    """
    try:
        # Query task from database
        result = await db.execute(
            select(AnalysisTask).where(AnalysisTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        # Calculate progress
        progress_percentage = 0
        if task.total_files > 0:
            progress_percentage = (task.processed_files / task.total_files) * 100
        
        progress_info = {
            "percentage": round(progress_percentage, 2),
            "current_stage": _get_current_stage(task.status),
            "files_processed": task.processed_files,
            "total_files": task.total_files
        }
        
        # Estimate completion time
        estimated_completion = None
        if task.status == TaskStatus.PROCESSING and task.started_at:
            estimated_completion = _estimate_completion_time(task)
        
        return TaskStatusResponse(
            task_id=task_id,
            status=task.status,
            progress=progress_info,
            current_file=task.current_file,
            processed_files=task.processed_files,
            total_files=task.total_files,
            created_at=task.created_at,
            started_at=task.started_at,
            estimated_completion=estimated_completion,
            error_message=task.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve task status: {str(e)}"
        )


@app.get("/results/{task_id}", response_model=AnalysisResults, tags=["Analysis"])
async def get_analysis_results(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the analysis results for a completed task.
    
    Returns detailed analysis results including issues found, suggestions,
    and summary statistics.
    """
    try:
        # Query task from database
        result = await db.execute(
            select(AnalysisTask).where(AnalysisTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} is not completed. Current status: {task.status.value}"
            )
        
        if not task.results:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for task {task_id}"
            )
        
        # Return structured results
        return AnalysisResults(
            task_id=task_id,
            status=task.status,
            repository=task.repo_url,
            pr_number=task.pr_number,
            files=task.results.get("files", []),
            summary=task.results.get("summary", {}),
            metadata=task.results.get("metadata", {}),
            created_at=task.created_at,
            completed_at=task.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve results: {str(e)}"
        )


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "running",
            "database": "connected",  # TODO: Add actual health checks
            "redis": "connected",
            "celery": "running"
        }
    }


def _get_current_stage(status: TaskStatus) -> str:
    """Get human-readable current stage description."""
    stage_map = {
        TaskStatus.PENDING: "Queued for processing",
        TaskStatus.PROCESSING: "Analyzing code",
        TaskStatus.COMPLETED: "Analysis complete",
        TaskStatus.FAILED: "Analysis failed"
    }
    return stage_map.get(status, "Unknown")


def _estimate_completion_time(task: AnalysisTask) -> str:
    """Estimate remaining completion time based on progress."""
    if not task.started_at or task.total_files == 0:
        return "Calculating..."
    
    elapsed = datetime.utcnow() - task.started_at
    if task.processed_files == 0:
        return "5-10 minutes"
    
    avg_time_per_file = elapsed.total_seconds() / task.processed_files
    remaining_files = task.total_files - task.processed_files
    estimated_seconds = remaining_files * avg_time_per_file
    
    if estimated_seconds < 60:
        return f"{int(estimated_seconds)} seconds"
    elif estimated_seconds < 3600:
        return f"{int(estimated_seconds / 60)} minutes"
    else:
        return f"{int(estimated_seconds / 3600)} hours"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )