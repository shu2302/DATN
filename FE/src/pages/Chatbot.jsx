import { useState, useRef, useEffect, useCallback } from "react";
import API from "../services/api";

const STORAGE_KEY = "chatbot_history";

const INTENT_LABELS = {
  DB_REVENUE:"📊 Doanh thu", DB_ORDERS:"🧾 Đơn hàng", DB_STOCK:"📦 Tồn kho",
  DB_TOP_PRODUCTS:"🏆 Bán chạy", DB_SLOW_PRODUCTS:"📉 Bán chậm",
  DB_IMPORT:"📥 Nhập hàng", DB_PRODUCT_INFO:"🛍️ Sản phẩm",
  DB_CATEGORY:"🗂️ Danh mục", GENERAL:"💬 Chung",
};

const QUICK = [
  "Doanh thu hôm nay?", "Doanh thu tháng này?",
  "Top sản phẩm bán chạy?", "Sản phẩm nào sắp hết hàng?",
  "Bao nhiêu đơn hàng hôm qua?", "Sản phẩm nào bán chậm nhất?",
  "Lịch sử nhập hàng tháng này?", "Doanh thu theo danh mục?",
];

// ── Bubble tin nhắn ──────────────────────────────────────
function Bubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`chat-msg ${msg.role}`}>
      <div className={`chat-avatar ${msg.role}`}>{isUser ? "U" : "🤖"}</div>
      <div style={{ maxWidth: "76%", display: "flex", flexDirection: "column",
        alignItems: isUser ? "flex-end" : "flex-start", gap: 4 }}>
        <div className="chat-bubble" style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>
        {msg.meta && (
          <div style={{ display: "flex", gap: 5, flexWrap: "wrap", paddingLeft: 2 }}>
            <span style={{ fontSize: 11, color: "#94a3b8", background: "#f8fafc",
              padding: "1px 7px", borderRadius: 8, border: "1px solid #e2e8f0" }}>
              {INTENT_LABELS[msg.meta.intent] || msg.meta.intent}
            </span>
            {msg.meta.sources?.map(s => (
              <span key={s} style={{ fontSize: 11, padding: "1px 7px", borderRadius: 8, fontWeight: 700,
                background: s === "database" ? "#dcfce7" : "#f1f5f9",
                color: s === "database" ? "#15803d" : "#475569" }}>
                {s === "database" ? "🗄️ DB" : "⚙️ Rule"}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Trang chính ──────────────────────────────────────────
export default function Chatbot() {
  // Lịch sử UI (có role: "user" | "bot", text, meta)
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : [defaultWelcome()];
    } catch { return [defaultWelcome()]; }
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  // Scroll xuống cuối mỗi khi messages thay đổi
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Lưu lịch sử vào localStorage mỗi khi đổi
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages)); } catch {}
  }, [messages]);

  // Xây history gửi lên API (chỉ role user/assistant, không gửi meta)
  const buildApiHistory = useCallback((msgs) =>
    msgs
      .filter(m => m.role === "user" || m.role === "bot")
      .slice(-12)  // tối đa 12 lượt gần nhất
      .map(m => ({ role: m.role === "bot" ? "assistant" : "user", content: m.text })),
  []);

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput("");

    const userMsg = { role: "user", text: msg, meta: null };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const res = await API.post("/chatbot/", {
        message: msg,
        history: buildApiHistory(nextMessages),
      });
      const { reply, intent, sources } = res.data;
      setMessages(prev => [...prev, { role: "bot", text: reply, meta: { intent, sources } }]);
    } catch (err) {
      const detail = err.response?.data?.detail || "Lỗi kết nối server. Thử lại sau.";
      setMessages(prev => [...prev, { role: "bot", text: `⚠️ ${detail}`, meta: null }]);
    } finally { setLoading(false); }
  };

  const clearHistory = () => {
    if (!confirm("Xoá toàn bộ lịch sử trò chuyện?")) return;
    const fresh = [defaultWelcome()];
    setMessages(fresh);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h2> AI Chatbot</h2>
          <p>Trợ lý thông minh — có nhớ ngữ cảnh hội thoại</p>
        </div>
        <button className="btn btn-outline btn-sm" onClick={clearHistory}
          style={{ color: "#dc2626", borderColor: "#fecaca" }}>
          🗑️ Xoá lịch sử
        </button>
      </div>

      <div className="chat-wrap">
        {/* Tin nhắn */}
        <div className="chat-messages">
          {messages.map((m, i) => <Bubble key={i} msg={m} />)}

          {loading && (
            <div className="chat-msg bot">
              <div className="chat-avatar bot">🤖</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div className="chat-bubble text-muted" style={{ fontStyle: "italic" }}>
                  Đang phân tích...
                </div>
                <div style={{ display: "flex", gap: 5 }}>
                  {[" Intent", " DB", " LLM"].map((s, i) => (
                    <span key={i} style={{ fontSize: 11, padding: "2px 8px", borderRadius: 8,
                      background: "#f1f5f9", color: "#94a3b8", fontWeight: 600,
                      animation: `fade ${0.5 + i * 0.25}s ease-in-out infinite alternate` }}>{s}</span>
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Câu hỏi nhanh */}
        <div className="quick-pills">
          {QUICK.map(q => (
            <button key={q} className="quick-pill" onClick={() => send(q)} disabled={loading}>{q}</button>
          ))}
        </div>

        {/* Input */}
        <div className="chat-input-row">
          <input
            placeholder="Nhập câu hỏi... (Enter gửi)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && !loading && send()}
            disabled={loading}
          />
          <button className="btn btn-primary" onClick={() => send()}
            disabled={loading || !input.trim()}>
            {loading ? "..." : "Gửi ➤"}
          </button>
        </div>
      </div>
      <style>{`@keyframes fade{from{opacity:.3}to{opacity:1}}`}</style>
    </div>
  );
}

function defaultWelcome() {
  return {
    role: "bot",
    text: "Xin chào!  Tôi là AI trợ lý siêu thị.\n\nTôi nhớ ngữ cảnh hội thoại — bạn có thể hỏi tiếp theo câu trước!\n\nVí dụ:\n• \"Doanh thu tháng này?\"\n• \"Còn sản phẩm nào sắp hết?\"\n• \"Top bán chạy tuần qua?\"",
    meta: null,
  };
}
