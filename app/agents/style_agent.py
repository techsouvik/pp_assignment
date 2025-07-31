"""Style analysis agent for code formatting and conventions."""

import json
import re
from typing import Optional

from app.agents.base_agent import BaseAgent, AnalysisType, FileAnalysisResult, CodeIssue


class StyleAnalysisAgent(BaseAgent):
    """Agent specialized in analyzing code style and formatting issues."""
    
    def __init__(self):
        """Initialize the style analysis agent."""
        super().__init__(AnalysisType.STYLE)
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for style analysis."""
        return """You are an expert code style and formatting analyzer. Your task is to identify style issues, formatting problems, and naming convention violations in code.

Focus on:
- Line length violations
- Indentation inconsistencies  
- Naming convention issues (camelCase, snake_case, PascalCase)
- Missing or excessive whitespace
- Comment style and placement
- Import organization
- Code organization and structure
- Language-specific style guide violations (PEP8 for Python, etc.)

Provide specific, actionable suggestions for each issue found. Be precise about line numbers and include code snippets where helpful.

Return your analysis in the following JSON format:
{
    "issues": [
        {
            "type": "style",
            "line": 15,
            "severity": "medium|low",
            "description": "Detailed description of the style issue",
            "suggestion": "Specific fix suggestion",
            "code_snippet": "problematic code",
            "fixed_code": "corrected code (optional)",
            "confidence_score": 0.85
        }
    ]
}"""
    
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template."""
        return """Analyze the following {language} code for style and formatting issues:

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

Please analyze this code for style issues including:
1. Line length violations
2. Indentation problems
3. Naming convention issues
4. Whitespace issues
5. Comment style problems
6. Import organization
7. Language-specific style guide violations

Focus especially on the changed lines in the diff, but consider the entire file context.
Provide specific line numbers and actionable suggestions."""
    
    def parse_analysis_result(self, response: str, file_path: str) -> FileAnalysisResult:
        """Parse the LLM response into structured style analysis results."""
        issues = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                for issue_data in result_data.get("issues", []):
                    issue = CodeIssue(
                        type=issue_data.get("type", "style"),
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
        
        # Simple pattern matching for common style issues
        patterns = [
            (r"line (\d+).*too long", "Line length violation", "medium"),
            (r"line (\d+).*indentation", "Indentation issue", "low"),
            (r"line (\d+).*naming", "Naming convention violation", "medium"),
            (r"line (\d+).*whitespace", "Whitespace issue", "low"),
        ]
        
        for pattern, description, severity in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                line_num = int(match.group(1)) if match.group(1) else None
                issue = CodeIssue(
                    type="style",
                    line=line_num,
                    severity=self._parse_severity(severity),
                    description=f"{description} (auto-detected)",
                    confidence_score=0.7
                )
                issues.append(issue)
        
        return issues