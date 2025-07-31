# GitHub PR Analyzer - Complete Dataflow Diagram

## System Architecture Overview

```mermaid
graph TB
    %% External Systems
    GitHub[GitHub API] --> |PR Data & Files| GHService[GitHub Service]
    
    %% User Interface Layer
    Client[Client/User] --> |HTTP Requests| FastAPI[FastAPI Application]
    Client --> |WebSocket| WS[WebSocket Updates]
    
    %% API Layer
    FastAPI --> |Task Creation| CeleryTask[Celery Task Queue]
    FastAPI --> |Status Queries| DB[(PostgreSQL Database)]
    FastAPI --> |Admin Operations| AdminAPI[Admin API]
    
    %% Task Processing Layer
    CeleryTask --> |Task Execution| Coordinator[Analysis Coordinator]
    CeleryTask --> |Progress Updates| Redis[(Redis Cache)]
    CeleryTask --> |Results Storage| DB
    
    %% Analysis Layer
    Coordinator --> |File Analysis| StyleAgent[Style Analysis Agent]
    Coordinator --> |File Analysis| BugAgent[Bug Detection Agent]
    Coordinator --> |File Analysis| SecurityAgent[Security Analysis Agent]
    Coordinator --> |File Analysis| PerfAgent[Performance Analysis Agent]
    
    %% AI Services
    StyleAgent --> |LLM Requests| Claude[Claude Sonnet 4]
    BugAgent --> |LLM Requests| Claude
    SecurityAgent --> |LLM Requests| Claude
    PerfAgent --> |LLM Requests| Claude
    
    %% Caching Layer
    VectorCache[Vector Cache Service] --> |Embeddings| OpenAI[OpenAI Embeddings]
    VectorCache --> |Cache Storage| Redis
    StyleAgent --> |Cache Check| VectorCache
    BugAgent --> |Cache Check| VectorCache
    SecurityAgent --> |Cache Check| VectorCache
    PerfAgent --> |Cache Check| VectorCache
    
    %% Data Services
    GHService --> |PR Metadata| Coordinator
    GHService --> |File Contents| Coordinator
    
    %% Monitoring
    Flower[Celery Flower] --> |Task Monitoring| CeleryTask
    AdminAPI --> |System Stats| VectorCache
    AdminAPI --> |Task Stats| CeleryTask
    
    %% Styling
    classDef external fill:#e1f5fe
    classDef api fill:#f3e5f5
    classDef service fill:#e8f5e8
    classDef agent fill:#fff3e0
    classDef storage fill:#fce4ec
    classDef ai fill:#f1f8e9
    
    class GitHub,Client external
    class FastAPI,AdminAPI,Flower api
    class GHService,VectorCache,Coordinator service
    class StyleAgent,BugAgent,SecurityAgent,PerfAgent agent
    class DB,Redis storage
    class Claude,OpenAI ai
```

## Detailed Data Flow

### 1. Request Initiation Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant DB
    participant Celery
    participant Redis
    
    Client->>FastAPI: POST /analyze-pr
    Note over Client,FastAPI: {repo_url, pr_number, analysis_types}
    
    FastAPI->>FastAPI: Generate Task ID
    FastAPI->>DB: Create AnalysisTask Record
    FastAPI->>Celery: Queue analyze_pr_task
    FastAPI->>Client: Return Task ID
    
    Celery->>Redis: Store Task Status
    Note over Redis: Status: PENDING
```

### 2. Task Processing Flow

```mermaid
sequenceDiagram
    participant Celery
    participant Coordinator
    participant GHService
    participant GitHub
    participant VectorCache
    participant Agents
    participant Claude
    participant DB
    participant Redis
    
    Celery->>Coordinator: Start Analysis
    Coordinator->>GHService: Fetch PR Data
    GHService->>GitHub: Get PR Metadata
    GitHub-->>GHService: PR Info
    GHService->>GitHub: Get Changed Files
    GitHub-->>GHService: File Contents
    GHService-->>Coordinator: PullRequestData
    
    loop For Each File
        Coordinator->>VectorCache: Check Cache
        alt Cache Hit
            VectorCache-->>Coordinator: Cached Results
        else Cache Miss
            Coordinator->>Agents: Analyze File
            Agents->>Claude: LLM Analysis
            Claude-->>Agents: Analysis Results
            Agents-->>Coordinator: File Analysis
            Coordinator->>VectorCache: Cache Results
        end
        Coordinator->>Redis: Update Progress
    end
    
    Coordinator->>DB: Store Final Results
    Coordinator->>Redis: Update Status: COMPLETED
```

### 3. Agent Analysis Flow

```mermaid
graph LR
    subgraph "File Input"
        File[File Content] --> Preprocess[Preprocessing]
        Preprocess --> Chunks[Code Chunks]
    end
    
    subgraph "Analysis Pipeline"
        Chunks --> Style[Style Analysis]
        Chunks --> Bug[Bug Detection]
        Chunks --> Security[Security Analysis]
        Chunks --> Performance[Performance Analysis]
    end
    
    subgraph "LLM Processing"
        Style --> Claude1[Claude Sonnet 4]
        Bug --> Claude2[Claude Sonnet 4]
        Security --> Claude3[Claude Sonnet 4]
        Performance --> Claude4[Claude Sonnet 4]
    end
    
    subgraph "Result Processing"
        Claude1 --> Parse1[Parse Style Results]
        Claude2 --> Parse2[Parse Bug Results]
        Claude3 --> Parse3[Parse Security Results]
        Claude4 --> Parse4[Parse Performance Results]
    end
    
    subgraph "Output"
        Parse1 --> Issues1[Style Issues]
        Parse2 --> Issues2[Bug Issues]
        Parse3 --> Issues3[Security Issues]
        Parse4 --> Issues4[Performance Issues]
    end
    
    Issues1 --> Aggregate[Aggregate Results]
    Issues2 --> Aggregate
    Issues3 --> Aggregate
    Issues4 --> Aggregate
```

### 4. Vector Cache Flow

```mermaid
graph TB
    subgraph "Cache Check Process"
        Input[Code Content] --> Hash[Generate Hash]
        Hash --> Embedding[Generate Embedding]
        Embedding --> Similarity[Find Similar Entries]
        Similarity --> Threshold{Similarity > 0.85?}
        
        Threshold -->|Yes| CacheHit[Return Cached Result]
        Threshold -->|No| CacheMiss[Perform New Analysis]
    end
    
    subgraph "Cache Storage"
        NewAnalysis[New Analysis Result] --> StoreEmbedding[Store Embedding]
        StoreEmbedding --> StoreResult[Store Result]
        StoreResult --> Redis[(Redis Cache)]
    end
    
    subgraph "Cache Management"
        Redis --> Cleanup[Cleanup Old Entries]
        Redis --> Stats[Cache Statistics]
    end
```

### 5. Database Schema Flow

```mermaid
erDiagram
    AnalysisTask {
        uuid task_id PK
        string repo_url
        int pr_number
        enum status
        json metadata
        json results
        datetime created_at
        datetime started_at
        datetime completed_at
        string error_message
    }
    
    CacheEntry {
        string content_hash PK
        string content_type
        array embedding_vector
        json analysis_results
        string language
        float similarity_threshold
        datetime created_at
        int usage_count
        datetime last_used_at
    }
    
    AnalysisTask ||--o{ CacheEntry : "uses"
```

## Component Interactions

### FastAPI Application (`app/main.py`)
- **Input**: HTTP requests for PR analysis
- **Output**: Task IDs and status responses
- **Key Functions**:
  - `POST /analyze-pr`: Creates analysis tasks
  - `GET /status/{task_id}`: Returns task progress
  - `GET /results/{task_id}`: Returns analysis results
  - `GET /health`: Health check endpoint

### Celery Task System (`app/celery_app.py`)
- **Input**: Task parameters from FastAPI
- **Output**: Analysis results stored in database
- **Key Functions**:
  - `analyze_pr_task`: Main analysis orchestration
  - Progress tracking and status updates
  - Error handling and retry logic

### Analysis Coordinator (`app/agents/coordinator.py`)
- **Input**: PR data and analysis types
- **Output**: Comprehensive analysis results
- **Key Functions**:
  - Orchestrates multiple analysis agents
  - Manages file-level analysis
  - Aggregates results from all agents
  - Handles progress callbacks

### GitHub Service (`app/services/github_service.py`)
- **Input**: Repository URL and PR number
- **Output**: PR metadata and file contents
- **Key Functions**:
  - Fetches PR data from GitHub API
  - Extracts changed files and their contents
  - Filters analyzable files
  - Handles authentication and rate limiting

### Vector Cache Service (`app/services/vector_cache.py`)
- **Input**: Code content and analysis type
- **Output**: Cached results or similarity matches
- **Key Functions**:
  - Generates embeddings using OpenAI
  - Finds similar cached analyses
  - Stores new analysis results
  - Manages cache lifecycle

### Analysis Agents
Each agent follows the same pattern:
- **Input**: File content and language
- **Output**: Structured analysis results
- **Key Functions**:
  - `StyleAnalysisAgent`: Code style and formatting
  - `BugDetectionAgent`: Logic errors and bugs
  - `SecurityAnalysisAgent`: Security vulnerabilities
  - `PerformanceAnalysisAgent`: Performance issues

## Data Storage Flow

### PostgreSQL Database
- **AnalysisTask**: Stores task metadata and results
- **Migrations**: Schema versioning with Alembic
- **Connection Pool**: Async database connections

### Redis Cache
- **Task Status**: Real-time task progress
- **Vector Cache**: Embeddings and analysis results
- **Celery Broker**: Task queue management
- **Session Storage**: Temporary data

## External API Dependencies

### GitHub API
- **Rate Limits**: 60 req/hour (public), 5000 req/hour (authenticated)
- **Endpoints Used**:
  - `/repos/{owner}/{repo}/pulls/{pr_number}`
  - `/repos/{owner}/{repo}/pulls/{pr_number}/files`
  - `/repos/{owner}/{repo}/contents/{path}`

### Anthropic Claude API
- **Model**: Claude Sonnet 4
- **Usage**: Code analysis and issue detection
- **Rate Limits**: Based on API tier

### OpenAI API
- **Model**: text-embedding-3-small
- **Usage**: Vector embeddings for caching
- **Rate Limits**: Based on API tier

## Error Handling and Resilience

```mermaid
graph TD
    Error[Error Occurs] --> Type{Error Type}
    
    Type -->|Network| Retry[Retry with Backoff]
    Type -->|API Limit| RateLimit[Wait and Retry]
    Type -->|Invalid Data| Validation[Validate and Skip]
    Type -->|System| Fallback[Use Fallback Logic]
    
    Retry --> Success{Success?}
    RateLimit --> Success
    Validation --> Success
    Fallback --> Success
    
    Success -->|Yes| Continue[Continue Processing]
    Success -->|No| Log[Log Error and Continue]
    
    Continue --> Next[Next File/Task]
    Log --> Next
```

## Performance Optimization Flow

### Caching Strategy
1. **Content Hash**: Generate SHA256 hash of code + analysis type
2. **Embedding Generation**: Create vector embedding for semantic similarity
3. **Similarity Search**: Find cached results above threshold (0.85)
4. **Cache Storage**: Store new results with metadata

### Parallel Processing
1. **File-Level Parallelism**: Analyze multiple files concurrently
2. **Agent-Level Parallelism**: Run different analysis types in parallel
3. **Chunk-Level Parallelism**: Process code chunks independently

### Resource Management
1. **Connection Pooling**: Reuse database and API connections
2. **Memory Management**: Stream large files and results
3. **Task Queuing**: Distribute load across multiple workers

## Monitoring and Observability

### Health Checks
- **API Health**: `/health` endpoint
- **Database Health**: Connection pool status
- **Redis Health**: Cache connectivity
- **External APIs**: GitHub, Claude, OpenAI availability

### Metrics Collection
- **Task Processing**: Success/failure rates, processing times
- **Cache Performance**: Hit rates, storage usage
- **API Usage**: Rate limit utilization, response times
- **System Resources**: CPU, memory, disk usage

### Logging Strategy
- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Context Tracking**: Task ID, file name, analysis type
- **Error Reporting**: Detailed error context and stack traces