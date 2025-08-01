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
        """Create Claude 3.5 Sonnet LLM instance optimized for comprehensive code analysis."""
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
        return ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=8192,  # Increased for comprehensive analysis
            timeout=120  # Increased timeout for thorough analysis
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
        Perform comprehensive analysis of a single file.
        
        Args:
            file_path: Path to the file being analyzed
            file_content: Complete content of the file
            file_diff: Git diff for the file (optional)
            language: Programming language (optional)
            
        Returns:
            FileAnalysisResult with comprehensive issues found
        """
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting comprehensive {self.analysis_type.value} analysis for {file_path}")
            
            # Detect programming language
            detected_language = language or self._detect_language(file_path)
            
            # Prepare comprehensive analysis context
            analysis_context = {
                "file_path": file_path,
                "file_content": file_content,
                "file_diff": file_diff or "No recent changes available - analyzing complete file",
                "language": detected_language,
                "analysis_type": self.analysis_type.value,
                "file_size": len(file_content),
                "line_count": len(file_content.splitlines()) if file_content else 0
            }
            
            # Add additional context for better analysis
            context_info = self._build_analysis_context(file_content, detected_language)
            analysis_context.update(context_info)
            
            # Create comprehensive prompt
            prompt = self.get_analysis_prompt().format(**analysis_context)
            
            self.logger.debug(f"Invoking LLM for {self.analysis_type.value} analysis of {file_path}")
            
            # Invoke LLM with comprehensive context
            response = await self.llm.ainvoke([
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt}
            ])
            
            # Parse response into structured result
            result = self.parse_analysis_result(
                response.content, 
                file_path
            )
            
            # Enrich result with metadata
            result.processing_time = time.time() - start_time
            result.language = detected_language
            
            # Log comprehensive results
            issue_summary = result.get_issue_summary()
            self.logger.info(
                f"Completed {self.analysis_type.value} analysis for {file_path}: "
                f"{len(result.issues)} total issues found "
                f"(Critical: {issue_summary.get('critical', 0)}, "
                f"High: {issue_summary.get('high', 0)}, "
                f"Medium: {issue_summary.get('medium', 0)}, "
                f"Low: {issue_summary.get('low', 0)}) "
                f"in {result.processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze {file_path}: {e}", exc_info=True)
            return FileAnalysisResult(
                file_path=file_path,
                language=language or self._detect_language(file_path),
                issues=[],
                processing_time=time.time() - start_time
            )
    
    def _build_analysis_context(self, file_content: str, language: str) -> dict:
        """Build additional context information for comprehensive analysis."""
        context = {}
        
        if not file_content:
            return context
            
        lines = file_content.splitlines()
        
        # Basic file statistics
        context["total_lines"] = len(lines)
        context["non_empty_lines"] = len([line for line in lines if line.strip()])
        context["comment_lines"] = self._count_comment_lines(lines, language)
        
        # Code complexity indicators
        context["function_count"] = self._count_functions(file_content, language)
        context["class_count"] = self._count_classes(file_content, language)
        context["import_count"] = self._count_imports(file_content, language)
        
        # Identify potential complexity areas
        context["nested_blocks"] = self._estimate_nesting_depth(lines)
        context["long_lines"] = len([line for line in lines if len(line) > 120])
        
        return context
    
    def _count_comment_lines(self, lines: list, language: str) -> int:
        """Count comment lines based on language."""
        comment_patterns = {
            'python': ['#'],
            'javascript': ['//', '/*', '*'],
            'typescript': ['//', '/*', '*'],
            'java': ['//', '/*', '*'],
            'cpp': ['//', '/*', '*'],
            'c': ['//', '/*', '*'],
            'csharp': ['//', '/*', '*'],
            'go': ['//', '/*', '*'],
            'rust': ['//', '/*', '*'],
            'php': ['//', '/*', '*', '#'],
            'ruby': ['#'],
            'swift': ['//', '/*', '*'],
            'kotlin': ['//', '/*', '*'],
            'scala': ['//', '/*', '*'],
        }
        
        patterns = comment_patterns.get(language, ['#', '//', '/*', '*'])
        count = 0
        
        for line in lines:
            stripped = line.strip()
            if any(stripped.startswith(pattern) for pattern in patterns):
                count += 1
                
        return count
    
    def _count_functions(self, content: str, language: str) -> int:
        """Estimate function count based on language patterns."""
        import re
        
        function_patterns = {
            'python': [r'^\s*def\s+\w+', r'^\s*async\s+def\s+\w+'],
            'javascript': [r'function\s+\w+', r'^\s*\w+\s*:\s*function', r'^\s*\w+\s*=>\s*'],
            'typescript': [r'function\s+\w+', r'^\s*\w+\s*:\s*function', r'^\s*\w+\s*=>\s*'],
            'java': [r'^\s*(public|private|protected).*\s+\w+\s*\('],
            'cpp': [r'^\s*\w+.*\s+\w+\s*\('],
            'c': [r'^\s*\w+.*\s+\w+\s*\('],
        }
        
        patterns = function_patterns.get(language, [r'function', r'def\s+'])
        count = 0
        
        for pattern in patterns:
            count += len(re.findall(pattern, content, re.MULTILINE | re.IGNORECASE))
            
        return count
    
    def _count_classes(self, content: str, language: str) -> int:
        """Estimate class count based on language patterns."""
        import re
        
        class_patterns = {
            'python': [r'^\s*class\s+\w+'],
            'javascript': [r'^\s*class\s+\w+'],
            'typescript': [r'^\s*class\s+\w+', r'^\s*interface\s+\w+'],
            'java': [r'^\s*(public|private|protected)?\s*class\s+\w+'],
            'cpp': [r'^\s*class\s+\w+'],
            'csharp': [r'^\s*(public|private|protected)?\s*class\s+\w+'],
        }
        
        patterns = class_patterns.get(language, [r'class\s+\w+'])
        count = 0
        
        for pattern in patterns:
            count += len(re.findall(pattern, content, re.MULTILINE | re.IGNORECASE))
            
        return count
    
    def _count_imports(self, content: str, language: str) -> int:
        """Count import statements based on language."""
        import re
        
        import_patterns = {
            'python': [r'^\s*import\s+', r'^\s*from\s+.*\s+import'],
            'javascript': [r'^\s*import\s+', r'^\s*require\s*\('],
            'typescript': [r'^\s*import\s+', r'^\s*require\s*\('],
            'java': [r'^\s*import\s+'],
            'cpp': [r'^\s*#include'],
            'c': [r'^\s*#include'],
        }
        
        patterns = import_patterns.get(language, [r'import', r'include'])
        count = 0
        
        for pattern in patterns:
            count += len(re.findall(pattern, content, re.MULTILINE | re.IGNORECASE))
            
        return count
    
    def _estimate_nesting_depth(self, lines: list) -> int:
        """Estimate maximum nesting depth."""
        max_depth = 0
        current_depth = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            # Count opening braces/blocks
            current_depth += line.count('{')
            current_depth += line.count('(')
            
            # Simple indentation-based estimation
            indent_level = len(line) - len(line.lstrip())
            estimated_depth = indent_level // 4  # Assuming 4-space indentation
            
            max_depth = max(max_depth, max(current_depth, estimated_depth))
            
            # Count closing braces/blocks
            current_depth -= line.count('}')
            current_depth -= line.count(')')
            current_depth = max(0, current_depth)
            
        return max_depth
    
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