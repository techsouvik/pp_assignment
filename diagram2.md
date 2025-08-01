# Docker Container Data Flow Diagram

## GitHub PR Analyzer - Container Architecture & Data Flow

This diagram illustrates how data flows between Docker containers in the GitHub PR Analyzer system.

```mermaid
graph TB
    %% External Systems
    User[👤 User/Client]
    GitHub[🐙 GitHub API]
    OpenAI[🤖 OpenAI API]
    Anthropic[🧠 Anthropic API]

    %% Docker Network
    subgraph DockerNetwork["🐳 pr_analyzer_network"]
        
        %% API Container
        subgraph APIContainer["📦 pr_analyzer_api<br/>Port: 8000"]
            FastAPI[FastAPI Server]
            MainApp[app.main]
            Schemas[Pydantic Schemas]
            Routes[API Routes]
        end

        %% Database Container
        subgraph DBContainer["📦 pr_analyzer_postgres<br/>Port: 5432"]
            PostgreSQL[(PostgreSQL DB)]
            AnalysisTasks[analysis_tasks table]
            AnalysisResults[analysis_results table]
            CacheEntries[cache_entries table]
        end

        %% Redis Container
        subgraph RedisContainer["📦 pr_analyzer_redis<br/>Port: 6379"]
            RedisDB[(Redis)]
            TaskQueue[Task Queue<br/>DB 1]
            ResultBackend[Result Backend<br/>DB 2]
            VectorCache[Vector Cache<br/>DB 0]
        end

        %% Celery Worker Container
        subgraph WorkerContainer["📦 pr_analyzer_celery_worker"]
            CeleryWorker[Celery Worker]
            TaskProcessor[Task Processor]
            AIAgents[AI Agents]
            Coordinator[Analysis Coordinator]
            GitHubService[GitHub Service]
            VectorCacheService[Vector Cache Service]
        end

        %% Flower Container
        subgraph FlowerContainer["📦 pr_analyzer_flower<br/>Port: 5555"]
            FlowerUI[Flower Web UI]
            TaskMonitor[Task Monitor]
        end
    end

    %% Data Flow Connections
    User -->|1. HTTP Request<br/>POST /analyze-pr| APIContainer
    APIContainer -->|2. Store Task<br/>SQL INSERT| DBContainer
    APIContainer -->|3. Queue Task<br/>Redis LPUSH| RedisContainer
    
    RedisContainer -->|4. Task Pickup<br/>Redis BRPOP| WorkerContainer
    WorkerContainer -->|5. Update Status<br/>SQL UPDATE| DBContainer
    WorkerContainer -->|6. Fetch PR Data<br/>HTTP GET| GitHub
    
    WorkerContainer -->|7. Check Cache<br/>Vector Search| RedisContainer
    WorkerContainer -->|8. AI Analysis<br/>HTTP POST| OpenAI
    WorkerContainer -->|9. AI Analysis<br/>HTTP POST| Anthropic
    
    WorkerContainer -->|10. Store Results<br/>SQL INSERT| DBContainer
    WorkerContainer -->|11. Cache Results<br/>Redis SET| RedisContainer
    WorkerContainer -->|12. Task Complete<br/>Redis SET| RedisContainer
    
    APIContainer -->|13. Get Status<br/>Redis GET| RedisContainer
    APIContainer -->|14. Get Results<br/>SQL SELECT| DBContainer
    APIContainer -->|15. HTTP Response<br/>JSON| User
    
    FlowerContainer -->|Monitor Tasks<br/>Redis MONITOR| RedisContainer
    User -->|View Monitoring<br/>HTTP GET| FlowerContainer

    %% Container Health Checks
    APIContainer -.->|Health Check| DBContainer
    APIContainer -.->|Health Check| RedisContainer
    WorkerContainer -.->|Health Check| DBContainer
    WorkerContainer -.->|Health Check| RedisContainer
    FlowerContainer -.->|Health Check| RedisContainer
```

## Container-Specific Data Flow Details

### 1. API Container (`pr_analyzer_api`)
**Image**: `potpie-assignemnt-api`  
**Port**: `8000:8000`  
**Health**: `/health` endpoint

**Data Flow**:
```
Incoming:
├── HTTP Requests from Users (Port 8000)
├── Environment Variables (.env file)
└── Docker Volumes (shared code)

Outgoing:
├── Database Queries → PostgreSQL Container (Port 5432)
├── Redis Commands → Redis Container (Port 6379)
├── Task Queuing → Redis DB 1
├── Result Retrieval → Redis DB 2
└── HTTP Responses → Users
```

**Internal Data Processing**:
- Request validation via Pydantic schemas
- Task creation and queuing
- Status checking and result retrieval
- Health monitoring of dependent services

### 2. PostgreSQL Container (`pr_analyzer_postgres`)
**Image**: `postgres:latest`  
**Port**: `5432:5432`  
**Health**: PostgreSQL health check

**Data Storage**:
```
Tables:
├── analysis_tasks
│   ├── Task metadata and status
│   ├── PR information
│   └── Progress tracking
├── analysis_results
│   ├── Individual code issues
│   ├── Severity levels
│   └── AI suggestions
└── cache_entries
    ├── Vector embeddings
    ├── Cached analysis results
    └── Usage statistics
```

**Data Flow**:
- Receives SQL queries from API and Worker containers
- Stores persistent data (tasks, results, cache)
- Provides ACID transactions for data consistency

### 3. Redis Container (`pr_analyzer_redis`)
**Image**: `redis:latest`  
**Port**: `6379:6379`  
**Health**: Redis ping check

**Database Organization**:
```
DB 0: Vector Cache
├── Semantic embeddings
├── Code similarity vectors
└── Cache hit/miss tracking

DB 1: Celery Task Queue (Broker)
├── Pending tasks
├── Task routing
└── Priority queues

DB 2: Celery Result Backend
├── Task results
├── Task status
└── Progress updates
```

**Data Flow**:
- Task queuing: API → Redis → Worker
- Result storage: Worker → Redis → API
- Caching: Worker ↔ Redis (bidirectional)
- Monitoring: Flower ← Redis

### 4. Celery Worker Container (`pr_analyzer_celery_worker`)
**Image**: `potpie-assignemnt-celery-worker`  
**Health**: Custom health check task

**Internal Components**:
```
Processing Pipeline:
├── Task Reception (from Redis)
├── GitHub API Integration
├── AI Agent Coordination
│   ├── Style Agent
│   ├── Bug Detection Agent
│   ├── Security Agent
│   └── Performance Agent
├── Vector Cache Management
├── Result Aggregation
└── Status Updates
```

**Data Flow**:
```
Input Sources:
├── Task Queue (Redis DB 1)
├── GitHub API (PR data)
├── Vector Cache (Redis DB 0)
└── Database (task metadata)

Output Destinations:
├── Analysis Results (PostgreSQL)
├── Task Status (Redis DB 2)
├── Vector Cache (Redis DB 0)
├── AI APIs (OpenAI, Anthropic)
└── GitHub API (PR comments)
```

### 5. Flower Container (`pr_analyzer_flower`)
**Image**: `potpie-assignemnt-celery-flower`  
**Port**: `5555:5555`  
**Health**: Flower web interface

**Monitoring Data**:
```
Real-time Metrics:
├── Active Workers
├── Task Queue Length  
├── Task Processing Rate
├── Failed Task Count
├── Worker Resource Usage
└── Task History
```

**Data Flow**:
- Connects to Redis for task monitoring
- Provides web interface for task visualization
- Real-time updates via WebSocket connections

## Inter-Container Communication

### Network Configuration
```yaml
Network: pr_analyzer_network
Type: bridge
Containers: All 5 containers
DNS: Automatic container name resolution
```

### Service Discovery
```
Container Communication:
├── api → postgres (database queries)
├── api → redis (task queuing, status)
├── celery-worker → postgres (result storage)
├── celery-worker → redis (task processing)
├── celery-flower → redis (monitoring)
└── All containers → external APIs
```

### Data Persistence
```
Volumes:
├── postgres_data (PostgreSQL data)
├── redis_data (Redis snapshots)
└── Shared application code
```

## Container Startup Sequence

```mermaid
sequenceDiagram
    participant DC as Docker Compose
    participant PG as PostgreSQL
    participant RD as Redis
    participant API as FastAPI
    participant CW as Celery Worker
    participant FL as Flower

    DC->>PG: 1. Start PostgreSQL
    DC->>RD: 2. Start Redis
    
    Note over PG,RD: Wait for health checks
    
    DC->>API: 3. Start FastAPI
    API->>PG: 4. Create tables
    API->>RD: 5. Test connections
    
    DC->>CW: 6. Start Celery Worker
    CW->>PG: 7. Connect to database
    CW->>RD: 8. Connect to broker
    
    DC->>FL: 9. Start Flower
    FL->>RD: 10. Connect for monitoring
    
    Note over API,FL: All services healthy
```

## Environment Variables Flow

```
.env file → Docker Compose → Container Environment
├── Database credentials
├── Redis connection strings
├── API keys (OpenAI, Anthropic, GitHub)
├── Application settings
└── Debug flags
```

## Data Security & Isolation

### Container Isolation
- Each container runs in isolated namespace
- Network communication only through defined ports
- File system isolation except shared volumes

### Data Protection
- Database credentials via environment variables
- API keys secured in container environment
- Redis password protection (if configured)
- Internal network communication only

## Scaling Considerations

### Horizontal Scaling
```
Scalable Components:
├── Celery Workers (multiple instances)
├── API Servers (load balancer needed)
└── Redis (cluster mode)

Fixed Components:
├── PostgreSQL (single master)
└── Flower (single monitoring instance)
```

This Docker-specific data flow diagram shows how the containerized architecture enables scalable, maintainable, and secure processing of GitHub PR analysis requests through well-defined container boundaries and communication patterns.