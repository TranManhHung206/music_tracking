# Music Analytics Dashboard (Spotify Tracker & AI Insights)

Music Analytics Dashboard là nền tảng web giúp người dùng tự động theo dõi, thống kê và trực quan hóa thói quen nghe nhạc trên Spotify theo thời gian thực. Hệ thống kết hợp hệ thống phân tích chuyên sâu cùng các mô hình Trí tuệ Nhân tạo và Học máy để giúp bạn thấu hiểu gu âm nhạc của chính mình.

---

## Tính Năng Nổi Bật

### 1. Đồng Bộ & Theo Dõi Lượt Nghe Tự Động
* Đăng nhập an toàn trực tiếp bằng tài khoản Spotify thông qua giao thức OAuth 2.0.
* Tự động thu thập và cập nhật lịch sử nghe nhạc mới nhất vào cơ sở dữ liệu mà không cần thao tác thủ công.
* Hỗ trợ nút bấm đồng bộ tức thì và cơ chế tự động lấy tiếp các bài hát vừa nghe.

### 2. Bảng Điều Khiển Phân Tích Trực Quan
* Biểu đồ Radar Đặc tính Âm thanh: Trích xuất trực tiếp từ sóng âm thanh 30 giây (DSP Engine) bằng thư viện `librosa` để đo đạc chuẩn xác BPM thật, năng lượng RMS thật, độ mộc mạc và tâm trạng bài hát.
* Bản đồ Nhiệt 24x7: Trực quan hóa mật độ nghe nhạc theo từng khung giờ trong ngày và từng ngày trong tuần.
* So Sánh Lượt Nghe Theo Tuần: Biểu đồ cột trực quan so sánh số lượt nghe mỗi ngày giữa tuần này và tuần trước kèm thông số tăng trưởng.
* Phân Bố Thể Loại Âm Nhạc Lai (Hybrid Genre Classification): Kết hợp thông minh giữa siêu dữ liệu ngôn ngữ/vùng miền và 5 chỉ số sóng âm thanh DSP để bóc tách chính xác các dòng nhạc (V-Pop Acoustic/Indie, V-Pop Electronic/Dance, EDM, Phonk, Lo-Fi, Hip-Hop...).
* Bảng Xếp Hạng Toàn Diện: Theo dõi Top Bài Hát, Top Nghệ Sĩ (đồng bộ ảnh chân dung chính chủ từ Spotify Web API theo mã định danh spotify_id riêng biệt) và Top Album được nghe nhiều nhất.
* Nhật Ký Nghe Gần Đây: Xem danh sách chi tiết các lượt nghe mới nhất với đầy đủ ảnh bìa và thông tin bài hát.

### 3. Bộ Lọc Chu Kỳ Thời Gian Cố Định
* Dễ dàng lựa chọn và tra cứu thống kê theo các chu kỳ cố định: Tuần (ISO Week từ Thứ Hai đến Chủ Nhật), Tháng hoặc Năm.
* Danh sách chu kỳ được sắp xếp trực quan từ hiện tại trở về quá khứ, kèm tổng số lượt nghe thực tế trên từng chu kỳ.
* Tự động thông báo khi xem các chu kỳ trong quá khứ chưa có dữ liệu kèm nút quay về kỳ hiện tại.

### 4. AI Music Persona & Gợi Ý Bài Hát
* Hồ sơ Tính cách Âm nhạc AI: Tích hợp mô hình AI (Groq hoặc Google Gemini) để phân tích tâm lý, cảm xúc nghe nhạc, khung giờ thưởng thức lý tưởng và lời khuyên âm nhạc dành riêng cho bạn.
* Gợi ý Bài hát Thông minh: Sử dụng thuật toán Machine Learning (KNN) để tìm kiếm và đề xuất các bài hát có giai điệu, phong cách tương đồng nhất với sở thích của bạn.

### 5. Giao Diện Obsidian Dark Mode & Chia Sẻ Mạng Xã Hội
* Giao diện tối Obsidian hiện đại, phù hợp với phong cách âm nhạc và tôn mắt khi xem vào ban đêm.
* Chế độ Xem thử (Demo Mode): Trải nghiệm đầy đủ mọi tính năng với dữ liệu mẫu ngay cả khi chưa kết nối tài khoản Spotify.
* Xuất Thẻ Chia Sẻ: Tạo thẻ ảnh tổng kết gu âm nhạc chuẩn tỉ lệ Story 9:16 sắc nét để chia sẻ lên mạng xã hội.

---

## Yêu Cầu Hệ Thống

* Python 3.10 trở lên
* Node.js 18.0 trở lên
* Git
* Redis Server (tùy chọn, chỉ cần khi kích hoạt chế độ cache Redis hoặc Celery Worker)

---

## Hướng Dẫn Cài Đặt & Khởi Chạy

### Bước 1: Chuẩn Bị Môi Trường Backend

1. Di chuyển vào thư mục dự án và kích hoạt môi trường ảo Python:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. Cài đặt các gói thư viện cần thiết:
   ```powershell
   pip install -r requirements.txt
   ```

### Bước 2: Cấu Hình Biến Môi Trường

Tạo file `backend/.env` và điền các thông tin cấu hình cơ bản:

```env
SECRET_KEY=django_insecure_development_key
DEBUG=True
FERNET_SECRET_KEY=your_fernet_256bit_key_base64
DATABASE_URL=sqlite:///db.sqlite3

# Thong tin Spotify Developer (dang ky tai developer.spotify.com)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/api/users/spotify/callback/

# Cau hinh AI (Chon groq hoac gemini)
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
AI_MODEL_GROQ=openai/gpt-oss-120b
GEMINI_API_KEY=your_gemini_api_key

# Cache & Celery (mac dinh dev dung LocMemCache va khong bat buoc co Redis)
USE_REDIS_CACHE=False
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

*Lưu ý:* Khóa `FERNET_SECRET_KEY` có thể tạo nhanh bằng lệnh Python:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Bước 3: Khởi Tạo Cơ Sở Dữ Liệu & Chạy Backend

1. Chạy migration để khởi tạo bảng dữ liệu:
   ```powershell
   python backend/manage.py migrate
   ```

2. Khởi động máy chủ Backend:
   ```powershell
   python backend/manage.py runserver
   ```
   Backend API sẽ hoạt động tại địa chỉ: `http://localhost:8000`

### Bước 4: Cài Đặt & Khởi Chạy Frontend

1. Mở một terminal mới và di chuyển vào thư mục `frontend`:
   ```powershell
   cd frontend
   npm install
   ```

2. Khởi động giao diện phát triển:
   ```powershell
   npm run dev
   ```
   Ứng dụng sẽ hoạt động tại địa chỉ: `http://localhost:5173`

### Bước 5: Khởi Chạy Celery Worker (Tùy Chọn)

Nếu bạn muốn hệ thống tự động cào dữ liệu định kỳ 24/7 mà không cần mở trình duyệt:
1. Đảm bảo Redis server đang chạy tại `127.0.0.1:6379`.
2. Mở terminal riêng và khởi chạy Worker:
   ```powershell
   cd backend
   celery -A config worker -l info
   ```
3. Mở một terminal khác và khởi chạy Beat Scheduler:
   ```powershell
   cd backend
   celery -A config beat -l info
   ```

### Bước 6: Các Lệnh Quản Trị & Đồng Bộ Dữ Liệu Chuyên Sâu

Hệ thống hỗ trợ các lệnh quản trị chạy ngầm giúp làm mới hoặc nâng cấp dữ liệu:

1. Đồng bộ ảnh chân dung đại diện chính chủ từ Spotify Web API theo mã định danh `spotify_id` riêng biệt của từng nghệ sĩ:
   ```powershell
   python backend/manage.py sync_spotify_artist_images
   ```

2. Phân tích sóng âm thanh 30 giây (DSP Engine) bằng `librosa` để nâng cấp chỉ số âm thanh thực tế cho toàn bộ bài hát:
   ```powershell
   python backend/manage.py enrich_existing_tracks
   ```

