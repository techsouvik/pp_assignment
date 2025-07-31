"""Base agent class for all code analysis agents."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.schema import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisType(Enum):
    """Types of code analysis."""
    STYLE = "style"
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"


class IssueSeverity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CodeIssue:
    """Represents a code issue found during analysis."""
    type: str
    line: Optional[int]
    severity: IssueSeverity
    description: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    fixed_code: Optional[str] = None
    confidence_score: Optional[float] = None


@dataclass
class FileAnalysisResult:
    """Result of analyzing a single file."""
    file_path: str
    language: Optional[str]
    issues: List[CodeIssue]
    processing_time: float
    cached: bool = False
    
    def get_issue_summary(self) -> Dict[str, int]:
        """Get count of issues by severity."""
        summary = {severity.value: 0 for severity in IssueSeverity}
        for issue in self.issues:
            summary[issue.severity.value] += 1
        return summary


class BaseAgent(ABC):
    """Base class for all code analysis agents."""
    
    def __init__(self, analysis_type: AnalysisType):
        """Initialize the base agent."""
        self.analysis_type = analysis_type
        self.llm = self._create_llm()
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def _create_llm(self) -> ChatAnthropic:
        """Create Claude Sonnet 4 LLM instance."""
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
        return ChatAnthropic(
            model="claude-3-sonnet-20240229",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=4096,
            timeout=60
        )
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent type."""
        pass
    
    @abstractmethod
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template for this agent type."""
        pass
    
    @abstractmethod
    def parse_analysis_result(self, response: str, file_path: str) -> FileAnalysisResult:
        """Parse the LLM response into structured results."""
        pass
    
    def create_prompt_template(self) -> ChatPromptTemplate:
        """Create the prompt template for this agent."""
        return ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", self.get_analysis_prompt()),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
    
    async def analyze_file(
        self, 
        file_path: str, 
        file_content: str, 
        file_diff: Optional[str] = None,
        language: Optional[str] = None
    ) -> FileAnalysisResult:
        """
        Analyze a single file for issues.
        
        Args:
            file_path: Path to the file being analyzed
            file_content: Content of the file
            file_diff: Git diff for the file (optional)
            language: Programming language (optional)
            
        Returns:
            FileAnalysisResult with issues found
        """
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting {self.analysis_type.value} analysis for {file_path}")
            
            # Prepare analysis context
            analysis_context = {
                "file_path": file_path,
                "file_content": file_content,
                "file_diff": file_diff or "No diff available",
                "language": language or self._detect_language(file_path),
                "analysis_type": self.analysis_type.value
            }
            
            # Create prompt and invoke LLM
            prompt = self.get_analysis_prompt().format(**analysis_context)
            
            response = await self.llm.ainvoke([
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt}
            ])
            
            # Parse response into structured result
            result = self.parse_analysis_result(
                response.content, 
                file_path
            )
            
            result.processing_time = time.time() - start_time
            result.language = analysis_context["language"]
            
            self.logger.info(
                f"Completed {self.analysis_type.value} analysis for {file_path}: "
                f"{len(result.issues)} issues found in {result.processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze {file_path}: {e}")
            return FileAnalysisResult(
                file_path=file_path,
                language=language,
                issues=[],
                processing_time=time.time() - start_time
            )
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
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
            '.css': 'css',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml'
        }
        
        for ext, lang in extension_map.items():
            if file_path.lower().endswith(ext):
                return lang
        
        return 'unknown'
    
    def _parse_severity(self, severity_str: str) -> IssueSeverity:
        """Parse severity string into enum."""
        severity_map = {
            'critical': IssueSeverity.CRITICAL,
            'high': IssueSeverity.HIGH,
            'medium': IssueSeverity.MEDIUM,
            'low': IssueSeverity.LOW
        }
        return severity_map.get(severity_str.lower(), IssueSeverity.MEDIUM)