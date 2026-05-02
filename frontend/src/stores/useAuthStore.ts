import { create } from "zustand";
import { authService } from "../services/authService";
import type { User } from "../types/common";

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;

  login: (username: string, password: string, rememberMe: boolean) => Promise<void>;
  init: (username: string, password: string, email: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<boolean>;
  clearError: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: false,
  user: null,
  accessToken: localStorage.getItem("access_token"),
  refreshToken: localStorage.getItem("refresh_token"),
  isLoading: false,
  isInitialized: false,
  error: null,

  login: async (username, password, rememberMe) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authService.login({ username, password });
      const tokens = res.data;
      localStorage.setItem("access_token", tokens.access_token);
      if (rememberMe) {
        localStorage.setItem("refresh_token", tokens.refresh_token);
      } else {
        sessionStorage.setItem("refresh_token", tokens.refresh_token);
      }
      // Fetch user profile
      const profileRes = await authService.getProfile();
      set({
        isAuthenticated: true,
        user: profileRes.data,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "response" in err
          ? (err as { response: { data: { message: string } } }).response?.data?.message || "登录失败"
          : "登录失败";
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  init: async (username, password, email) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authService.init({ username, password, email });
      const tokens = res.data;
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      const profileRes = await authService.getProfile();
      set({
        isAuthenticated: true,
        user: profileRes.data,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "response" in err
          ? (err as { response: { data: { message: string } } }).response?.data?.message || "初始化失败"
          : "初始化失败";
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  logout: async () => {
    try {
      await authService.logout();
    } catch {
      // Ignore errors on logout
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      sessionStorage.removeItem("refresh_token");
      set({
        isAuthenticated: false,
        user: null,
        accessToken: null,
        refreshToken: null,
      });
    }
  },

  refreshAccessToken: async () => {
    const refreshToken = get().refreshToken;
    if (!refreshToken) return false;
    try {
      const res = await authService.refresh(refreshToken);
      const newToken = res.data.access_token;
      localStorage.setItem("access_token", newToken);
      set({ accessToken: newToken });
      return true;
    } catch {
      set({ isAuthenticated: false, user: null, accessToken: null, refreshToken: null });
      return false;
    }
  },

  clearError: () => set({ error: null }),

  checkAuth: async () => {
    const accessToken = get().accessToken;
    if (!accessToken) {
      set({ isAuthenticated: false, isInitialized: true });
      return;
    }
    try {
      const res = await authService.getProfile();
      set({
        isAuthenticated: true,
        user: res.data,
        isInitialized: true,
      });
    } catch {
      // Try refresh
      const ok = await get().refreshAccessToken();
      if (ok) {
        const res = await authService.getProfile();
        set({
          isAuthenticated: true,
          user: res.data,
          isInitialized: true,
        });
      } else {
        set({ isAuthenticated: false, isInitialized: true });
      }
    }
  },
}));
