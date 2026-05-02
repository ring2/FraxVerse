// FraxVerse Cosmic Color System
// Brand philosophy: 交易修心、心念为碎片、宇宙为心之投影

export const colors = {
  // Deep space backgrounds
  bg: "#0a0a1a",
  surface: "#12122a",
  card: "#1a1a3a",
  border: "#2a2a4a",

  // Brand accent colors
  nebula: "#6b5ce7", // 星云紫 — primary
  gold: "#f0c040", // 星芒金 — profit/positive
  shard: "#4a9eff", // 碎片蓝 — info/links
  amber: "#ef9f27", // 琥珀 — hold/watch

  // Semantic colors
  danger: "#ff4757", // loss/error
  success: "#2ed573", // success/completed
  warning: "#ffa502",

  // Text colors
  text: "#e0e0f0",
  muted: "#8887a8",
  dimmed: "#555577",

  // Gradient presets
  gradients: {
    primary: "linear-gradient(135deg, #6b5ce7, #4a9eff)",
    gold: "linear-gradient(135deg, #f0c040, #f5d76e)",
    danger: "linear-gradient(135deg, #ff4757, #ff6b81)",
    surface: "linear-gradient(135deg, #12122a, #1a1a3a)",
  },
} as const;

export const spacing = {
  sidebar: 240,
  header: 56,
  mobileBottomNav: 60,
} as const;
