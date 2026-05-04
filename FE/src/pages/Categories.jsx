import { useEffect, useState } from "react";
import API from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Categories() {
  const { isAdmin } = useAuth();
  const [cats, setCats] = useState([]);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [editing, setEditing] = useState(null);

  const load = () => API.get("/categories/").then(r => setCats(r.data));
  useEffect(() => { load(); }, []);

  const openAdd = () => { setForm({ name: "", description: "" }); setEditing(null); setModal(true); };
  const openEdit = c => { setForm({ name: c.name, description: c.description || "" }); setEditing(c.id); setModal(true); };

  const save = async () => {
    try {
      if (editing) await API.put(`/categories/${editing}`, form);
      else await API.post("/categories/", form);
      setModal(false); load();
    } catch (err) { alert(err.response?.data?.detail || "Lỗi"); }
  };

  const del = async id => {
    if (!confirm("Xóa danh mục này?")) return;
    try { await API.delete(`/categories/${id}`); load(); }
    catch (err) { alert(err.response?.data?.detail || "Không thể xóa (có sản phẩm liên quan)"); }
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div><h2>📂 Danh mục</h2><p>Phân loại sản phẩm theo nhóm</p></div>
        {isAdmin && <button className="btn btn-primary btn-sm" onClick={openAdd}>+ Thêm danh mục</button>}
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Tên danh mục</th><th>Mô tả</th>{isAdmin && <th>Thao tác</th>}</tr></thead>
          <tbody>
            {cats.length === 0 && <tr><td colSpan={4}><div className="empty"><div className="empty-icon">📂</div>Chưa có danh mục</div></td></tr>}
            {cats.map(c => (
              <tr key={c.id}>
                <td className="text-muted">{c.id}</td>
                <td className="fw-600">{c.name}</td>
                <td className="text-muted">{c.description || "—"}</td>
                {isAdmin && <td>
                  <button className="btn btn-outline btn-sm" style={{ marginRight: 6 }} onClick={() => openEdit(c)}>✏️ Sửa</button>
                  <button className="btn btn-danger btn-sm" onClick={() => del(c.id)}>🗑️</button>
                </td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {modal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>{editing ? "Sửa danh mục" : "Thêm danh mục"}</h3>
              <button className="btn-close" onClick={() => setModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group"><label>Tên danh mục *</label><input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="VD: Thực phẩm" /></div>
              <div className="form-group"><label>Mô tả</label><textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})} placeholder="Mô tả ngắn..." /></div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setModal(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={save}>{editing ? "Lưu" : "Thêm"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
