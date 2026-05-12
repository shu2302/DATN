import { useEffect, useState } from "react";
import API from "../services/api";
import { useAuth } from "../context/AuthContext";

const LEVEL_CONFIG = {
  danger:  { bg:"#fef2f2", border:"#fecaca", label:"Khẩn cấp" },
  warning: { bg:"#fffbeb", border:"#fde68a",   label:"Cảnh báo" },
  info:    { bg:"#f0f9ff", border:"#bae6fd",   label:"Thông tin" },
};

const TYPE_HINT = {
  out_of_stock:  "→ Cần nhập hàng ngay",
  low_stock:     "→ Xem xét nhập thêm",
  predicted_out: "→ AI dự đoán sắp hết dựa trên tốc độ bán",
  slow_moving:   "→ Xem xét khuyến mãi hoặc điều chỉnh giá",
};

// ── Tab 1: Notifications ───────────────────────────────────
function NotifTab() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    API.get("/notifications/").then(r => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">⏳ Đang tải...</div>;
  const { notifications=[], count } = data || {};

  return (
    <div>
      {count === 0 ? (
        <div className="table-wrap" style={{ padding:"48px 24px", textAlign:"center" }}>
          <div style={{ fontSize:48, marginBottom:12 }}>✅</div>
          <div className="fw-600" style={{ fontSize:16 }}>Tất cả ổn định!</div>
          <div className="text-muted mt-3">Không có cảnh báo nào cần xử lý</div>
        </div>
      ) : (
        ["danger","warning","info"].map(level => {
          const group = notifications.filter(n => n.level === level);
          if (!group.length) return null;
          const cfg = LEVEL_CONFIG[level];
          return (
            <div key={level} style={{ marginBottom:20 }}>
              <h3 style={{ marginBottom:10, fontSize:15, fontWeight:700 }}>
                {cfg.icon} {cfg.label} ({group.length})
              </h3>
              <div className="table-wrap" style={{ padding:"10px 14px" }}>
                {group.map((n, i) => (
                  <div key={i} style={{
                    display:"flex", gap:12, padding:"12px 14px", marginBottom:6,
                    borderRadius:10, background:cfg.bg, border:`1px solid ${cfg.border}`
                  }}>
                    <span style={{ fontSize:18 }}>{cfg.icon}</span>
                    <div style={{ flex:1 }}>
                      <div style={{ fontWeight:600, fontSize:13.5 }}>{n.message}</div>
                      <div style={{ display:"flex", gap:16, marginTop:4, fontSize:12, color:"#64748b" }}>
                        {n.sell_rate > 0 && <span>📈 Tốc độ bán: <b>{n.sell_rate}</b> SP/ngày</span>}
                        {n.days_left != null && <span>⏳ Dự kiến còn: <b>{n.days_left}</b> ngày</span>}
                        <span>{TYPE_HINT[n.type]}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

// ── Tab 2: AI Auto-Import (Admin only) ────────────────────
function AIImportTab() {
  const [suggestions, setSuggestions]   = useState(null);
  const [loading, setLoading]           = useState(true);
  const [editedItems, setEditedItems]   = useState({});
  const [confirming, setConfirming]     = useState(false);
  const [result, setResult]             = useState(null);

  useEffect(() => {
    API.get("/notifications/ai-import-suggestions")
      .then(r => {
        setSuggestions(r.data);
        // Init editable fields
        const init = {};
        r.data.suggestions.forEach(s => {
          init[s.product_id] = {
            qty:   s.suggested_qty,
            price: s.suggested_price,
            checked: true,
          };
        });
        setEditedItems(init);
      })
      .finally(() => setLoading(false));
  }, []);

  const fmt = n => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + "đ";

  const handleConfirm = async () => {
    const items = suggestions.suggestions
      .filter(s => editedItems[s.product_id]?.checked)
      .map(s => ({
        product_id:   s.product_id,
        quantity:     Number(editedItems[s.product_id]?.qty  || s.suggested_qty),
        import_price: Number(editedItems[s.product_id]?.price || s.suggested_price),
        supplier:     "AI Auto-Import",
        note:         `Tự động nhập theo dự đoán AI (${s.reason})`,
      }));

    if (!items.length) { alert("Chọn ít nhất 1 sản phẩm để nhập"); return; }
    if (!confirm(`Xác nhận nhập hàng ${items.length} sản phẩm?`)) return;

    setConfirming(true);
    try {
      const res = await API.post("/notifications/ai-import-confirm", { items });
      setResult(res.data);
      // Reload suggestions
      API.get("/notifications/ai-import-suggestions").then(r => {
        setSuggestions(r.data);
        const init = {};
        r.data.suggestions.forEach(s => {
          init[s.product_id] = { qty: s.suggested_qty, price: s.suggested_price, checked: true };
        });
        setEditedItems(init);
      });
    } catch (err) {
      alert(err.response?.data?.detail || "Lỗi nhập hàng");
    } finally { setConfirming(false); }
  };

  const update = (pid, field, val) =>
    setEditedItems(prev => ({ ...prev, [pid]: { ...prev[pid], [field]: val } }));

  const checkedItems    = suggestions?.suggestions.filter(s => editedItems[s.product_id]?.checked) || [];
  const totalCostChecked = checkedItems.reduce((sum, s) =>
    sum + (editedItems[s.product_id]?.qty || s.suggested_qty) * (editedItems[s.product_id]?.price || s.suggested_price), 0);

  if (loading) return <div className="loading">🤖 AI đang phân tích dữ liệu bán hàng...</div>;

  return (
    <div>
      {/* Result banner */}
      {result && (
        <div style={{ background:"#dcfce7", border:"1px solid #bbf7d0", borderRadius:10,
          padding:"14px 18px", marginBottom:18 }}>
          <div className="fw-700" style={{ color:"#15803d", fontSize:15 }}>
            ✅ {result.message}
          </div>
          <div style={{ color:"#166534", fontSize:13, marginTop:4 }}>
            Tổng chi phí: {fmt(result.total_cost)} — Đã cập nhật vào lịch sử nhập hàng
          </div>
        </div>
      )}

      {/* Header info */}
      <div style={{ background:"#eff6ff", border:"1px solid #bfdbfe", borderRadius:10,
        padding:"12px 16px", marginBottom:18, fontSize:13, color:"#1e40af" }}>
        <div className="fw-700" style={{ marginBottom:4 }}>🤖 AI Agent — Gợi ý nhập hàng tự động</div>
        <div>Dự đoán dựa trên tốc độ bán 7 ngày qua. Số lượng = đủ bán cho 14 ngày tới.
          Giá nhập = giá nhập lần gần nhất (hoặc 65% giá bán nếu chưa có lịch sử).</div>
      </div>

      {!suggestions?.suggestions.length ? (
        <div className="table-wrap" style={{ padding:"48px", textAlign:"center" }}>
          <div style={{ fontSize:44, marginBottom:12 }}>🎉</div>
          <div className="fw-600" style={{ fontSize:16 }}>Tất cả sản phẩm đang đủ hàng!</div>
          <div className="text-muted mt-3">AI không phát hiện sản phẩm nào cần nhập lúc này</div>
        </div>
      ) : (
        <>
          <div className="table-wrap" style={{ marginBottom:16 }}>
            <div className="table-header flex-between">
              <span className="fw-600">{suggestions.suggestions.length} sản phẩm cần nhập</span>
              <label style={{ display:"flex", alignItems:"center", gap:8, fontSize:13, cursor:"pointer" }}>
                <input type="checkbox"
                  checked={suggestions.suggestions.every(s => editedItems[s.product_id]?.checked)}
                  onChange={e => {
                    const all = {};
                    suggestions.suggestions.forEach(s => {
                      all[s.product_id] = { ...editedItems[s.product_id], checked: e.target.checked };
                    });
                    setEditedItems(all);
                  }} />
                Chọn tất cả
              </label>
            </div>
            <table>
              <thead>
                <tr>
                  <th style={{ width:40 }}></th>
                  <th>Sản phẩm</th>
                  <th>Lý do</th>
                  <th>Tốc độ bán</th>
                  <th>Tồn hiện tại</th>
                  <th>SL nhập (sửa được)</th>
                  <th>Giá nhập (sửa được)</th>
                  <th>Thành tiền</th>
                </tr>
              </thead>
              <tbody>
                {suggestions.suggestions.map(s => {
                  const e    = editedItems[s.product_id] || {};
                  const qty  = Number(e.qty   || s.suggested_qty);
                  const price= Number(e.price || s.suggested_price);
                  const cost = qty * price;
                  return (
                    <tr key={s.product_id} style={{ opacity: e.checked === false ? 0.4 : 1 }}>
                      <td style={{ textAlign:"center" }}>
                        <input type="checkbox" checked={e.checked !== false}
                          onChange={ev => update(s.product_id, "checked", ev.target.checked)} />
                      </td>
                      <td className="fw-600">{s.product_name}</td>
                      <td>
                        <span className="badge badge-orange" style={{ fontSize:11 }}>{s.reason}</span>
                        {s.days_left != null && (
                          <div style={{ fontSize:11, color:"#64748b", marginTop:2 }}>
                            Còn ~{s.days_left} ngày
                          </div>
                        )}
                      </td>
                      <td className="text-muted">{s.sell_rate} SP/ngày</td>
                      <td>
                        <span className={s.current_qty === 0 ? "text-danger fw-700" : "text-warning fw-700"}>
                          {s.current_qty}
                        </span>
                      </td>
                      <td>
                        <input type="number" min={1} value={qty}
                          onChange={ev => update(s.product_id, "qty", ev.target.value)}
                          style={{ width:80, padding:"4px 8px", border:"1.5px solid #e2e8f0", borderRadius:6, fontSize:13 }} />
                      </td>
                      <td>
                        <input type="number" min={0} value={price}
                          onChange={ev => update(s.product_id, "price", ev.target.value)}
                          style={{ width:100, padding:"4px 8px", border:"1.5px solid #e2e8f0", borderRadius:6, fontSize:13 }} />
                      </td>
                      <td className="fw-600 text-warning">{fmt(cost)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Summary + Confirm */}
          <div style={{ background:"#f8fafc", borderRadius:12, padding:"16px 20px",
            border:"1px solid #e2e8f0", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <div>
              <div className="fw-700" style={{ fontSize:15 }}>
                Tổng chi phí dự kiến: <span className="text-warning">{fmt(totalCostChecked)}</span>
              </div>
              <div className="text-muted" style={{ fontSize:12, marginTop:2 }}>
                {checkedItems.length} sản phẩm được chọn — Sau khi xác nhận sẽ tự cập nhật tồn kho và lịch sử nhập
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleConfirm} disabled={confirming || !checkedItems.length}
              style={{ padding:"10px 24px", fontSize:14 }}>
              {confirming ? "Đang xử lý..." : "✅ Xác nhận nhập hàng"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Tab 3: AI Weekly Report (Admin only) ─────────────────
function AIReportTab() {
  const [report, setReport]   = useState(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true); setReport(null);
    try {
      const res = await API.get("/notifications/ai-report-summary");
      setReport(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Lỗi tạo báo cáo");
    } finally { setLoading(false); }
  };

  const fmt = n => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + "đ";
  const data = report?.data;

  return (
    <div>
      <div style={{ background:"#f0fdf4", border:"1px solid #bbf7d0", borderRadius:10,
        padding:"14px 18px", marginBottom:20, fontSize:13, color:"#166534" }}>
        <div className="fw-700" style={{ marginBottom:4 }}>📊 AI Tóm tắt báo cáo kinh doanh tuần này</div>
        <div>AI tự động tổng hợp doanh thu, top sản phẩm, cảnh báo và đề xuất cho tuần tới.</div>
      </div>

      {!report && (
        <div style={{ textAlign:"center", padding:"40px 0" }}>
          <div style={{ fontSize:48, marginBottom:16 }}>📈</div>
          <button className="btn btn-primary" onClick={generate} disabled={loading}
            style={{ padding:"12px 32px", fontSize:15 }}>
            {loading ? "🤖 AI đang phân tích..." : "🚀 Tạo báo cáo AI"}
          </button>
          {loading && (
            <div className="text-muted mt-4" style={{ fontSize:13 }}>
              Đang thu thập dữ liệu và tổng hợp báo cáo...
            </div>
          )}
        </div>
      )}

      {report && (
        <>
          {/* Quick stats */}
          {data && (
            <div className="stat-grid" style={{ marginBottom:20 }}>
              <div className="stat-card blue">
                <div className="stat-label">Doanh thu tuần</div>
                <div className="stat-value" style={{ fontSize:20 }}>{fmt(data.revenue_week)}</div>
                <div className="stat-sub">
                  <span style={{ color: data.revenue_change >= 0 ? "#16a34a" : "#dc2626", fontWeight:700 }}>
                    {data.revenue_change >= 0 ? "▲" : "▼"} {Math.abs(data.revenue_change)}%
                  </span> so tuần trước
                </div>
              </div>
              <div className="stat-card green">
                <div className="stat-label">Số đơn hàng</div>
                <div className="stat-value">{data.orders_week}</div>
              </div>
              <div className="stat-card orange">
                <div className="stat-label">Cần nhập hàng</div>
                <div className="stat-value">{data.need_import?.length || 0}</div>
                <div className="stat-sub">sản phẩm</div>
              </div>
            </div>
          )}

          {/* AI Summary text */}
          <div className="table-wrap" style={{ padding:"20px 22px", marginBottom:16 }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
              <div className="fw-700" style={{ fontSize:14 }}>
                🤖 Tóm tắt AI
                <span className="badge badge-gray" style={{ marginLeft:8, fontSize:11 }}>
                  {report.source === "llm" ? "LLaMA" : "Rule-based"}
                </span>
              </div>
              <button className="btn btn-outline btn-sm" onClick={generate} disabled={loading}>
                🔄 Tạo lại
              </button>
            </div>
            <div style={{ whiteSpace:"pre-wrap", lineHeight:1.8, fontSize:14,
              background:"#fafafa", borderRadius:8, padding:"16px 18px", border:"1px solid #f1f5f9" }}>
              {report.summary}
            </div>
          </div>

          {/* Top products detail */}
          {data?.top_products?.length > 0 && (
            <div className="table-wrap" style={{ padding:"14px 18px" }}>
              <div className="fw-700 mb-4" style={{ fontSize:13 }}>🏆 Top sản phẩm tuần này:</div>
              {data.top_products.map((p, i) => (
                <div key={i} style={{ display:"flex", justifyContent:"space-between",
                  padding:"8px 0", borderBottom:"1px solid #f1f5f9", fontSize:13 }}>
                  <span><b>{i+1}.</b> {p.name}</span>
                  <span className="badge badge-blue">{p.sold} cái</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Main Notifications Page ────────────────────────────────
export default function Notifications() {
  const { isAdmin } = useAuth();
  const [tab, setTab]   = useState("notif");
  const [count, setCount] = useState(0);

  useEffect(() => {
    API.get("/notifications/").then(r => setCount(r.data.count)).catch(() => {});
  }, []);

  const tabs = [
    { key:"notif",  label:`🔔 Thông báo${count > 0 ? ` (${count})` : ""}`, adminOnly: false },
    { key:"import", label:"🤖 Nhập hàng AI", adminOnly: true },
    { key:"report", label:"📊 Báo cáo AI",   adminOnly: true },
  ];

  return (
    <div>
      <div className="page-header">
        <h2>🔔 Thông báo & AI Assistant</h2>
        <p>Cảnh báo tồn kho thông minh, tự động nhập hàng và báo cáo AI</p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2 mb-4">
        {tabs.map(t => (
          (!t.adminOnly || isAdmin) && (
            <button key={t.key}
              className={`btn btn-sm ${tab === t.key ? "btn-primary" : "btn-outline"}`}
              onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          )
        ))}
      </div>

      {tab === "notif"  && <NotifTab />}
      {tab === "import" && isAdmin && <AIImportTab />}
      {tab === "report" && isAdmin && <AIReportTab />}
    </div>
  );
}
