# 🤖 Day 12: AI Agent Deployment Workshop

Chào mừng bạn đến với dự án triển khai AI Agent lên Production. Đây là lộ trình từ số 0 đến một hệ thống AI có khả năng mở rộng, bảo mật và chạy ổn định trên Cloud.

## 🚀 Lộ trình bài tập (Steps 01 - 06)

### 01. Localhost vs Production
- **Mục tiêu:** Hiểu sự khác biệt giữa môi trường phát triển và thực tế.
- **Cách chạy:**
  ```bash
  cd 01-localhost-vs-production/develop
  python app.py
  ```

### 02. Dockerization
- **Mục tiêu:** Đóng gói ứng dụng vào Container để chạy ở mọi nơi.
- **Cách chạy:**
  ```bash
  cd 02-docker/production
  docker build -t ai-agent .
  docker run -p 8000:8000 ai-agent
  ```

### 03. Cloud Deployment
- **Mục tiêu:** Đưa ứng dụng lên các nền tảng Cloud (Railway/Render).
- **Cách chạy:** Xem hướng dẫn chi tiết trong file `DEPLOYMENT.md`.

### 4. API Gateway & Security
- **Mục tiêu:** Bảo mật API với Authentication và Rate Limiting.
- **Key Features:**
    - `API Key`: Bảo vệ truy cập.
    - `Rate Limit`: Chống spam.
    - `Cost Guard`: Kiểm soát chi phí LLM.

### 5. Scaling & Reliability
- **Mục tiêu:** Thiết kế hệ thống tự phục hồi và mở rộng theo chiều ngang.
- **Cách chạy (Test Stateless):**
  ```bash
  cd 05-scaling-reliability/production
  docker compose up --scale agent=3 -d
  python test_stateless.py
  ```

### 06. Final Project (Production Ready)
- **Mục tiêu:** Kết hợp tất cả kiến thức vào một Agent hoàn chỉnh.
- **Điểm nhấn:** Stateless hoàn toàn, Chat History trong Redis, Healthchecks.
- **Cách khởi chạy toàn bộ Stack:**
  ```bash
  cd 06-lab-complete
  docker compose up --build -d
  ```
- **Kiểm tra chuẩn Production:**
  ```bash
  python check_production_ready.py
  ```

## 🛠 Yêu cầu hệ thống
- **Python 3.11+**
- **Docker & Docker Compose**
- **Redis** (Hoặc dùng Docker Compose đi kèm)
- **Railway CLI** (Dành cho việc deploy lên Cloud)

## 📝 Báo cáo kết quả
- Xem toàn bộ lời giải và log thực tế tại: [MISSION_ANSWERS.md](./MISSION_ANSWERS.md)
- Xem thông tin URL công khai và test case tại: [DEPLOYMENT.md](./DEPLOYMENT.md)

---
