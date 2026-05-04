import { useEffect, useState } from "react";
import API from "../services/api";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend } from "chart.js";
import { Bar, Line, Doughnut } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend);

const opts = { responsive: true, plugins: { legend: { display: false } },
  scales: { x: { grid: { display: false } }, y: { grid: { color: "#f1f5f9" } } } };
const fmt = n => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + "đ";

export default function Dashboard() {
  const [dash, setDash] = useState(null);
  const [top, setTop] = useState([]);
  const [revCat, setRevCat] = useState([]);

  useEffect(() => {
    Promise.all([
      API.get("/orders/dashboard"),
      API.get("/orders/top-products"),
      API.get("/orders/revenue-by-category"),
    ]).then(([r1, r2, r3]) => { setDash(r1.data); setTop(r2.data); setRevCat(r3.data); });
  }, []);

  if (!dash) return <div className="loading">⏳ Đang tải dữ liệu...</div>;

  const days = Object.keys(dash.revenue || {}).sort().slice(-14);
  const COLORS = ["#2563eb","#16a34a","#d97706","#dc2626","#0891b2","#7c3aed","#db2777"];

  const revenueData = { labels: days, datasets: [{ data: days.map(d => dash.revenue[d] || 0),
    borderColor: "#2563eb", backgroundColor: "rgba(37,99,235,.1)", fill: true, tension: 0.4, pointRadius: 3 }] };
  const ordersData = { labels: days, datasets: [{ data: days.map(d => dash.orders_per_day[d] || 0),
    backgroundColor: "#16a34a", borderRadius: 6 }] };
  const topData = { labels: top.map(p => p.name),
    datasets: [{ data: top.map(p => p.total_sold), backgroundColor: COLORS }] };
  const catData = { labels: revCat.map(r => r.category),
    datasets: [{ data: revCat.map(r => r.revenue), backgroundColor: "#2563eb", borderRadius: 6 }] };

  return (
    <div>
      <div className="page-header">
        <h2>📊 Dashboard</h2>
        <p>Tổng quan hoạt động kinh doanh siêu thị</p>
      </div>
      <div className="stat-grid">
        <div className="stat-card blue">
          <div className="stat-label">Tổng doanh thu</div>
          <div className="stat-value">{fmt(dash.total_revenue || 0)}</div>
          <div className="stat-sub">Tất cả đơn hàng</div>
        </div>
        <div className="stat-card green">
          <div className="stat-label">Tổng đơn hàng</div>
          <div className="stat-value">{dash.total_orders || 0}</div>
          <div className="stat-sub">Đã hoàn thành</div>
        </div>
        <div className="stat-card orange">
          <div className="stat-label">Bán chạy nhất</div>
          <div className="stat-value" style={{ fontSize: 18, marginTop: 6 }}>{top[0]?.name?.slice(0,14) || "—"}</div>
          <div className="stat-sub">{top[0] ? `${top[0].total_sold} sản phẩm đã bán` : "Chưa có dữ liệu"}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">Danh mục</div>
          <div className="stat-value">{revCat.length}</div>
          <div className="stat-sub">Nhóm sản phẩm</div>
        </div>
      </div>
      <div className="charts-grid">
        <div className="chart-card">
          <div className="chart-title">📈 Doanh thu 14 ngày gần nhất</div>
          <Line data={revenueData} options={opts} />
        </div>
        <div className="chart-card">
          <div className="chart-title">📦 Số đơn hàng theo ngày</div>
          <Bar data={ordersData} options={opts} />
        </div>
        <div className="chart-card">
          <div className="chart-title">🏆 Top sản phẩm bán chạy</div>
          {top.length ? <Doughnut data={topData} options={{ ...opts, plugins: { legend: { position: "right", labels: { font: { size: 11 } } } } }} /> : <div className="empty">Chưa có dữ liệu</div>}
        </div>
        <div className="chart-card">
          <div className="chart-title">🗂️ Doanh thu theo danh mục</div>
          {revCat.length ? <Bar data={catData} options={opts} /> : <div className="empty">Chưa có dữ liệu</div>}
        </div>
      </div>
    </div>
  );
}
