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
* Biểu đồ Radar Đặc tính Âm thanh: Trích xuất trực tiếp từ sóng âm thanh 30 giây (DSP Engine) bằng thư viện `librosa` để đo đạc chuẩn xác BPM thật, năng lượng RMS thật, độ mộc mạc và tâm trạng bài hát.
* Bản Đồ Nhiệt Thích Ứng Đa Chu Kỳ (Adaptive Calendar Heatmap): Tự động chuyển đổi giao diện linh hoạt và tối ưu theo chu kỳ thời gian:
  * Chu kỳ Tuần (Week): Ma trận 7 ngày x 24 giờ phân tích nhịp sinh học và khung giờ vàng nghe nhạc trong tuần.
  * Chu kỳ Tháng (Month): Lịch Bàn Tháng (Monthly Calendar Grid 7 cột x 5 hàng) hiển thị trực quan cường độ nghe nhạc của từng ngày từ ngày 1 đến 28..31, đệm đúng thứ đầu tháng, kèm số liệu ngày đỉnh cao và tỷ lệ ngày hoạt động.
  * Chu kỳ Năm (Year): Bản đồ hoạt động cả năm dạng Annual Activity Graph (53 tuần x 7 ngày) phong cách GitHub / Spotify Wrapped, bố cục thanh thoát kèm thanh cuộn mượt mà, phân định 12 tháng rõ ràng và bảng chỉ số chuỗi nghe liên tục (Streak), tháng bùng nổ nhất và ngày đỉnh cao.
* So Sánh Lượt Nghe Theo Tuần: Biểu đồ cột trực quan so sánh số lượt nghe mỗi ngày giữa tuần này và tuần trước kèm thông số tăng trưởng.
* Phân Bố Thể Loại Âm Nhạc Lai (Hybrid Genre Classification): Kết hợp thông minh giữa nhận diện khu vực địa phương (hợp nhất chuẩn hóa V-Pop, K-Pop) và phân loại chuyên sâu bằng chỉ số sóng âm thanh DSP đối với các dòng nhạc quốc tế (EDM / Electronic, Phonk / High Energy, Acoustic / Lo-Fi, Hip-Hop / Rap, US-UK / Pop, Global Pop).
* Bảng Xếp Hạng Toàn Diện: Theo dõi Top Bài Hát, Top Nghệ Sĩ (đồng bộ ảnh chân dung chính chủ từ Spotify Web API theo mã định danh spotify_id riêng biệt) và Top Album được nghe nhiều nhất.
* Nhật Ký Nghe Gần Đây: Xem danh sách chi tiết các lượt nghe mới nhất với đầy đủ ảnh bìa và thông tin bài hát.

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


### 5. Hệ Thống Codebase RAG & Trợ Lý Kiến Trúc Hệ Thống (Knowledge Harness RAG)
* Truy vấn mã nguồn và kiến trúc: Cho phép đặt câu hỏi kỹ thuật về toàn bộ logic backend (models, services, views, tasks) và tài liệu hệ thống.
* Thác truy xuất (Retrieval Cascade): Kết hợp Dense Vector (ChromaDB) và Sparse Search (BM25Plus với CodeTokenizer), hợp nhất bằng thuật toán Reciprocal Rank Fusion (RRF k=60) và tái xếp hạng TermSemanticReranker.
* Trích dẫn kiểm chứng được (Citation Verification): Mọi khẳng định đều có nhãn trích dẫn `[S1]`, `[S2]` nối trực tiếp với file vật lý, vị trí dòng code và tên hàm/lớp (Symbol), ngăn chặn hoàn toàn ảo giác (hallucination).
* Chế độ phòng vệ Escape Hatch: Tự động nhận diện và từ chối trả lời chính xác khi câu hỏi nằm ngoài phạm vi tài liệu dự án.
* Tích hợp Agent Tool: Công cụ `@tool search_codebase` cho phép Agentic AI tự động tra cứu mã nguồn trong chu trình ReAct.

### 6. Giao Diện Obsidian Dark Mode & Chia Sẻ Mạng Xã Hội
* Giao diện tối Obsidian hiện đại, phù hợp với phong cách âm nhạc và tôn mắt khi xem vào ban đêm.
* Chế độ Xem thử (Demo Mode): Trải nghiệm đầy đủ mọi tính năng với dữ liệu mẫu ngay cả khi chưa kết nối tài khoản Spotify.
* Xuất Thẻ Chia Sẻ Đa Tỷ Lệ: Tạo thẻ ảnh tổng kết gu âm nhạc và AI Persona độ phân giải cao 2x với 4 tỷ lệ chuẩn mạng xã hội (Story 9:16, Dọc Chân dung 4:5, Vuông Post 1:1, Ngang Banner 16:9). Tích hợp ảnh bìa album và chân dung nghệ sĩ thật từ Spotify, tối ưu bố cục cân đối và phòng vệ lỗi hiển thị.

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

