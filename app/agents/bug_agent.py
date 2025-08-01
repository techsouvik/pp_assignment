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
        return """You are an expert static code analyzer and bug detection specialist with deep knowledge of common programming errors, edge cases, and subtle bugs. Your mission is to perform comprehensive bug detection that goes far beyond surface-level issues.

COMPREHENSIVE BUG DETECTION AREAS:

1. MEMORY & RESOURCE MANAGEMENT:
- Null/undefined pointer dereferences
- Memory leaks and resource leaks
- Double-free errors and use-after-free
- Buffer overflows and underflows
- Unclosed file handles, database connections, network sockets
- Improper resource cleanup in exception paths

2. LOGIC & CONTROL FLOW ERRORS:
- Off-by-one errors in loops and array access
- Incorrect conditional logic and boolean expressions
- Unreachable code and dead code paths
- Infinite loops and infinite recursion
- Missing break statements in switch/case
- Incorrect loop termination conditions

3. DATA HANDLING ISSUES:
- Array/list index out of bounds
- Type mismatches and implicit conversions
- Integer overflow/underflow
- Division by zero scenarios
- String manipulation errors
- Incorrect data validation

4. EXCEPTION & ERROR HANDLING:
- Unhandled exceptions and error conditions
- Catching overly broad exception types
- Missing finally blocks for cleanup
- Swallowing exceptions without logging
- Incorrect error propagation
- Missing input validation

5. CONCURRENCY & THREADING BUGS:
- Race conditions and data races
- Deadlocks and livelocks
- Thread safety violations
- Improper synchronization
- Shared state modification without locks
- Atomic operation violations

6. API & LIBRARY MISUSE:
- Incorrect API usage patterns
- Missing required parameters or configurations
- Deprecated method usage
- Framework-specific anti-patterns
- Library version compatibility issues
- Improper callback handling

7. SUBTLE LOGIC ERRORS:
- Operator precedence mistakes
- Assignment vs. equality confusion (= vs ==)
- Short-circuit evaluation issues
- Floating-point precision problems
- Time zone and date handling errors
- State management inconsistencies

8. EDGE CASE VULNERABILITIES:
- Empty collection handling
- Null/None value propagation
- Boundary condition failures
- Input sanitization gaps
- Configuration-dependent bugs
- Environment-specific issues

ANALYSIS METHODOLOGY:
- Examine the COMPLETE code context, not just changes
- Trace data flow and control flow paths
- Consider all possible execution paths
- Think about edge cases and error scenarios
- Analyze interactions between different code sections
- Look for patterns that commonly lead to bugs
- Consider the broader system context and dependencies

Return your analysis in the following JSON format:
{
    "issues": [
        {
            "type": "bug",
            "line": 42,
            "severity": "critical|high|medium|low",
            "description": "Detailed description of the potential bug and its impact",
            "suggestion": "Specific fix with code example and explanation",
            "code_snippet": "problematic code section",
            "fixed_code": "corrected code example",
            "confidence_score": 0.90
        }
    ]
}"""
    
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template."""
        return """Perform DEEP BUG DETECTION analysis on the following {language} code:

File: {file_path}
Language: {language}

COMPLETE CODE CONTENT:
```{language}
{file_content}
```

RECENT CHANGES (Git Diff):
```diff
{file_diff}
```

COMPREHENSIVE BUG ANALYSIS INSTRUCTIONS:
Perform thorough bug detection on the ENTIRE codebase. While noting recent changes, analyze the complete file for potential bugs, logic errors, and edge cases:

1. TRACE EXECUTION PATHS:
   - Follow all possible code execution flows
   - Identify paths that could lead to errors
   - Check for unreachable or dead code
   - Analyze loop termination conditions
   - Verify all conditional branches

2. MEMORY & RESOURCE ANALYSIS:
   - Check for null/undefined dereferences
   - Identify potential memory leaks
   - Verify proper resource cleanup (files, connections, etc.)
   - Look for buffer overflow possibilities
   - Check resource acquisition/release patterns

3. DATA FLOW VALIDATION:
   - Trace variable initialization and usage
   - Check for uninitialized variable access
   - Verify array/list bounds checking
   - Identify type conversion issues
   - Check for division by zero scenarios

4. ERROR HANDLING REVIEW:
   - Find unhandled exception scenarios
   - Check for proper error propagation
   - Verify input validation coverage
   - Look for swallowed exceptions
   - Identify missing error checks

5. CONCURRENCY ISSUES:
   - Check for race conditions
   - Identify thread safety violations
   - Look for deadlock possibilities
   - Verify proper synchronization
   - Check shared state access patterns

6. API & FRAMEWORK USAGE:
   - Verify correct API usage patterns
   - Check for deprecated method calls
   - Identify framework-specific bugs
   - Verify callback handling
   - Check configuration dependencies

7. EDGE CASE ANALYSIS:
   - Test boundary conditions
   - Check empty/null input handling
   - Verify error state handling
   - Look for off-by-one errors
   - Check overflow/underflow scenarios

8. SUBTLE LOGIC BUGS:
   - Check operator precedence issues
   - Look for assignment vs equality mistakes
   - Verify boolean logic correctness
   - Check floating-point operations
   - Identify state management issues

For each potential bug:
- Provide exact line number and code snippet
- Explain the bug mechanism and conditions
- Describe the potential impact and consequences
- Provide a detailed fix with example code
- Assess the likelihood and severity
- Consider how it might manifest in production

Be extremely thorough - look for bugs that other tools might miss."""
    
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