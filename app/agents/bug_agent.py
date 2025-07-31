"""Bug detection agent for identifying potential code issues."""

import json
import re
from typing import Optional

from app.agents.base_agent import BaseAgent, AnalysisType, FileAnalysisResult, CodeIssue


class BugDetectionAgent(BaseAgent):
    """Agent specialized in detecting potential bugs and logic errors."""
    
    def __init__(self):
        """Initialize the bug detection agent."""
        super().__init__(AnalysisType.BUG)
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for bug detection."""
        return """You are an expert bug detection and static analysis tool. Your task is to identify potential bugs, logic errors, and problematic code patterns.

Focus on:
- Null pointer/reference exceptions
- Array/list index out of bounds
- Unhandled exceptions and error conditions
- Logic errors and incorrect conditionals
- Resource leaks (file handles, database connections, etc.)
- Race conditions and thread safety issues
- Infinite loops and recursion issues
- Type mismatches and conversion errors
- Dead code and unreachable statements
- Missing error handling
- Incorrect API usage

Analyze the code carefully and provide specific evidence for each potential bug. Consider edge cases and error conditions.

Return your analysis in the following JSON format:
{
    "issues": [
        {
            "type": "bug",
            "line": 42,
            "severity": "critical|high|medium|low",
            "description": "Detailed description of the potential bug",
            "suggestion": "How to fix the issue",
            "code_snippet": "problematic code section",
            "fixed_code": "corrected code example",
            "confidence_score": 0.90
        }
    ]
}"""
    
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template."""
        return """Analyze the following {language} code for potential bugs and logic errors:

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

Please analyze this code for potential bugs including:
1. Null/undefined reference errors
2. Array/list boundary issues
3. Exception handling problems
4. Logic errors in conditionals and loops
5. Resource management issues
6. Concurrency and thread safety problems
7. Type-related errors
8. API misuse and incorrect method calls

Pay special attention to the changed lines in the diff, but consider the entire file context for comprehensive bug detection.
Provide specific line numbers, explain the potential impact, and suggest concrete fixes."""
    
    def parse_analysis_result(self, response: str, file_path: str) -> FileAnalysisResult:
        """Parse the LLM response into structured bug analysis results."""
        issues = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                for issue_data in result_data.get("issues", []):
                    issue = CodeIssue(
                        type=issue_data.get("type", "bug"),
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
        
        # Pattern matching for common bug indicators
        bug_patterns = [
            (r"line (\d+).*null.*pointer", "Potential null pointer exception", "high"),
            (r"line (\d+).*index.*bound", "Array index out of bounds", "high"),
            (r"line (\d+).*exception.*unhandled", "Unhandled exception", "medium"),
            (r"line (\d+).*infinite.*loop", "Potential infinite loop", "critical"),
            (r"line (\d+).*resource.*leak", "Resource leak", "high"),
            (r"line (\d+).*race.*condition", "Race condition", "high"),
            (r"line (\d+).*dead.*code", "Dead code detected", "medium"),
        ]
        
        for pattern, description, severity in bug_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                line_num = int(match.group(1)) if match.group(1) else None
                issue = CodeIssue(
                    type="bug",
                    line=line_num,
                    severity=self._parse_severity(severity),
                    description=f"{description} (auto-detected)",
                    confidence_score=0.75
                )
                issues.append(issue)
        
        return issues