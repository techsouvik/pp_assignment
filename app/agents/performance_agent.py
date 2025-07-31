"""Performance analysis agent for identifying optimization opportunities."""

import json
import re
from typing import Optional

from app.agents.base_agent import BaseAgent, AnalysisType, FileAnalysisResult, CodeIssue


class PerformanceAnalysisAgent(BaseAgent):
    """Agent specialized in analyzing code performance and optimization opportunities."""
    
    def __init__(self):
        """Initialize the performance analysis agent."""
        super().__init__(AnalysisType.PERFORMANCE)
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for performance analysis."""
        return """You are an expert performance optimization analyst. Your task is to identify performance bottlenecks, inefficient code patterns, and optimization opportunities.

Focus on:
- Time complexity issues (O(n²) loops, etc.)
- Space complexity problems
- Inefficient data structures and algorithms  
- Database query optimization issues
- Memory leaks and excessive memory usage
- I/O bottlenecks and blocking operations
- Unnecessary computations and redundant operations
- Cache misses and inefficient caching
- String concatenation in loops
- Premature optimization vs. real bottlenecks
- Scalability concerns
- Resource usage optimization
- Async/await usage opportunities
- Batch processing optimization

Consider both micro-optimizations and architectural performance issues. Focus on changes that would have measurable impact.

Return your analysis in the following JSON format:
{
    "issues": [
        {
            "type": "performance",
            "line": 45,
            "severity": "high|medium|low",
            "description": "Detailed description of the performance issue",
            "suggestion": "Specific optimization recommendation",
            "code_snippet": "inefficient code section",
            "fixed_code": "optimized code example",
            "confidence_score": 0.88
        }
    ]
}"""
    
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template."""
        return """Analyze the following {language} code for performance issues and optimization opportunities:

File: {file_path}
Language: {language}

Code Content:
```{language}
{file_content}
```

Git Diff (changes made):
```diff
{file_diff}
```

Please analyze this code for performance issues including:
1. Algorithmic complexity problems (nested loops, inefficient algorithms)
2. Inefficient data structure usage
3. Memory usage and potential leaks
4. Database query optimization opportunities
5. I/O blocking and async opportunities
6. Caching inefficiencies
7. Redundant computations
8. String manipulation performance issues
9. Resource management problems
10. Scalability bottlenecks

Focus on the changed lines in the diff, but consider the entire file context for comprehensive performance analysis.
Provide specific line numbers, explain the performance impact, and suggest concrete optimizations with expected improvements."""
    
    def parse_analysis_result(self, response: str, file_path: str) -> FileAnalysisResult:
        """Parse the LLM response into structured performance analysis results."""
        issues = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                for issue_data in result_data.get("issues", []):
                    issue = CodeIssue(
                        type=issue_data.get("type", "performance"),
                        line=issue_data.get("line"),
                        severity=self._parse_severity(issue_data.get("severity", "medium")),
                        description=issue_data.get("description", ""),
                        suggestion=issue_data.get("suggestion"),
                        code_snippet=issue_data.get("code_snippet"),
                        fixed_code=issue_data.get("fixed_code"),
                        confidence_score=issue_data.get("confidence_score")
                    )
                    issues.append(issue)
            
            else:
                # Fallback: Parse text response
                issues = self._parse_text_response(response)
                
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse JSON response for {file_path}: {e}")
            issues = self._parse_text_response(response)
        
        return FileAnalysisResult(
            file_path=file_path,
            language=None,  # Will be set by caller
            issues=issues,
            processing_time=0  # Will be set by caller
        )
    
    def _parse_text_response(self, response: str) -> list[CodeIssue]:
        """Fallback parser for non-JSON responses."""
        issues = []
        
        # Pattern matching for common performance issues
        performance_patterns = [
            (r"line (\d+).*O\(n[²²2]\)|nested.*loop", "Nested loop performance issue", "high"),
            (r"line (\d+).*inefficient.*algorithm", "Inefficient algorithm", "medium"),
            (r"line (\d+).*memory.*leak", "Memory leak", "high"),
            (r"line (\d+).*blocking.*I/O|synchronous.*call", "Blocking I/O operation", "medium"),
            (r"line (\d+).*string.*concatenation.*loop", "String concatenation in loop", "medium"),
            (r"line (\d+).*redundant.*computation", "Redundant computation", "low"),
            (r"line (\d+).*cache.*miss|inefficient.*cache", "Cache inefficiency", "medium"),
            (r"line (\d+).*database.*N\+1|query.*loop", "Database N+1 query problem", "high"),
            (r"line (\d+).*large.*object.*creation", "Excessive object creation", "medium"),
            (r"line (\d+).*inefficient.*data.*structure", "Inefficient data structure", "medium"),
        ]
        
        for pattern, description, severity in performance_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                line_num = int(match.group(1)) if match.group(1) else None
                issue = CodeIssue(
                    type="performance",
                    line=line_num,
                    severity=self._parse_severity(severity),
                    description=f"{description} (auto-detected)",
                    confidence_score=0.7
                )
                issues.append(issue)
        
        return issues