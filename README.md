# Music Analytics Dashboard (Spotify Tracker & AI Insights)

Music Analytics Dashboard là nền tảng web giúp người dùng tự động theo dõi, thống kê và trực quan hóa thói quen nghe nhạc trên Spotify theo thời gian thực. Hệ thống kết hợp hệ thống phân tích chuyên sâu cùng các mô hình Trí tuệ Nhân tạo và Học máy để giúp bạn thấu hiểu gu âm nhạc của chính mình.

---

## Tính Năng Nổi Bật

### 1. Đồng Bộ & Theo Dõi Lượt Nghe Tự Động
* Đăng nhập an toàn trực tiếp bằng tài khoản Spotify thông qua giao thức OAuth 2.0.
* Tự động thu thập và cập nhật lịch sử nghe nhạc mới nhất vào cơ sở dữ liệu mà không cần thao tác thủ công.
* Hỗ trợ nút bấm đồng bộ tức thì và cơ chế tự động lấy tiếp các bài hát vừa nghe.
* Cơ Chế Chống Trùng Lặp Lượt Nghe (Deduplication): Hệ thống đối chiếu chính xác thời điểm bạn nghe từng bài hát (mốc thời gian played_at), chỉ lưu lại những lượt nghe mới và tự động bỏ qua các bản ghi trùng lặp khi nghe lại nhiều lần.
* Bảo Mật & Mã Hóa Token Spotify: Toàn bộ access token và refresh token của người dùng đều được mã hóa đối xứng AES-256 qua Fernet trước khi lưu vào cơ sở dữ liệu, đảm bảo bí mật tuyệt đối.

### 2. Bảng Điều Khiển Phân Tích Trực Quan
* **Biểu Đồ Radar Đặc Tính Âm Thanh & Minh Bạch Nguồn Dữ Liệu:** Trích xuất trực tiếp từ sóng âm thanh 30 giây (DSP Engine) bằng thư viện `librosa` để đo đạc BPM thật, năng lượng RMS thật, độ mộc mạc và tâm trạng bài hát; hiển thị rõ tỷ lệ dữ liệu đo trực tiếp so với ước lượng ngay trên giao diện.
* **Bản Đồ Nhiệt Thích Ứng Đa Chu Kỳ (Adaptive Calendar Heatmap):** Tự động chuyển đổi giao diện theo chu kỳ thời gian và hỗ trợ chạm/nhấn trực tiếp từng ô trên cả máy tính lẫn màn hình cảm ứng:
  * **Chu kỳ Tuần (Week):** Ma trận 7 ngày x 24 giờ phân tích nhịp sinh học và khung giờ nghe nhạc nổi bật trong tuần.
  * **Chu kỳ Tháng (Month):** Lịch Bàn Tháng (Monthly Calendar Grid 7 cột x 5 hàng) hiển thị cường độ nghe nhạc từng ngày từ ngày 1 đến cuối tháng, kèm ngày đỉnh cao và tỷ lệ ngày hoạt động.
  * **Chu kỳ Năm (Year):** Bản đồ hoạt động cả năm (53 tuần x 7 ngày) phân định 12 tháng rõ ràng kèm chỉ số chuỗi ngày nghe liên tục (Streak), tháng nổi bật nhất và ngày đỉnh cao.
* **Biểu Đồ So Sánh Xu Hướng Nghe Nhạc Thích Ứng (Adaptive Trend Comparison):** Tự động thích ứng trục so sánh theo từng chu kỳ:
  * **Tuần:** Đối chiếu 7 ngày trong tuần với tuần liền trước.
  * **Tháng:** Đối chiếu từng tuần trong tháng với tháng liền trước, tự động gắn nhãn hoạt động mới khi kỳ trước không có dữ liệu.
  * **Năm:** Đối chiếu tổng lượt phát 12 tháng với năm liền trước.
* **Phân Bố Thể Loại Âm Nhạc Lai (Hybrid Genre Classification):** Kết hợp nhận diện nghệ sĩ theo khu vực (V-Pop, K-Pop) và phân loại bằng đặc trưng âm thanh DSP cho nhạc quốc tế; hỗ trợ thẻ thống kê chuyên biệt khi một thể loại chiếm 100% lượt phát trong kỳ.
* **Bảng Xếp Hạng & Nhật Ký Nghe Gần Đây:** Theo dõi Top Bài Hát, Top Nghệ Sĩ (đồng bộ ảnh chân dung theo mã định danh `spotify_id` riêng biệt), Top Album và lịch sử phát gần nhất gắn rõ phạm vi thời gian đang chọn.

### 3. Bộ Lọc Chu Kỳ Thời Gian Cố Định
* Dễ dàng lựa chọn và tra cứu thống kê theo các chu kỳ cố định: Tuần (ISO Week từ Thứ Hai đến Chủ Nhật), Tháng hoặc Năm.
* Danh sách chu kỳ được sắp xếp trực quan từ hiện tại trở về quá khứ, kèm tổng số lượt nghe thực tế trên từng chu kỳ.
* Tự động thông báo khi xem các chu kỳ trong quá khứ chưa có dữ liệu kèm nút quay về kỳ hiện tại.

### 4. AI Music Persona & Agentic AI Thám Tử Âm Nhạc
* Hồ sơ Tính cách Âm nhạc AI: Tích hợp mô hình AI (Groq hoặc Google Gemini) để phân tích tâm lý, cảm xúc nghe nhạc, khung giờ thưởng thức lý tưởng và lời khuyên âm nhạc dành riêng cho bạn.
* Thám Tử Âm Nhạc Agentic AI (Aura Music Detective): Tích hợp Groq Function Calling (chu trình ReAct: Thought - Tool Call - Synthesis) kết hợp bộ khung điều khiển Harness an toàn. Agent tự động gọi các công cụ truy vấn cơ sở dữ liệu để tìm kiếm các sự thật âm nhạc bất ngờ (cày lặp bài hát, thói quen cú đêm, phiên nghe marathon, độ trung thành nghệ sĩ, cú nhảy năng lượng đột ngột) kèm số liệu và bằng chứng thực tế.
* Kiến Trúc LLM 3 Tầng Dự Phòng Tự Phục Hồi (Cascading Multi-Tier Architecture):
  * Tầng 1 (Primary): `openai/gpt-oss-120b` đảm bảo năng lực suy luận sâu sắc nhất.
  * Tầng 2 (Backup): `openai/gpt-oss-20b` sở hữu hạn mức token riêng biệt, tự động kích hoạt ngay khi Tầng 1 gặp lỗi Rate Limit 429 hoặc quá tải.
  * Tầng 3 (Fallback Engine): Thuật toán thống kê nội bộ tự động kích hoạt nếu cả hai model AI đều bận, đảm bảo giao diện luôn phản hồi mượt mà và không gián đoạn.
* Cơ Chế Kích Hoạt Thủ Công (On-Demand / Zero-Token Browsing): Quá trình lướt web, đổi chu kỳ tuần/tháng/năm chỉ hiển thị bản xem trước từ cơ sở dữ liệu (0 token AI). Chỉ khi người dùng chủ động nhấn nút "Kích hoạt Thám tử AI" hoặc "Phân tích lại cá tính", hệ thống mới gọi API.
* Phòng Vệ Rate Limit (Circuit Breaker & Cooldown 15s): Tự động ngắt mạch (Circuit Breaker) trong 60 giây khi gặp lỗi 429 để tránh spam vô ích, kết hợp bộ đếm đếm lùi 15 giây chống nhấn đúp vượt ngưỡng 8,000 TPM.
* Gợi ý Bài hát Thông minh: Sử dụng thuật toán Machine Learning (KNN) để tìm kiếm và đề xuất các bài hát có giai điệu, phong cách tương đồng nhất với sở thích của bạn.


### 5. Trợ Lý Lai MusicTrack Assistant (Dữ Liệu Âm Nhạc & Hỗ Trợ Website)
* **3 Chế Độ Hỏi Đáp Linh Hoạt:** Cho phép chọn chế độ `Tự động` (nhận diện ý định và hỏi làm rõ nếu câu hỏi mơ hồ), `Dữ liệu Âm nhạc` (hỏi đáp cá nhân hóa) hoặc `Hỗ trợ Website` (hướng dẫn sử dụng và giải đáp cơ chế).
* **Phân Tích Dữ Liệu Âm Nhạc Cá Nhân Theo Kỳ:** Tự động đồng bộ với chu kỳ Tuần / Tháng / Năm đang chọn trên Dashboard (hoặc theo khoảng thời gian bạn nhắc trong câu hỏi) để giải đáp tổng lượt phát, giờ nghe, xu hướng so với kỳ trước, Top bài hát/nghệ sĩ/album/thể loại, khung giờ vàng và gợi ý bài hát tương đồng kèm căn cứ số liệu rõ ràng.
* **Hỗ Trợ Website Thân Thiện & Phân Quyền An Toàn:** Cung cấp hướng dẫn cách đồng bộ Spotify, bảo vệ quyền riêng tư, giải thích các chỉ số phân tích và tự động duy trì ngữ cảnh hội thoại nhiều lượt theo phiên; các tùy chọn quản trị hệ thống và thông tin kỹ thuật nội bộ được ẩn khỏi tài khoản người dùng thông thường.

### 6. Giao Diện Tối Đa Thiết Bị & Chia Sẻ Mạng Xã Hội
* **Trải Nghiệm Đa Thiết Bị (Responsive Desktop / Tablet / Mobile):** Tối ưu bố cục lưới, bộ chọn chu kỳ và biểu đồ cuộn ngang mượt mà từ màn hình điện thoại nhỏ (`320px`) đến màn hình máy tính rộng, hỗ trợ đầy đủ điều hướng bàn phím (`Tab`, `Enter`, `Escape`) và tôn trọng tùy chọn giảm chuyển động (`prefers-reduced-motion`).
* **Chế Độ Xem Thử (Demo Mode) Đồng Bộ Toàn Trang:** Trải nghiệm đầy đủ cả 3 chế độ Tuần / Tháng / Năm, trạng thái kỳ rỗng và MusicTrack Assistant với dữ liệu mẫu đồng nhất ngay cả khi chưa kết nối Spotify.
* **Xuất Thẻ Chia Sẻ Đa Tỷ Lệ:** Tạo thẻ ảnh tổng kết gu âm nhạc và AI Persona độ phân giải cao 2x với 4 tỷ lệ chuẩn mạng xã hội (Story 9:16, Dọc Chân dung 4:5, Vuông Post 1:1, Ngang Banner 16:9), hiển thị linh hoạt ảnh bìa thật từ Spotify và nhãn tần suất nghe phù hợp từng chu kỳ.

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

### Bước 5: Tự Động Cào Dữ Liệu Định Kỳ Chạy Ngầm (Tùy Chọn)

Khi nghe nhạc liên tục qua đêm hoặc nhiều giờ, để tránh các bài hát bị trôi khỏi giới hạn 50 bài gần nhất của Spotify:

* **Cách 1 (Khuyên dùng trên Windows - Không cần cài Redis hay Celery):**
  Mở một terminal riêng và khởi chạy tiến trình Auto-Sync Daemon độc lập (chu kỳ mặc định 15 phút):
  ```powershell
  python backend/manage.py run_auto_sync --interval 15
  ```
  Nhấn `Ctrl + C` bất kỳ lúc nào để dừng tiến trình một cách an toàn.

* **Cách 2 (Sử dụng Celery Worker & Beat - Yêu cầu có Redis Server):**
  1. Đảm bảo Redis server đang chạy tại `127.0.0.1:6379`.
  2. Khởi chạy Celery Worker (thêm cờ `-P solo` trên Windows):
     ```powershell
     cd backend
     celery -A config worker -l info -P solo
     ```
  3. Khởi chạy Celery Beat Scheduler:
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

