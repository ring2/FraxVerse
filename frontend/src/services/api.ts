import axios from "axios";
import type { ApiResponse } from "../types/api-extended";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 360000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 强制 runtime 设置 timeout，防止 build-time tree-shaking 优化掉
api.defaults.timeout = 360000;

// Request interceptor — attach access token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // 每个请求单独设 timeout，绕开 rolldown 常量折叠
    config.timeout = 360000;
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — token refresh on 401, notifies store
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) throw new Error("No refresh token");

        const res = await axios.post<
          ApiResponse<{ access_token: string; refresh_token?: string }>
        >("/api/v1/auth/refresh", { refresh_token: refreshToken });

        const newAccessToken = res.data.data?.access_token || (res.data as unknown as { access_token: string }).access_token;
        if (!newAccessToken) throw new Error("No access_token in refresh response");

        // Store new token
        localStorage.setItem("access_token", newAccessToken);

        // Notify the Zustand store so its state stays in sync
        // Lazy import to avoid circular dependency at module level
        const { useAuthStore } = await import("../stores/useAuthStore");
        useAuthStore.getState().setTokens(newAccessToken, null);

        processQueue(null, newAccessToken);

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        // Clear store state too
        try {
          const { useAuthStore } = await import("../stores/useAuthStore");
          useAuthStore.getState().setTokens(null, null);
        } catch {
          // Best effort
        }
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
