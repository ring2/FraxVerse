import { create } from "zustand";
import { authService } from "../services/authService";
import type { User } from "../types/api-extended";

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;

  login: (username: string, password: string) => Promise<void>;
  init: (username: string, password: string, deepseekApiKey: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<boolean>;
  clearError: () => void;
  checkAuth: () => Promise<void>;
  /** Called by axios interceptor after silent refresh — syncs store with latest tokens */
  setTokens: (accessToken: string | null, refreshToken: string | null) => void;
}

// Decode JWT payload to extract basic user info (no network call needed)
function decodeUserFromToken(token: string): User | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return {
      id: Number(payload.sub) || 0,
      username: payload.username || "admin",
      created_at: new Date((payload.iat || 0) * 1000).toISOString(),
    };
  } catch {
    return null;
  }
}

function loadTokens() {
  return {
    accessToken: localStorage.getItem("access_token"),
    refreshToken: localStorage.getItem("refresh_token"),
  };
}

export const useAuthStore = create<AuthState>((set, get) => {
  const { accessToken, refreshToken } = loadTokens();

  return {
    isAuthenticated: !!accessToken,
    user: accessToken ? decodeUserFromToken(accessToken) : null,
    accessToken,
    refreshToken,
    isLoading: false,
    isInitialized: false,
    error: null,

    setTokens: (accessToken, refreshToken) => {
      set((state) => {
        const next = { ...state };
        if (accessToken !== null) {
          next.accessToken = accessToken;
          localStorage.setItem("access_token", accessToken);
        }
        if (refreshToken !== null) {
          next.refreshToken = refreshToken;
          localStorage.setItem("refresh_token", refreshToken);
        }
        next.isAuthenticated = !!next.accessToken;
        next.user = next.accessToken ? decodeUserFromToken(next.accessToken) : null;
        return next;
      });
    },

    login: async (username, password) => {
      set({ isLoading: true, error: null });
      try {
        const res = await authService.login({ username, password });
        const tokens = res.data;
        localStorage.setItem("access_token", tokens.access_token);
        localStorage.setItem("refresh_token", tokens.refresh_token);
        set({
          isAuthenticated: true,
          user: decodeUserFromToken(tokens.access_token),
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

    init: async (username, password, deepseekApiKey) => {
      set({ isLoading: true, error: null });
      try {
        const res = await authService.init({ username, password, deepseek_api_key: deepseekApiKey });
        const tokens = res.data;
        localStorage.setItem("access_token", tokens.access_token);
        localStorage.setItem("refresh_token", tokens.refresh_token);
        set({
          isAuthenticated: true,
          user: decodeUserFromToken(tokens.access_token),
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
        set({
          accessToken: newToken,
          isAuthenticated: true,
          user: decodeUserFromToken(newToken),
        });
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
      // Token exists — decode user from JWT, no API call needed
      const user = decodeUserFromToken(accessToken);
      if (user) {
        set({ isAuthenticated: true, user, isInitialized: true });
      } else {
        // Invalid token format — try refresh
        const ok = await get().refreshAccessToken();
        set({ isInitialized: true, isAuthenticated: ok });
      }
    },
  };
});

// Expose setTokens globally so axios interceptor can call it without circular import
// The interceptor imports this file; store creation is lazy so no circular issue at runtime.
export const notifyTokenRefresh = (accessToken: string) => {
  useAuthStore.getState().setTokens(accessToken, null);
};
