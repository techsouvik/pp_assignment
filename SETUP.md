# Quick Setup Guide

## 🚀 Get Started in 5 Minutes

### 1. Clone and Setup Environment

```bash
git clone <repo-url>
cd potpie-assignment
cp .env.example .env
```

### 2. Configure API Keys

Edit `.env` file with your keys:
```bash
# Required for AI analysis
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here

# Optional: Only needed as fallback or for private repos
# You can also pass github_token in each API request
GITHUB_TOKEN=your_github_token_here
```

**⚡ Quick Start**: You can analyze **any public GitHub repository** without any GitHub token!

### 3. Start with Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f api
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Analyze a public PR (no token needed!)
curl -X POST "http://localhost:8000/analyze-pr" \
     -H "Content-Type: application/json" \
     -d '{
       "repo_url": "https://github.com/microsoft/vscode",
       "pr_number": 200000
     }'

# For private repos, add github_token:
curl -X POST "http://localhost:8000/analyze-pr" \
     -H "Content-Type: application/json" \
     -d '{
       "repo_url": "https://github.com/your/private-repo",
       "pr_number": 123,
       "github_token": "ghp_your_token_here"
     }'
```

### 5. Monitor Progress

```bash
# Check task status (replace with your task_id)
curl http://localhost:8000/status/YOUR_TASK_ID

# Get results when completed
curl http://localhost:8000/results/YOUR_TASK_ID
```

## 🔧 Development Setup

### Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start services locally
redis-server &
postgres -D /usr/local/var/postgres &

# Run migrations
alembic upgrade head

# Start API server
python run_dev.py &

# Start Celery worker
python run_celery.py &
```

## 📊 Access Points

- **API Documentation**: http://localhost:8000/docs
- **Admin Dashboard**: http://localhost:8000/admin/health
- **Celery Flower**: http://localhost:5555
- **Database**: localhost:5432 (postgres/password)
- **Redis**: localhost:6379

## 🐛 Troubleshooting

### Common Issues

1. **API Keys not working**: Ensure keys are set in `.env` file
2. **Services not starting**: Check Docker is running and ports are free
3. **Database errors**: Run `docker-compose down -v` then `docker-compose up -d`
4. **Memory issues**: Increase Docker memory limit to 4GB+

### Logs

```bash
# API logs
docker-compose logs -f api

# Celery worker logs  
docker-compose logs -f celery-worker

# All services
docker-compose logs -f
```

## ✅ Verification Checklist

- [ ] All containers running (`docker-compose ps`)
- [ ] API responds to health check (`curl localhost:8000/health`)
- [ ] Admin endpoints work (`curl localhost:8000/admin/health`)
- [ ] Can submit analysis request
- [ ] Celery worker processing tasks
- [ ] Results stored in database

## 🔄 Next Steps

1. Try analyzing a real PR from your repository
2. Explore the admin endpoints for monitoring
3. Check the vector cache statistics
4. Review the comprehensive API documentation

Happy analyzing! 🤖