import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import API from "../services/api";
import { useAuth } from "../context/AuthContext";

const fmt = n => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + "đ";
const fmtDate = d => new Date(d).toLocaleString("vi-VN");
const toInput = d => d?.toISOString?.().slice(0,10) ?? "";

const emptyRow = () => ({ product_id:"", quantity:"", import_price:"", supplier:"", note:"" });

// ── ProductSearch ────────────────────────────────────────
function ProductSearch({ products, selectedId, onSelect }) {
  const [query, setQuery] = useState(""); const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const selected = products.find(p => p.id === Number(selectedId));
  useEffect(() => {
    const h = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const filtered = products.filter(p => !query || p.name.toLowerCase().includes(query.toLowerCase())).slice(0,10);
  return (
    <div ref={ref} style={{ position:"relative" }}>
      {selected && !open ? (
        <div onClick={() => setOpen(true)} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
          padding:"8px 11px", border:"1.5px solid #2563eb", borderRadius:8, background:"#eff6ff", fontSize:13, cursor:"pointer" }}>
          <span style={{ fontWeight:600, color:"#1e40af" }}>{selected.name}</span>
          <button onClick={e => { e.stopPropagation(); onSelect(""); }}
            style={{ background:"none", border:"none", cursor:"pointer", fontSize:15, color:"#94a3b8" }}>×</button>
        </div>
      ) : (
        <input autoFocus={open} value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder="Gõ tên sản phẩm..." style={{ width:"100%" }} />
      )}
      {open && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", left:0, right:0, zIndex:999,
          background:"#fff", border:"1.5px solid #e2e8f0", borderRadius:10,
          boxShadow:"0 8px 24px rgba(0,0,0,.12)", maxHeight:230, overflowY:"auto" }}>
          {filtered.length === 0
            ? <div style={{ padding:"10px 14px", color:"#94a3b8", fontSize:13 }}>Không tìm thấy</div>
            : filtered.map(p => (
              <div key={p.id} onClick={() => { onSelect(p.id); setQuery(""); setOpen(false); }}
                style={{ padding:"9px 14px", cursor:"pointer", fontSize:13, display:"flex",
                  justifyContent:"space-between", borderBottom:"1px solid #f1f5f9" }}
                onMouseEnter={e => e.currentTarget.style.background="#f8fafc"}
                onMouseLeave={e => e.currentTarget.style.background="transparent"}>
                <span style={{ fontWeight:500 }}>{p.name}</span>
                <span style={{ fontSize:11.5, color:"#64748b" }}>tồn: {p.quantity}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

// ── Trang chính ──────────────────────────────────────────
export default function StockImport() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [records, setRecords] = useState([]);
  const [products, setProducts] = useState([]);
  const [modal, setModal] = useState(false);
  const [rows, setRows] = useState([emptyRow()]);
  const [saving, setSaving] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { if (!isAdmin) { navigate("/"); return; } loadAll(); }, []);

  const loadRecords = async () => {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate)   params.end_date   = endDate;
    const res = await API.get("/stock-imports/", { params });
    setRecords(res.data);
  };
  const loadAll = () => Promise.all([
    loadRecords(),
    API.get("/products/").then(r => setProducts(r.data))
  ]).finally(() => setLoading(false));

  // ── Rows helpers ──
  const addRow    = () => setRows(p => [...p, emptyRow()]);
  const removeRow = i => setRows(p => p.filter((_,idx) => idx !== i));
  const updateRow = (i, field, val) => setRows(p => p.map((r,idx) => idx===i ? {...r,[field]:val} : r));

  const rowCost = row => {
    const q = Number(row.quantity); const p = Number(row.import_price);
    return (!isNaN(q) && !isNaN(p) && q > 0 && p >= 0) ? q * p : 0;
  };
  const grandTotal = rows.reduce((s,r) => s + rowCost(r), 0);

  const openModal = () => { setRows([emptyRow()]); setModal(true); };

  const handleSave = async () => {
    const valid = rows.filter(r => r.product_id && Number(r.quantity) > 0 && Number(r.import_price) >= 0);
    if (!valid.length) { alert("Vui lòng điền đầy đủ ít nhất 1 sản phẩm"); return; }
    setSaving(true);
    try {
      await API.post("/stock-imports/bulk", valid.map(r => ({
        product_id: Number(r.product_id), quantity: Number(r.quantity),
        import_price: Number(r.import_price),
        supplier: r.supplier || null, note: r.note || null,
      })));
      setModal(false);
      await loadAll();
    } catch (err) { alert(err.response?.data?.detail || "Lỗi nhập hàng"); }
    finally { setSaving(false); }
  };

  const setPreset = days => {
    const end = new Date(); const start = new Date();
    start.setDate(end.getDate() - days);
    setStartDate(toInput(start)); setEndDate(toInput(end));
  };

  const totalCostAll  = records.reduce((s,r) => s + r.total_cost, 0);
  const totalQtyAll   = records.reduce((s,r) => s + r.quantity, 0);

  if (loading) return <div className="loading">⏳ Đang tải...</div>;

  return (
    <div>
      <div className="page-header flex-between">
        <div><h2>📥 Nhập hàng</h2><p>Quản lý phiếu nhập kho (chỉ Admin)</p></div>
        <div className="flex gap-2">
          <a href={`http://127.0.0.1:8000/stock-imports/export-csv${startDate||endDate?`?${new URLSearchParams({...(startDate&&{start_date:startDate}),...(endDate&&{end_date:endDate})})}`:"" }`}
            target="_blank" className="btn btn-outline btn-sm">📊 Export CSV</a>
          <button className="btn btn-primary btn-sm" onClick={openModal}>+ Tạo phiếu nhập hàng</button>
        </div>
      </div>

      {/* Thống kê */}
      <div className="stat-grid" style={{ marginBottom:18 }}>
        <div className="stat-card blue"><div className="stat-label">Tổng phiếu</div>
          <div className="stat-value">{records.length}</div><div className="stat-sub">Đang hiển thị</div></div>
        <div className="stat-card green"><div className="stat-label">Tổng SL nhập</div>
          <div className="stat-value">{totalQtyAll.toLocaleString()}</div><div className="stat-sub">Đơn vị</div></div>
        <div className="stat-card orange"><div className="stat-label">Tổng chi phí</div>
          <div className="stat-value" style={{ fontSize:19 }}>{fmt(totalCostAll)}</div><div className="stat-sub">Vốn nhập</div></div>
      </div>

      {/* Bộ lọc ngày */}
      <div className="table-wrap" style={{ marginBottom:16 }}>
        <div className="table-header" style={{ flexWrap:"wrap", gap:10 }}>
          <div className="flex gap-2" style={{ alignItems:"center", flexWrap:"wrap" }}>
            <span className="fw-600" style={{ fontSize:13 }}>🗓️ Lọc ngày nhập:</span>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={{ width:145 }} />
            <span className="text-muted">→</span>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={{ width:145 }} />
            <button className="btn btn-primary btn-sm" onClick={loadRecords}>Lọc</button>
            {(startDate||endDate) && (
              <button className="btn btn-outline btn-sm" onClick={() => { setStartDate(""); setEndDate(""); setTimeout(loadRecords,0); }}>✕ Bỏ lọc</button>
            )}
          </div>
          <div className="flex gap-2">
            {[["Hôm nay",0],["7 ngày",7],["30 ngày",30],["Tháng này",-1]].map(([label,days]) => (
              <button key={label} className="btn btn-outline btn-sm" onClick={() => {
                if (days === -1) {
                  const t = new Date(); const s = new Date(t.getFullYear(), t.getMonth(), 1);
                  setStartDate(toInput(s)); setEndDate(toInput(t));
                } else if (days === 0) { const t = toInput(new Date()); setStartDate(t); setEndDate(t); }
                else setPreset(days);
                setTimeout(loadRecords, 50);
              }}>{label}</button>
            ))}
          </div>
        </div>
      </div>

      {/* Bảng lịch sử */}
      <div className="table-wrap">
        <div className="table-header">
          <span className="fw-600">{records.length} phiếu nhập</span>
          <span className="fw-700 text-warning">{fmt(totalCostAll)}</span>
        </div>
        <table>
          <thead>
            <tr><th>#</th><th>Sản phẩm</th><th>SL nhập</th><th>Giá nhập/đvt</th>
              <th>Tổng chi phí</th><th>Nhà cung cấp</th><th>Người nhập</th><th>Ngày nhập</th></tr>
          </thead>
          <tbody>
            {records.length === 0 && <tr><td colSpan={8}><div className="empty"><div className="empty-icon">📥</div>Chưa có phiếu nhập</div></td></tr>}
            {records.map(r => (
              <tr key={r.id}>
                <td className="text-muted">#{r.id}</td>
                <td className="fw-600">{r.product_name}</td>
                <td><span className="badge badge-blue">+{r.quantity}</span></td>
                <td>{fmt(r.import_price)}</td>
                <td className="fw-700 text-warning">{fmt(r.total_cost)}</td>
                <td className="text-muted">{r.supplier || "—"}</td>
                <td><span className="badge badge-gray">{r.imported_by_name}</span></td>
                <td className="text-muted" style={{ fontSize:12, whiteSpace:"nowrap" }}>{fmtDate(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal nhập nhiều sản phẩm */}
      {modal && (
        <div className="modal-overlay" onClick={e => e.target===e.currentTarget && setModal(false)}>
          <div className="modal" style={{ maxWidth:740 }}>
            <div className="modal-header">
              <h3>📥 Tạo phiếu nhập hàng</h3>
              <button className="btn-close" onClick={() => setModal(false)}>×</button>
            </div>
            <div className="modal-body">
              {/* Header cột */}
              <div style={{ display:"grid", gridTemplateColumns:"2fr 80px 110px 1fr 1fr 36px",
                gap:8, marginBottom:6, paddingBottom:6, borderBottom:"1px solid #e2e8f0" }}>
                {["Sản phẩm *","SL *","Giá nhập *","Nhà cung cấp","Ghi chú",""].map((h,i) => (
                  <div key={i} style={{ fontSize:12, fontWeight:700, color:"#64748b" }}>{h}</div>
                ))}
              </div>

              {/* Danh sách dòng */}
              {rows.map((row, i) => {
                const sp = products.find(p => p.id === Number(row.product_id));
                const cost = rowCost(row);
                return (
                  <div key={i}>
                    <div style={{ display:"grid", gridTemplateColumns:"2fr 80px 110px 1fr 1fr 36px", gap:8, marginBottom:6 }}>
                      <ProductSearch products={products} selectedId={row.product_id}
                        onSelect={v => updateRow(i,"product_id",v)} />
                      <input type="number" min={1} value={row.quantity} placeholder="0"
                        onChange={e => updateRow(i,"quantity",e.target.value)} style={{ width:"100%" }} />
                      <input type="number" min={0} value={row.import_price} placeholder="0"
                        onChange={e => updateRow(i,"import_price",e.target.value)} style={{ width:"100%" }} />
                      <input value={row.supplier} placeholder="Nhà cung cấp"
                        onChange={e => updateRow(i,"supplier",e.target.value)} style={{ width:"100%" }} />
                      <input value={row.note} placeholder="Ghi chú"
                        onChange={e => updateRow(i,"note",e.target.value)} style={{ width:"100%" }} />
                      <button className="btn btn-danger btn-sm" style={{ padding:"5px 8px" }}
                        onClick={() => rows.length > 1 && removeRow(i)} disabled={rows.length===1}>✕</button>
                    </div>
                    {/* Thông tin sản phẩm được chọn */}
                    {sp && (
                      <div style={{ marginBottom:8, marginLeft:0, padding:"5px 10px", background:"#f0fdf4",
                        border:"1px solid #bbf7d0", borderRadius:6, fontSize:12, color:"#15803d",
                        display:"flex", gap:16 }}>
                        <span>📦 Tồn kho: <b>{sp.quantity}</b></span>
                        <span>💰 Giá bán: <b>{fmt(sp.price)}</b></span>
                        {cost > 0 && <span>🧾 Chi phí dòng này: <b>{fmt(cost)}</b></span>}
                        {cost > 0 && sp.price > 0 && (
                          <span>📈 Margin: <b>{(((sp.price - Number(row.import_price)) / sp.price) * 100).toFixed(0)}%</b></span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              <button className="btn btn-outline btn-sm" onClick={addRow} style={{ marginBottom:16 }}>
                + Thêm sản phẩm khác
              </button>

              {/* Tổng chi phí */}
              {grandTotal > 0 && (
                <div style={{ background:"#fff7ed", border:"1px solid #fed7aa", borderRadius:8,
                  padding:"12px 16px", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <span className="fw-600">💰 Tổng chi phí phiếu nhập ({rows.filter(r=>r.product_id&&r.quantity&&r.import_price).length} sản phẩm):</span>
                  <span className="fw-700 text-warning" style={{ fontSize:18 }}>{fmt(grandTotal)}</span>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setModal(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? "Đang lưu..." : `📥 Nhập hàng (${rows.filter(r=>r.product_id&&r.quantity).length} SP)`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
