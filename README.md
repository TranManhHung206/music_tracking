# 🎵 Music Analytics Dashboard (Spotify Tracker & AI Insights)

**Music Analytics Dashboard** là ứng dụng web tự động theo dõi lịch sử nghe nhạc của người dùng trên nền tảng Spotify theo thời gian thực (**Real-time Auto-Scrobbling**). Hệ thống cung cấp các báo cáo phân tích âm nhạc chuyên sâu, biểu đồ trực quan hóa tương tác cao và tích hợp trí tuệ nhân tạo để phân tích cá tính âm nhạc cũng như gợi ý bài hát theo vibe âm thanh.

---

## ✨ TÍNH NĂNG NỔI BẬT (FEATURES)

* 🔐 **Xác thực Spotify OAuth 2.0:** Đăng nhập trực tiếp và an toàn bằng tài khoản Spotify, tự động bảo vệ và làm mới token truy cập.
* 🔄 **Thu thập Dữ liệu Tự động (Auto-Scrobbling 24/7):** Tác vụ nền định kỳ cào lịch sử nghe nhạc gần đây (*Recently Played Tracks*) mà không yêu cầu người dùng phải mở giao diện web liên tục, tích hợp thuật toán lọc chống trùng lặp dữ liệu.
* 📊 **Thống kê & Phân tích Đa chiều:**
  * Bộ lọc dữ liệu linh hoạt: 7 ngày, 30 ngày, 1 năm hoặc khoảng thời gian tùy chọn (*Custom Date Range*).
  * **Biểu đồ Radar (Audio Features):** Phân tích các chỉ số âm thanh Spotify: `valence` (tích cực/buồn), `energy` (sôi động), `danceability`, `acousticness` và `tempo`.
  * **Listening Heatmap 24x7:** Ma trận biểu thị mật độ thói quen nghe nhạc theo từng khung giờ trong ngày và các ngày trong tuần.
  * **Bar Chart Race:** Biểu đồ cột động mô phỏng cuộc rượt đuổi thứ hạng của Top nghệ sĩ qua các mốc thời gian.
* 🤖 **Trí tuệ Nhân tạo & Gợi ý Âm nhạc:**
  * **AI Music Persona:** Sinh báo cáo nhận xét tâm lý và phong cách nghe nhạc định kỳ với Google Gemini.
  * **Smart Recommendation:** Thuật toán K-Nearest Neighbors (KNN) tìm kiếm và gợi ý các bài hát có thuộc tính âm thanh tương đồng.
* 🎨 **Giao diện Hiện đại & Chia sẻ:**
  * Giao diện tối sang trọng (*Aesthetic Dark Mode*), thiết kế tối ưu hiển thị ảnh bìa album nhạc.
  * Hỗ trợ xuất thẻ ảnh tóm tắt (*Shareable Cards*) chuẩn tỷ lệ Story để chia sẻ lên mạng xã hội.

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG (TECH STACK)

| Phân hệ | Công nghệ | Mục đích |
| :--- | :--- | :--- |
| **Backend** | Python 3 + Django 5 + Django REST Framework | Xây dựng RESTful API, ORM tối ưu hiệu năng |
| **Background Tasks** | Celery 5 + Redis | Xử lý các tác vụ cào dữ liệu ngầm và hàng đợi |
| **Scheduler** | `django-celery-beat` | Lên lịch cào dữ liệu định kỳ (15-30 phút/lần) |
| **Caching** | Redis Cache | Tối ưu thời gian phản hồi API thống kê (< 1.5s) |
| **Frontend** | React + Vite + TypeScript | Giao diện Single Page Application (SPA) |
| **Styling** | Tailwind CSS | Hệ thống giao diện Dark Mode chuẩn thẩm mỹ |
| **Charts** | Recharts, D3.js | Trực quan hóa dữ liệu biểu đồ chuyên sâu |
| **AI / Machine Learning** | Google Gemini API + `scikit-learn` | Phân tích Persona & Thuật toán KNN Audio Features |
| **Database** | PostgreSQL / SQLite3 | Lưu trữ dữ liệu quan hệ và lịch sử nghe nhạc |

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY (GETTING STARTED)

### 1. Chuẩn bị Môi trường
* Python `>= 3.10`
* Node.js `>= 18.0`
* Redis Server (chạy cục bộ hoặc Docker)

### 2. Cài đặt & Vận hành Backend

1. **Kích hoạt môi trường ảo Python:**
   ```powershell
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Cài đặt thư viện phụ thuộc:**
   ```powershell
   pip install -r requirement.txt
   ```

3. **Cấu hình file môi trường:**
   Tạo file `backend/.env` với các khóa cấu hình cần thiết:
   ```env
   SECRET_KEY=your_django_secret_key
   DEBUG=True
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIFY_REDIRECT_URI=http://localhost:8000/api/users/spotify/callback/
   GEMINI_API_KEY=your_gemini_api_key
   DATABASE_URL=sqlite:///db.sqlite3
   REDIS_URL=redis://127.0.0.1:6379/0
   CELERY_BROKER_URL=redis://127.0.0.1:6379/0
   ```

4. **Chạy Migration & Khởi động Server:**
   ```powershell
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```

5. **Khởi chạy Celery Worker & Beat (Mở terminal riêng):**
   ```powershell
   cd backend
   celery -A config worker -l info
   celery -A config beat -l info
   ```

### 3. Cài đặt & Vận hành Frontend

1. **Cài đặt dependencies:**
   ```powershell
   cd frontend
   npm install
   ```

2. **Khởi động Development Server:**
   ```powershell
   npm run dev
   ```
   Ứng dụng sẽ chạy tại: `http://localhost:5173`
