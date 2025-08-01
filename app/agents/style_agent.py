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
        return """You are an expert code style and formatting analyzer with deep knowledge of coding standards and best practices. Your task is to perform comprehensive style analysis, going beyond basic formatting to identify maintainability and readability issues.

COMPREHENSIVE ANALYSIS AREAS:

1. FORMATTING & STRUCTURE:
- Line length violations and proper line breaking
- Indentation inconsistencies and alignment issues
- Whitespace problems (trailing, excessive, missing)
- Bracket and parentheses placement
- Code block organization and logical grouping

2. NAMING CONVENTIONS:
- Variable, function, class, and constant naming
- Language-specific conventions (PEP8, camelCase, etc.)
- Meaningful and descriptive names
- Consistency across the codebase
- Abbreviation and acronym usage

3. CODE ORGANIZATION:
- Import statement organization and grouping
- Function and class ordering
- Code duplication and repetition
- Logical flow and structure
- Separation of concerns

4. DOCUMENTATION & COMMENTS:
- Missing or inadequate docstrings
- Comment placement and style
- Inline comment quality
- Documentation consistency
- Over-commenting or under-commenting

5. LANGUAGE-SPECIFIC STANDARDS:
- PEP8 compliance for Python
- JavaScript/TypeScript style guides
- Java coding conventions
- C++ best practices
- Framework-specific patterns

6. MAINTAINABILITY ISSUES:
- Complex expressions that should be simplified
- Magic numbers and hardcoded values
- Long parameter lists
- Deeply nested code structures
- Code that's hard to read or understand

ANALYSIS APPROACH:
- Examine the ENTIRE file content, not just diffs
- Look for patterns and consistency issues
- Consider the broader context and codebase conventions
- Provide specific, actionable improvements
- Focus on issues that impact code maintainability and readability
- Be thorough but practical in your recommendations

Return your analysis in the following JSON format:
{
    "issues": [
        {
            "type": "style",
            "line": 15,
            "severity": "high|medium|low",
            "description": "Detailed description of the style issue and its impact",
            "suggestion": "Specific fix suggestion with reasoning",
            "code_snippet": "problematic code section",
            "fixed_code": "corrected code example",
            "confidence_score": 0.85
        }
    ]
}"""
    
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template."""
        return """Perform a COMPREHENSIVE style analysis of the following {language} code:

File: {file_path}
Language: {language}

FULL CODE CONTENT:
```{language}
{file_content}
```

RECENT CHANGES (Git Diff):
```diff
{file_diff}
```

ANALYSIS INSTRUCTIONS:
Analyze the ENTIRE file thoroughly, not just the diff. While paying attention to recent changes, examine the complete codebase for:

1. FORMATTING ISSUES:
   - Line length violations (>80-120 chars depending on language)
   - Inconsistent indentation or mixed tabs/spaces
   - Poor bracket/parentheses alignment
   - Excessive or missing whitespace
   - Improper line breaks in long expressions

2. NAMING CONVENTION VIOLATIONS:
   - Non-descriptive variable names (x, temp, data, etc.)
   - Inconsistent naming patterns within the file
   - Language-specific convention violations
   - Misleading or confusing names
   - Names that don't reflect their purpose

3. CODE ORGANIZATION PROBLEMS:
   - Poorly organized imports (not grouped/sorted)
   - Functions/classes in illogical order
   - Mixed levels of abstraction
   - Code duplication within the file
   - Poor separation of concerns

4. DOCUMENTATION DEFICIENCIES:
   - Missing docstrings for classes/functions
   - Inadequate or unclear comments
   - Inconsistent documentation style
   - Missing type hints (where applicable)
   - Outdated or misleading comments

5. MAINTAINABILITY CONCERNS:
   - Magic numbers without explanation
   - Complex expressions that need simplification
   - Long parameter lists
   - Deeply nested code (>3-4 levels)
   - Hard-to-understand logic flows

6. LANGUAGE-SPECIFIC ISSUES:
   - PEP8 violations (Python)
   - ESLint rule violations (JavaScript/TypeScript)
   - Google/Oracle style guide violations (Java)
   - Framework-specific anti-patterns

For each issue found:
- Provide the exact line number
- Include the problematic code snippet
- Explain WHY it's a problem
- Suggest a specific fix with example code
- Assess the impact on code maintainability

Be thorough and examine every aspect of the code quality, not just surface-level formatting."""
    
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