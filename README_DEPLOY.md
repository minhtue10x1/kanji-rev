# Hướng Dẫn Deploy Kanji Master Lên Vercel + Vercel Postgres

Hệ thống được thiết kế theo kiến trúc **Unified Vercel Serverless Architecture** (Gộp toàn bộ Frontend, Backend Serverless Functions và Database Postgres trên cùng 1 Vercel Dashboard).

---

## 1. Kiến trúc triển khai

- **Frontend:** Single Page App chạy trên Vercel Global Edge CDN (`index.html`, `kanji-data.js`).
- **Backend API:** FastAPI chạy qua Vercel Python Serverless Functions (`api/index.py`).
- **Database:** **Vercel Postgres (Neon)** — Database PostgreSQL serverless chính chủ của Vercel, tự động scale, kết nối qua biến môi trường `POSTGRES_URL`.
- **Cục bộ (Local Dev):** Tự động chuyển về SQLite (`kanji_users.db`) mà không cần cài đặt Postgres.

---

## 2. Các bước Deploy qua GitHub (Khuyên dùng - 2 phút)

### Bước 1: Đẩy mã nguồn lên GitHub của bạn
Mở terminal tại thư mục dự án `d:\Projects\kanji-rev` và chạy:
```bash
git init
git add .
git commit -m "feat: complete kanji master 5 levels with vercel postgres support"
git branch -M main
git remote add origin https://github.com/TÊN_GITHUB_CỦA_BẠN/kanji-rev.git
git push -u origin main
```
*(File `.gitignore` đã được cấu hình tự động loại bỏ các file PDF 90MB và file database local để repo siêu nhẹ, chỉ vài MB).*

---

### Bước 2: Import dự án vào Vercel
1. Đăng nhập vào [Vercel Dashboard](https://vercel.com).
2. Bấm nút **"Add New..."** $\rightarrow$ chọn **"Project"**.
3. Chọn kho chứa GitHub `kanji-rev` vừa push và bấm **"Import"**.
4. Để nguyên tất cả thiết lập mặc định (Framework Preset: *Other*, Root Directory: `./`).
5. Bấm **"Deploy"**.

---

### Bước 3: Tạo và kết nối Vercel Postgres (1 Cú Click)
1. Trong màn hình Project vừa tạo trên Vercel, chuyển sang tab **"Storage"**.
2. Bấm nút **"Create Database"** $\rightarrow$ Chọn **"Postgres"** (Powered by Neon).
3. Đặt tên database (ví dụ: `kanji-master-db`), chọn khu vực máy chủ (khuyên dùng `Singapore - sin1` để tốc độ về Việt Nam nhanh nhất).
4. Bấm **"Create & Continue"**.
5. Ở bước kế tiếp, bấm **"Connect to Project"** và chọn project `kanji-rev` của bạn.
6. **Xong!** Vercel sẽ tự động inject `POSTGRES_URL` vào biến môi trường. Khi có request đầu tiên, hệ thống sẽ tự động tạo bảng (users, progress, sessions, logs) và index.

---

### Bước 4 (Tùy chọn): Cấu hình Google Login
1. Vào [Google Cloud Console](https://console.cloud.google.com/) $\rightarrow$ **APIs & Services** $\rightarrow$ **Credentials**.
2. Tạo **OAuth 2.0 Client ID** (Web application).
3. Thêm domain Vercel của bạn vào **Authorized JavaScript origins** (ví dụ `https://kanji-rev.vercel.app`).
4. Vào Vercel Project $\rightarrow$ **Settings** $\rightarrow$ **Environment Variables**, thêm biến:
   - Name: `GOOGLE_CLIENT_ID`
   - Value: `client-id-cua-ban.apps.googleusercontent.com`
5. Bấm **Save** và Redeploy lại phiên bản mới nhất.

---

## 3. Cấu hình file đã chuẩn bị sẵn trong mã nguồn
- `vercel.json`: Định tuyến `/api/*` sang serverless Python `api/index.py`, static files phục vụ tại root.
- `requirements.txt`: Chứa dependencies `fastapi`, `uvicorn`, `pydantic`, `psycopg2-binary`, `pg8000`.
- `database.py`: Tự động nhận diện `POSTGRES_URL` trên Vercel để kết nối PostgreSQL, hoặc dùng SQLite cục bộ khi chạy offline.
- `api/index.py`: Serverless handler tự động migrate bảng trên cold-start.
