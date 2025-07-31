# GitHub PR Analyzer - Complete Dataflow Diagram

---

## System Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client/User   │───▶│  FastAPI App    │───▶│  Celery Task    │
│                 │    │                 │    │     Queue       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ PostgreSQL DB   │    │ Analysis        │
                       │                 │    │ Coordinator     │
                       └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Redis Cache   │◀───│  GitHub Service │
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Vector Cache   │    │   GitHub API    │
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │  (Embeddings)   │
                       └─────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Style Analysis  │    │ Bug Detection   │    │ Security Analysis│
│     Agent       │    │     Agent       │    │     Agent       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                       ┌─────────────────┐
                       │ Performance     │
                       │ Analysis Agent  │
                       └─────────────────┘
                                 │
                                 ▼
                       ┌─────────────────┐
                       │ Claude Sonnet 4 │
                       │   (LLM API)     │
                       └─────────────────┘
```

---

## Detailed Data Flow

---

### 1. Request Initiation Flow

```
Client Request
       │
       ▼
┌─────────────────┐
│ POST /analyze-pr│
│ {repo_url,      │
│  pr_number,     │
│  analysis_types}│
└─────────────────┘
       │
       ▼
┌─────────────────┐
│ Generate Task ID│
└─────────────────┘
       │
       ▼
┌─────────────────┐
│ Create DB Record│
└─────────────────┘
       │
       ▼
┌─────────────────┐
│ Queue Celery    │
│    Task         │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│ Return Task ID  │
└─────────────────┘
```

---

### 2. Task Processing Flow

```
Celery Task Execution
         │
         ▼
┌─────────────────┐
│ Analysis        │
│ Coordinator     │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Fetch PR Data   │
│ from GitHub     │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Get Changed     │
│ Files & Content │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ For Each File:  │
│ 1. Check Cache  │
│ 2. Run Analysis │
│ 3. Update Progress│
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Store Results   │
│ in Database     │
└─────────────────┘
```

---

### 3. Agent Analysis Flow

```
File Content Input
         │
         ▼
┌─────────────────┐
│ Preprocessing   │
│ & Code Chunks   │
└─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Style Analysis  │    │ Bug Detection   │    │ Security Analysis│    │ Performance     │
│                 │    │                 │    │                 │    │ Analysis        │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Claude Sonnet 4 │    │ Claude Sonnet 4 │    │ Claude Sonnet 4 │    │ Claude Sonnet 4 │
│                 │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Parse Style     │    │ Parse Bug       │    │ Parse Security  │    │ Parse Performance│
│ Results         │    │ Results         │    │ Results         │    │ Results         │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         └───────────────────────┼───────────────────────┼───────────────────────┘
                                 ▼
                       ┌─────────────────┐
                       │ Aggregate All   │
                       │ Results         │
                       └─────────────────┘
```

---

### 4. Vector Cache Flow

```
Code Content Input
         │
         ▼
┌─────────────────┐
│ Generate Hash   │
│ (SHA256)        │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Generate        │
│ Embedding       │
│ (OpenAI)        │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Find Similar    │
│ Cached Entries  │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Similarity >    │
│ 0.85?           │
└─────────────────┘
         │
         ▼
    ┌─────────┐    ┌─────────┐
    │   Yes   │    │   No    │
    │ (Cache  │    │ (New    │
    │  Hit)   │    │ Analysis)│
    └─────────┘    └─────────┘
         │               │
         ▼               ▼
┌─────────────────┐    ┌─────────────────┐
│ Return Cached   │    │ Perform New     │
│ Results         │    │ Analysis        │
└─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Store Results   │
                       │ in Cache        │
                       └─────────────────┘
```

---

### 5. Database Schema Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    AnalysisTask Table                       │
├─────────────────────────────────────────────────────────────┤
│ task_id (UUID, PK)                                          │
│ repo_url (String)                                           │
│ pr_number (Integer)                                         │
│ status (Enum: PENDING, PROCESSING, COMPLETED, FAILED)      │
│ metadata (JSON)                                             │
│ results (JSON)                                              │
│ created_at (DateTime)                                       │
│ started_at (DateTime)                                       │
│ completed_at (DateTime)                                     │
│ error_message (String)                                      │
└─────────────────────────────────────────────────────────────┘
                                │
                                │ uses
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    CacheEntry Table                         │
├─────────────────────────────────────────────────────────────┤
│ content_hash (String, PK)                                   │
│ content_type (String)                                       │
│ embedding_vector (Array)                                    │
│ analysis_results (JSON)                                     │
│ language (String)                                           │
│ similarity_threshold (Float)                                │
│ created_at (DateTime)                                       │
│ usage_count (Integer)                                       │
│ last_used_at (DateTime)                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Interactions

---

### FastAPI Application (`app/main.py`)
```
Input: HTTP requests for PR analysis
Output: Task IDs and status responses

Key Functions:
├── POST /analyze-pr: Creates analysis tasks
├── GET /status/{task_id}: Returns task progress
├── GET /results/{task_id}: Returns analysis results
└── GET /health: Health check endpoint
```

---

### Celery Task System (`app/celery_app.py`)
```
Input: Task parameters from FastAPI
Output: Analysis results stored in database

Key Functions:
├── analyze_pr_task: Main analysis orchestration
├── Progress tracking and status updates
└── Error handling and retry logic
```

---

### Analysis Coordinator (`app/agents/coordinator.py`)
```
Input: PR data and analysis types
Output: Comprehensive analysis results

Key Functions:
├── Orchestrates multiple analysis agents
├── Manages file-level analysis
├── Aggregates results from all agents
└── Handles progress callbacks
```

---

### GitHub Service (`app/services/github_service.py`)
```
Input: Repository URL and PR number
Output: PR metadata and file contents

Key Functions:
├── Fetches PR data from GitHub API
├── Extracts changed files and their contents
├── Filters analyzable files
└── Handles authentication and rate limiting
```

---

### Vector Cache Service (`app/services/vector_cache.py`)
```
Input: Code content and analysis type
Output: Cached results or similarity matches

Key Functions:
├── Generates embeddings using OpenAI
├── Finds similar cached analyses
├── Stores new analysis results
└── Manages cache lifecycle
```

---

### Analysis Agents
```
Each agent follows the same pattern:
Input: File content and language
Output: Structured analysis results

Key Functions:
├── StyleAnalysisAgent: Code style and formatting
├── BugDetectionAgent: Logic errors and bugs
├── SecurityAnalysisAgent: Security vulnerabilities
└── PerformanceAnalysisAgent: Performance issues
```

---

## Data Storage Flow

---

### PostgreSQL Database
```
┌─────────────────┐
│ AnalysisTask    │
│ - Stores task   │
│   metadata and  │
│   results       │
└─────────────────┘

┌─────────────────┐
│ Migrations      │
│ - Schema        │
│   versioning    │
│   with Alembic  │
└─────────────────┘

┌─────────────────┐
│ Connection Pool │
│ - Async database│
│   connections   │
└─────────────────┘
```

---

### Redis Cache
```
┌─────────────────┐
│ Task Status     │
│ - Real-time     │
│   task progress │
└─────────────────┘

┌─────────────────┐
│ Vector Cache    │
│ - Embeddings    │
│   and analysis  │
│   results       │
└─────────────────┘

┌─────────────────┐
│ Celery Broker   │
│ - Task queue    │
│   management    │
└─────────────────┘

┌─────────────────┐
│ Session Storage │
│ - Temporary     │
│   data          │
└─────────────────┘
```

---

## External API Dependencies

---

### GitHub API
```
Rate Limits:
├── Public API: 60 requests/hour
└── Authenticated: 5,000 requests/hour

Endpoints Used:
├── /repos/{owner}/{repo}/pulls/{pr_number}
├── /repos/{owner}/{repo}/pulls/{pr_number}/files
└── /repos/{owner}/{repo}/contents/{path}
```

---

### Anthropic Claude API
```
Model: Claude Sonnet 4
Usage: Code analysis and issue detection
Rate Limits: Based on API tier
```

---

### OpenAI API
```
Model: text-embedding-3-small
Usage: Vector embeddings for caching
Rate Limits: Based on API tier
```

---

## Error Handling and Resilience

```
Error Occurs
     │
     ▼
┌─────────────────┐
│ Determine Error │
│     Type        │
└─────────────────┘
     │
     ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Network Error   │    │ API Rate Limit  │    │ Invalid Data    │    │ System Error    │
│                 │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
     │                       │                       │                       │
     ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Retry with      │    │ Wait and Retry  │    │ Validate and    │    │ Use Fallback    │
│ Backoff         │    │                 │    │ Skip            │    │ Logic           │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
     │                       │                       │                       │
     └───────────────────────┼───────────────────────┼───────────────────────┘
                             ▼
                       ┌─────────────────┐
                       │ Success?        │
                       └─────────────────┘
                             │
                             ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Yes: Continue   │    │ No: Log Error   │
                       │ Processing      │    │ and Continue    │
                       └─────────────────┘    └─────────────────┘
```

---

## Performance Optimization Flow

---

### Caching Strategy
```
1. Content Hash: Generate SHA256 hash of code + analysis type
2. Embedding Generation: Create vector embedding for semantic similarity
3. Similarity Search: Find cached results above threshold (0.85)
4. Cache Storage: Store new results with metadata
```

---

### Parallel Processing
```
1. File-Level Parallelism: Analyze multiple files concurrently
2. Agent-Level Parallelism: Run different analysis types in parallel
3. Chunk-Level Parallelism: Process code chunks independently
```

---

### Resource Management
```
1. Connection Pooling: Reuse database and API connections
2. Memory Management: Stream large files and results
3. Task Queuing: Distribute load across multiple workers
```

---

## Monitoring and Observability

---

### Health Checks
```
┌─────────────────┐
│ API Health      │
│ - /health       │
│   endpoint      │
└─────────────────┘

┌─────────────────┐
│ Database Health │
│ - Connection    │
│   pool status   │
└─────────────────┘

┌─────────────────┐
│ Redis Health    │
│ - Cache         │
│   connectivity  │
└─────────────────┘

┌─────────────────┐
│ External APIs   │
│ - GitHub,       │
│   Claude,       │
│   OpenAI        │
└─────────────────┘
```

---

### Metrics Collection
```
┌─────────────────┐
│ Task Processing │
│ - Success/failure│
│   rates         │
│ - Processing    │
│   times         │
└─────────────────┘

┌─────────────────┐
│ Cache Performance│
│ - Hit rates     │
│ - Storage usage │
└─────────────────┘

┌─────────────────┐
│ API Usage       │
│ - Rate limit    │
│   utilization   │
│ - Response times│
└─────────────────┘

┌─────────────────┐
│ System Resources│
│ - CPU, memory,  │
│   disk usage    │
└─────────────────┘
```

---

### Logging Strategy
```
┌─────────────────┐
│ Structured      │
│ Logging         │
│ - JSON format   │
│ - Correlation   │
│   IDs           │
└─────────────────┘

┌─────────────────┐
│ Log Levels      │
│ - DEBUG         │
│ - INFO          │
│ - WARNING       │
│ - ERROR         │
└─────────────────┘

┌─────────────────┐
│ Context Tracking│
│ - Task ID       │
│ - File name     │
│ - Analysis type │
└─────────────────┘

┌─────────────────┐
│ Error Reporting │
│ - Detailed error│
│   context       │
│ - Stack traces  │
└─────────────────┘
```