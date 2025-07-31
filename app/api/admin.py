"""Admin API endpoints for system monitoring and management."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.services.vector_cache import vector_cache
from app.utils.redis_client import redis_client
from app.services.github_service import GitHubService
from app.database import get_db, AsyncSession
from sqlalchemy import select, func
from app.models import AnalysisTask, TaskStatus

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health")
async def detailed_health_check():
    """Comprehensive health check for all system components."""
    health_status = {
        "api": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "components": {}
    }
    
    # Check Redis
    try:
        redis_healthy = redis_client.ping()
        health_status["components"]["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "response_time": "< 1ms"
        }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check GitHub API
    try:
        github_service = GitHubService()
        github_health = await github_service.health_check()
        health_status["components"]["github"] = github_health
    except Exception as e:
        health_status["components"]["github"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check Vector Cache
    try:
        cache_stats = vector_cache.get_cache_statistics()
        health_status["components"]["vector_cache"] = {
            "status": "healthy",
            "total_entries": cache_stats.get("total_entries", 0),
            "hit_rate": cache_stats.get("hit_rate", "0%")
        }
    except Exception as e:
        health_status["components"]["vector_cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Determine overall status
    component_statuses = [
        comp.get("status", "unhealthy") 
        for comp in health_status["components"].values()
    ]
    
    if all(status == "healthy" for status in component_statuses):
        health_status["status"] = "healthy"
    elif any(status == "healthy" for status in component_statuses):
        health_status["status"] = "degraded"
    else:
        health_status["status"] = "unhealthy"
    
    return health_status


@router.get("/cache/stats")
async def get_cache_statistics():
    """Get vector cache usage statistics."""
    try:
        return vector_cache.get_cache_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {e}")


@router.post("/cache/cleanup")
async def cleanup_cache(days_old: int = 30):
    """Clean up old cache entries."""
    try:
        removed_count = vector_cache.cleanup_old_entries(days_old)
        return {
            "message": f"Successfully cleaned up {removed_count} old cache entries",
            "removed_entries": removed_count,
            "days_threshold": days_old
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup cache: {e}")


@router.get("/tasks/stats")
async def get_task_statistics(db: AsyncSession = Depends(get_db)):
    """Get analysis task statistics."""
    try:
        # Count tasks by status
        status_counts = {}
        for status in TaskStatus:
            result = await db.execute(
                select(func.count(AnalysisTask.id)).where(
                    AnalysisTask.status == status
                )
            )
            status_counts[status.value] = result.scalar()
        
        # Get recent task metrics
        recent_tasks_result = await db.execute(
            select(AnalysisTask).order_by(AnalysisTask.created_at.desc()).limit(10)
        )
        recent_tasks = recent_tasks_result.scalars().all()
        
        # Calculate average processing time for completed tasks
        completed_tasks_result = await db.execute(
            select(AnalysisTask).where(
                AnalysisTask.status == TaskStatus.COMPLETED,
                AnalysisTask.started_at.isnot(None),
                AnalysisTask.completed_at.isnot(None)
            ).limit(50)
        )
        completed_tasks = completed_tasks_result.scalars().all()
        
        avg_processing_time = 0
        if completed_tasks:
            total_time = sum(
                (task.completed_at - task.started_at).total_seconds()
                for task in completed_tasks
                if task.started_at and task.completed_at
            )
            avg_processing_time = total_time / len(completed_tasks)
        
        return {
            "status_counts": status_counts,
            "total_tasks": sum(status_counts.values()),
            "recent_tasks": [
                {
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "repo_url": task.repo_url,
                    "pr_number": task.pr_number,
                    "created_at": task.created_at.isoformat(),
                    "processing_time": (
                        (task.completed_at - task.started_at).total_seconds()
                        if task.started_at and task.completed_at
                        else None
                    )
                }
                for task in recent_tasks
            ],
            "metrics": {
                "average_processing_time_seconds": round(avg_processing_time, 2),
                "average_processing_time_minutes": round(avg_processing_time / 60, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task stats: {e}")


@router.get("/system/info")
async def get_system_info():
    """Get system information and configuration."""
    return {
        "version": "1.0.0",
        "environment": "development",  # This could be set from env var
        "features": {
            "vector_caching": bool(vector_cache.openai_client),
            "github_integration": True,
            "multiple_analysis_types": True,
            "async_processing": True
        },
        "configuration": {
            "embedding_model": vector_cache.embedding_model,
            "vector_dimension": vector_cache.vector_dimension,
            "similarity_threshold": vector_cache.similarity_threshold,
            "supported_languages": [
                "python", "javascript", "typescript", "java", "cpp", "c",
                "csharp", "go", "rust", "php", "ruby", "swift", "kotlin"
            ]
        }
    }