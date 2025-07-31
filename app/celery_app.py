"""Celery application configuration and task definitions."""

from celery import Celery
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.config import settings
from app.utils.logging import get_logger
from app.agents.coordinator import AnalysisCoordinator

logger = get_logger(__name__)

# Initialize Celery app
celery_app = Celery(
    "pr_analyzer",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.celery_app"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
)


@celery_app.task(bind=True, name="analyze_pr_task")
def analyze_pr_task(
    self,
    task_id: str,
    repo_url: str,
    pr_number: int,
    github_token: Optional[str] = None,
    analysis_types: List[str] = None
) -> Dict[str, Any]:
    """
    Main Celery task for analyzing a GitHub pull request.
    
    This task coordinates the entire analysis pipeline:
    1. Fetch PR data and changed files from GitHub
    2. Run different types of analysis (style, bugs, security, performance)
    3. Aggregate results and store in database
    4. Update task status and progress
    """
    if analysis_types is None:
        analysis_types = ["style", "bug", "security", "performance"]
    
    logger.info(f"Starting PR analysis task {task_id} for {repo_url}/pull/{pr_number}")
    
    try:
        # Update task status to processing
        _update_task_status(task_id, "processing", started_at=datetime.utcnow())
        
        # Create analysis coordinator
        coordinator = AnalysisCoordinator(github_token)
        
        # Define progress callback
        async def progress_callback(**kwargs):
            """Update task progress in database."""
            _update_task_status(
                task_id,
                kwargs.get("status", "processing"),
                current_file=kwargs.get("current_file"),
                processed_files=kwargs.get("processed_files"),
                total_files=kwargs.get("total_files")
            )
        
        # Run analysis using asyncio
        import asyncio
        results = asyncio.run(
            coordinator.analyze_pull_request(
                repo_url=repo_url,
                pr_number=pr_number,
                analysis_types=analysis_types,
                progress_callback=progress_callback
            )
        )
        
        # Update task as completed
        _update_task_status(
            task_id, 
            "completed", 
            results=results,
            completed_at=datetime.utcnow()
        )
        
        logger.info(f"Completed PR analysis task {task_id}")
        return results
        
    except Exception as exc:
        logger.error(f"PR analysis task {task_id} failed: {exc}")
        
        # Update task as failed
        _update_task_status(
            task_id,
            "failed",
            error_message=str(exc),
            completed_at=datetime.utcnow()
        )
        
        # Re-raise exception for Celery to handle
        self.retry(exc=exc, countdown=60, max_retries=3)


def _update_task_status(
    task_id: str,
    status: str,
    results: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    current_file: Optional[str] = None,
    processed_files: Optional[int] = None,
    total_files: Optional[int] = None
):
    """Update task status in database."""
    try:
        from app.database import get_db_session
        from app.models import AnalysisTask
        
        with get_db_session() as db:
            task = db.query(AnalysisTask).filter(
                AnalysisTask.task_id == task_id
            ).first()
            
            if task:
                task.status = status
                task.updated_at = datetime.utcnow()
                
                if results is not None:
                    task.results = results
                if error_message is not None:
                    task.error_message = error_message
                if started_at is not None:
                    task.started_at = started_at
                if completed_at is not None:
                    task.completed_at = completed_at
                if current_file is not None:
                    task.current_file = current_file
                if processed_files is not None:
                    task.processed_files = processed_files
                if total_files is not None:
                    task.total_files = total_files
                
                db.commit()
                logger.info(f"Updated task {task_id} status to {status}")
            else:
                logger.warning(f"Task {task_id} not found in database")
                
    except Exception as e:
        logger.error(f"Failed to update task {task_id} status: {e}")


@celery_app.task(name="health_check_task")
def health_check_task() -> Dict[str, Any]:
    """Health check task for monitoring Celery worker status."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "worker_id": health_check_task.request.hostname,
        "task_id": health_check_task.request.id
    }