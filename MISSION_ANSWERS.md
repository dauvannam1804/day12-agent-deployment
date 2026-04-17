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

###  Exercise 3.3: (Optional) GCP Cloud Run (15 phút)

```bash
cd ../production-cloud-run
```

**Yêu cầu:** GCP account (có free tier).

**Nhiệm vụ:** Đọc `cloudbuild.yaml` và `service.yaml`. Hiểu CI/CD pipeline.

###  Checkpoint 3

- [ ] Deploy thành công lên ít nhất 1 platform
- [ ] Có public URL hoạt động
- [ ] Hiểu cách set environment variables trên cloud
- [ ] Biết cách xem logs

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results
[Paste your test outputs]

### Exercise 4.4: Cost guard implementation
[Explain your approach]

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
[Your explanations and test results]

---