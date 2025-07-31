"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyzeRequest(BaseModel):
    """Request model for PR analysis."""
    repo_url: HttpUrl = Field(..., description="GitHub repository URL")
    pr_number: int = Field(..., gt=0, description="Pull request number")
    github_token: Optional[str] = Field(None, description="Optional GitHub token for private repos")
    analysis_types: Optional[List[str]] = Field(
        default=["style", "bug", "security", "performance"],
        description="Types of analysis to perform"
    )
    priority: Optional[str] = Field(default="normal", description="Task priority (low, normal, high)")


class AnalyzeResponse(BaseModel):
    """Response model for PR analysis request."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    message: str = Field(..., description="Status message")
    estimated_completion_time: Optional[str] = Field(None, description="Estimated completion time")


class TaskStatusResponse(BaseModel):
    """Response model for task status check."""
    task_id: str
    status: TaskStatus
    progress: Dict[str, Any] = Field(default_factory=dict)
    current_file: Optional[str] = None
    processed_files: int = 0
    total_files: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    estimated_completion: Optional[str] = None
    error_message: Optional[str] = None


class IssueDetail(BaseModel):
    """Model for individual code issues."""
    type: str = Field(..., description="Issue type (style, bug, security, performance)")
    line: Optional[int] = Field(None, description="Line number where issue occurs")
    severity: str = Field(..., description="Issue severity (critical, high, medium, low)")
    description: str = Field(..., description="Detailed issue description")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    code_snippet: Optional[str] = Field(None, description="Relevant code snippet")
    fixed_code: Optional[str] = Field(None, description="Suggested code fix")
    confidence_score: Optional[float] = Field(None, description="AI confidence in the issue")


class FileAnalysis(BaseModel):
    """Model for file-level analysis results."""
    name: str = Field(..., description="File name/path")
    language: Optional[str] = Field(None, description="Programming language")
    issues: List[IssueDetail] = Field(default_factory=list, description="List of issues found")
    summary: Dict[str, int] = Field(default_factory=dict, description="Issue count by severity")


class AnalysisSummary(BaseModel):
    """Model for overall analysis summary."""
    total_files: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    analysis_duration: Optional[str] = None
    cost_savings: Optional[Dict[str, Any]] = None


class AnalysisResults(BaseModel):
    """Complete analysis results model."""
    task_id: str
    status: TaskStatus
    repository: str
    pr_number: int
    files: List[FileAnalysis] = Field(default_factory=list)
    summary: AnalysisSummary = Field(default_factory=AnalysisSummary)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    completed_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    task_id: Optional[str] = Field(None, description="Task ID if applicable")