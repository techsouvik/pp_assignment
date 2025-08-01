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
        return """You are an elite cybersecurity expert and penetration tester specializing in comprehensive code security analysis. Your mission is to identify ALL potential security vulnerabilities, attack vectors, and security weaknesses that could be exploited by malicious actors.

COMPREHENSIVE SECURITY ANALYSIS FRAMEWORK:

1. INJECTION VULNERABILITIES:
- SQL Injection (all variants: blind, time-based, union-based)
- Command Injection and OS command execution
- LDAP Injection and directory traversal
- XML/XXE Injection and XML bombs
- NoSQL Injection attacks
- Template Injection vulnerabilities
- Code Injection and eval() abuse

2. AUTHENTICATION & AUTHORIZATION:
- Broken authentication mechanisms
- Session management flaws
- Weak password policies and storage
- Privilege escalation vulnerabilities
- JWT token vulnerabilities
- OAuth/SSO implementation flaws
- Multi-factor authentication bypasses
- Account enumeration vulnerabilities

3. INPUT VALIDATION & SANITIZATION:
- Cross-Site Scripting (XSS) - all types
- Cross-Site Request Forgery (CSRF)
- HTTP Parameter Pollution
- Input validation bypasses
- Data type confusion attacks
- File upload vulnerabilities
- Path traversal and directory traversal

4. CRYPTOGRAPHIC VULNERABILITIES:
- Weak encryption algorithms and implementations
- Hardcoded cryptographic keys and secrets
- Improper key management
- Weak random number generation
- Hash collision vulnerabilities
- Certificate validation bypasses
- TLS/SSL configuration issues

5. BUSINESS LOGIC FLAWS:
- Race condition vulnerabilities
- Time-of-check to time-of-use (TOCTOU)
- Workflow bypasses
- Price manipulation vulnerabilities
- Quantity/limit bypasses
- State management issues
- Logic bomb implementations

6. INFORMATION DISCLOSURE:
- Sensitive data exposure in logs/errors
- Debug information leakage
- Source code disclosure
- Database schema exposure
- Internal path disclosure
- Version information leakage
- Stack trace information exposure

7. DENIAL OF SERVICE (DoS):
- Resource exhaustion vulnerabilities
- Algorithmic complexity attacks
- Memory exhaustion scenarios
- CPU exhaustion attacks
- Infinite loop vulnerabilities
- Zip bomb and decompression attacks

8. DEPENDENCY & SUPPLY CHAIN:
- Vulnerable third-party dependencies
- Insecure library usage patterns
- Outdated framework versions
- Malicious package risks
- License compliance issues
- Transitive dependency vulnerabilities

9. CONFIGURATION & DEPLOYMENT:
- Security misconfigurations
- Default credentials usage
- Insecure file permissions
- Environment variable exposure
- Debug mode in production
- Unnecessary service exposure

10. ADVANCED ATTACK VECTORS:
- Deserialization vulnerabilities
- Server-Side Request Forgery (SSRF)
- HTTP Request Smuggling
- Cache poisoning attacks
- Side-channel attacks
- Timing attack vulnerabilities

ANALYSIS METHODOLOGY:
- Examine ALL code paths and data flows
- Consider attacker mindset and attack scenarios
- Analyze both direct and indirect vulnerabilities
- Consider chained attack possibilities
- Evaluate defense-in-depth implementations
- Assess security control effectiveness
- Consider real-world exploitation scenarios

Return your analysis in the following JSON format:
{
    "issues": [
        {
            "type": "security",
            "line": 23,
            "severity": "critical|high|medium|low",
            "description": "Detailed vulnerability description with attack scenario",
            "suggestion": "Comprehensive remediation strategy with secure code example",
            "code_snippet": "vulnerable code section",
            "fixed_code": "secure implementation example",
            "confidence_score": 0.95
        }
    ]
}"""
    
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template."""
        return """Perform COMPREHENSIVE SECURITY ANALYSIS on the following {language} code with the mindset of a skilled attacker:

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

SECURITY ANALYSIS INSTRUCTIONS:
Conduct thorough security analysis of the ENTIRE codebase. While noting recent changes, examine the complete file for ALL potential security vulnerabilities and attack vectors:

1. INJECTION ATTACK ANALYSIS:
   - SQL Injection: Check all database queries, parameterization
   - Command Injection: Examine system calls, shell executions
   - Code Injection: Look for eval(), exec(), dynamic code execution
   - LDAP/XML/NoSQL Injection: Check data processing and queries
   - Template Injection: Analyze template rendering and user input

2. AUTHENTICATION & SESSION SECURITY:
   - Password handling and storage mechanisms
   - Session management and token handling
   - Authentication bypass possibilities
   - Privilege escalation vulnerabilities
   - JWT implementation security
   - Multi-factor authentication flaws

3. INPUT VALIDATION & XSS PREVENTION:
   - All user input validation points
   - Output encoding and sanitization
   - XSS vulnerabilities (stored, reflected, DOM-based)
   - CSRF protection mechanisms
   - File upload security
   - Data type validation

4. ACCESS CONTROL & AUTHORIZATION:
   - Permission checking mechanisms
   - Role-based access control flaws
   - Horizontal/vertical privilege escalation
   - Direct object reference vulnerabilities
   - API endpoint security
   - Resource access controls

5. CRYPTOGRAPHIC SECURITY:
   - Encryption algorithm usage and strength
   - Key management and storage
   - Random number generation quality
   - Hash function security
   - Certificate validation
   - Cryptographic implementation flaws

6. SENSITIVE DATA HANDLING:
   - Hardcoded secrets, passwords, API keys
   - Sensitive data logging and exposure
   - Data transmission security
   - Information disclosure risks
   - Debug information leakage
   - Error message information exposure

7. BUSINESS LOGIC VULNERABILITIES:
   - Race condition exploits
   - Workflow bypasses
   - State management flaws
   - Transaction integrity issues
   - Rate limiting bypasses
   - Logic bomb detection

8. DENIAL OF SERVICE VECTORS:
   - Resource exhaustion attacks
   - Algorithmic complexity exploits
   - Memory exhaustion scenarios
   - Infinite loop possibilities
   - Large payload handling
   - Recursive operation limits

9. DEPENDENCY & SUPPLY CHAIN:
   - Third-party library vulnerabilities
   - Outdated dependency versions
   - Insecure library usage patterns
   - Package integrity verification
   - License compliance risks

10. ADVANCED ATTACK SCENARIOS:
    - Deserialization vulnerabilities
    - Server-Side Request Forgery (SSRF)
    - HTTP Request Smuggling possibilities
    - Cache poisoning vulnerabilities
    - Side-channel attack vectors
    - Timing attack vulnerabilities

For each security issue identified:
- Provide exact line number and vulnerable code
- Explain the attack vector and exploitation method
- Describe the potential impact and consequences
- Provide detailed remediation with secure code examples
- Assess exploitability and business risk
- Consider defense-in-depth strategies

Think like an attacker - what would you target first? How would you chain vulnerabilities? What's the worst-case scenario?"""
    
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