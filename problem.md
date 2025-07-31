We need to implement this,

Build an autonomous code review agent system that uses AI to analyze GitHub pull requests. The system should implement a goal-oriented AI agent that can plan and execute code reviews independently, process them asynchronously using Celery, and interact with developers through a structured API.

## Core Requirements

### 1. Basic API Endpoints

- Create a FastAPI application with the following endpoints:
    - POST `/analyze-pr`: Accept GitHub PR details (repo, PR number)
    - GET `/status/<task_id>`: Check the status of an analysis task
    - GET `/results/<task_id>`: Retrieve the analysis results

### 2. Asynchronous Processing

- Use Celery to handle the code analysis tasks asynchronously
- Implement proper task status tracking and error handling
- Store task results in Redis or PostgreSQL


### 3. AI Agent Implementation

The agent should analyze code for:

- Code style and formatting issues
- Potential bugs or errors
- Performance improvements
- Best practices

Use langchain, langgraph agent framework

Build required tooling for to fetch code, diff etc w

## Bonus Points

- Docker configuration
- Basic caching of API results
- Meaningful logging
- Support for different programming languages

## Core Requirements

### 1. API Endpoints (FastAPI)

- POST `/analyze-pr`
    
    ```json
    {
      "repo_url": "https://github.com/user/repo",
      "pr_number": 123,
      "github_token": "optional_token"
    }
    
    ```
    
- GET `/status/<task_id>`
- GET `/results/<task_id>`

### . Asynchronous Processing

- Use Celery for async task processing
- Store results in Redis or PostgreSQL
- Implement task status tracking (pending, processing, completed, failed)
- Handle errors gracefully

### 3. AI Agent Implementation

Use any agent framework (langchain, crewai, litellm, autogen):

- The agent should analyze code for:
    - Code style and formatting issues
    - Potential bugs or errors
    - Performance improvements
    - Best practices

Expected output format:
```json
{
    "task_id": "abc123",
    "status": "completed",
    "results": {
        "files": [
            {
                "name": "main.py",
                "issues": [
                    {
                        "type": "style",
                        "line": 15,
                        "description": "Line too long",
                        "suggestion": "Break line into multiple lines"
                    },
                    {
                        "type": "bug",
                        "line": 23,
                        "description": "Potential null pointer",
                        "suggestion": "Add null check"
                    }
                ]
            }
        ],
        "summary": {
            "total_files": 1,
            "total_issues": 2,
            "critical_issues": 1
        }
    }
}
```
​
## Technical Requirements

- Python 3.8+
- FastAPI
- Celery
- Redis or PostgreSQL
- Choice of:
    - Any LLM API (OpenAI, Anthropic, etc.)
- pytest for 



Now out idea to solve the problem is,

Complete GitHub PR Analyzer Agent Solution
- Based on our comprehensive discussion, here’s the complete descriptive solution for building a scalable, cost-effective GitHub PR analyzer agent using LangChain, Claude Sonnet 4, Redis, Celery, and vector embeddings for enhanced performance and detailed code analysis.

Project Overview
- We’re building an enterprise-grade GitHub PR analyzer that provides detailed, file-level code analysis with line-by-line issue detection. The system combines multiple specialized AI agents for different analysis types (style, bugs, security, performance) while maintaining cost efficiency through intelligent vector-based semantic caching.

System Architecture & Technology Stack
- Core Technologies
	•	Framework: LangChain (chosen for mature ecosystem and Redis integration)
	•	LLM: Claude Sonnet 4 (for high-quality code analysis)
	•	Task Queue: Celery (for parallel processing and scalability)
	•	Caching/Storage: Redis (for task management, results, and vector embeddings)
	•	Database: PostgreSQL (for persistent storage and analytics)
	•	API Framework: FastAPI (for high-performance async endpoints)
	•	Vector Embeddings: OpenAI text-embedding-3-small (for cost-effective semantic caching)

System Components

1. API Layer
Three primary endpoints handle the complete analysis workflow:
- POST /analyze-pr
	•	Accepts repository URL, PR number, and analysis configuration
	•	Validates GitHub permissions and PR accessibility
	•	Creates parallel Celery task groups for different analysis types
	•	Returns task ID for tracking progress
	•	Estimated response time: <500ms
- GET /check-status/{task_id}
	•	Provides real-time progress updates across all analysis components
	•	Shows completion status for each analysis type (style, bugs, security, performance)
	•	Includes estimated completion time and current processing file
	•	Supports WebSocket upgrades for real-time updates
- GET /get-result/{task_id}
	•	Returns comprehensive analysis results with detailed metrics
	•	Includes file-level issues with line numbers, severity, and fix suggestions
	•	Provides summary statistics and overall code quality scores
	•	Indicates cache usage and cost savings achieved

2. Task Processing Layer
- Celery manages distributed task execution with specialized workers:
- Task Distribution Strategy
	•	Parallel File Processing: Each file analyzed independently
	•	Agent Specialization: Separate workers for style, bugs, security, and performance
	•	Smart Queuing: Priority-based task execution with critical issues first
	•	Auto-scaling: Workers scale based on queue depth and processing time
- Worker Types
	•	Style Analysis Workers: PEP8 compliance, formatting, naming conventions
	•	Bug Detection Workers: Static analysis + LLM-powered logic error detection
	•	Security Analysis Workers: Vulnerability scanning and pattern matching
	•	Performance Analysis Workers: Complexity analysis and optimization suggestions

3. Vector-Enhanced Caching System
- The most innovative aspect of our solution is the multi-level semantic caching:
- Semantic Cache Architecture
	•	Code Pattern Embeddings: Generate vector representations of code chunks
	•	Similarity Matching: Use cosine similarity (threshold: 0.85) to find similar patterns
	•	Hierarchical Caching: Function-level, file-level, and repository-level caching
	•	Cost Optimization: Achieves 68.8% reduction in LLM API calls

Cache Implementation
```
# Redis Vector Store Configuration
vector_store = RedisVectorStore(
    redis_url="redis://localhost:6379",
    index_name="code_embeddings",
    embedding_dimension=1536,
    similarity_algorithm="COSINE"
)

# Multi-level caching strategy
cache_levels = {
    "function": 0.95,    # High precision for function-level matches
    "class": 0.90,       # Medium precision for class-level matches  
    "file": 0.85,        # Lower precision for file-level patterns
    "project": 0.80      # Broad patterns across projects
}

```

4. Analysis Engine Components
Style Analysis Agent
	•	Rule-based Checks: Line length, indentation, naming conventions
	•	LLM Enhancement: Complex style pattern detection using Claude
	•	Auto-fix Suggestions: Provides specific code corrections
	•	Integration: Supports popular linters (flake8, black, isort)
Bug Detection Agent
	•	Static Analysis: AST-based parsing for common error patterns
	•	Dynamic Analysis: LLM-powered logic error detection
	•	Pattern Recognition: Learns from historical bug patterns
	•	Severity Assessment: Critical, high, medium, low classification
Security Analysis Agent
	•	Vulnerability Scanning: OWASP Top 10 compliance checking
	•	Pattern Matching: SQL injection, XSS, hardcoded secrets detection
	•	Dependency Analysis: Known vulnerability database checking
	•	Compliance Reporting: Security standard adherence metrics
Performance Analysis Agent
	•	Complexity Analysis: Cyclomatic complexity calculation
	•	Optimization Suggestions: Algorithm and data structure improvements
	•	Resource Usage: Memory and CPU optimization opportunities
	•	Scalability Assessment: Performance bottleneck identification

 
Implementation Strategy
Phase 1: Core Infrastructure Setup
- Redis Configuration
- Celery Configuration
Phase 2: LangChain Agent Development
- Agent Architecture
Phase 3: Analysis Output Format
- Comprehensive Results Structure