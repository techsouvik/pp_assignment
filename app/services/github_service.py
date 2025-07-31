"""GitHub API integration service for fetching PR data and diffs."""

import base64
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from github import Github, GithubException

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FileChange:
    """Represents a changed file in a pull request."""
    filename: str
    status: str  # added, modified, removed, renamed
    additions: int
    deletions: int
    changes: int
    patch: Optional[str]  # Git diff patch
    content: Optional[str]  # File content
    previous_filename: Optional[str] = None  # For renamed files


@dataclass
class PullRequestData:
    """Contains all relevant data from a GitHub pull request."""
    number: int
    title: str
    description: str
    author: str
    base_branch: str
    head_branch: str
    state: str
    created_at: str
    updated_at: str
    files_changed: List[FileChange]
    total_additions: int
    total_deletions: int
    commits_count: int
    repository_url: str
    repository_name: str


class GitHubService:
    """Service for interacting with GitHub API to fetch PR data."""
    
    def __init__(self, github_token: Optional[str] = None):
        """Initialize GitHub service with optional token."""
        self.token = github_token or settings.github_token
        self.github = None
        
        if self.token:
            self.github = Github(self.token)
        else:
            # Use public API without authentication (rate limited)
            self.github = Github()
            logger.warning("No GitHub token provided, using public API with rate limits")
    
    def parse_github_url(self, repo_url: str) -> Tuple[str, str]:
        """
        Parse GitHub repository URL to extract owner and repo name.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Tuple of (owner, repo_name)
        """
        # Handle different URL formats
        if repo_url.startswith("https://github.com/"):
            path = urlparse(repo_url).path.strip("/")
            parts = path.split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        elif "/" in repo_url and not repo_url.startswith("http"):
            # Handle owner/repo format
            parts = repo_url.split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        
        raise ValueError(f"Invalid GitHub repository URL format: {repo_url}")
    
    async def get_pull_request_data(
        self, 
        repo_url: str, 
        pr_number: int
    ) -> PullRequestData:
        """
        Fetch comprehensive pull request data from GitHub.
        
        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number
            
        Returns:
            PullRequestData object with all PR information
        """
        try:
            owner, repo_name = self.parse_github_url(repo_url)
            logger.info(f"Fetching PR #{pr_number} from {owner}/{repo_name}")
            
            # Get repository and pull request
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            # Get changed files
            files_changed = []
            for file in pr.get_files():
                file_content = None
                
                # Fetch file content if it's not too large
                if file.status != "removed" and file.changes < 1000:
                    try:
                        file_content = self._get_file_content(repo, file.filename, pr.head.sha)
                    except Exception as e:
                        logger.warning(f"Failed to fetch content for {file.filename}: {e}")
                
                file_change = FileChange(
                    filename=file.filename,
                    status=file.status,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    patch=file.patch,
                    content=file_content,
                    previous_filename=getattr(file, 'previous_filename', None)
                )
                files_changed.append(file_change)
            
            # Create PR data object
            pr_data = PullRequestData(
                number=pr.number,
                title=pr.title,
                description=pr.body or "",
                author=pr.user.login,
                base_branch=pr.base.ref,
                head_branch=pr.head.ref,
                state=pr.state,
                created_at=pr.created_at.isoformat(),
                updated_at=pr.updated_at.isoformat(),
                files_changed=files_changed,
                total_additions=pr.additions,
                total_deletions=pr.deletions,
                commits_count=pr.commits,
                repository_url=repo_url,
                repository_name=f"{owner}/{repo_name}"
            )
            
            logger.info(
                f"Successfully fetched PR data: {len(files_changed)} files changed, "
                f"{pr.additions} additions, {pr.deletions} deletions"
            )
            
            return pr_data
            
        except GithubException as e:
            logger.error(f"GitHub API error fetching PR #{pr_number}: {e}")
            raise ValueError(f"Failed to fetch PR from GitHub: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching PR #{pr_number}: {e}")
            raise
    
    def _get_file_content(self, repo, file_path: str, sha: str) -> str:
        """
        Get the content of a file at a specific commit.
        
        Args:
            repo: GitHub repository object
            file_path: Path to the file
            sha: Commit SHA
            
        Returns:
            File content as string
        """
        try:
            file_content = repo.get_contents(file_path, ref=sha)
            
            if file_content.encoding == "base64":
                content = base64.b64decode(file_content.content).decode('utf-8')
            else:
                content = file_content.content
                
            return content
            
        except GithubException as e:
            if e.status == 404:
                logger.warning(f"File {file_path} not found at commit {sha}")
                return ""
            raise
    
    def get_supported_languages(self) -> List[str]:
        """Get list of programming languages supported for analysis."""
        return [
            "python", "javascript", "typescript", "java", "cpp", "c",
            "csharp", "go", "rust", "php", "ruby", "swift", "kotlin",
            "scala", "bash", "sql", "html", "css", "json", "yaml"
        ]
    
    def is_analyzable_file(self, filename: str) -> bool:
        """Check if a file should be analyzed based on its extension."""
        analyzable_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.cc', 
            '.cxx', '.c', '.cs', '.go', '.rs', '.php', '.rb', '.swift',
            '.kt', '.scala', '.sh', '.bash', '.sql', '.html', '.css',
            '.json', '.yaml', '.yml'
        }
        
        return any(filename.lower().endswith(ext) for ext in analyzable_extensions)
    
    def filter_analyzable_files(self, files: List[FileChange]) -> List[FileChange]:
        """Filter files to only include those that should be analyzed."""
        return [
            file for file in files 
            if file.status != "removed" and self.is_analyzable_file(file.filename)
        ]
    
    async def health_check(self) -> Dict[str, any]:
        """Check GitHub API connectivity and rate limits."""
        try:
            rate_limit = self.github.get_rate_limit()
            user = self.github.get_user() if self.token else None
            
            return {
                "status": "healthy",
                "authenticated": bool(self.token),
                "user": user.login if user else "anonymous",
                "rate_limit": {
                    "remaining": rate_limit.core.remaining,
                    "limit": rate_limit.core.limit,
                    "reset_time": rate_limit.core.reset.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"GitHub health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }