# 📄 TÀI LIỆU YÊU CẦU PHẦN MỀM & KIẾN TRÚC HỆ THỐNG
**Tên dự án:** Music Analytics Dashboard (Spotify Tracker & AI Insights)  
**Tác giả:** BA & Dev Team  
**Phiên bản:** 1.0.0  

---

## 📌 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)
Dự án phát triển một ứng dụng web dạng **Music Analytics Dashboard** tự động theo dõi lịch sử nghe nhạc của người dùng trên nền tảng Spotify theo thời gian thực (Real-time tracking/Scrobbling). Hệ thống khắc phục các hạn chế của ứng dụng gốc (như Last.fm Pro hoặc Spotify Wrapped) bằng cách cung cấp thống kê tùy chỉnh thời gian sâu sắc, trực quan hóa biểu đồ phong phú và tích hợp AI phân tích tâm trạng/gợi ý âm nhạc.

---

## 🎵 2. YÊU CẦU PHẦN MỀM (REQUIREMENTS)

### 2.1. Yêu cầu Chức năng (Functional Requirements - FR)

* **FR-1: Xác thực & Kết nối Spotify (OAuth2)**
  * **FR-1.1:** Người dùng đăng nhập trực tiếp qua tài khoản Spotify bằng giao thức OAuth 2.0.
  * **FR-1.2:** Lần đầu đăng nhập, hệ thống tự động quét và lưu trữ ngay lập tức danh sách các bài hát vừa nghe (*Recently Played Tracks*).

* **FR-2: Thu thập Dữ liệu Tự động (Auto-Scrobbling)**
  * **FR-2.1:** Hệ thống có tác vụ chạy ngầm định kỳ để lưu trữ lịch sử nghe nhạc của người dùng mà không yêu cầu mở giao diện web 24/7.
  * **FR-2.2:** Xử lý trùng lặp dữ liệu (*Deduplication*) bằng cách kết hợp `user_id` và mốc thời gian `played_at`.

* **FR-3: Báo cáo & Phân tích Thống kê (Music Analytics)**
  * **FR-3.1:** Cho phép lọc dữ liệu (*Top Tracks, Artists, Albums, Genres*) theo khoảng thời gian tùy chọn (7 ngày, 30 ngày, theo năm hoặc Custom Date Range).
  * **FR-3.2:** Hiển thị **Biểu đồ Radar (Audio Features)** phân tích các chỉ số: `valence` (tích cực/buồn), `energy` (sôi động), `danceability`, `acousticness`.
  * **FR-3.3:** Hiển thị **Listening Heatmap** biểu thị mật độ nghe nhạc theo khung giờ trong ngày và các ngày trong tuần.
  * **FR-3.4:** Cung cấp biểu đồ động **Bar Chart Race** mô phỏng sự rượt đuổi thứ hạng của Top 5 nghệ sĩ/bài hát qua các tháng.

* **FR-4: Tính năng Trí tuệ Nhân tạo (AI Features)**
  * **FR-4.1 (AI Music Persona):** Tự động sinh báo cáo nhận xét tâm lý/phong cách nghe nhạc định kỳ (mỗi tuần/tháng) sử dụng LLM.
  * **FR-4.2 (AI Smart Recommendation):** Tìm kiếm và gợi ý các bài hát có "vibe/chất âm" tương đồng dựa trên thuật toán phân tích thuộc tính âm thanh.

---

### 2.2. Yêu cầu Phi chức năng (Non-Functional Requirements - NFR)

* **NFR-1: Hiệu năng & Tốc độ (Performance)**
  * **NFR-1.1:** Tốc độ tải trang Dashboard chính < **1.5 giây**.
  * **NFR-1.2:** Áp dụng Caching cho các truy vấn tính toán thống kê lịch sử dữ liệu lớn.
* **NFR-2: Bảo mật & Quyền riêng tư (Security)**
  * **NFR-2.1:** Không lưu trữ mật khẩu Spotify. Mã hóa Access Token & Refresh Token trong cơ sở dữ liệu.
  * **NFR-2.2:** Giới hạn Scope truy cập API Spotify ở mức vừa đủ (*Least Privilege Principle*).
* **NFR-3: Giao diện & Trải nghiệm (UI/UX)**
  * **NFR-3.1:** Giao diện tối (*Dark Mode*) tối ưu hóa việc hiển thị ảnh bìa album nhạc.
  * **NFR-3.2:** Tương thích hoàn toàn với các thiết bị di động (*Responsive Design*).
  * **NFR-3.3:** Cho phép xuất hình ảnh thẻ thống kê (*Shareable Cards*) để chia sẻ lên Mạng xã hội.

---

## 🛠️ 3. KIẾN TRÚC CÔNG NGHỆ (TECH STACK)

| Tầng (Layer) | Công nghệ sử dụng | Lý do lựa chọn |
| :--- | :--- | :--- |
| **Frontend** | React (Next.js/Vite) + TailwindCSS + Shadcn UI | Giao diện tối mượt mà, render linh hoạt. |
| **Data Visuals** | Recharts, D3.js | Vẽ biểu đồ Radar, Heatmap và Bar Chart Race động. |
| **Backend** | Django + Django REST Framework | ORM tính toán dữ liệu mạnh, xử lý API nhanh, tích hợp sẵn Auth. |
| **Database** | PostgreSQL | Tối ưu Index cho truy vấn `timestamp` và `user_id`. |
| **Background Task** | Celery + Redis | Chạy tác vụ cào dữ liệu ngầm và Caching dữ liệu. |
| **AI Integration** | Google Gemini API + `scikit-learn` | Tạo văn bản báo cáo tự động & Thuật toán KNN/Phân cụm. |

---

## 📐 4. MÔ HÌNH HỆ THỐNG (SYSTEM MODELING)

### 4.1. Sơ đồ Thực thể Quan hệ (Database Schema Concept)

```text
  +---------------+       1..*      +--------------------+
  |     Users     |---------------->|  ListeningHistory  |
  +---------------+                 +--------------------+
          |                                   | *
          | 1..*                              |
          v                                   v 1
  +---------------+                 +--------------------+
  | AI_Summaries  |                 |       Tracks       |
  +---------------+                 +--------------------+
                                              | *
                                              |
                                              v 1
                                    +--------------------+
                                    |       Albums       |
                                    +--------------------+
                                              | *
                                              |
                                              v *
                                    +--------------------+
                                    |      Artists       |
                                    +--------------------+