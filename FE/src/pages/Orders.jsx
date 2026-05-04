import { useEffect, useState, useRef } from "react";
import API from "../services/api";

const fmt = n => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + "đ";
const toInput = d => d?.toISOString?.().slice(0,10) ?? "";

function ProductSearch({ allProducts, selectedId, onSelect }) {
  const [query, setQuery] = useState(""); const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const selected = allProducts.find(p => p.id === Number(selectedId));
  useEffect(() => {
    const h = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const filtered = allProducts.filter(p => p.quantity > 0)
    .filter(p => !query || p.name.toLowerCase().includes(query.toLowerCase())).slice(0,10);

  return (
    <div ref={ref} style={{ position:"relative" }}>
      {selected && !open ? (
        <div onClick={() => setOpen(true)} style={{ display:"flex", alignItems:"center",
          justifyContent:"space-between", padding:"9px 12px", border:"1.5px solid #2563eb",
          borderRadius:8, background:"#eff6ff", fontSize:13.5, cursor:"pointer" }}>
          <span style={{ fontWeight:600, color:"#1e40af" }}>{selected.name}</span>
          <span style={{ display:"flex", alignItems:"center", gap:8 }}>
            <span style={{ fontSize:12, color:"#64748b" }}>còn {selected.quantity}</span>
            <button onClick={e => { e.stopPropagation(); onSelect(""); setQuery(""); }}
              style={{ background:"none", border:"none", cursor:"pointer", fontSize:16, color:"#94a3b8" }}>×</button>
          </span>
        </div>
      ) : (
        <input autoFocus={open} value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder={selected ? selected.name : "Gõ tên sản phẩm..."}
          style={{ width:"100%" }} />
      )}
      {open && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", left:0, right:0, zIndex:999,
          background:"#fff", border:"1.5px solid #e2e8f0", borderRadius:10,
          boxShadow:"0 8px 24px rgba(0,0,0,.12)", maxHeight:250, overflowY:"auto" }}>
          {filtered.length === 0
            ? <div style={{ padding:"12px 16px", color:"#94a3b8", fontSize:13 }}>Không tìm thấy</div>
            : filtered.map(p => (
              <div key={p.id} onClick={() => { onSelect(p.id); setQuery(""); setOpen(false); }}
                style={{ padding:"10px 16px", cursor:"pointer", fontSize:13.5, display:"flex",
                  justifyContent:"space-between", borderBottom:"1px solid #f1f5f9" }}
                onMouseEnter={e => e.currentTarget.style.background="#f8fafc"}
                onMouseLeave={e => e.currentTarget.style.background="transparent"}>
                <span style={{ fontWeight:500 }}>{p.name}</span>
                <span style={{ fontSize:12, color:"#64748b" }}>{fmt(p.price)} · còn {p.quantity}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [products, setProducts] = useState([]);
  const [modal, setModal] = useState(false);
  const [detail, setDetail] = useState(null);
  const [items, setItems] = useState([{ product_id:"", quantity:1 }]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  // Bộ lọc ngày
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const loadOrders = async () => {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate)   params.end_date   = endDate;
    const res = await API.get("/orders/", { params });
    setOrders(res.data);
  };
  const loadProducts = () => API.get("/products/").then(r => setProducts(r.data));

  useEffect(() => {
    Promise.all([loadOrders(), loadProducts()]).finally(() => setLoading(false));
  }, []);

  const openModal = () => { setItems([{ product_id:"", quantity:1 }]); setModal(true); };
  const addItem    = () => setItems(p => [...p, { product_id:"", quantity:1 }]);
  const removeItem = i => setItems(p => p.filter((_,idx) => idx !== i));
  const setProductId = (i, v) => setItems(p => p.map((it,idx) => idx===i ? {...it,product_id:v} : it));
  const setQty = (i, v) => setItems(p => p.map((it,idx) => idx===i ? {...it,quantity:v} : it));
  const calcTotal = () => items.reduce((s,it) => {
    const p = products.find(pr => pr.id === Number(it.product_id));
    return s + (p ? p.price * Number(it.quantity) : 0);
  }, 0);

  const createOrder = async () => {
    const valid = items.filter(i => i.product_id && Number(i.quantity) > 0);
    if (!valid.length) { alert("Chọn ít nhất 1 sản phẩm"); return; }
    const ids = valid.map(i => i.product_id);
    if (new Set(ids).size !== ids.length) { alert("Có sản phẩm bị trùng"); return; }
    setSaving(true);
    try {
      await API.post("/orders/", { items: valid.map(i => ({ product_id: Number(i.product_id), quantity: Number(i.quantity) })) });
      setModal(false);
      await Promise.all([loadOrders(), loadProducts()]);
    } catch (err) { alert(err.response?.data?.detail || "Lỗi tạo đơn hàng"); }
    finally { setSaving(false); }
  };

  const openDetail = async id => {
    const res = await API.get(`/orders/${id}`);
    setDetail(res.data);
  };

  const setPreset = (days) => {
    const end = new Date(); const start = new Date();
    start.setDate(end.getDate() - days);
    setStartDate(toInput(start)); setEndDate(toInput(end));
  };

  if (loading) return <div className="loading">⏳ Đang tải...</div>;

  return (
    <div>
      <div className="page-header flex-between">
        <div><h2>🧾 Đơn hàng</h2><p>Quản lý và theo dõi đơn hàng</p></div>
        <div className="flex gap-2">
          <a href={`http://127.0.0.1:8000/orders/export-csv${startDate||endDate?`?${new URLSearchParams({...(startDate&&{start_date:startDate}),...( endDate&&{end_date:endDate})})}`:"" }`}
            target="_blank" className="btn btn-outline btn-sm">📥 Export CSV</a>
          <button className="btn btn-primary btn-sm" onClick={openModal}>+ Tạo đơn hàng</button>
        </div>
      </div>

      {/* Bộ lọc ngày */}
      <div className="table-wrap" style={{ marginBottom:16 }}>
        <div className="table-header" style={{ flexWrap:"wrap", gap:10 }}>
          <div className="flex gap-2" style={{ alignItems:"center", flexWrap:"wrap" }}>
            <span className="fw-600" style={{ fontSize:13 }}>🗓️ Lọc theo ngày:</span>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={{ width:145 }} />
            <span className="text-muted">→</span>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={{ width:145 }} />
            <button className="btn btn-primary btn-sm" onClick={loadOrders}>Lọc</button>
            {(startDate||endDate) && (
              <button className="btn btn-outline btn-sm" onClick={() => { setStartDate(""); setEndDate(""); setTimeout(loadOrders,0); }}>✕ Bỏ lọc</button>
            )}
          </div>
          <div className="flex gap-2">
            {[["Hôm nay",0],["7 ngày",7],["30 ngày",30]].map(([label,days]) => (
              <button key={label} className="btn btn-outline btn-sm"
                onClick={() => { if(days===0){const t=toInput(new Date());setStartDate(t);setEndDate(t);}else setPreset(days); setTimeout(loadOrders,50); }}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Bảng đơn hàng */}
      <div className="table-wrap">
        <div className="table-header">
          <span className="fw-600">Tổng: {orders.length} đơn</span>
          <span className="fw-700 text-success">{fmt(orders.reduce((s,o)=>s+o.total_price,0))}</span>
        </div>
        <table>
          <thead><tr><th>Mã đơn</th><th>Tổng tiền</th><th>Trạng thái</th><th>Ngày tạo</th><th>Chi tiết</th></tr></thead>
          <tbody>
            {orders.length===0 && <tr><td colSpan={5}><div className="empty"><div className="empty-icon">🧾</div>Không có đơn hàng nào</div></td></tr>}
            {orders.map(o => (
              <tr key={o.id}>
                <td className="fw-600 text-muted">#{o.id}</td>
                <td className="fw-700 text-success">{fmt(o.total_price)}</td>
                <td><span className="badge badge-green">{o.status}</span></td>
                <td className="text-muted">{new Date(o.created_at).toLocaleString("vi-VN")}</td>
                <td><button className="btn btn-outline btn-sm" onClick={() => openDetail(o.id)}>🔍 Xem</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal tạo đơn */}
      {modal && (
        <div className="modal-overlay" onClick={e => e.target===e.currentTarget && setModal(false)}>
          <div className="modal" style={{ maxWidth:580 }}>
            <div className="modal-header">
              <h3>➕ Tạo đơn hàng mới</h3>
              <button className="btn-close" onClick={() => setModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom:12, padding:"8px 12px", background:"#f0f9ff",
                border:"1px solid #bae6fd", borderRadius:8, fontSize:12.5, color:"#0369a1" }}>
                💡 Gõ tên để tìm sản phẩm nhanh
              </div>
              {items.map((item, i) => {
                const sp = products.find(p => p.id === Number(item.product_id));
                return (
                  <div key={i} style={{ display:"flex", gap:8, alignItems:"flex-end", marginBottom:12 }}>
                    <div style={{ flex:2 }}>
                      {i===0 && <label style={{ display:"block", fontSize:13, fontWeight:600, marginBottom:5 }}>Tìm sản phẩm</label>}
                      <ProductSearch allProducts={products} selectedId={item.product_id} onSelect={v => setProductId(i,v)} />
                    </div>
                    <div style={{ flex:"0 0 90px" }}>
                      {i===0 && <label style={{ display:"block", fontSize:13, fontWeight:600, marginBottom:5 }}>Số lượng</label>}
                      <input type="number" min={1} max={sp?.quantity||9999} value={item.quantity}
                        onChange={e => setQty(i, Number(e.target.value))} style={{ width:"100%" }} />
                      {sp && Number(item.quantity) > sp.quantity && (
                        <div style={{ fontSize:11, color:"#dc2626", marginTop:2 }}>Tối đa {sp.quantity}</div>
                      )}
                    </div>
                    <button className="btn btn-danger btn-sm" onClick={() => removeItem(i)}>✕</button>
                  </div>
                );
              })}
              <button className="btn btn-outline btn-sm" onClick={addItem} style={{ marginBottom:16 }}>+ Thêm sản phẩm khác</button>
              {items.some(i => i.product_id) && (
                <div style={{ background:"#f8fafc", borderRadius:10, padding:"14px 16px", border:"1px solid #e2e8f0" }}>
                  <div className="fw-600 mb-4" style={{ fontSize:13 }}>📋 Tóm tắt:</div>
                  {items.filter(i => i.product_id).map((item,i) => {
                    const p = products.find(pr => pr.id===Number(item.product_id));
                    return p ? (
                      <div key={i} style={{ display:"flex", justifyContent:"space-between", fontSize:13, marginBottom:6, color:"#475569" }}>
                        <span>{p.name} × {item.quantity}</span>
                        <span className="fw-600">{fmt(p.price*Number(item.quantity))}</span>
                      </div>
                    ) : null;
                  })}
                  <div style={{ display:"flex", justifyContent:"space-between", borderTop:"1px solid #e2e8f0", paddingTop:10, marginTop:6, fontWeight:700, fontSize:15 }}>
                    <span>Tổng cộng</span>
                    <span className="text-success">{fmt(calcTotal())}</span>
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setModal(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={createOrder} disabled={saving}>
                {saving ? "Đang xử lý..." : "✅ Xác nhận tạo đơn"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal chi tiết */}
      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>🧾 Chi tiết đơn #{detail.id}</h3>
              <button className="btn-close" onClick={() => setDetail(null)}>×</button>
            </div>
            <div className="modal-body">
              <table style={{ width:"100%" }}>
                <thead><tr><th>Sản phẩm</th><th>SL</th><th>Đơn giá</th><th>Thành tiền</th></tr></thead>
                <tbody>
                  {detail.items.map((item,i) => (
                    <tr key={i}>
                      <td>{item.product_name}</td><td>{item.quantity}</td>
                      <td>{fmt(item.unit_price)}</td>
                      <td className="fw-600">{fmt(item.unit_price*item.quantity)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ display:"flex", justifyContent:"space-between", fontWeight:700, marginTop:14, paddingTop:12, borderTop:"1px solid #e2e8f0", fontSize:15 }}>
                <span>Tổng cộng</span><span className="text-success">{fmt(detail.total_price)}</span>
              </div>
              <div className="text-muted mt-3" style={{ fontSize:12 }}>Ngày: {new Date(detail.created_at).toLocaleString("vi-VN")}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
