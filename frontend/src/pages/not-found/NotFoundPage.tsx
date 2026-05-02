// FraxVerse 404 Not Found 页面
// 有品牌气质的错误页面，而非简陋的重定向到 login

import { Button } from "antd";
import { useNavigate } from "react-router-dom";
import { colors } from "../../theme/colors";

function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        background: colors.bg,
        padding: 24,
        textAlign: "center",
      }}
    >
      {/* 404 数字 — 用碎片风格 */}
      <div
        style={{
          fontSize: 96,
          fontWeight: 800,
          background: colors.gradients.primary,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          lineHeight: 1,
          marginBottom: 8,
          letterSpacing: -4,
        }}
      >
        404
      </div>

      {/* 装饰线 */}
      <div
        style={{
          width: 60,
          height: 3,
          borderRadius: 2,
          background: colors.gradients.primary,
          marginBottom: 20,
        }}
      />

      <div
        style={{
          fontSize: 18,
          fontWeight: 500,
          color: colors.text,
          marginBottom: 8,
        }}
      >
        这片星域还没有被探索过
      </div>

      <div
        style={{
          fontSize: 14,
          color: colors.dimmed,
          maxWidth: 340,
          lineHeight: 1.7,
          marginBottom: 28,
        }}
      >
        你访问的页面不存在，或者曾经存在但已消散于宇宙尘埃中。
        <br />
        回到安全的地方重新导航吧。
      </div>

      <div style={{ display: "flex", gap: 12 }}>
        <Button type="primary" size="large" onClick={() => navigate("/dashboard")}>
          返回主面板
        </Button>
        <Button size="large" onClick={() => navigate(-1)}>
          回退一步
        </Button>
      </div>
    </div>
  );
}

export default NotFoundPage;
