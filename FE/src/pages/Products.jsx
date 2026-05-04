import { useEffect, useState } from "react";
import API from "../services/api";
import { useAuth } from "../context/AuthContext";

const empty = { name: "", price: "", quantity: "", category_id: "", low_stock_threshold: 10 };
const fmt = n => new Intl.NumberFormat("vi-VN").format(n) + "đ";

export default function Products() {
  const { isAdmin } = useAuth();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState(""); const [catF, setCatF] = useState("");
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(empty); const [editing, setEditing] = useState(null);

  const load = async () => {
    const params = { search, min_price: 0, max_price: 1e9 };
    if (catF) params.category_id = catF;
    const res = await API.get("/products/", { params });
    setProducts(res.data);
  };

  useEffect(() => {
    load();
    API.get("/categories/").then(r => setCategories(r.data));
  }, []);

  const openAdd = () => { setForm(empty); setEditing(null); setModal(true); };
  const openEdit = p => { setForm({ name: p.name, price: p.price, quantity: p.quantity, category_id: p.category_id || "", low_stock_threshold: p.low_stock_threshold }); setEditing(p.id); setModal(true); };

  const save = async () => {
    const body = { ...form, price: Number(form.price), quantity: Number(form.quantity), category_id: form.category_id ? Number(form.category_id) : null };
    try {
      if (editing) await API.put(`/products/${editing}`, body);
      else await API.post("/products/", body);
      setModal(false); load();
    } catch (err) { alert(err.response?.data?.detail || "Lỗi lưu sản phẩm"); }
  };

  const del = async id => {
    if (!confirm("Xác nhận xóa sản phẩm này?")) return;
    await API.delete(`/products/${id}`); load();
  };

  const catName = id => categories.find(c => c.id === id)?.name || "—";

  return (
    <div>
      <div className="page-header flex-between">
        <div><h2>🛍️ Sản phẩm</h2><p>Quản lý danh sách sản phẩm trong kho</p></div>
        <div className="flex gap-2">
          <a href="http://127.0.0.1:8000/products/export-csv" target="_blank" className="btn btn-outline btn-sm">📥 Export CSV</a>
          <button className="btn btn-primary btn-sm" onClick={openAdd}>+ Thêm sản phẩm</button>
        </div>
      </div>
      <div className="table-wrap">
        <div className="table-header">
          <div className="search-bar">
            <input placeholder="🔍 Tìm sản phẩm..." value={search} onChange={e => setSearch(e.target.value)} style={{ width: 200 }} />
            <select value={catF} onChange={e => setCatF(e.target.value)} style={{ width: 150 }}>
              <option value="">Tất cả danh mục</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <button className="btn btn-outline btn-sm" onClick={load}>Lọc</button>
          </div>
          <span className="text-muted">{products.length} sản phẩm</span>
        </div>
        <table>
          <thead><tr><th>#</th><th>Tên sản phẩm</th><th>Danh mục</th><th>Giá bán</th><th>Tồn kho</th><th>Trạng thái</th>{isAdmin && <th>Thao tác</th>}</tr></thead>
          <tbody>
            {products.length === 0 && <tr><td colSpan={7}><div className="empty"><div className="empty-icon">📦</div>Chưa có sản phẩm nào</div></td></tr>}
            {products.map(p => (
              <tr key={p.id}>
                <td className="text-muted">{p.id}</td>
                <td className="fw-600">{p.name}</td>
                <td>{catName(p.category_id)}</td>
                <td className="fw-600">{fmt(p.price)}</td>
                <td><span className={p.quantity === 0 ? "text-danger fw-700" : p.quantity <= p.low_stock_threshold ? "text-warning fw-700" : ""}>{p.quantity}</span></td>
                <td>
                  {p.quantity === 0 ? <span className="badge badge-red">Hết hàng</span>
                    : p.quantity <= p.low_stock_threshold ? <span className="badge badge-orange">Sắp hết</span>
                    : <span className="badge badge-green">Còn hàng</span>}
                </td>
                {isAdmin && <td>
                  <button className="btn btn-outline btn-sm" style={{ marginRight: 6 }} onClick={() => openEdit(p)}>✏️ Sửa</button>
                  <button className="btn btn-danger btn-sm" onClick={() => del(p.id)}>🗑️</button>
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
              <h3>{editing ? "✏️ Sửa sản phẩm" : "➕ Thêm sản phẩm"}</h3>
              <button className="btn-close" onClick={() => setModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group"><label>Tên sản phẩm *</label><input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Nhập tên sản phẩm..." /></div>
              <div className="form-group"><label>Giá bán (VNĐ) *</label><input type="number" value={form.price} onChange={e => setForm({...form, price: e.target.value})} placeholder="0" /></div>
              <div className="form-group"><label>Số lượng tồn kho *</label><input type="number" value={form.quantity} onChange={e => setForm({...form, quantity: e.target.value})} placeholder="0" /></div>
              <div className="form-group"><label>Danh mục</label>
                <select value={form.category_id} onChange={e => setForm({...form, category_id: e.target.value})}>
                  <option value="">-- Chọn danh mục --</option>
                  {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="form-group"><label>Ngưỡng cảnh báo hết hàng</label><input type="number" value={form.low_stock_threshold} onChange={e => setForm({...form, low_stock_threshold: Number(e.target.value)})} /></div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setModal(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={save}>{editing ? "Lưu thay đổi" : "Thêm mới"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
