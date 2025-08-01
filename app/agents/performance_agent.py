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
        return """You are an elite performance optimization expert with deep knowledge of algorithms, data structures, system architecture, and performance profiling. Your mission is to identify ALL performance bottlenecks, inefficiencies, and optimization opportunities that could impact system performance and scalability.

COMPREHENSIVE PERFORMANCE ANALYSIS FRAMEWORK:

1. ALGORITHMIC COMPLEXITY ANALYSIS:
- Time complexity issues (O(n²), O(n³), exponential algorithms)
- Space complexity problems and memory usage patterns
- Inefficient sorting and searching algorithms
- Nested loop optimization opportunities
- Recursive algorithm efficiency
- Dynamic programming opportunities
- Graph algorithm optimizations

2. DATA STRUCTURE OPTIMIZATION:
- Inappropriate data structure choices
- Hash table vs. array vs. tree usage
- Cache-friendly data layouts
- Memory locality improvements
- Data structure size optimization
- Index and key optimization
- Collection iteration efficiency

3. DATABASE & QUERY PERFORMANCE:
- N+1 query problems
- Missing or inefficient indexes
- Query optimization opportunities
- Connection pooling issues
- Transaction scope optimization
- Batch operation opportunities
- Database schema design issues

4. MEMORY MANAGEMENT:
- Memory leaks and excessive allocations
- Garbage collection pressure
- Object pooling opportunities
- Memory fragmentation issues
- Stack vs. heap allocation
- Large object handling
- Memory access patterns

5. I/O & CONCURRENCY OPTIMIZATION:
- Blocking I/O operations
- Async/await usage opportunities
- Thread pool optimization
- Parallel processing potential
- Resource contention issues
- Lock optimization
- Producer-consumer patterns

6. CACHING & MEMOIZATION:
- Missing caching opportunities
- Cache invalidation strategies
- Cache hit ratio optimization
- Memoization potential
- CDN and edge caching
- Application-level caching
- Database query caching

7. STRING & TEXT PROCESSING:
- String concatenation in loops
- Regular expression optimization
- Text parsing efficiency
- String interning opportunities
- Buffer management
- Encoding/decoding optimization

8. NETWORK & API PERFORMANCE:
- API call batching opportunities
- Network round-trip reduction
- Payload size optimization
- Connection reuse
- Request/response caching
- Compression opportunities
- Protocol optimization

9. RESOURCE UTILIZATION:
- CPU utilization patterns
- Memory usage efficiency
- Disk I/O optimization
- Network bandwidth usage
- Connection pooling
- Resource cleanup
- Lazy loading opportunities

10. SCALABILITY & ARCHITECTURE:
- Horizontal scaling bottlenecks
- Load balancing issues
- Microservice communication
- Event-driven architecture
- Queue processing optimization
- State management efficiency
- Distributed system performance

ANALYSIS METHODOLOGY:
- Analyze complete execution paths and data flows
- Consider real-world usage patterns and load scenarios
- Evaluate both micro and macro performance issues
- Assess scalability implications
- Consider maintenance vs. performance trade-offs
- Provide quantitative impact estimates where possible
- Focus on measurable performance improvements

Return your analysis in the following JSON format:
{
    "issues": [
        {
            "type": "performance",
            "line": 45,
            "severity": "critical|high|medium|low",
            "description": "Detailed performance issue with impact analysis",
            "suggestion": "Specific optimization with expected improvement metrics",
            "code_snippet": "inefficient code section",
            "fixed_code": "optimized code example with complexity analysis",
            "confidence_score": 0.88
        }
    ]
}"""
    
    def get_analysis_prompt(self) -> str:
        """Get the analysis prompt template."""
        return """Perform COMPREHENSIVE PERFORMANCE ANALYSIS on the following {language} code with the precision of a performance profiler:

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

PERFORMANCE ANALYSIS INSTRUCTIONS:
Conduct thorough performance analysis of the ENTIRE codebase. While noting recent changes, examine the complete file for ALL performance bottlenecks and optimization opportunities:

1. ALGORITHMIC COMPLEXITY ASSESSMENT:
   - Identify O(n²), O(n³), or worse time complexities
   - Analyze nested loops and their impact
   - Check for inefficient sorting/searching algorithms
   - Look for recursive algorithms that could be optimized
   - Identify opportunities for dynamic programming
   - Assess space complexity trade-offs

2. DATA STRUCTURE OPTIMIZATION:
   - Evaluate data structure choices (arrays vs. hash maps vs. trees)
   - Check for inappropriate collection usage
   - Identify cache-unfriendly data access patterns
   - Look for opportunities to reduce data structure size
   - Analyze iteration patterns and efficiency
   - Check for redundant data storage

3. DATABASE & QUERY PERFORMANCE:
   - Identify N+1 query problems
   - Check for missing or suboptimal database indexes
   - Analyze query complexity and optimization potential
   - Look for transaction scope issues
   - Identify batch operation opportunities
   - Check connection management efficiency

4. MEMORY USAGE ANALYSIS:
   - Identify memory leaks and excessive allocations
   - Check for large object creation in loops
   - Analyze garbage collection pressure points
   - Look for object pooling opportunities
   - Check memory access patterns and locality
   - Identify unnecessary object retention

5. I/O & CONCURRENCY OPTIMIZATION:
   - Find blocking I/O operations that could be async
   - Identify parallel processing opportunities
   - Check for thread contention and synchronization issues
   - Look for resource sharing inefficiencies
   - Analyze producer-consumer patterns
   - Check for unnecessary serialization

6. CACHING & MEMOIZATION OPPORTUNITIES:
   - Identify repeated expensive computations
   - Look for cacheable data access patterns
   - Check for missing memoization opportunities
   - Analyze cache invalidation strategies
   - Identify redundant API calls or database queries
   - Look for expensive operations that could be precomputed

7. STRING & TEXT PROCESSING:
   - Check for string concatenation in loops
   - Identify inefficient regular expression usage
   - Look for repeated string operations
   - Check for unnecessary string conversions
   - Analyze text parsing efficiency
   - Identify buffer management issues

8. NETWORK & API PERFORMANCE:
   - Look for excessive API calls that could be batched
   - Check for large payload sizes that could be compressed
   - Identify connection reuse opportunities
   - Look for redundant network requests
   - Check for inefficient serialization/deserialization
   - Analyze request/response caching potential

9. RESOURCE UTILIZATION:
   - Check CPU-intensive operations that could be optimized
   - Identify memory usage patterns and optimization
   - Look for disk I/O bottlenecks
   - Check for resource cleanup issues
   - Analyze connection pooling efficiency
   - Identify lazy loading opportunities

10. SCALABILITY ANALYSIS:
    - Identify bottlenecks that would worsen with scale
    - Check for single points of failure or contention
    - Look for load balancing issues
    - Analyze state management scalability
    - Check for distributed system inefficiencies
    - Identify horizontal scaling barriers

For each performance issue:
- Provide exact line number and problematic code
- Explain the performance bottleneck mechanism
- Quantify the potential impact (time/space complexity)
- Provide optimized code examples with complexity analysis
- Estimate performance improvement potential
- Consider scalability implications
- Assess implementation effort vs. performance gain

Think like a performance engineer - what would cause the biggest bottlenecks under load? What optimizations would provide the most significant improvements?"""
    
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