import { useEffect, useState } from "react";
import API from "../services/api";

const ICON = { out_of_stock: "🚨", low_stock: "⚠️", slow_moving: "📉" };
const TITLE = { danger: "🚨 Khẩn cấp — Cần xử lý ngay", warning: "⚠️ Cảnh báo — Cần chú ý", info: "ℹ️ Thông tin — Để theo dõi" };

export default function Notifications() {
  const [data, setData] = useState(null);

  useEffect(() => { API.get("/notifications/").then(r => setData(r.data)); }, []);

  if (!data) return <div className="loading">⏳ Đang tải...</div>;

  const { notifications = [], count } = data;

  return (
    <div>
      <div className="page-header flex-between">
        <div><h2>🔔 Thông báo & Cảnh báo</h2><p>Cảnh báo thông minh từ hệ thống</p></div>
        <button className="btn btn-outline btn-sm" onClick={() => API.get("/notifications/").then(r => setData(r.data))}>
          🔄 Làm mới
        </button>
      </div>

      {count === 0 ? (
        <div className="table-wrap" style={{ padding: "48px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>✅</div>
          <div className="fw-600" style={{ fontSize: 16 }}>Tất cả ổn định!</div>
          <div className="text-muted mt-3">Không có cảnh báo nào cần xử lý</div>
        </div>
      ) : (
        ["danger", "warning", "info"].map(level => {
          const group = notifications.filter(n => n.level === level);
          if (!group.length) return null;
          return (
            <div key={level} style={{ marginBottom: 24 }}>
              <h3 style={{ marginBottom: 12, fontSize: 15, fontWeight: 700 }}>{TITLE[level]}</h3>
              <div className="table-wrap" style={{ padding: "12px 14px" }}>
                {group.map((n, i) => (
                  <div key={i} className={`notif-item ${level}`}>
                    <span style={{ fontSize: 20 }}>{ICON[n.type]}</span>
                    <div style={{ flex: 1 }}>
                      <div>{n.message}</div>
                      <div className="text-muted" style={{ fontSize: 12, marginTop: 2 }}>
                        {n.type === "out_of_stock" && "→ Cần nhập hàng ngay"}
                        {n.type === "low_stock" && "→ Xem xét nhập thêm hàng"}
                        {n.type === "slow_moving" && "→ Xem xét điều chỉnh giá hoặc khuyến mãi"}
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
