# Music Analytics Dashboard (Spotify Tracker & AI Insights)

Music Analytics Dashboard là nền tảng web toàn diện phục vụ việc tự động theo dõi, phân tích chuyên sâu và trực quan hóa thói quen nghe nhạc của người dùng trên Spotify theo thời gian thực (Real-time Auto-Scrobbling). Hệ thống kết hợp kiến trúc phân tán giữa Django REST Framework, Celery, Redis cùng giao diện React 19, đồng thời tích hợp các mô hình Trí tuệ Nhân tạo (Groq / Google Gemini) và Học máy (KNN) để khám phá cá tính âm nhạc độc bản.

---

## Tính Năng Nổi Bật (Features)

### 1. Quản Lý Phiên & Xác Thực Spotify OAuth 2.0
* Đăng nhập trực tiếp và bảo mật thông qua giao thức Spotify Authorization Code Flow.
* Lưu trữ và mã hóa an toàn toàn bộ access token và refresh token bằng chuẩn mã hóa đối xứng AES-256 (Fernet) trong cơ sở dữ liệu.
* Tự động kích hoạt đồng bộ nền (Instant Background Sync) lưu lịch sử nghe nhạc vào DB ngay khi đăng nhập thành công, không làm gián đoạn chuyển hướng trình duyệt.
* Tự động làm mới phiên truy cập (Token Auto-Refresh) ngầm trước khi thực hiện các yêu cầu API, ngăn chặn gián đoạn trải nghiệm người dùng.

### 2. Đường Ống Thu Thập Dữ Liệu Tự Động (Auto-Scrobbling 24/7)
* Bộ điều phối Celery Beat kết hợp Celery Worker thực hiện thu thập lịch sử nghe nhạc gần đây (Recently Played Tracks) theo định kỳ 15 phút, kèm cơ chế auto-sync định kỳ trên trình duyệt và nút đồng bộ thủ công tức thì.
* Cơ chế lưu trữ bền vững tuyệt đối: Cấu hình cơ sở dữ liệu SQLite luôn sử dụng đường dẫn tuyệt đối cấp hệ thống, ngăn chặn triệt để hiện tượng phân tách dữ liệu khi khởi chạy server từ các thư mục khác nhau.
* Cơ chế lấy dữ liệu thông minh theo mốc bài nghe cuối cùng: Tự động phát hiện bài hát gần nhất trong DB (`last_played`). Nếu bài hát thuộc 24 giờ qua, hệ thống bắt đầu kéo từ mốc thời gian đó (`after_ms`) kèm hỗ trợ phân trang tối đa 150 bài để thu thập trọn vẹn toàn bộ lượt nghe qua đêm; nếu chưa có bản ghi hoặc bản ghi đã quá 1 ngày, hệ thống mặc định lấy 50 bài gần nhất.
* Cơ chế lọc trùng lặp nghiêm ngặt (Deduplication Gate) 2 tầng (bộ nhớ tạm và ràng buộc cơ sở dữ liệu `UniqueConstraint(user, played_at)` với `ignore_conflicts=True`), đảm bảo dữ liệu toàn vẹn tuyệt đối.
* Cơ chế kiểm soát giới hạn tần suất yêu cầu (Rate Limit Handling): Tự động phát hiện mã lỗi HTTP 429 từ Spotify, bóc tách header `Retry-After` và áp dụng backoff exponential an toàn.

### 3. Bộ Điều Hướng Chu Kỳ Lịch Cố Định (Discrete Calendar Periods Navigator)
* Thay thế cơ chế cửa sổ trượt (sliding window) truyền thống bằng hệ thống chu kỳ lịch cố định chuẩn ISO:
  * Tuần: Tính từ 00:00:00 Thứ Hai đến 23:59:59 Chủ Nhật (ISO Week).
  * Tháng: Tính từ 00:00:00 ngày đầu tháng đến 23:59:59 ngày cuối tháng.
  * Năm: Tính từ 00:00:00 ngày 01/01 đến 23:59:59 ngày 31/12.
* Sắp xếp nghiêm ngặt từ Hiện tại lùi về Quá khứ, hoàn toàn không tạo hoặc hiển thị các mốc thời gian tương lai.
* Hiển thị số lượt nghe thực tế trên từng mục dropdown giúp người dùng tra cứu nhanh mật độ hoạt động trong từng kỳ.
* Giao diện Trạng thái Rỗng (Zero-Data / Empty State UI): Tự động phát hiện và hiển thị hộp cảnh báo chuẩn Obsidian khi truy vấn các chu kỳ trong quá khứ chưa có dữ liệu, kèm nút bấm "Quay lại kỳ hiện tại" để điều hướng tức thì.

### 4. Kiến Trúc Bộ Nhớ Đệm Đa Tầng (Multi-Tier Caching)
* Phân loại thời gian sống bộ nhớ đệm (TTL) thông minh:
  * Chu kỳ quá khứ: Áp dụng TTL 30 ngày (dữ liệu bất biến) giúp tốc độ phản hồi tức thì (< 0.1s).
  * Chu kỳ hiện tại: Áp dụng TTL 60 giây, tự động làm mới đồng bộ khi có dữ liệu lượt nghe mới.
* Cơ chế vô hiệu hóa cache nguyên tử (Atomic Invalidation): Tự động dọn dẹp toàn bộ khóa cache phân tích của người dùng khi có sự kiện Scrobble mới hoặc phiên đăng nhập mới, hỗ trợ cả Redis và LocMemCache trong môi trường phát triển.

### 5. Phân Tích Dữ Liệu & Trực Quan Hóa Chuyên Sâu
* Biểu Đồ Radar Thuộc Tính Âm Thanh (Audio Features): Phân tích 5 chỉ số cốt lõi từ Spotify Web API gồm Valence (tích cực/buồn), Energy (năng lượng), Danceability (độ bắt tai), Acousticness (mộc) và Tempo (nhịp độ).
* Bản Đồ Nhiệt Nghe Nhạc 24x7 (Listening Heatmap Matrix): Trực quan hóa ma trận thói quen thưởng thức âm nhạc qua 168 ô tương ứng 24 giờ trong ngày và 7 ngày trong tuần.
* Phân Bổ Thể Loại Âm Nhạc Nâng Cao (Genre Distribution Engine): Tích hợp bộ nhận diện biểu thức chính quy tiếng Việt có dấu (Vietnamese Diacritics Regex) kết hợp danh mục nghệ sĩ độc lập (Indie, Rap, Collab), đảm bảo phân loại chính xác các dòng nhạc V-Pop, Global Pop, EDM, US-UK, Russian Pop, K-Pop và Phonk.
* Đua Thứ Hạng Nghệ Sĩ Động (Animated Bar Chart Race): Biểu đồ cột chuyển động mượt mà mô phỏng sự biến chuyển thứ hạng và lũy kế lượt nghe của các nghệ sĩ hàng đầu theo dòng thời gian.
* Nhật Ký Nghe Nhạc Gần Đây (Recent Scrobbles): Danh sách chi tiết 20-50 lượt nghe gần nhất với đầy đủ ảnh bìa album, tên nghệ sĩ, mốc thời gian và chỉ số năng lượng âm thanh.

### 6. Trí Tuệ Nhân Tạo & Gợi Ý Bài Hát Thông Minh
* AI Music Persona: Khởi tạo hồ sơ tính cách âm nhạc chuyên sâu sử dụng Groq LLM (openai/gpt-oss-120b) hoặc Google Gemini API, phân tích tâm lý, biểu đồ phân bổ cảm xúc (Energetic, Melancholic, Focused), khung giờ nghe nhạc lý tưởng và lời khuyên thưởng thức.
* Smart Song Recommendations: Thuật toán Học máy K-Nearest Neighbors (KNN với khoảng cách Euclidean) trích xuất không gian đặc trưng âm thanh 5 chiều để tìm kiếm và đề xuất các bài hát có giai điệu và phong cách tương đồng nhất từ thư viện bài hát.

### 7. Thẩm Mỹ Dark Mode & Thẻ Chia Sẻ Xã Hội
* Thiết kế theo phong cách Obsidian Dark Mode cao cấp: Nền chính tối sâu (#0B0F17), thẻ Card nổi (#131B2E) và điểm nhấn xanh Spotify (#1DB954).
* Chế độ Xem thử (Demo Mode): Cho phép người dùng trải nghiệm toàn bộ bảng điều khiển với dữ liệu mẫu hoàn chỉnh mà không bắt buộc phải liên kết tài khoản ngay từ đầu.
* Xuất Thẻ Chia Sẻ (Shareable Cards): Tạo thẻ ảnh cá tính âm nhạc chuẩn tỷ lệ Story 9:16 với độ sắc nét cao (pixelRatio: 2) để người dùng chia sẻ trực tiếp lên mạng xã hội.

### 8. Phòng Vệ An Toàn & Bảo Mật Hệ Thống (Defense-in-Depth)
* Nguyên tắc Zero-Leakage: Biến môi trường và khóa bí mật được cô lập hoàn toàn trong `backend/.env`.
* Vệ sinh Dữ liệu Đầu ra (Data Sanitization): Các API Serializers dành cho client loại trừ toàn bộ token và thông tin nhạy cảm.
* Kiểm soát Phân quyền Nghiêm ngặt: Toàn bộ endpoint phân tích và dữ liệu cá nhân bắt buộc xác thực qua `BearerOrTokenAuthentication`.

---

## Công Nghệ Sử Dụng (Tech Stack)

| Phân hệ | Công nghệ | Mục đích |
| :--- | :--- | :--- |
| Backend Core | Python 3.12 + Django 5 + Django REST Framework | Xây dựng RESTful API, ORM tối ưu truy vấn aggregation |
| Background Workers | Celery 5 + Redis | Xử lý hàng đợi cào dữ liệu và đồng bộ thuộc tính âm thanh |
| Scheduler | django-celery-beat | Lên lịch tự động hóa tác vụ định kỳ chạy ngầm |
| Caching | Redis Cache / LocMemCache | Tối ưu hóa hiệu năng phản hồi API (< 1.5s), cơ chế TTL phân tầng |
| Security | Cryptography (AES-256 Fernet) + DRF Token Auth | Mã hóa token Spotify, bảo vệ điểm cuối API |
| AI & Machine Learning | Groq API + Google Gemini API + scikit-learn | Phân tích AI Music Persona và thuật toán KNN Recommender |
| Frontend Core | React 19 + Vite 8 + TypeScript | Kiến trúc Single Page Application (SPA), Type-safe 100% |
| Styling | Tailwind CSS v4 + Vanilla CSS | Hệ thống giao diện Obsidian Dark Mode hiện đại |
| Data Visualization | Recharts + D3.js | Trực quan hóa Radar, Heatmap, Bar Chart Race |
| Export Engine | html-to-image | Xuất thẻ ảnh chia sẻ độ phân giải cao |
| Database | SQLite3 (Development) / PostgreSQL (Production) | Lưu trữ quan hệ thực thể, ràng buộc dữ liệu toàn vẹn |

---

## Cấu Trúc Mã Nguồn (Directory Structure)

```text
music_tracking/
├── .agents/                    # Bộ quy tắc kiến trúc, skills và scripts kiểm thử tự động
│   ├── rules/                  # Quy chuẩn Backend, Frontend và Git
│   └── skills/                 # 6 kỹ năng kiểm định chuyên biệt và security audit
├── backend/                    # Mã nguồn máy chủ Django
│   ├── config/                 # Cấu hình dự án, Celery, CORS và Caching
│   ├── users/                  # App quản lý người dùng và luồng Spotify OAuth 2.0
│   ├── tracker/                # App data pipeline, ingestion và Celery tasks
│   ├── analytics/              # App tính toán thống kê, bộ lọc chu kỳ và caching
│   ├── ai_engine/              # App tích hợp Groq/Gemini LLM và thuật toán KNN
│   └── manage.py               # Điểm thực thi lệnh quản trị Django
├── frontend/                   # Mã nguồn giao diện React
│   ├── src/
│   │   ├── components/         # UI components, biểu đồ trực quan hóa, cards và modals
│   │   ├── services/           # Axios API client tích hợp fallback mock data
│   │   ├── types/              # Định nghĩa interface TypeScript chặt chẽ
│   │   ├── App.tsx             # Root Dashboard Component điều phối dữ liệu
│   │   └── main.tsx            # Entry point bọc ErrorBoundary phòng vệ
│   └── package.json            # Cấu hình dependencies Frontend
├── owner_md/                   # Nhật ký sửa lỗi, phân tích kỹ thuật và tổng kết các giai đoạn
├── README.md                   # Tài liệu giới thiệu và hướng dẫn tổng thể dự án
└── requirements.txt            # Danh sách thư viện Python Backend
```

---

## Hướng Dẫn Cài Đặt & Vận Hành (Getting Started)

### 1. Chuẩn Bị Môi Trường
* Python >= 3.10
* Node.js >= 18.0
* Redis Server (nếu bật chế độ Redis Cache và Celery)

### 2. Cài Đặt & Khởi Chạy Backend

1. Kích hoạt môi trường ảo Python:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. Cài đặt thư viện phụ thuộc:
   ```powershell
   pip install -r requirements.txt
   ```

3. Cấu hình biến môi trường:
   Tạo file `backend/.env` với các khóa cấu hình chuẩn:
   ```env
   SECRET_KEY=your_django_secret_key
   DEBUG=True
   FERNET_SECRET_KEY=your_fernet_256bit_key
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIFY_REDIRECT_URI=http://localhost:8000/api/users/spotify/callback/
   GROQ_API_KEY=your_groq_api_key
   AI_PROVIDER=groq
   AI_MODEL_GROQ=openai/gpt-oss-120b
   GEMINI_API_KEY=your_gemini_api_key
   DATABASE_URL=sqlite:///db.sqlite3
   REDIS_URL=redis://127.0.0.1:6379/0
   CELERY_BROKER_URL=redis://127.0.0.1:6379/0
   USE_REDIS_CACHE=False
   ```

4. Áp dụng Database Migrations:
   ```powershell
   python backend/manage.py migrate
   ```

5. Khởi động Máy chủ Phát triển:
   ```powershell
   python backend/manage.py runserver
   ```
   Backend API sẽ hoạt động tại: `http://localhost:8000`

6. Khởi chạy Celery Worker & Celery Beat (Chạy trên các terminal riêng nếu sử dụng hàng đợi ngầm):
   ```powershell
   cd backend
   celery -A config worker -l info
   celery -A config beat -l info
   ```

### 3. Cài Đặt & Khởi Chạy Frontend

1. Cài đặt các gói thư viện:
   ```powershell
   cd frontend
   npm install
   ```

2. Khởi động Development Server:
   ```powershell
   npm run dev
   ```
   Giao diện người dùng sẽ chạy tại: `http://localhost:5173`

---

## Quy Trình Kiểm Định Chất Lượng Tự Động (Quality & Debug Verification)

Dự án áp dụng bộ công cụ chẩn đoán đa tầng thông qua script tự động để đảm bảo tính ổn định và an toàn trước mỗi lần bàn giao:

```powershell
python .agents/skills/system-debug-verification/scripts/run_system_debug.py
```

Quy trình tự động quét qua 16 tiêu chí kiểm định thuộc 6 giai đoạn:
1. Xác thực biến môi trường và bí mật bảo mật trong `backend/.env`.
2. Kiểm tra tính hiện diện của `.env` trong `.gitignore`.
3. Kiểm tra tính đầy đủ của 12 gói thư viện cốt lõi trong `.venv`.
4. Chạy `manage.py check` phát hiện lỗi hệ thống Django.
5. Kiểm tra tính toàn vẹn của migrations trong cơ sở dữ liệu.
6. Chạy 50 bài kiểm thử tự động (Unit, Integration & Contract Tests) trên toàn bộ hệ thống Backend.
7. Kiểm tra khế ước truyền nhận dữ liệu Frontend - Backend (`tests_fe_be_contract.py`), xác thực tính tương thích 100% giữa TypeScript types và API responses.
8. Kiểm tra cú pháp Frontend qua ESLint (0 errors, 0 warnings).
9. Kiểm tra Type-check TypeScript và biên dịch Production Bundle qua Vite Build.
10. Kích hoạt 6 Verification Gates của các Skill:
   * `spotify-auth-users`
   * `spotify-tracker-pipeline`
   * `music-analytics-engine`
   * `music-ai-insights`
   * `frontend-analytics-ui`
   * `system-security-audit` (Kiểm toán bảo mật và chống rò rỉ bí mật)
