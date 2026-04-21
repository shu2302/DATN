import { useEffect, useState } from "react";
import API from "../api";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
} from "chart.js";

ChartJS.register(LineElement, CategoryScale, LinearScale, PointElement);

export default function RevenueChart() {
  const [data, setData] = useState({});

  useEffect(() => {
    API.get("/orders/revenue").then((res) => {
      setData(res.data);
    });
  }, []);

  const chartData = {
    labels: Object.keys(data),
    datasets: [
      {
        label: "Revenue",
        data: Object.values(data),
      },
    ],
  };

  return (
    <div>
      <h2>Revenue</h2>
      <Line data={chartData} />
    </div>
  );
}