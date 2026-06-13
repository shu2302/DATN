import { useEffect, useState, useRef } from "react";
import API from "../services/api";
import { useAuth } from "../context/AuthContext";

const fmt = n => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + "đ";

// ── ProductSearch cho form combo ──────────────────────────
function ProductSearch({ products, selectedIds, onToggle }) {
  const [query, setQuery] = useState("");
  const filtered = products
    .filter(p => !query || p.name.toLowerCase().includes(query.toLowerCase()))
    .slice(0, 12);

  return (
    <div>
      <input value={query} onChange={e => setQuery(e.target.value)}
        placeholder="🔍 Tìm sản phẩm để thêm vào combo..."
        style={{ width:"100%", marginBottom:10 }} />
      <div style={{ display:"flex", flexWrap:"wrap", gap:8, maxHeight:200, overflowY:"auto" }}>
        {filtered.map(p => {
          const selected = selectedIds.includes(p.id);
          return (
            <div key={p.id} onClick={() => onToggle(p.id)}
              style={{
                padding:"6px 12px", borderRadius:8, fontSize:13, cursor:"pointer",
                border:`1.5px solid ${selected ? "#2563eb" : "#e2e8f0"}`,
                background: selected ? "#eff6ff" : "#fff",
                color:      selected ? "#1e40af" : "#374151",
                fontWeight: selected ? 700 : 400,
              }}>
              {selected ? "✓ " : ""}{p.name}
              <span style={{ fontSize:11, color:"#64748b", marginLeft:6 }}>{fmt(p.price)}</span>
            </div>
          );
        })}
      </div>
      {selectedIds.length > 0 && (
        <div style={{ marginTop:10, fontSize:12.5, color:"#475569" }}>
          Đã chọn: <b>{selectedIds.length}</b> sản phẩm
          — Tổng giá gốc: <b>{fmt(
            selectedIds.reduce((s, id) => s + (products.find(p => p.id === id)?.price || 0), 0)
          )}</b>
        </div>
      )}
    </div>
  );
}

// ── Combo Card ─────────────────────────────────────────────
function ComboCard({ combo, onEdit, onDelete, isAdmin }) {
  return (
    <div className="table-wrap" style={{ padding:"18px 20px", marginBottom:14 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
        <div>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
            <span className="fw-700" style={{ fontSize:15 }}>{combo.name}</span>
            <span className="badge badge-green" style={{ fontSize:12 }}>
              -{combo.discount_pct}% giảm giá
            </span>
            {!combo.is_active && <span className="badge badge-red">Tắt</span>}
          </div>
          <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:10 }}>
            {combo.products.map(p => (
              <span key={p.product_id} style={{
                padding:"3px 10px", borderRadius:20, fontSize:12,
                background:"#f1f5f9", color:"#475569", fontWeight:500
              }}>
                {p.name} — {fmt(p.price)}
              </span>
            ))}
          </div>
          <div style={{ display:"flex", gap:20, fontSize:13 }}>
            <span className="text-muted" style={{ textDecoration:"line-through" }}>
              {fmt(combo.total_original)}
            </span>
            <span className="text-success fw-700">{fmt(combo.total_discounted)}</span>
            <span style={{ color:"#dc2626", fontWeight:600 }}>
              Tiết kiệm {fmt(combo.saved)}
            </span>
          </div>
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            <button className="btn btn-outline btn-sm" onClick={() => onEdit(combo)}>✏️ Sửa</button>
            <button className="btn btn-danger btn-sm" onClick={() => onDelete(combo.id)}>🗑️</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── AI Suggest Panel ────────────────────────────────────────
function AISuggestPanel({ products, onApply }) {
  const [loading, setLoading]       = useState(false);
  const [suggestions, setSuggestions] = useState(null);

  const analyze = async () => {
    setLoading(true); setSuggestions(null);
    try {
      const res = await API.get("/combos/ai-suggest");
      setSuggestions(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Lỗi phân tích");
    } finally { setLoading(false); }
  };

  return (
    <div className="table-wrap" style={{ padding:"20px", marginBottom:20 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
        <div>
          <div className="fw-700" style={{ fontSize:14 }}>🤖 AI Gợi ý Combo</div>
          <div className="text-muted" style={{ fontSize:12.5, marginTop:2 }}>
            Phân tích lịch sử mua hàng để tìm sản phẩm hay được mua cùng nhau
          </div>
        </div>
        <button className="btn btn-primary btn-sm" onClick={analyze} disabled={loading}>
          {loading ? "🔍 Đang phân tích..." : "🚀 Phân tích"}
        </button>
      </div>

      {suggestions && (
        <>
          <div className="text-muted" style={{ fontSize:12, marginBottom:12 }}>
            Phân tích từ <b>{suggestions.total_orders_analyzed}</b> đơn hàng
          </div>

          {suggestions.suggestions.length === 0 ? (
            <div className="empty">
              <div className="empty-icon">📊</div>
              Chưa đủ dữ liệu để gợi ý combo
            </div>
          ) : (
            suggestions.suggestions.map((s, i) => {
              const discounted = s.total_price * (1 - s.suggested_discount / 100);
              return (
                <div key={i} style={{
                  padding:"14px 16px", borderRadius:10, marginBottom:10,
                  background:"#f8fafc", border:"1px solid #e2e8f0"
                }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
                    <div>
                      <div className="fw-700" style={{ fontSize:13.5 }}>
                        💡 {s.suggested_name}
                      </div>
                      <div className="text-muted" style={{ fontSize:12, margin:"4px 0 8px" }}>
                        {s.suggested_reason} • Đã mua cùng {s.co_buy_count} lần
                      </div>
                      <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                        {s.product_names.map((n, j) => (
                          <span key={j} style={{
                            padding:"2px 8px", borderRadius:12, fontSize:12,
                            background:"#dbeafe", color:"#1e40af"
                          }}>{n}</span>
                        ))}
                      </div>
                    </div>
                    <div style={{ textAlign:"right" }}>
                      <div style={{ fontSize:12, color:"#64748b", textDecoration:"line-through" }}>
                        {fmt(s.total_price)}
                      </div>
                      <div className="fw-700 text-success">{fmt(discounted)}</div>
                      <div style={{ fontSize:12, color:"#dc2626" }}>-{s.suggested_discount}%</div>
                      <button className="btn btn-outline btn-sm" style={{ marginTop:8 }}
                        onClick={() => onApply(s)}>
                        + Tạo combo này
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </>
      )}
    </div>
  );
}

// ── Main Combos Page ────────────────────────────────────────
export default function Combos() {
  const { isAdmin } = useAuth();
  const [combos, setCombos]       = useState([]);
  const [products, setProducts]   = useState([]);
  const [modal, setModal]         = useState(false);
  const [editing, setEditing]     = useState(null);
  const [form, setForm]           = useState({ name:"", discount_pct:5, product_ids:[] });
  const [saving, setSaving]       = useState(false);
  const [tab, setTab]             = useState("list");

  const load = () => {
    const ep = isAdmin ? "/combos/all" : "/combos/";
    API.get(ep).then(r => setCombos(r.data));
  };

  useEffect(() => {
    load();
    API.get("/products/").then(r => setProducts(r.data));
  }, []);

  const openAdd  = () => { setForm({ name:"", discount_pct:5, product_ids:[] }); setEditing(null); setModal(true); };
  const openEdit = c => { setForm({ name:c.name, discount_pct:c.discount_pct, product_ids:c.products.map(p=>p.product_id) }); setEditing(c.id); setModal(true); };

  const toggleProduct = pid => {
    setForm(prev => ({
      ...prev,
      product_ids: prev.product_ids.includes(pid)
        ? prev.product_ids.filter(id => id !== pid)
        : [...prev.product_ids, pid]
    }));
  };

  const applyAISuggest = s => {
    setForm({ name: s.suggested_name, discount_pct: s.suggested_discount, product_ids: s.product_ids });
    setEditing(null);
    setModal(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) { alert("Nhập tên combo"); return; }
    if (form.product_ids.length < 2) { alert("Chọn ít nhất 2 sản phẩm"); return; }
    setSaving(true);
    try {
      if (editing) await API.put(`/combos/${editing}`, form);
      else         await API.post("/combos/", form);
      setModal(false); load();
    } catch (err) { alert(err.response?.data?.detail || "Lỗi lưu combo"); }
    finally { setSaving(false); }
  };

  const handleDelete = async id => {
    if (!confirm("Xóa combo này?")) return;
    await API.delete(`/combos/${id}`); load();
  };

  const activeCombos   = combos.filter(c => c.is_active);
  const inactiveCombos = combos.filter(c => !c.is_active);

  const previewDiscount = form.product_ids.reduce(
    (s, id) => s + (products.find(p => p.id === id)?.price || 0), 0
  ) * (form.discount_pct / 100);

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h2>🎁 Gói Sản phẩm</h2>
          <p>Tạo gói giảm giá — mua nhiều tiết kiệm hơn</p>
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            <button className={`btn btn-sm ${tab==="ai" ? "btn-primary":"btn-outline"}`}
              onClick={() => setTab(t => t==="ai" ? "list" : "ai")}>
              🤖 AI Gợi ý
            </button>
            <button className="btn btn-primary btn-sm" onClick={openAdd}>+ Tạo gói</button>
          </div>
        )}
      </div>

      {/* AI Suggest Panel (Admin only) */}
      {isAdmin && tab === "ai" && (
        <AISuggestPanel products={products} onApply={applyAISuggest} />
      )}

      {/* Active combos */}
      <h3 style={{ marginBottom:12, fontSize:14, fontWeight:700 }}>
        🟢 gói đang hoạt động ({activeCombos.length})
      </h3>
      {activeCombos.length === 0 ? (
        <div className="table-wrap" style={{ padding:"40px", textAlign:"center" }}>
          <div className="empty-icon">🎁</div>
          <div>Chưa có gói giảm giá nào. {isAdmin && "Nhấn '+ Tạo combo' hoặc dùng AI gợi ý!"}</div>
        </div>
      ) : (
        activeCombos.map(c => (
          <ComboCard key={c.id} combo={c} onEdit={openEdit}
            onDelete={handleDelete} isAdmin={isAdmin} />
        ))
      )}

      {/* Inactive combos (admin only) */}
      {isAdmin && inactiveCombos.length > 0 && (
        <>
          <h3 style={{ marginTop:24, marginBottom:12, fontSize:14, fontWeight:700, color:"#94a3b8" }}>
            ⚫ gói giảm giá đã tắt ({inactiveCombos.length})
          </h3>
          {inactiveCombos.map(c => (
            <ComboCard key={c.id} combo={c} onEdit={openEdit}
              onDelete={handleDelete} isAdmin={isAdmin} />
          ))}
        </>
      )}

      {/* Modal tạo/sửa combo */}
      {modal && (
        <div className="modal-overlay" onClick={e => e.target===e.currentTarget && setModal(false)}>
          <div className="modal" style={{ maxWidth:620 }}>
            <div className="modal-header">
              <h3>{editing ? "✏️ Sửa combo" : "➕ Tạo combo mới"}</h3>
              <button className="btn-close" onClick={() => setModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Tên combo *</label>
                <input value={form.name} onChange={e => setForm({...form, name:e.target.value})}
                  placeholder="VD: Combo Bữa sáng, Combo Đồ uống..." />
              </div>

              <div className="form-group">
                <label>% Giảm giá *</label>
                <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                  <input type="range" min={1} max={50} value={form.discount_pct}
                    onChange={e => setForm({...form, discount_pct:Number(e.target.value)})}
                    style={{ flex:1 }} />
                  <span className="fw-700 text-success" style={{ fontSize:18, minWidth:48 }}>
                    -{form.discount_pct}%
                  </span>
                </div>
                {form.product_ids.length >= 2 && (
                  <div style={{ marginTop:6, fontSize:12.5, color:"#15803d" }}>
                    💰 Khách tiết kiệm: {fmt(previewDiscount)} khi mua combo này
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>Chọn sản phẩm trong gói giảm giá (tối thiểu 2) *</label>
                <ProductSearch products={products} selectedIds={form.product_ids} onToggle={toggleProduct} />
              </div>

              {editing && (
                <div className="form-group">
                  <label style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer" }}>
                    <input type="checkbox"
                      checked={form.is_active !== false}
                      onChange={e => setForm({...form, is_active:e.target.checked})} />
                    Gói giảm giá đang hoạt động
                  </label>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setModal(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? "Đang lưu..." : editing ? "Lưu thay đổi" : "Tạo combo"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
