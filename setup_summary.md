# 📌 BÁO CÁO TỔNG HỢP CẤU HÌNH DỰ ÁN (SETUP SUMMARY)
**Tên dự án:** Music Analytics Dashboard (Spotify Tracker & AI Insights)  
**Ngày cập nhật:** 29/07/2026  
**Trạng thái:** Khởi tạo khung sườn Backend & Cấu hình môi trường thành công 🚀  

---

## 🏗️ 1. CẤU TRÚC THƯ MỤC DỰ ÁN (MONOREPO ARCHITECTURE)

Dự án được phân chia theo cấu trúc Monorepo tiêu chuẩn, tách biệt giữa Backend (Django) và Frontend (React Vite):

```text
d:\Python\music_tracking\
├── .gitignore                      # Quản lý file bỏ qua cho Git (Bảo mật & File rác)
├── .venv/                          # Môi trường ảo Python của dự án
├── project_idea.md                 # Tài liệu mô tả yêu cầu & kiến trúc hệ thống
├── requirement.txt                 # Danh sách gói thư viện Python Backend
├── setup_summary.md                # (File này) Báo cáo tổng hợp cấu hình
└── backend/                        # THƯ MỤC BACKEND (Django REST Framework)
    ├── .env                        # Biến môi trường & Bí mật (Secrets/API Keys)
    ├── db.sqlite3                  # Database SQLite mặc định cho môi trường Dev
    ├── manage.py                   # Script quản trị Django
    ├── config/                     # Cấu hình gốc Django (settings.py, urls.py)
    ├── users/                      # App xử lý User & Spotify OAuth Login
    ├── tracker/                    # App quản lý Lịch sử nghe nhạc & Celery Task
    ├── analytics/                  # App tính toán dữ liệu Biểu đồ (Heatmap, Radar, Bar Chart Race)
    └── ai_engine/                  # App tích hợp Gemini AI Persona & KNN Recommendation
```

---

## 🛠️ 2. DANH SÁCH THƯ VIỆN ĐÃ CÀI ĐẶT (`requirement.txt`)

Tất cả các thư viện dưới đây đã được cài đặt thành công vào môi trường ảo `.venv`:

| Thư viện | Phiên bản | Mục đích sử dụng |
| :--- | :--- | :--- |
| **`Django`** | `>=5.0,<6.0` | Framework Backend chính |
| **`djangorestframework`** | `>=3.15.0` | Xây dựng RESTful API cho Frontend kết nối |
| **`django-cors-headers`** | `>=4.3.0` | Bật CORS cho phép Frontend (Vite/React) truy cập API |
| **`spotipy` & `requests`** | `>=2.23.0` | Thư viện làm việc trực tiếp với Spotify API |
| **`celery` & `redis`** | `>=5.3.6` | Xử lý các tác vụ cào dữ liệu ngầm (Auto-Scrobble 24/7) |
| **`django-celery-beat`** | `>=2.6.0` | Tự động hóa lên lịch chạy định kỳ (15-30 phút/lần) |
| **`psycopg2-binary`** | `>=2.9.9` | Driver kết nối cơ sở dữ liệu PostgreSQL |
| **`dj-database-url`** | `>=2.1.0` | Tự động chuyển đổi giữa SQLite3 và PostgreSQL qua `.env` |
| **`google-genai`** | `>=0.1.1` | SDK AI Google Gemini (Tạo văn bản AI Music Persona) |
| **`scikit-learn`** | `>=1.4.0` | Thuật toán KNN gợi ý bài hát theo thuộc tính âm thanh |
| **`pandas` & `numpy`** | `>=2.2.0` | Xử lý ma trận dữ liệu nghe nhạc & thống kê |
| **`python-dotenv`** | `>=1.0.1` | Nạp biến môi trường từ file `.env` vào Django |

---

## ⚙️ 3. CHI TIẾT CẤU HÌNH CÁC FILE CHÍNH

### 3.1. File Bảo mật `backend/.env`
> [!IMPORTANT]
> File này chứa thông tin bảo mật và API Key. **Tuyệt đối không push file này lên GitHub/GitLab.**

```env
# DJANGO CORE
SECRET_KEY=django-insecure-music-analytics-dev-key-987654321
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# SPOTIFY API (Đăng ký tại: https://developer.spotify.com/dashboard)
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8000/api/users/spotify/callback/

# GEMINI AI (Lấy tại: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# DATABASE (Mặc định SQLite, chuyển PostgreSQL bằng cách đổi chuỗi kết nối)
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

---

### 3.2. Cấu hình Django `backend/config/settings.py`
Đã cập nhật các thành phần cốt lõi:
- **Tự động nạp `.env`:** Sử dụng `dotenv.load_dotenv(BASE_DIR / '.env')`.
- **Đăng ký Installed Apps:** Đã thêm `rest_framework`, `corsheaders`, `users`, `tracker`, `analytics`, `ai_engine`.
- **Cấu hình Middleware:** Đã thêm `corsheaders.middleware.CorsMiddleware`.
- **Cấu hình Linh hoạt Database (`dj_database_url`):** Tự động chuyển đổi giữa SQLite và PostgreSQL dựa vào `DATABASE_URL` trong `.env`.

---

### 3.3. Quyền bỏ qua Git (`.gitignore`)
Đã thiết lập đầy đủ các quy tắc bảo mật & loại bỏ file rác:
- Bỏ qua file môi trường: `.env`, `*.env`
- Bỏ qua môi trường ảo: `.venv/`
- Bỏ qua Database local & cache: `*.sqlite3`, `__pycache__/`
- Bỏ qua thư mục Frontend build sau này: `node_modules/`, `dist/`

---

## 🗄️ 4. TRẠNG THÁI CƠ SỞ DỮ LIỆU (DATABASE STATUS)

- **Hiện tại:** Dự án đang chạy trên **SQLite3** (`backend/db.sqlite3`) và đã áp dụng thành công các lệnh `migrate` cơ bản của Django.
- **Khuyên dùng khi chạy thật:** Chuyển sang **PostgreSQL** để xử lý tác vụ ghi ngầm 24/7 không bị nghẽn (`database is locked`).
- **Cách chuyển PostgreSQL Cloud (Miễn phí):**
  1. Đăng ký tại [Neon.tech](https://neon.tech) ➔ Lấy `Connection String`.
  2. Dán vào `DATABASE_URL` trong `backend/.env`.
  3. Chạy `python manage.py migrate`.

---

## 🚀 5. CÁC LỆNH THƯỜNG DÙNG ĐỂ VẬN HÀNH BACKEND

1. **Kích hoạt môi trường ảo (PowerShell):**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Kiểm tra trạng thái Django:**
   ```powershell
   cd backend
   python manage.py check
   ```

3. **Khởi chạy Server Development:**
   ```powershell
   cd backend
   python manage.py runserver
   ```

4. **Tạo Superuser quản trị:**
   ```powershell
   cd backend
   python manage.py createsuperuser
   ```

---

## 🎯 6. CÁC BƯỚC TIẾP THEO (NEXT STEPS)
1. 🔑 Điền `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET` vào file `backend/.env`.
2. ⚛️ Khởi tạo dự án Frontend React (Vite + Tailwind CSS + Shadcn UI).
3. 📐 Thiết kế Models cho App `users` & `tracker` (User Spotify Token, Listening History).
