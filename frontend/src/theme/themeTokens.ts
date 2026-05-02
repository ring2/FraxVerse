// FraxVerse 双主题 Token 体系 v3.0
// 精确映射设计稿 FraxVerse-V2-AllPages.html 的 CSS 变量
// Light Mode = :root (默认), Dark Mode = [data-theme="dark"]

export interface FraxThemeColors {
  bg: { page: string; surface: string; sidebar: string; subtle: string; elevated: string };
  purple: { 50: string; 100: string; 200: string; 400: string; 500: string; 600: string; 700: string };
  semantic: { up: string; upBg: string; down: string; downBg: string; amber: string; amberBg: string };
  text: { primary: string; secondary: string; tertiary: string; inverse: string };
  border: { light: string; medium: string };
  shadow: { card: string; elevated: string };
  gradient: { logo: string; primary: string };
  chart: { grid: string; line: string };
  radius: { sm: number; md: number; lg: number; xl: number };
  scrollbar: string;
  btnShadow: string;
  btnShadowHover: string;
}

export const lightTheme: FraxThemeColors = {
  bg: {
    page: "#FAF9F7",
    surface: "#FFFFFF",
    sidebar: "#F5F3EF",
    subtle: "#F8F6F2",
    elevated: "#FFFFFF",
  },
  purple: {
    50: "#F3F1FE",
    100: "#E6E2FC",
    200: "#CECBF6",
    400: "#9B93E4",
    500: "#7F77DD",
    600: "#5F56C8",
    700: "#4A42A8",
  },
  semantic: {
    up: "#E8735A",
    upBg: "#FEF2EF",
    down: "#4DB899",
    downBg: "#EFF9F5",
    amber: "#E8A840",
    amberBg: "#FFF8EB",
  },
  text: {
    primary: "#2D2B28",
    secondary: "#6B6760",
    tertiary: "#9E9A92",
    inverse: "#FFFFFF",
  },
  border: {
    light: "rgba(0,0,0,0.06)",
    medium: "rgba(0,0,0,0.10)",
  },
  shadow: {
    card: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
    elevated: "0 4px 16px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.03)",
  },
  gradient: {
    logo: "linear-gradient(135deg, #9B93E4, #5F56C8)",
    primary: "linear-gradient(135deg, #7F77DD, #5F56C8)",
  },
  chart: {
    grid: "rgba(0,0,0,0.04)",
    line: "#7F77DD",
  },
  radius: { sm: 6, md: 10, lg: 14, xl: 20 },
  scrollbar: "rgba(0,0,0,0.1)",
  btnShadow: "0 2px 8px rgba(127,119,221,0.3)",
  btnShadowHover: "0 4px 14px rgba(127,119,221,0.4)",
};

export const darkTheme: FraxThemeColors = {
  bg: {
    page: "#06060F",
    surface: "rgba(15,15,35,0.85)",
    sidebar: "rgba(6,6,15,0.7)",
    subtle: "rgba(10,10,26,0.6)",
    elevated: "rgba(25,25,55,0.95)",
  },
  purple: {
    50: "rgba(83,74,183,0.10)",
    100: "rgba(83,74,183,0.15)",
    200: "rgba(127,119,221,0.25)",
    400: "#AFA9EC",
    500: "#7F77DD",
    600: "#AFA9EC",
    700: "#CECBF6",
  },
  semantic: {
    up: "#F0997B",
    upBg: "rgba(216,90,48,0.15)",
    down: "#5DCAA5",
    downBg: "rgba(29,158,117,0.15)",
    amber: "#EF9F27",
    amberBg: "rgba(239,159,39,0.15)",
  },
  text: {
    primary: "#E0DFF0",
    secondary: "#8887A8",
    tertiary: "#5A5880",
    inverse: "#06060F",
  },
  border: {
    light: "rgba(83,74,183,0.2)",
    medium: "rgba(127,119,221,0.4)",
  },
  shadow: {
    card: "0 1px 3px rgba(0,0,0,0.3)",
    elevated: "0 4px 16px rgba(0,0,0,0.4)",
  },
  gradient: {
    logo: "linear-gradient(135deg, #7F77DD, #534AB7)",
    primary: "linear-gradient(135deg, #7F77DD, #534AB7)",
  },
  chart: {
    grid: "rgba(83,74,183,0.08)",
    line: "#AFA9EC",
  },
  radius: { sm: 6, md: 10, lg: 14, xl: 20 },
  scrollbar: "rgba(83,74,183,0.3)",
  btnShadow: "0 2px 8px rgba(127,119,221,0.4)",
  btnShadowHover: "0 4px 14px rgba(127,119,221,0.5)",
};

export type ThemeMode = "light" | "dark";
