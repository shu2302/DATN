import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useEffect, useState } from "react";
import API from "../services/api";

const NAV = [
  { to:"/",             label:"Dashboard",      icon:"📊", section:"Tổng quan" },
  { to:"/products",     label:"Sản phẩm",       icon:"🛍️", section:"Quản lý" },
  { to:"/categories",   label:"Danh mục",       icon:"📂" },
  { to:"/combos",       label:"Combo giảm giá", icon:"🎁" },
  { to:"/orders",       label:"Đơn hàng",       icon:"🧾" },
  { to:"/stock-import", label:"Nhập hàng",      icon:"📥", adminOnly:true },
  { to:"/notifications",label:"Thông báo & AI", icon:"🔔", section:"AI Assistant" },
  { to:"/chatbot",      label:"AI Chatbot",     icon:"🤖" },
  { to:"/users",        label:"Người dùng",     icon:"👥", section:"Hệ thống", adminOnly:true },
  { to:"/profile",      label:"Hồ sơ",          icon:"👤" },
];

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [notifCount, setNotifCount] = useState(0);

  useEffect(() => {
    API.get("/notifications/").then(r => setNotifCount(r.data.count)).catch(()=>{});
  }, []);

  let lastSection = null;
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>🛒 SuperMarket AI</h1>
          <span>Hệ thống quản lý thông minh</span>
        </div>
        <nav className="sidebar-nav">
          {NAV.map(item => {
            if (item.adminOnly && !isAdmin) return null;
            const showSection = item.section && item.section !== lastSection;
            if (item.section) lastSection = item.section;
            return (
              <div key={item.to}>
                {showSection && <div className="nav-section">{item.section}</div>}
                <NavLink to={item.to} end={item.to==="/"}
                  className={({ isActive }) => `nav-item${isActive?" active":""}`}>
                  <span className="nav-icon">{item.icon}</span>
                  <span>{item.label}</span>
                  {item.to==="/notifications" && notifCount > 0 && (
                    <span className="badge badge-red"
                      style={{ marginLeft:"auto", fontSize:10, padding:"1px 6px" }}>
                      {notifCount}
                    </span>
                  )}
                </NavLink>
              </div>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="user-info">
            <div className="avatar">{user?.username?.[0]?.toUpperCase()}</div>
            <div>
              <div className="user-name">{user?.full_name || user?.username}</div>
              <div className="user-role">{user?.role==="admin" ? "🔑 Admin":"👤 Staff"}</div>
            </div>
          </div>
          <button className="btn-logout" onClick={() => { logout(); navigate("/login"); }}>
            🚪 Đăng xuất
          </button>
        </div>
      </aside>
      <main className="main"><Outlet /></main>
    </div>
  );
}
