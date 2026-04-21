import { useEffect, useState } from "react";
import API from "../api";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
} from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale);

export default function TopProductsChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    API.get("/orders/top-products").then((res) => {
      setData(res.data);
    });
  }, []);

  const chartData = {
    labels: data.map((p) => p.name),
    datasets: [
      {
        label: "Sold",
        data: data.map((p) => p.total_sold),
      },
    ],
  };

  return (
    <div>
      <h2>Top Products</h2>
      <Bar data={chartData} />
    </div>
  );
}