import { useEffect, useState } from "react";
import API from "../services/api";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend
);

export default function Dashboard() {
  const [revenue, setRevenue] = useState({});
  const [ordersPerDay, setOrdersPerDay] = useState({});
  const [topProducts, setTopProducts] = useState([]);
  const [totalRevenue, setTotalRevenue] = useState(0);
  const [totalOrders, setTotalOrders] = useState(0);
  const [totalProducts, setTotalProducts] = useState(0);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    const res1 = await API.get("/orders/dashboard");
    const res2 = await API.get("/orders/top-products");
    const res3 = await API.get("/products");

    setRevenue(res1.data.revenue);
    setOrdersPerDay(res1.data.orders_per_day);
    setTopProducts(res2.data);

    // tính tổng
    const totalRev = Object.values(res1.data.revenue).reduce(
      (a, b) => a + b,
      0
    );
    const totalOrd = Object.values(res1.data.orders_per_day).reduce(
      (a, b) => a + b,
      0
    );

    setTotalRevenue(totalRev);
    setTotalOrders(totalOrd);
    setTotalProducts(res3.data.length);
  };

  // ===== Revenue chart =====
  const revenueData = {
    labels: Object.keys(revenue),
    datasets: [
      {
        label: "Revenue",
        data: Object.values(revenue),
      },
    ],
  };

  // ===== Orders per day =====
  const ordersData = {
    labels: Object.keys(ordersPerDay),
    datasets: [
      {
        label: "Orders",
        data: Object.values(ordersPerDay),
      },
    ],
  };

  // ===== Top products =====
  const topData = {
    labels: topProducts.map((p) => p.name),
    datasets: [
      {
        label: "Top Products",
        data: topProducts.map((p) => p.total_sold),
      },
    ],
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>Dashboard</h2>

      {/* ===== CARDS ===== */}
      <div style={{ display: "flex", gap: 20, marginBottom: 20 }}>
        <div style={cardStyle}>
          <h3>Total Revenue</h3>
          <p>{totalRevenue}</p>
        </div>

        <div style={cardStyle}>
          <h3>Total Orders</h3>
          <p>{totalOrders}</p>
        </div>

        <div style={cardStyle}>
          <h3>Total Products</h3>
          <p>{totalProducts}</p>
        </div>
      </div>

      {/* ===== CHARTS ===== */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          <h3>Revenue</h3>
          <Line data={revenueData} />
        </div>

        <div>
          <h3>Orders per Day</h3>
          <Line data={ordersData} />
        </div>

        <div>
          <h3>Top Products</h3>
          <Bar data={topData} />
        </div>
      </div>
    </div>
  );
}

const cardStyle = {
  border: "1px solid #ccc",
  padding: 20,
  borderRadius: 10,
  width: 200,
};