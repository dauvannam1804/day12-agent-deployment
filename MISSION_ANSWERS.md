# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **Hardcoded Secrets**: API keys (`OPENAI_API_KEY`) và Database URL (`DATABASE_URL`) bị để lộ ngay trong mã nguồn.
2. **Thiếu Quản lý Cấu hình (Config Management)**: Các biến cấu hình như `DEBUG`, `MAX_TOKENS` bị gán cứng (hardcoded) thay vì đọc từ biến môi trường.
3. **Sử dụng Print thay vì Logging**: Dùng hàm `print()` không có cấu trúc và thậm chí in cả Secret ra log (dòng 34), gây nguy cơ bảo mật.
4. **Không có Health Check Endpoint**: Thiếu endpoint `/health` để các nền tảng Cloud có thể kiểm tra trạng thái sống/chết của Agent.
5. **Gán cứng Port và Host**: Sử dụng `host="localhost"` và `port=8000` khiến ứng dụng không thể chạy được trên Docker hoặc các nền tảng như Railway/Render vốn yêu cầu nghe ở `0.0.0.0` và cổng động.
6. **Sử dụng Query Parameter thay vì Request Body**: Truyền dữ liệu trên URL (`?question=...`) bị giới hạn độ dài và dễ lỗi ký tự đặc biệt.
   - *Ví dụ:* Thay vì dùng `def ask(question: str)`, nên dùng Pydantic Model:
     ```python
     class Req(BaseModel): question: str
     @app.post("/ask")
     def ask(data: Req): ...
     ```
7. **Thiếu xử lý bất đồng bộ (Non-async)**: Sử dụng `def` thay vì `async def` làm giảm khả năng xử lý đồng thời (concurrency) của ứng dụng FastAPI khi gọi các dịch vụ I/O như LLM API.
8. **Hoàn toàn thiếu lớp bảo vệ (No Security)**: API được công khai hoàn toàn, không có cơ chế Authentication (API Key, JWT), dẫn đến nguy cơ bị lạm dụng tài nguyên và chi phí LLM.
9. **Thiếu giới hạn tần suất (No Rate Limiting)**: Không có cơ chế ngăn chặn spam hoặc tấn công DoS, dễ gây quá tải server và thâm hụt ngân sách API.
10. **Không có Graceful Shutdown**: App bị tắt đột ngột (giống rút phích cắm), làm ngắt các request đang xử lý dở dang.
    - **Hậu quả:** 
        1. **Lỗi người dùng:** User nhận lỗi 502/504 thay vì câu trả lời hoàn chỉnh.
        2. **Lãng phí tài nguyên:** AI Agent đã chạy xong logic (đã tốn tiền gọi LLM) nhưng chưa kịp trả về cho user thì app đã bị tắt -> Tốn tiền API vô ích.
        3. **Lỗi dữ liệu:** Nếu app đang ghi dở vào database (ví dụ lưu lịch sử chat) thì dữ liệu sẽ bị "què cụt", không nhất quán.
    - *Ví dụ:* Giống nhà hàng đuổi khách ngay khi đang ăn để đóng cửa thay vì ngừng nhận khách mới và đợi khách cũ ăn xong.


### Exercise 1.3: Comparison table (Bản đầy đủ)
| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
| :--- | :--- | :--- | :--- |
| **Quản lý cấu hình** | Gán cứng (Hardcoded) trong code. | `Pydantic Settings` + `.env`. | Bảo mật, dễ thay đổi (Rotate) key mà không cần sửa code. |
| **Bảo mật (CORS)** | Không cấu hình. | `CORSMiddleware` (Whitelist). | Chỉ cho phép Website của bạn gọi API, chặn đứng các trang web hacker. |
| **Logging** | Dùng `print()` thô sơ. | **Structured JSON Logging**. | Giúp máy móc có thể đọc và phân tích log tự động (Search, Alert). |
| **Xử lý Shutdown** | Tắt đột ngột (Hard kill). | **Graceful Shutdown** (SIGTERM). | Để app "ăn nốt miếng cuối" (trả lời xong request) rồi mới nghỉ. |
| **Health Check** | Không có. | `/health` (Liveness probe). | Để Cloud Platform tự động khởi động lại nếu app bị "đơ". |
| **Async/Await** | Đồng bộ (`def`). | Bất đồng bộ (`async def`). | Giúp server chịu tải cao (nhiều người dùng cùng lúc) mà không bị nghẽn. |
| **Cách chạy app** | `uvicorn.run(app)`. | `uvicorn.run("app:app")`. | Hỗ trợ tính năng Reload và Multi-processing chuyên nghiệp. |
| **Validation** | Không có. | Đọc metadata từ `settings`. | Đảm bảo các tham số cấu hình luôn đúng kiểu dữ liệu trước khi chạy. |

###  Checkpoint 1

- [x] Hiểu tại sao hardcode secrets là nguy hiểm
- [x] Biết cách dùng environment variables
- [x] Hiểu vai trò của health check endpoint
- [x] Biết graceful shutdown là gì


## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: `python:3.11` (Bản phân phối Python đầy đủ, dung lượng khoảng 1GB).
2. Working directory: `/app` (Mọi lệnh phía sau như COPY, RUN sẽ mặc định thực hiện tại đây).
3. Tại sao COPY requirements.txt trước?
   - Để tận dụng **Docker Layer Cache**. Vì thư viện ít thay đổi hơn code, nên cài chúng trước giúp Docker không phải tải lại thư viện mỗi khi bạn sửa code, làm giảm thời gian build từ vài phút xuống vài giây.
4. CMD vs ENTRYPOINT khác nhau thế nào? Tại sao ở đây dùng CMD?
   - `CMD`: Đặt lệnh mặc định, dễ dàng bị ghi đè (override) khi chạy lệnh `docker run <image> <lệnh_mới>`.
   - `ENTRYPOINT`: Đặt lệnh chính, không bị ghi đè bởi các tham số truyền vào lệnh `docker run`.
   - **Tại sao dùng CMD ở đây?** Vì đây là Image phục vụ việc phát triển (develop). Dùng `CMD` giúp lập trình viên dễ dàng ghi đè lệnh mặc định để nhảy vào bên trong container kiểm tra (ví dụ: `docker run -it agent-develop bash`) hoặc chạy các lệnh test khác mà không cần sửa Dockerfile.

### Exercise 2.2: Build và run

**Lưu ý sửa lỗi (Bug Fix):** 
Code gốc trong `app.py` dùng Query Parameter nên bị lỗi khi dùng lệnh `curl` có `-d` (JSON Body). Tôi đã sửa code sang dùng **Pydantic BaseModel** để nhận dữ liệu qua JSON Body cho đúng chuẩn.

**Quy trình chạy lại:**
Vì mã nguồn đã thay đổi, chúng ta **bắt buộc** phải thực hiện lại 2 bước này để cập nhận code mới vào trong Image:

1. **Build lại Image:**
   ```bash
   # Đứng tại thư mục gốc day12-agent-deployment
   docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
   ```

2. **Chạy lại Container:**
   ```bash
   # Tắt container cũ nếu đang chạy
   docker stop $(docker ps -q --filter ancestor=my-agent:develop)
   
   # Chạy container mới
   docker run -p 8000:8000 my-agent:develop
   ```

Sau đó, lệnh `curl` gửi JSON sẽ hoạt động hoàn hảo!

**Quan sát:** Image size là `1.15GB`
```bash
docker images my-agent:develop
```

Output
```
IMAGE              ID             DISK USAGE   CONTENT SIZE   EXTRA
my-agent:develop   a301b4e4974c       1.15GB             0B  
```

###  Exercise 2.3: Multi-stage build

```bash
cd ../production
```

**Nhiệm vụ:** Đọc `Dockerfile` và tìm:
- Stage 1 làm gì?
- Stage 2 làm gì?
- Tại sao image nhỏ hơn?

Build và so sánh:
```bash
docker build -t my-agent:advanced .
docker images | grep my-agent
```

Output
```
IMAGE              ID             DISK USAGE   CONTENT SIZE   EXTRA
my-agent:advanced  9b4a682e0d77       160MB             0B  
my-agent:develop   a301b4e4974c       1.15GB            0B  
```


**Phân tích Dockerfile production:**
- **Stage 1 (Builder) làm gì?** Sử dụng image `python:3.11-slim` để cài đặt các dự phòng (dependencies) và các công cụ build (`gcc`, `libpq-dev`). Các thư viện được cài vào thư mục `/root/.local`.
- **Stage 2 (Runtime) làm gì?** Tạo một image mới từ `python:3.11-slim`. Sau đó, nó **chỉ copy** các thư viện đã cài từ Stage 1 sang Stage 2 và thêm mã nguồn vào. Stage này cũng thiết lập một `appuser` (non-root) để tăng tính bảo mật.
- **Tại sao image nhỏ hơn?** Vì Stage 2 không chứa các công cụ build (`gcc`, `apt cache`, v.v.) và các file rác phát sinh khi cài đặt thư viện. Nó chỉ giữ lại những gì thực sự cần thiết để chạy ứng dụng. Ngoài ra, việc dùng bản `-slim` thay vì bản full giúp giảm dung lượng gốc đáng kể.

**So sánh dung lượng thực tế:**
- Develop (Bản full): **1.15 GB**
- Production (Multi-stage + Slim): **160 MB**
- **Sự khác biệt:** Giảm khoảng **86%** dung lượng (nhỏ hơn gần 7 lần).

### Exercise 2.4: Docker Compose stack

**Architecture Diagram:**

```text
       [ Người dùng ]
             |
             | (Port 80)
             v
  +-----------------------+
  |  NGINX Reverse Proxy  | (Gateway)
  +----------+------------+
             |
             | (Docker Network)
             v
  +----------+------------+
  |    AI Agent Service   | (Logic)
  +--------+-------+------+
           |       |
           |       +-----------+
           v                   v
  +----------------+   +----------------+
  |     Redis      |   |     Qdrant     |
  | (Cache/State)  |   |   (Vector DB)  |
  +----------------+   +----------------+
```

**Phân tích hệ thống:**
- **Dịch vụ được khởi chạy:** 
    1. `nginx`: Đóng vai trò Reverse Proxy (cổng chào), nhận request từ người dùng.
    2. `agent`: Chứa logic chính của AI Agent.
    3. `redis`: Dùng làm cache và quản lý trạng thái phiên làm việc (session).
    4. `qdrant`: Cơ sở dữ liệu vector dùng cho RAG (Retrieval-Augmented Generation).
- **Cách thức giao tiếp:**
    - Người dùng chỉ nhìn thấy duy nhất Nginx ở port `80`.
    - Các dịch vụ bên trong giao tiếp với nhau bằng **tên service** (ví dụ: `http://redis:6379`) thông qua mạng nội bộ (Internal Network) của Docker, giúp cô lập an toàn với bên ngoài.

**Kết quả kiểm tra thực tế:**
- **Health check:**
  ```bash
  curl http://localhost/health

  # Output:
  {"status":"ok","uptime_seconds":208.4,"version":"2.0.0","timestamp":"2026-04-17T06:29:40.663874"}
  ```
- **Agent endpoint:**
  ```bash
  curl http://localhost/ask -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "Explain microservices"}'

  # Output: 
  {"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
  ```
###  Checkpoint 2

- [x] Hiểu cấu trúc Dockerfile
- [x] Biết lợi ích của multi-stage builds
- [x] Hiểu Docker Compose orchestration
- [x] Biết cách debug container (`docker logs`, `docker exec`)



## Part 3: Cloud Deployment

###  Exercise 3.1: Deploy Railway (15 phút)

```bash
cd ../../03-cloud-deployment/railway
```

**Steps:**

1. Install Railway CLI:
```bash
npm i -g @railway/cli
```

2. Login:
```bash
railway login
```

3. Initialize project:
```bash
railway init
```

4. Deploy:
```bash
railway up
```

5. Set environment variables:
```bash
railway variables set PORT=8000
railway variables set AGENT_API_KEY=my-secret-key
railway up
```

6. Get public URL:
```bash
railway domain
```

**Nhiệm vụ:** Test public URL với curl hoặc Postman.

Test:
```bash
# Health check
curl  https://soothing-kindness-production-bb69.up.railway.app/health

# Output:
{"status":"ok","uptime_seconds":2.3,"platform":"Railway","timestamp":"2026-04-17T06:38:35.867104+00:00"}

# Agent endpoint
curl https://soothing-kindness-production-bb69.up.railway.app/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'

# Output:
{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","platform":"Railway"}
```

###  Exercise 3.2: Deploy Render (15 phút)

```bash
cd ../render
```

**Steps:**

1. Push code lên GitHub (nếu chưa có)
2. Vào [render.com](https://render.com) → Sign up
3. New → Blueprint
4. Connect GitHub repo
5. Render tự động đọc `render.yaml`
6. Set environment variables trong dashboard
7. Deploy!

**Nhiệm vụ:** So sánh `render.yaml` với `railway.toml`. Khác nhau gì?

| Đặc điểm | `render.yaml` (Render Blueprints) | `railway.toml` (Railway Service Config) |
| :--- | :--- | :--- |
| **Quy mô** | **Infrastructure as Code (IaC)** - Tầm dự án. | **Service Config** - Tầm dịch vụ lẻ. |
| **Phạm vi** | Định nghĩa được **nhiều dịch vụ** (Web + Redis + DB). | Tập trung cấu hình cho **duy nhất 1** dịch vụ. |
| **Vai trò** | "Bản thiết kế" cho toàn bộ hệ thống (Stack). | "Cẩm nang hướng dẫn" cho riêng 1 ứng dụng. |
| **Cách dùng** | Deploy 1 tập hợp các tài nguyên liên kết nhau. | Tinh chỉnh cách Build và Deploy của 1 Microservice. |

Test Render URL:
```bash
# Health check
curl https://ai-agent-myo8.onrender.com/health

# Output:
{"status":"ok","uptime_seconds":562.9,"version":"1.0.0","environment":"production",...}

# Agent endpoint
curl https://ai-agent-myo8.onrender.com/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Render check"}'

# Output:
{"question":"Render check","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","model":"gpt-4o-mini"}
```

###  Exercise 3.3: (Optional) GCP Cloud Run (15 phút)

```bash
cd ../production-cloud-run
```

**Yêu cầu:** GCP account (có free tier).

**Nhiệm vụ:** Đọc `cloudbuild.yaml` và `service.yaml`. Hiểu CI/CD pipeline.

###  Checkpoint 3

- [x] Deploy thành công lên ít nhất 1 platform (Railway/Render)
- [x] Có public URL hoạt động
- [x] Hiểu cách set environment variables trên cloud
- [x] Biết cách xem logs

---

## Part 4: API Security (40 phút)

###  Concepts

**Vấn đề:** Public URL = ai cũng gọi được = hết tiền OpenAI.

**Giải pháp:**
1. **Authentication** — Chỉ user hợp lệ mới gọi được
2. **Rate Limiting** — Giới hạn số request/phút
3. **Cost Guard** — Dừng khi vượt budget

###  Exercise 4.1: API Key authentication

**Phân tích mã nguồn:**
- **API key được check ở đâu?** Được kiểm tra trong hàm `verify_api_key` (dòng 39-54) bằng thư viện `fastapi.security.api_key`. Hàm này được gắn vào endpoint `/ask` thông qua cơ chế `Depends`.
- **Điều gì xảy ra nếu sai key?**
    - Nếu thiếu Key: Trả về lỗi `401 Unauthorized`.
    - Nếu sai Key: Trả về lỗi `403 Forbidden`.
- **Làm sao rotate key?** Key được quản lý qua biến môi trường `AGENT_API_KEY`. Chỉ cần thay đổi giá trị biến này trên hệ thống (Railway/Render) và restart app mà không cần sửa code.

**Test Results:**
```bash
# 1. Không có key (Lỗi 401)
curl http://localhost:8000/ask -X POST -H "Content-Type: application/json" -d '{"question": "Hello"}'

# Output:
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

# 2. Sai key (Lỗi 403)
curl http://localhost:8000/ask -X POST -H "X-API-Key: wrong-key" -H "Content-Type: application/json" -d '{"question": "Hello"}'
# Output: 
{"detail":"Invalid API key."}

# 3. Đúng key (Thành công - 200)
curl http://localhost:8000/ask -X POST -H "X-API-Key: demo-key-change-in-production" -H "Content-Type: application/json" -d '{"question": "Hello"}'
# Output: 
{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

###  Exercise 4.2: JWT authentication (Advanced)

```bash
cd ../production
```

**Nhiệm vụ:** 
1. Đọc `auth.py` — hiểu JWT flow
2. Chạy app:
```bash
python app.py

#output:
=== Demo credentials ===
  student / demo123  (10 req/min, $1/day budget)
  teacher / teach456 (100 req/min, $1/day budget)

Docs: http://localhost:8000/docs

INFO:     Will watch for changes in these directories: ['/home/namdv/workspace/day12-agent-deployment/04-api-gateway/production']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [31155] using WatchFiles
INFO:     Started server process [31157]
INFO:     Waiting for application startup.
INFO:app:Security layer initialized
INFO:     Application startup complete.
...
```

3. Lấy token:
```bash
curl -X POST http://localhost:8000/auth/token -H "Content-Type: application/json" -d '{"username": "student", "password": "demo123"}'

#output
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0MTMxMDQsImV4cCI6MTc3NjQxNjcwNH0.QQqVjef-0Df7uBQ9zxLmZ-N847VyqB87zCeDfyG62T4","token_type":"bearer","expires_in_minutes":60,"hint":"Include in header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."}
```

4. Dùng token để gọi API:
```bash
TOKEN="<token_từ_bước_3>"
curl http://localhost:8000/ask -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain JWT"}'

#output
{"question":"Explain JWT","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}
```

###  Exercise 4.3: Rate limiting

**Nhiệm vụ:** Đọc `rate_limiter.py` và trả lời:
- **Algorithm nào được dùng?** Thuật toán **Sliding Window Counter** (Cửa sổ trượt). Nó ghi lại timestamp của từng request và loại bỏ các request cũ nằm ngoài cửa sổ thời gian 60 giây.
- **Limit là bao nhiêu requests/minute?** 10 req/phút đối với User thường và 100 req/phút đối với Admin.
- **Làm sao bypass limit cho admin?** Không bypass hoàn toàn mà thiết lập một "tier" cao hơn. Trong `app.py`, hệ thống kiểm tra trường `role` trong JWT token để quyết định sử dụng bộ giới hạn dành cho User hay Admin.

Test:
```bash
# Gọi liên tục 20 lần
for i in {1..20}; do
  curl http://localhost:8000/ask -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"question": "Test '$i'"}'
  echo ""
done

#output
{"question":"Test 1","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":9,"budget_remaining_usd":1.6e-05}}
{"question":"Test 2","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":8,"budget_remaining_usd":3.2e-05}}
{"question":"Test 3","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":7,"budget_remaining_usd":5.1e-05}}
{"question":"Test 4","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":6,"budget_remaining_usd":7e-05}}
{"question":"Test 5","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","usage":{"requests_remaining":5,"budget_remaining_usd":9.1e-05}}
{"question":"Test 6","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","usage":{"requests_remaining":4,"budget_remaining_usd":0.000112}}
{"question":"Test 7","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":3,"budget_remaining_usd":0.000128}}
{"question":"Test 8","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":2,"budget_remaining_usd":0.000144}}
{"question":"Test 9","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":1,"budget_remaining_usd":0.000163}}
{"question":"Test 10","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","usage":{"requests_remaining":0,"budget_remaining_usd":0.000184}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

Quan sát response khi hit limit.

###  Exercise 4.4: Cost guard

**Nhiệm vụ:** Đọc `cost_guard.py` và implement logic:

```python
def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, False nếu vượt.
    
    Logic:
    - Mỗi user có budget $10/tháng
    - Track spending trong Redis
    - Reset đầu tháng
    """
    # TODO: Implement
    pass
```

<details>
<summary> Solution</summary>

```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False
    
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # 32 days
    return True
```

</details>

###  Checkpoint 4

- [x] Implement API key authentication
- [x] Hiểu JWT flow
- [x] Implement rate limiting
- [x] Implement cost guard với Redis

---

## Part 5: Scaling & Reliability (40 phút)

###  Concepts

**Vấn đề:** 1 instance không đủ khi có nhiều users.

**Giải pháp:**
1. **Stateless design** — Không lưu state trong memory
2. **Health checks** — Platform biết khi nào restart
3. **Graceful shutdown** — Hoàn thành requests trước khi tắt
4. **Load balancing** — Phân tán traffic

###  Exercise 5.1: Health checks

```bash
cd ../../05-scaling-reliability/develop
```

**Nhiệm vụ:** Implement 2 endpoints:

```python
@app.get("/health")
def health():
    """Liveness probe — container còn sống không?"""
    # TODO: Return 200 nếu process OK
    pass

@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic không?"""
    # TODO: Check database connection, Redis, etc.
    # Return 200 nếu OK, 503 nếu chưa ready
    pass
```

<details>
<summary> Solution</summary>

```python
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        # Check Redis
        r.ping()
        # Check database
        db.execute("SELECT 1")
        return {"status": "ready"}
    except:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready"}
        )
```

</details>

###  Exercise 5.2: Graceful shutdown

**Nhiệm vụ:** Implement signal handler:

```python
import signal
import sys

def shutdown_handler(signum, frame):
    """Handle SIGTERM from container orchestrator"""
    # TODO:
    # 1. Stop accepting new requests
    # 2. Finish current requests
    # 3. Close connections
    # 4. Exit
    pass

signal.signal(signal.SIGTERM, shutdown_handler)
```

Test:
```bash
python app.py &
PID=$!

# Gửi request
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Long task"}' &

# Ngay lập tức kill
kill -TERM $PID

# Quan sát: Request có hoàn thành không?
```

**Log thực tế:**
```bash
# Terminal 1: App log
2026-04-17 15:51:49,076 INFO Processing question: Test Graceful Shutdown
INFO:     Shutting down
INFO:     Waiting for connections to close. (CTRL+C to force quit)
INFO:     127.0.0.1:52478 - "POST /ask HTTP/1.1" 200 OK
2026-04-17 15:51:54,297 INFO 🔄 Graceful shutdown initiated...
2026-04-17 15:51:54,297 INFO ✅ Shutdown complete

# Terminal 2: Curl output
{"question":"Test Graceful Shutdown","answer":"...","note":"Request completed successfully even during shutdown!"}
```

**Kết quả:** Có, request đã hoàn thành 100% với mã trả về 200 OK.

**Phân tích log:**
- Mặc dù lệnh `kill -TERM` được gửi ngay sau khi request bắt đầu, nhưng Agent không hề bị tắt đột ngột.
- Uvicorn đã giữ process tồn tại trong trạng thái "Waiting for connections to close" để đợi hàm `ask_agent` xử lý xong (mất 5 giây `asyncio.sleep`).
- Chỉ sau khi dữ liệu đã được gửi trả về cho Client (lệnh `curl` nhận được JSON), Agent mới thực hiện các bước shutdown cuối cùng và thoát hoàn toàn.
- **Kết luận:** Hệ thống đã thực hiện đúng cơ chế Graceful Shutdown, giúp tránh tình trạng mất dữ liệu hoặc làm lỗi request của người dùng khi hệ thống cần bảo trì hoặc scale-down.


###  Exercise 5.3: Stateless design

```bash
cd ../production
```

**Nhiệm vụ:** Refactor code để stateless.

###  Exercise 5.3: Stateless design
**Nhiệm vụ:** Refactor code để stateless.

**Anti-pattern:**
```python
# Mọi thứ lưu trong RAM của 1 instance đơn lẻ
_memory_store: dict = {}

def save_session(session_id: str, data: dict):
    # Dữ liệu sẽ mất khi restart server hoặc khi request nhảy sang instance khác
    _memory_store[f"session:{session_id}"] = data
```

**Correct:**
```python
# Dữ liệu tập trung tại Redis (mọi instance đều truy cập được)
_redis = redis.from_url(REDIS_URL, decode_responses=True)

def save_session(session_id: str, data: dict):
    # Dữ liệu tồn tại độc lập với lifecycle của Agent
    _redis.setex(f"session:{session_id}", 3600, json.dumps(data))
```

**Phân tích log khởi tạo:**
```bash
agent-1  | INFO:app:Starting instance instance-5c83a2
agent-1  | INFO:app:Storage: Redis ✅
agent-1  | ✅ Connected to Redis
```
=> Chứng tỏ các Agent đã được cấu hình Stateless thành công.

###  Exercise 5.4: Load balancing
**Nhiệm vụ:** Quan sát Nginx phân tán requests.

**Log hệ thống (`docker compose logs agent`):**
```bash
agent-3  | INFO: 172.18.0.6:49034 - "POST /chat HTTP/1.1" 200 OK
agent-1  | INFO: 172.18.0.6:34296 - "POST /chat HTTP/1.1" 200 OK
agent-2  | INFO: 172.18.0.6:44242 - "POST /chat HTTP/1.1" 200 OK
```
**Quan sát:** Các request từ IP của Nginx (`172.18.0.6`) được luân chuyển đều qua cả 3 container `agent-1`, `agent-2`, `agent-3` theo cơ chế Round Robin.

###  Exercise 5.5: Test stateless
**Nhiệm vụ:** Kiểm chứng Session được bảo toàn khi đi qua nhiều instance.

**Log chạy `test_stateless.py`:**
```bash
============================================================
Stateless Scaling Demo
============================================================
Session ID: 70229f01-c808-4863-98f8-929836cd4767

Request 1: [instance-b98347]
Request 2: [instance-5c83a2]
Request 3: [instance-4c143e]
Request 4: [instance-b98347]
Request 5: [instance-5c83a2]

------------------------------------------------------------
Instances used: {'instance-b98347', 'instance-4c143e', 'instance-5c83a2'}
✅ All requests served despite different instances!

--- Conversation History ---
Total messages: 10
...
✅ Session history preserved across all instances via Redis!
```
**Kết luận:** Hệ thống đã đạt trạng thái Stateless hoàn toàn. User có thể tiếp tục cuộc hội thoại mà không bị ngắt quãng dù Load Balancer đẩy họ tới bất kỳ Instance nào.

###  Checkpoint 5
- [x] Implement health và readiness checks
- [x] Implement graceful shutdown
- [x] Refactor code thành stateless
- [x] Hiểu load balancing với Nginx
- [x] Test stateless design

---

## Part 6: Final Project (60 phút)

###  Objective

Build một production-ready AI agent từ đầu, kết hợp TẤT CẢ concepts đã học.

###  Requirements

**Functional:**
- [ ] Agent trả lời câu hỏi qua REST API
- [ ] Support conversation history
- [ ] Streaming responses (optional)

**Non-functional:**
- [ ] Dockerized với multi-stage build
- [ ] Config từ environment variables
- [ ] API key authentication
- [ ] Rate limiting (10 req/min per user)
- [ ] Cost guard ($10/month per user)
- [ ] Health check endpoint
- [ ] Readiness check endpoint
- [ ] Graceful shutdown
- [ ] Stateless design (state trong Redis)
- [ ] Structured JSON logging
- [ ] Deploy lên Railway hoặc Render
- [ ] Public URL hoạt động

### 🏗 Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Nginx (LB)     │
└──────┬──────────┘
       │
       ├─────────┬─────────┐
       ▼         ▼         ▼
   ┌──────┐  ┌──────┐  ┌──────┐
   │Agent1│  │Agent2│  │Agent3│
   └───┬──┘  └───┬──┘  └───┬──┘
       │         │         │
       └─────────┴─────────┘
                 │
                 ▼
           ┌──────────┐
           │  Redis   │
           └──────────┘
```


```bash
# Railway
railway init
railway variables set REDIS_URL=...
railway variables set AGENT_API_KEY=...
railway up
railway domain
```

###  Validation

Chạy script kiểm tra:

```bash
cd 06-lab-complete
python check_production_ready.py
```

```
# Output

=======================================================
  Production Readiness Check — Day 12 Lab
=======================================================

📁 Required Files
  ✅ Dockerfile exists
  ✅ docker-compose.yml exists
  ✅ .dockerignore exists
  ✅ .env.example exists
  ✅ requirements.txt exists
  ✅ railway.toml or render.yaml exists

🔒 Security
  ✅ .env in .gitignore
  ✅ No hardcoded secrets in code

🌐 API Endpoints (code check)
  ✅ /health endpoint defined
  ✅ /ready endpoint defined
  ✅ Authentication implemented
  ✅ Rate limiting implemented
  ✅ Graceful shutdown (SIGTERM)
  ✅ Structured logging (JSON)

🐳 Docker
  ✅ Multi-stage build
  ✅ Non-root user
  ✅ HEALTHCHECK instruction
  ✅ Slim base image
  ✅ .dockerignore covers .env
  ✅ .dockerignore covers __pycache__

=======================================================
  Result: 20/20 checks passed (100%)
  🎉 PRODUCTION READY! Deploy nào!
=======================================================
```

Script sẽ kiểm tra:
-  Dockerfile exists và valid
-  Multi-stage build
-  .dockerignore exists
-  Health endpoint returns 200
-  Readiness endpoint returns 200
-  Auth required (401 without key)
-  Rate limiting works (429 after limit)
-  Cost guard works (402 when exceeded)
-  Graceful shutdown (SIGTERM handled)
-  Stateless (state trong Redis, không trong memory)
-  Structured logging (JSON format)

###  Grading Rubric

| Criteria | Points | Description |
|----------|--------|-------------|
| **Functionality** | 20 | Agent hoạt động đúng |
| **Docker** | 15 | Multi-stage, optimized |
| **Security** | 20 | Auth + rate limit + cost guard |
| **Reliability** | 20 | Health checks + graceful shutdown |
| **Scalability** | 15 | Stateless + load balanced |
| **Deployment** | 10 | Public URL hoạt động |
| **Total** | 100 | |

---

##  Hoàn Thành!

Bạn đã:
-  Hiểu sự khác biệt dev vs production
-  Containerize app với Docker
-  Deploy lên cloud platform
-  Bảo mật API
-  Thiết kế hệ thống scalable và reliable

###  Next Steps

1. **Monitoring:** Thêm Prometheus + Grafana
2. **CI/CD:** GitHub Actions auto-deploy
3. **Advanced scaling:** Kubernetes
4. **Observability:** Distributed tracing với OpenTelemetry
5. **Cost optimization:** Spot instances, auto-scaling

###  Resources

- [12-Factor App](https://12factor.net/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Railway Docs](https://docs.railway.app/)
- [Render Docs](https://render.com/docs)