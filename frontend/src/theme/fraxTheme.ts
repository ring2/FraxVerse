import type { ThemeConfig } from "antd";

// Ant Design 5.x theme tokens for FraxVerse Cosmic theme
export const fraxTheme: ThemeConfig = {
  token: {
    colorPrimary: "#6b5ce7",
    colorBgContainer: "#12122a",
    colorBgElevated: "#1a1a3a",
    colorBorder: "#2a2a4a",
    colorText: "#e0e0f0",
    colorTextSecondary: "#8887a8",
    colorTextTertiary: "#555577",
    colorSuccess: "#2ed573",
    colorWarning: "#ffa502",
    colorError: "#ff4757",
    colorInfo: "#4a9eff",
    borderRadius: 8,
    fontSize: 14,
    fontFamily:
      '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
  },
  components: {
    Button: {
      borderRadius: 8,
      controlHeight: 38,
    },
    Card: {
      paddingLG: 20,
    },
    Table: {
      headerBg: "transparent",
      rowHoverBg: "rgba(107, 92, 231, 0.08)",
    },
    Menu: {
      itemBg: "transparent",
      itemColor: "#8887a8",
    },
    Input: {
      colorBgContainer: "#12122a",
      colorBorder: "#2a2a4a",
    },
    Modal: {
      contentBg: "#1a1a3a",
      headerBg: "#1a1a3a",
    },
    Drawer: {
      colorBgElevated: "#1a1a3a",
    },
    Select: {
      colorBgContainer: "#12122a",
      colorBorder: "#2a2a4a",
    },
  },
};
