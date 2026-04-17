# Deployment Information

## Public URL
https://lab-complete-production.up.railway.app/docs

## Platform
Railway

## Test Commands

### Info
```bash
curl -X 'GET' \
  'https://lab-complete-production.up.railway.app/' \
  -H 'accept: application/json'
```

### Output
```
{
  "app": "Production AI Agent",
  "version": "1.0.0",
  "environment": "development",
  "endpoints": {
    "ask": "POST /ask (requires X-API-Key)",
    "health": "GET /health",
    "ready": "GET /ready"
  }
}
```

### Ask
```bash
curl -X 'POST' \
  'https://lab-complete-production.up.railway.app/ask' \
  -H 'accept: application/json' \
  -H 'X-API-Key: <your-key>' \
  -H 'Content-Type: application/json' \
  -d '{
  "question": "hehe",
  "session_id": "1"
}'
```

### Output
```
{
  "question": "hehe",
  "answer": "Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.",
  "model": "gpt-4o-mini",
  "timestamp": "2026-04-17T10:12:45.066019+00:00"
}
```

### Health Check
```bash
curl -X 'GET' \
  'https://lab-complete-production.up.railway.app/health' \
  -H 'accept: application/json'
```

### Output
```
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "uptime_seconds": 939.9,
  "total_requests": 4,
  "checks": {
    "llm": "mock"
  },
  "timestamp": "2026-04-17T10:16:31.550092+00:00"
}
```

### Readiness Probe
```bash
curl -X 'GET' \
  'https://lab-complete-production.up.railway.app/ready' \
  -H 'accept: application/json'
```

### Output
```
{
  "ready": true
}
```

### Metrics
```bash
curl -X 'GET' \
  'https://lab-complete-production.up.railway.app/metrics' \
  -H 'accept: application/json' \
  -H 'X-API-Key: <your-key>'
```

### Output
```
{
  "uptime_seconds": 1020.3,
  "total_requests": 11,
  "error_count": 0,
  "daily_cost_usd": 0,
  "daily_budget_usd": 5,
  "budget_used_pct": 0
}
```

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
```

##  Pre-Submission Checklist

- [x] Repository is public (or instructor has access)
- [x] `MISSION_ANSWERS.md` completed with all exercises
- [x] `DEPLOYMENT.md` has working public URL
- [x] All source code in `app/` directory
- [x] `README.md` has clear setup instructions
- [x] No `.env` file committed (only `.env.example`)
- [x] No hardcoded secrets in code
- [x] Public URL is accessible and working
- [x] Screenshots included in `screenshots/` folder
- [x] Repository has clear commit history

---