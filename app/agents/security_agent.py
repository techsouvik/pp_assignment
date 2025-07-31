"""Security analysis agent for identifying vulnerabilities and security issues."""

import json
import re
from typing import Optional

from app.agents.base_agent import BaseAgent, AnalysisType, FileAnalysisResult, CodeIssue


class SecurityAnalysisAgent(BaseAgent):
    """Agent specialized in detecting security vulnerabilities and risks."""
    
    def __init__(self):
        """Initialize the security analysis agent."""
        super().__init__(AnalysisType.SECURITY)
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for security analysis."""
        return """You are an expert cybersecurity analyst specializing in code security review. Your task is to identify security vulnerabilities, risks, and unsafe coding practices.

Focus on OWASP Top 10 and common security issues:
- SQL Injection vulnerabilities
- Cross-Site Scripting (XSS) risks
- Authentication and authorization flaws
- Hardcoded secrets and credentials
- Insecure data transmission
- Input validation issues
- Command injection vulnerabilities
- Path traversal risks
- Insecure deserialization
- Cryptographic weaknesses
- Information disclosure
- Denial of Service (DoS) vulnerabilities
- Insecure dependencies and imports
- Access control violations
- Security misconfigurations

Analyze code patterns that could lead to security breaches. Consider both direct vulnerabilities and design patterns that increase security risk.

Return your analysis in the following JSON format:
{
    "issues": [
        {
            "type": "security",
            "line": 23,
            "severity": "critical|high|medium|low",
            "description": "Detailed description of the security vulnerability",
            "suggestion": "How to remediate the security issue",
            "code_snippet": "vulnerable code section",
            "fixed_code": "secure code example",
            "confidence_score": 0.95
        }
    ]
}"""
    
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template."""
        return """Analyze the following {language} code for security vulnerabilities and risks:

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

Please analyze this code for security issues including:
1. SQL Injection and other injection vulnerabilities
2. Cross-Site Scripting (XSS) risks
3. Hardcoded credentials, API keys, and secrets
4. Authentication and authorization bypasses
5. Input validation and sanitization issues
6. Insecure data handling and transmission
7. Command injection vulnerabilities
8. Path traversal and directory traversal risks
9. Insecure cryptographic practices
10. Information disclosure vulnerabilities
11. Access control weaknesses
12. Dependency security issues

Focus particularly on the changed lines in the diff, but consider the entire file context for comprehensive security analysis.
Provide specific line numbers, explain the security impact, and suggest secure alternatives."""
    
    def parse_analysis_result(self, response: str, file_path: str) -> FileAnalysisResult:
        """Parse the LLM response into structured security analysis results."""
        issues = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                for issue_data in result_data.get("issues", []):
                    issue = CodeIssue(
                        type=issue_data.get("type", "security"),
                        line=issue_data.get("line"),
                        severity=self._parse_severity(issue_data.get("severity", "high")),
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
        
        # Pattern matching for common security issues
        security_patterns = [
            (r"line (\d+).*sql.*injection", "SQL Injection vulnerability", "critical"),
            (r"line (\d+).*xss|cross.*site.*script", "Cross-Site Scripting risk", "high"),
            (r"line (\d+).*hardcoded.*secret|api.*key", "Hardcoded credentials", "critical"),
            (r"line (\d+).*command.*injection", "Command injection vulnerability", "critical"),
            (r"line (\d+).*path.*traversal", "Path traversal vulnerability", "high"),
            (r"line (\d+).*insecure.*crypto", "Weak cryptographic implementation", "high"),
            (r"line (\d+).*unsafe.*deserializ", "Unsafe deserialization", "high"),
            (r"line (\d+).*auth.*bypass", "Authentication bypass", "critical"),
            (r"line (\d+).*access.*control", "Access control violation", "high"),
            (r"line (\d+).*information.*disclosure", "Information disclosure", "medium"),
        ]
        
        for pattern, description, severity in security_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                line_num = int(match.group(1)) if match.group(1) else None
                issue = CodeIssue(
                    type="security",
                    line=line_num,
                    severity=self._parse_severity(severity),
                    description=f"{description} (auto-detected)",
                    confidence_score=0.8
                )
                issues.append(issue)
        
        return issues