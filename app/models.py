"""Database models for the PR Analyzer application."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTask(Base):
    """Model for storing analysis task information."""
    
    __tablename__ = "analysis_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    repo_url = Column(String(500), nullable=False)
    pr_number = Column(Integer, nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results and metadata
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    task_metadata = Column(JSON, nullable=True)
    
    # Progress tracking
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    current_file = Column(String(500), nullable=True)
    
    # Cost tracking
    api_calls_made = Column(Integer, default=0)
    api_calls_cached = Column(Integer, default=0)
    estimated_cost = Column(String(50), nullable=True)


class AnalysisResult(Base):
    """Model for storing detailed analysis results."""
    
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), index=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    analysis_type = Column(String(50), nullable=False)  # style, bug, security, performance
    
    # Issue details
    line_number = Column(Integer, nullable=True)
    issue_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    description = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=True)
    
    # Code context
    code_snippet = Column(Text, nullable=True)
    fixed_code = Column(Text, nullable=True)
    
    # Metadata
    confidence_score = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CacheEntry(Base):
    """Model for storing semantic cache entries."""
    
    __tablename__ = "cache_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    content_type = Column(String(50), nullable=False)  # function, class, file, project
    
    # Vector embedding data
    embedding_vector = Column(JSON, nullable=False)
    similarity_threshold = Column(String(10), nullable=False)
    
    # Cached analysis results
    analysis_results = Column(JSON, nullable=False)
    
    # Metadata
    language = Column(String(50), nullable=True)
    file_extension = Column(String(10), nullable=True)
    usage_count = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Performance metrics
    original_processing_time = Column(String(20), nullable=True)
    cache_hit_count = Column(Integer, default=0)