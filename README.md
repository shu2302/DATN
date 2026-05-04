
 BƯỚC 1 — Cài đặt Backend

### Mở terminal 1, vào thư mục BE:
```bash
cd BE
```

### Tạo môi trường ảo (khuyến nghị):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### Cài thư viện:
```bash
pip install -r requirements.txt
```

### Tạo dữ liệu mẫu (chỉ chạy 1 lần đầu):
```bash
python seed_data.py
```
> Lệnh này tạo: 2 tài khoản, 5 danh mục, 18 sản phẩm, 25 đơn hàng mẫu

### Khởi động server:
```bash
uvicorn main:app --reload --port 8000
```

---

 BƯỚC 2 — Cài đặt Frontend

### Mở terminal 2, vào thư mục FE:
```bash
cd FE
```

### Cài thư viện Node.js:
```bash
npm install
```

### Khởi động dev server:
```bash
npm run dev
```

---

## 👤 Tài khoản demo

| Username | Password  | Quyền |
|----------|-----------|-------|
| admin    | admin123  | 🔑 Admin — toàn quyền |
| staff    | staff123  | 👤 Staff — xem + nhập liệu |

**Admin** có thể: thêm/xóa sản phẩm, quản lý danh mục, xem log, đổi role user  
**Staff** có thể: xem sản phẩm, tạo đơn hàng, dùng chatbot, xem dashboard

---

## 🤖 BƯỚC 3 — Cài đặt AI Chatbot (Tùy chọn)

### Cài Ollama:
Tải tại: https://ollama.com/download

### Tải model LLaMA:
```bash
ollama pull llama3.2
```

### Chạy Ollama (giữ terminal này mở):
```bash
ollama serve
```

> **Không bắt buộc:** Nếu chưa cài Ollama, chatbot tự động chuyển sang chế độ **rule-based** — vẫn trả lời được các câu hỏi thông dụng.

---

## ✅ Tính năng hoàn chỉnh

| Tính năng | Mô tả |
|-----------|-------|
| 🔐 Xác thực | Đăng ký, đăng nhập JWT, phân quyền Admin/Staff |
| 👤 Hồ sơ | Xem & cập nhật thông tin, đổi mật khẩu |
| 🛍️ Sản phẩm | CRUD đầy đủ, tìm kiếm, lọc theo danh mục, cảnh báo tồn kho |
| 📂 Danh mục | Thêm/sửa/xóa, gán sản phẩm vào danh mục |
| 🧾 Đơn hàng | Tạo đơn, xem danh sách, xem chi tiết |
| 📊 Dashboard | 4 biểu đồ: doanh thu, đơn hàng, top SP, doanh thu theo danh mục |
| 🔔 Thông báo | Cảnh báo hết hàng, sắp hết, hàng tồn chậm bán |
| 🤖 AI Chatbot | Hỏi đáp tiếng Việt (LLaMA hoặc rule-based tự động) |
| 👥 Quản lý User | Xem danh sách, đổi role, khóa tài khoản (Admin) |
| 📝 Log hệ thống | Lịch sử đăng nhập và thao tác của từng user |
| 📥 Export CSV | Xuất danh sách sản phẩm và đơn hàng |

---



## ❗ Lưu ý quan trọng

1. **Thứ tự chạy:** Phải chạy Backend trước, sau đó mới chạy Frontend
2. **Seed data:** Chỉ chạy `python seed_data.py` một lần. Nếu chạy lại sẽ báo lỗi trùng username
3. **Nếu muốn reset DB:** Xóa file `BE/supermarket.db` rồi chạy lại seed
4. **Port mặc định:** Backend = 8000, Frontend = 5173
