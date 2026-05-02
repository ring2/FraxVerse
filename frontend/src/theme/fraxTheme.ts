import type { ThemeConfig } from "antd";

// FraxVerse Ant Design theme tokens — light mode
export const fraxLightTheme: ThemeConfig = {
  token: {
    colorPrimary: "#7F77DD",
    colorBgContainer: "#FFFFFF",
    colorBgElevated: "#FFFFFF",
    colorBorder: "#E5E3DC",
    colorText: "#1A1A1A",
    colorTextSecondary: "#6B6B6B",
    colorTextTertiary: "#999999",
    colorSuccess: "#4DB899",
    colorWarning: "#E8A840",
    colorError: "#E8735A",
    colorInfo: "#7F77DD",
    borderRadius: 8,
    fontSize: 14,
    fontFamily:
      '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
  },
  components: {
    Button: {
      borderRadius: 10,
      controlHeight: 44,
    },
    Card: {
      paddingLG: 20,
    },
    Input: {
      borderRadius: 10,
    },
  },
};

// Dark mode
export const fraxDarkTheme: ThemeConfig = {
  token: {
    colorPrimary: "#6C5CE7",
    colorBgContainer: "#1A1A3A",
    colorBgElevated: "#12122A",
    colorBorder: "#2A2A4A",
    colorText: "#E0E0F0",
    colorTextSecondary: "#8887A8",
    colorTextTertiary: "#555577",
    colorSuccess: "#5CC4A6",
    colorWarning: "#F0A86B",
    colorError: "#F0856E",
    colorInfo: "#6C5CE7",
    borderRadius: 8,
    fontSize: 14,
    fontFamily:
      '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
  },
  components: {
    Button: {
      borderRadius: 10,
      controlHeight: 44,
    },
    Card: {
      paddingLG: 20,
    },
    Input: {
      borderRadius: 10,
    },
  },
};
