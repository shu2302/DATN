import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../services/api";
import { useAuth } from "../context/AuthContext";

const emptyForm = { username: "", password: "", full_name: "", email: "", role: "staff" };

export default function Users() {
  const { isAdmin } = useAuth();
  const navigate    = useNavigate();
  const [users, setUsers]   = useState([]);
  const [logs, setLogs]     = useState([]);
  const [tab, setTab]       = useState("users");
  const [loading, setLoading] = useState(true);

  // Modal tạo tài khoản
  const [modal, setModal]   = useState(false);
  const [form, setForm]     = useState(emptyForm);
  const [formErr, setFormErr] = useState("");
  const [saving, setSaving] = useState(false);

  const set = (f, v) => setForm(prev => ({ ...prev, [f]: v }));

  const loadUsers = () => API.get("/users/").then(r => setUsers(r.data));
  const loadLogs  = () => API.get("/users/logs").then(r => setLogs(r.data));

  useEffect(() => {
    if (!isAdmin) { navigate("/"); return; }
    Promise.all([loadUsers(), loadLogs()]).finally(() => setLoading(false));
  }, []);

  // ── Tạo tài khoản ──────────────────────────────────────
  const openModal  = () => { setForm(emptyForm); setFormErr(""); setModal(true); };
  const closeModal = () => { setModal(false); setFormErr(""); };

  const handleCreate = async () => {
    if (!form.username || !form.password) { setFormErr("Username và mật khẩu là bắt buộc"); return; }
    if (form.password.length < 6)         { setFormErr("Mật khẩu phải có ít nhất 6 ký tự"); return; }
    setSaving(true); setFormErr("");
    try {
      await API.post("/auth/register", {
        username:  form.username,
        password:  form.password,
        full_name: form.full_name || null,
        email:     form.email     || null,
        role:      form.role,
      });
      closeModal();
      loadUsers();
    } catch (err) {
      setFormErr(err.response?.data?.detail || "Lỗi tạo tài khoản");
    } finally { setSaving(false); }
  };

  // ── Đổi role ───────────────────────────────────────────
  const changeRole = async (id, newRole) => {
    if (!confirm(`Đổi role thành "${newRole}"?`)) return;
    await API.put(`/users/${id}/role?role=${newRole}`);
    loadUsers();
  };

  // ── Khóa tài khoản ─────────────────────────────────────
  const deactivate = async id => {
    if (!confirm("Vô hiệu hóa tài khoản này?")) return;
    await API.put(`/users/${id}/deactivate`);
    loadUsers();
  };

  if (loading) return <div className="loading">⏳ Đang tải...</div>;

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h2>👥 Người dùng</h2>
          <p>Quản lý tài khoản và lịch sử hoạt động hệ thống</p>
        </div>
        {tab === "users" && (
          <button className="btn btn-primary btn-sm" onClick={openModal}>
            + Tạo tài khoản
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button className={`btn btn-sm ${tab === "users" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setTab("users")}>👥 Tài khoản ({users.length})</button>
        <button className={`btn btn-sm ${tab === "logs" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setTab("logs")}>📝 Lịch sử hoạt động</button>
      </div>

      {/* ── Tab: Danh sách tài khoản ── */}
      {tab === "users" && (
        <div className="table-wrap">
          <div className="table-header">
            <span className="fw-600">{users.length} tài khoản</span>
            <div className="flex gap-2">
              <span className="badge badge-blue">{users.filter(u => u.role === "admin").length} Admin</span>
              <span className="badge badge-gray">{users.filter(u => u.role === "staff").length} Staff</span>
              <span className="badge badge-red">{users.filter(u => !u.is_active).length} Bị khóa</span>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>#</th><th>Username</th><th>Họ tên</th><th>Email</th>
                <th>Role</th><th>Trạng thái</th><th>Ngày tạo</th><th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 && (
                <tr><td colSpan={8}>
                  <div className="empty"><div className="empty-icon">👥</div>Chưa có tài khoản nào</div>
                </td></tr>
              )}
              {users.map(u => (
                <tr key={u.id}>
                  <td className="text-muted">{u.id}</td>
                  <td className="fw-700">{u.username}</td>
                  <td>{u.full_name || "—"}</td>
                  <td className="text-muted" style={{ fontSize: 12 }}>{u.email || "—"}</td>
                  <td>
                    <span className={`badge ${u.role === "admin" ? "badge-blue" : "badge-gray"}`}>
                      {u.role === "admin" ? "🔑 Admin" : "👤 Staff"}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${u.is_active ? "badge-green" : "badge-red"}`}>
                      {u.is_active ? "Hoạt động" : "Bị khóa"}
                    </span>
                  </td>
                  <td className="text-muted" style={{ fontSize: 12 }}>
                    {new Date(u.created_at).toLocaleDateString("vi-VN")}
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button className="btn btn-outline btn-sm"
                        onClick={() => changeRole(u.id, u.role === "admin" ? "staff" : "admin")}
                        title={u.role === "admin" ? "Đổi thành Staff" : "Đổi thành Admin"}>
                        {u.role === "admin" ? "→ Staff" : "→ Admin"}
                      </button>
                      {u.is_active && (
                        <button className="btn btn-danger btn-sm" onClick={() => deactivate(u.id)}
                          title="Khóa tài khoản">
                          🔒
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Tab: Log hoạt động ── */}
      {tab === "logs" && (
        <div className="table-wrap">
          <div className="table-header">
            <span className="fw-600">Lịch sử hoạt động gần nhất</span>
            <span className="text-muted">{logs.length} bản ghi</span>
          </div>
          <table>
            <thead>
              <tr><th>Thời gian</th><th>Người dùng</th><th>Hành động</th><th>Chi tiết</th></tr>
            </thead>
            <tbody>
              {logs.length === 0 && (
                <tr><td colSpan={4}><div className="empty">Chưa có log nào</div></td></tr>
              )}
              {logs.map(l => (
                <tr key={l.id}>
                  <td className="text-muted" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                    {new Date(l.created_at).toLocaleString("vi-VN")}
                  </td>
                  <td className="fw-600">{l.username}</td>
                  <td>
                    <span className={`badge ${
                      l.action === "login"          ? "badge-green" :
                      l.action === "register"       ? "badge-blue"  :
                      l.action.includes("delete")   ? "badge-red"   :
                      l.action.includes("import")   ? "badge-orange" : "badge-gray"
                    }`}>{l.action}</span>
                  </td>
                  <td className="text-muted" style={{ fontSize: 13 }}>{l.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Modal tạo tài khoản ── */}
      {modal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && closeModal()}>
          <div className="modal" style={{ maxWidth: 460 }}>
            <div className="modal-header">
              <h3>➕ Tạo tài khoản mới</h3>
              <button className="btn-close" onClick={closeModal}>×</button>
            </div>
            <div className="modal-body">

              {formErr && (
                <div className="error-msg" style={{ marginBottom: 14 }}>⚠️ {formErr}</div>
              )}

              <div className="form-group">
                <label>Tên đăng nhập <span style={{ color:"#dc2626" }}>*</span></label>
                <input placeholder="Nhập username..." value={form.username}
                  onChange={e => set("username", e.target.value)} autoFocus />
              </div>

              <div className="form-group">
                <label>Họ và tên</label>
                <input placeholder="Nhập họ tên đầy đủ..." value={form.full_name}
                  onChange={e => set("full_name", e.target.value)} />
              </div>

              <div className="form-group">
                <label>Email</label>
                <input type="email" placeholder="example@email.com" value={form.email}
                  onChange={e => set("email", e.target.value)} />
              </div>

              <div className="form-group">
                <label>Mật khẩu <span style={{ color:"#dc2626" }}>*</span></label>
                <input type="password" placeholder="Tối thiểu 6 ký tự..." value={form.password}
                  onChange={e => set("password", e.target.value)} />
              </div>

              <div className="form-group">
                <label>Phân quyền</label>
                <select value={form.role} onChange={e => set("role", e.target.value)}>
                  <option value="staff"> Staff — Xem + nhập dữ liệu</option>
                  <option value="admin"> Admin — Toàn quyền hệ thống</option>
                </select>
              </div>

              <div style={{ background:"#f8fafc", border:"1px solid #e2e8f0", borderRadius:8,
                padding:"10px 14px", fontSize:12.5, color:"#475569" }}>
                <div style={{ fontWeight:600, marginBottom:4 }}>Phân quyền:</div>
                <div><strong>Staff:</strong> Xem SP, tạo đơn hàng, dùng chatbot, xem dashboard</div>
                <div><strong>Admin:</strong> Toàn quyền + quản lý user, xóa SP, nhập hàng, xem log</div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn btn-outline" onClick={closeModal}>Hủy</button>
              <button className="btn btn-primary" onClick={handleCreate} disabled={saving}>
                {saving ? "Đang tạo..." : " Tạo tài khoản"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
