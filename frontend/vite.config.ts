import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { visualizer } from "rollup-plugin-visualizer";

// 手动分包：将大型 vendor 库拆为独立 chunk
// 避免入口 JS 过大导致移动端加载缓慢
function manualChunks(id: string) {
  if (id.includes("node_modules/echarts")) return "vendor-echarts";
  if (id.includes("node_modules/antd")) return "vendor-antd";
  if (id.includes("node_modules/@ant-design/icons")) return "vendor-icons";
  if (id.includes("node_modules/lightweight-charts")) return "vendor-lightweight-charts";
  if (id.includes("node_modules/react") || id.includes("node_modules/react-dom"))
    return "vendor-react";
  if (id.includes("node_modules/axios")) return "vendor-axios";
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks,
        // 建议的 chunk 大小警告阈值
        chunkFileNames: "assets/[name]-[hash].js",
      },
    },
    // 关闭 chunk 大小警告（已手动分包）
    chunkSizeWarningLimit: 1000,
  },
});
