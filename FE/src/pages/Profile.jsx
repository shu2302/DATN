import { useEffect, useState } from "react";
import API from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Profile() {
  const { user } = useAuth();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    API.get("/auth/me").then(r => setForm({ full_name: r.data.full_name || "", email: r.data.email || "", password: "" }));
  }, []);

  const save = async () => {
    setLoading(true); setSuccess(false);
    const body = {};
    if (form.full_name) body.full_name = form.full_name;
    if (form.email) body.email = form.email;
    if (form.password) body.password = form.password;
    try {
      await API.put("/auth/me", body);
      setSuccess(true);
      setForm(f => ({ ...f, password: "" }));
    } catch (err) { alert(err.response?.data?.detail || "Lỗi cập nhật"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <div className="page-header">
        <h2>👤 Hồ sơ cá nhân</h2>
        <p>Cập nhật thông tin tài khoản của bạn</p>
      </div>
      <div className="table-wrap" style={{ maxWidth: 500 }}>
        <div style={{ padding: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24, paddingBottom: 20, borderBottom: "1px solid #e2e8f0" }}>
            <div className="avatar" style={{ width: 52, height: 52, fontSize: 22 }}>
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div>
              <div className="fw-700" style={{ fontSize: 17 }}>{user?.username}</div>
              <span className={`badge ${user?.role === "admin" ? "badge-blue" : "badge-gray"}`} style={{ marginTop: 4 }}>
                {user?.role === "admin" ? "🔑 Admin" : "👤 Staff"}
              </span>
            </div>
          </div>

          {success && (
            <div style={{ background: "#dcfce7", color: "#15803d", padding: "10px 14px", borderRadius: 8, marginBottom: 16, fontSize: 13, fontWeight: 600 }}>
              ✅ Cập nhật thành công!
            </div>
          )}

          <div className="form-group">
            <label>Username (không thể thay đổi)</label>
            <input value={user?.username || ""} disabled style={{ background: "#f8fafc", color: "#94a3b8" }} />
          </div>
          <div className="form-group">
            <label>Họ và tên</label>
            <input value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} placeholder="Nhập họ tên đầy đủ..." />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="example@email.com" />
          </div>
          <div className="form-group">
            <label>Mật khẩu mới <span className="text-muted">(để trống nếu không đổi)</span></label>
            <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="••••••••" />
          </div>
          <button className="btn btn-primary" style={{ width: "100%", padding: "10px" }} onClick={save} disabled={loading}>
            {loading ? "Đang lưu..." : "💾 Lưu thay đổi"}
          </button>
        </div>
      </div>
    </div>
  );
}
