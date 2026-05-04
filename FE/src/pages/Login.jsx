import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import API from "../services/api";

export default function Login() {
  const [tab, setTab]           = useState("login");   // "login" | "register"
  const [form, setForm]         = useState({ username: "", password: "", confirmPassword: "", email: "", full_name: "" });
  const [error, setError]       = useState("");
  const [success, setSuccess]   = useState("");
  const [loading, setLoading]   = useState(false);
  const { login }               = useAuth();
  const navigate                = useNavigate();

  const set = (field, val) => setForm(f => ({ ...f, [field]: val }));

  // ── Đăng nhập ──────────────────────────────────────────
  const handleLogin = async () => {
    if (!form.username || !form.password) { setError("Vui lòng nhập đầy đủ thông tin"); return; }
    setLoading(true); setError("");
    try {
      const res = await API.post("/auth/login", { username: form.username, password: form.password });
      login(res.data.access_token, res.data.user);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Đăng nhập thất bại");
    } finally { setLoading(false); }
  };

  // ── Đăng ký ────────────────────────────────────────────
  const handleRegister = async () => {
    if (!form.username || !form.password) { setError("Username và mật khẩu là bắt buộc"); return; }
    if (form.password.length < 6)         { setError("Mật khẩu phải có ít nhất 6 ký tự"); return; }
    if (form.password !== form.confirmPassword) { setError("Mật khẩu xác nhận không khớp"); return; }
    setLoading(true); setError(""); setSuccess("");
    try {
      await API.post("/auth/register", {
        username:  form.username,
        password:  form.password,
        email:     form.email     || null,
        full_name: form.full_name || null,
        role:      "staff",   // tự đăng ký mặc định là staff
      });
      setSuccess("Đăng ký thành công! Hãy đăng nhập.");
      setForm(f => ({ ...f, username: form.username, password: "", confirmPassword: "", email: "", full_name: "" }));
      setTimeout(() => { setTab("login"); setSuccess(""); }, 1800);
    } catch (err) {
      setError(err.response?.data?.detail || "Đăng ký thất bại");
    } finally { setLoading(false); }
  };

  const handleKey = (e) => {
    if (e.key !== "Enter") return;
    tab === "login" ? handleLogin() : handleRegister();
  };

  return (
    <div className="login-page">
      <div className="login-card" style={{ maxWidth: 400 }}>
        {/* Logo */}
        <div className="login-logo">
          <h1>🛒 SuperMarket AI</h1>
          <p>Hệ thống quản lý siêu thị thông minh</p>
        </div>

        {/* Tab switcher */}
        <div style={{ display: "flex", marginBottom: 22, borderRadius: 10,
          background: "#f1f5f9", padding: 4, gap: 4 }}>
          {[["login", "Đăng nhập"], ["register", "Đăng ký"]].map(([key, label]) => (
            <button key={key} onClick={() => { setTab(key); setError(""); setSuccess(""); }}
              style={{
                flex: 1, padding: "8px 0", border: "none", borderRadius: 8,
                fontFamily: "inherit", fontSize: 13.5, fontWeight: 600, cursor: "pointer",
                transition: "all .15s",
                background: tab === key ? "#fff" : "transparent",
                color:      tab === key ? "#2563eb" : "#64748b",
                boxShadow:  tab === key ? "0 1px 4px rgba(0,0,0,.1)" : "none",
              }}>
              {label}
            </button>
          ))}
        </div>

        {/* Thông báo */}
        {error   && <div className="error-msg">⚠️ {error}</div>}
        {success && <div style={{ background:"#dcfce7", color:"#15803d", padding:"10px 13px",
          borderRadius:8, fontSize:13, marginBottom:14, fontWeight:600 }}>✅ {success}</div>}

        {/* ── FORM ĐĂNG NHẬP ── */}
        {tab === "login" && (
          <>
            <div className="form-group">
              <label>Tên đăng nhập</label>
              <input placeholder="Nhập username..." value={form.username}
                onChange={e => set("username", e.target.value)} onKeyDown={handleKey} autoFocus />
            </div>
            <div className="form-group">
              <label>Mật khẩu</label>
              <input type="password" placeholder="Nhập mật khẩu..." value={form.password}
                onChange={e => set("password", e.target.value)} onKeyDown={handleKey} />
            </div>
            <button className="btn btn-primary" style={{ width:"100%", padding:"10px", marginTop:4 }}
              onClick={handleLogin} disabled={loading}>
              {loading ? "Đang đăng nhập..." : "Đăng nhập →"}
            </button>
          </>
        )}

        {/* ── FORM ĐĂNG KÝ ── */}
        {tab === "register" && (
          <>
            <div className="form-group">
              <label>Tên đăng nhập <span style={{ color:"#dc2626" }}>*</span></label>
              <input placeholder="Tối thiểu 3 ký tự..." value={form.username}
                onChange={e => set("username", e.target.value)} onKeyDown={handleKey} autoFocus />
            </div>
            <div className="form-group">
              <label>Họ và tên</label>
              <input placeholder="Nhập họ tên đầy đủ..." value={form.full_name}
                onChange={e => set("full_name", e.target.value)} onKeyDown={handleKey} />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input type="email" placeholder="example@email.com" value={form.email}
                onChange={e => set("email", e.target.value)} onKeyDown={handleKey} />
            </div>
            <div className="form-group">
              <label>Mật khẩu <span style={{ color:"#dc2626" }}>*</span></label>
              <input type="password" placeholder="Tối thiểu 6 ký tự..." value={form.password}
                onChange={e => set("password", e.target.value)} onKeyDown={handleKey} />
            </div>
            <div className="form-group">
              <label>Xác nhận mật khẩu <span style={{ color:"#dc2626" }}>*</span></label>
              <input type="password" placeholder="Nhập lại mật khẩu..." value={form.confirmPassword}
                onChange={e => set("confirmPassword", e.target.value)} onKeyDown={handleKey} />
            </div>
            <div style={{ background:"#f0f9ff", border:"1px solid #bae6fd", borderRadius:8,
              padding:"8px 12px", marginBottom:14, fontSize:12, color:"#0369a1" }}>
              ℹ️ Tài khoản tự đăng ký sẽ có quyền <strong>Staff</strong>. Admin có thể nâng quyền sau.
            </div>
            <button className="btn btn-primary" style={{ width:"100%", padding:"10px" }}
              onClick={handleRegister} disabled={loading}>
              {loading ? "Đang tạo tài khoản..." : "Tạo tài khoản →"}
            </button>
            <p style={{ marginTop:12, fontSize:12, color:"#94a3b8", textAlign:"center", cursor:"pointer" }}
              onClick={() => { setTab("login"); setError(""); }}>
              Đã có tài khoản? <span style={{ color:"#2563eb", fontWeight:600 }}>Đăng nhập</span>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
