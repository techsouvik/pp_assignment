"""Agent coordinator for orchestrating multiple analysis agents."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.agents.base_agent import FileAnalysisResult, AnalysisType
from app.agents.style_agent import StyleAnalysisAgent
from app.agents.bug_agent import BugDetectionAgent
from app.agents.security_agent import SecurityAnalysisAgent
from app.agents.performance_agent import PerformanceAnalysisAgent
from app.services.github_service import GitHubService, PullRequestData, FileChange
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisCoordinator:
    """Coordinates multiple AI agents for comprehensive code analysis."""
    
    def __init__(self, github_token: Optional[str] = None):
        """Initialize the analysis coordinator."""
        self.github_service = GitHubService(github_token)
        self.agents = {
            AnalysisType.STYLE: StyleAnalysisAgent(),
            AnalysisType.BUG: BugDetectionAgent(),
            AnalysisType.SECURITY: SecurityAnalysisAgent(),
            AnalysisType.PERFORMANCE: PerformanceAnalysisAgent()
        }
        self.logger = get_logger(__name__)
    
    async def analyze_pull_request(
        self,
        repo_url: str,
        pr_number: int,
        analysis_types: List[str],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a GitHub pull request.
        
        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number
            analysis_types: List of analysis types to perform
            progress_callback: Optional callback for progress updates
            
        Returns:
            Comprehensive analysis results
        """
        try:
            self.logger.info(f"Starting PR analysis for {repo_url}/pull/{pr_number}")
            
            # Fetch PR data from GitHub
            pr_data = await self.github_service.get_pull_request_data(repo_url, pr_number)
            
            # Filter files that can be analyzed
            analyzable_files = self.github_service.filter_analyzable_files(pr_data.files_changed)
            
            if not analyzable_files:
                self.logger.warning("No analyzable files found in PR")
                return self._create_empty_result(pr_data, "No analyzable files found")
            
            # Update progress
            if progress_callback:
                await progress_callback(
                    total_files=len(analyzable_files),
                    processed_files=0,
                    current_file=None,
                    status="processing"
                )
            
            # Analyze each file with selected agents
            file_results = []
            processed_count = 0
            
            for file_change in analyzable_files:
                if not file_change.content:
                    self.logger.warning(f"Skipping {file_change.filename}: no content available")
                    continue
                
                # Update progress
                if progress_callback:
                    await progress_callback(
                        current_file=file_change.filename,
                        processed_files=processed_count
                    )
                
                # Analyze file with all requested agents
                file_result = await self._analyze_file(
                    file_change, 
                    analysis_types
                )
                
                if file_result:
                    file_results.append(file_result)
                
                processed_count += 1
            
            # Generate comprehensive results
            results = self._aggregate_results(pr_data, file_results, analysis_types)
            
            # Final progress update
            if progress_callback:
                await progress_callback(
                    processed_files=processed_count,
                    status="completed"
                )
            
            self.logger.info(f"Completed PR analysis: {len(file_results)} files analyzed")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to analyze PR: {e}")
            raise
    
    async def _analyze_file(
        self,
        file_change: FileChange,
        analysis_types: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Analyze a single file with multiple agents."""
        try:
            self.logger.info(f"Analyzing file: {file_change.filename}")
            
            # Run analyses in parallel for each requested type
            tasks = []
            for analysis_type_str in analysis_types:
                try:
                    analysis_type = AnalysisType(analysis_type_str)
                    if analysis_type in self.agents:
                        agent = self.agents[analysis_type]
                        task = agent.analyze_file(
                            file_path=file_change.filename,
                            file_content=file_change.content,
                            file_diff=file_change.patch,
                            language=self.github_service.github._detect_language(file_change.filename) if hasattr(self.github_service.github, '_detect_language') else None
                        )
                        tasks.append((analysis_type_str, task))
                except ValueError:
                    self.logger.warning(f"Unknown analysis type: {analysis_type_str}")
            
            if not tasks:
                return None
            
            # Execute all analysis tasks concurrently
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Combine results from all agents
            all_issues = []
            analysis_metadata = {}
            
            for (analysis_type_str, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    self.logger.error(f"Analysis failed for {file_change.filename} ({analysis_type_str}): {result}")
                    continue
                
                if isinstance(result, FileAnalysisResult):
                    all_issues.extend(result.issues)
                    analysis_metadata[analysis_type_str] = {
                        "processing_time": result.processing_time,
                        "issues_found": len(result.issues),
                        "cached": result.cached
                    }
            
            return {
                "name": file_change.filename,
                "language": self._detect_language(file_change.filename),
                "status": file_change.status,
                "additions": file_change.additions,
                "deletions": file_change.deletions,
                "issues": [self._issue_to_dict(issue) for issue in all_issues],
                "summary": self._calculate_file_summary(all_issues),
                "metadata": analysis_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_change.filename}: {e}")
            return None
    
    def _issue_to_dict(self, issue) -> Dict[str, Any]:
        """Convert CodeIssue to dictionary format."""
        return {
            "type": issue.type,
            "line": issue.line,
            "severity": issue.severity.value,
            "description": issue.description,
            "suggestion": issue.suggestion,
            "code_snippet": issue.code_snippet,
            "fixed_code": issue.fixed_code,
            "confidence_score": issue.confidence_score
        }
    
    def _calculate_file_summary(self, issues: List) -> Dict[str, int]:
        """Calculate summary statistics for a file's issues."""
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
            if severity in summary:
                summary[severity] += 1
        return summary
    
    def _aggregate_results(
        self,
        pr_data: PullRequestData,
        file_results: List[Dict[str, Any]],
        analysis_types: List[str]
    ) -> Dict[str, Any]:
        """Aggregate results from all file analyses."""
        
        # Calculate overall summary
        total_issues = 0
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for file_result in file_results:
            file_summary = file_result.get("summary", {})
            for severity, count in file_summary.items():
                if severity in severity_counts:
                    severity_counts[severity] += count
                    total_issues += count
        
        # Calculate performance metrics
        total_processing_time = 0
        total_api_calls = 0
        cached_calls = 0
        
        for file_result in file_results:
            metadata = file_result.get("metadata", {})
            for analysis_type, stats in metadata.items():
                total_processing_time += stats.get("processing_time", 0)
                if stats.get("cached", False):
                    cached_calls += 1
                else:
                    total_api_calls += 1
        
        return {
            "files": file_results,
            "summary": {
                "total_files": len(file_results),
                "total_issues": total_issues,
                "critical_issues": severity_counts["critical"],
                "high_issues": severity_counts["high"],
                "medium_issues": severity_counts["medium"],
                "low_issues": severity_counts["low"],
                "analysis_duration": f"{total_processing_time:.2f}s",
                "cost_savings": {
                    "api_calls_made": total_api_calls,
                    "api_calls_cached": cached_calls,
                    "cache_hit_rate": f"{(cached_calls / max(total_api_calls + cached_calls, 1)) * 100:.1f}%"
                }
            },
            "metadata": {
                "repository": pr_data.repository_name,
                "pr_number": pr_data.number,
                "pr_title": pr_data.title,
                "pr_author": pr_data.author,
                "analysis_types": analysis_types,
                "total_file_changes": len(pr_data.files_changed),
                "analyzable_files": len(file_results),
                "pr_stats": {
                    "additions": pr_data.total_additions,
                    "deletions": pr_data.total_deletions,
                    "commits": pr_data.commits_count
                },
                "processed_at": datetime.utcnow().isoformat()
            }
        }
    
    def _create_empty_result(self, pr_data: PullRequestData, reason: str) -> Dict[str, Any]:
        """Create empty result structure when no analysis is possible."""
        return {
            "files": [],
            "summary": {
                "total_files": 0,
                "total_issues": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
                "analysis_duration": "0s",
                "message": reason
            },
            "metadata": {
                "repository": pr_data.repository_name,
                "pr_number": pr_data.number,
                "pr_title": pr_data.title,
                "processed_at": datetime.utcnow().isoformat()
            }
        }
    
    def _detect_language(self, filename: str) -> Optional[str]:
        """Detect programming language from filename."""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sh': 'bash',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css'
        }
        
        for ext, lang in extension_map.items():
            if filename.lower().endswith(ext):
                return lang
        
        return None