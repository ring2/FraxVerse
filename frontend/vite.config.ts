import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // 把两个 zustand store 都拆到独立 chunk
          if (id.includes("useAuthStore") || id.includes("useNotificationStore")) {
            return "vendor-stores";
          }
          // zustand 本身也独立
          if (id.includes("node_modules/zustand")) {
            return "vendor-zustand";
          }
        },
      },
    },
  },
});
