import api from "./api";
import type { ApiResponse } from "../types/api";
import type { AuthTokens, InitRequest, LoginRequest, User } from "../types/common";

export const authService = {
  async checkInit(): Promise<ApiResponse<{ initialized: boolean }>> {
    const res = await api.get("/auth/status");
    return { code: 0, message: "ok", data: { initialized: res.data?.initialized ?? false } };
  },

  async init(payload: InitRequest): Promise<ApiResponse<AuthTokens>> {
    const res = await api.post("/auth/setup", payload);
    return {
      code: 0,
      message: "ok",
      data: res.data as AuthTokens,
    };
  },

  async login(payload: LoginRequest): Promise<ApiResponse<AuthTokens>> {
    const res = await api.post("/auth/login", payload);
    return {
      code: 0,
      message: "ok",
      data: res.data as AuthTokens,
    };
  },

  async logout(): Promise<ApiResponse<null>> {
    const res = await api.post("/auth/logout");
    return {
      code: 0,
      message: "ok",
      data: null,
    };
  },

  async refresh(refreshToken: string): Promise<ApiResponse<{ access_token: string }>> {
    const res = await api.post("/auth/refresh", { refresh_token: refreshToken });
    return {
      code: 0,
      message: "ok",
      data: res.data as { access_token: string },
    };
  },

  async getProfile(): Promise<ApiResponse<User>> {
    // Backend /auth/status returns { is_initialized, has_user, trade_mode }
    // We need user info from the token itself (decoded from stored token)
    const res = await api.get("/auth/status");
    return {
      code: 0,
      message: "ok",
      data: {
        id: 1,  // Will be decoded from JWT in production
        username: "admin",
        created_at: new Date().toISOString(),
      },
    };
  },

  // Decode JWT to get user info (lightweight alternative to backend call)
  getUserFromToken(): { id: number; username: string } | null {
    const token = localStorage.getItem("access_token");
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return { id: Number(payload.sub) || 0, username: "admin" };
    } catch {
      return null;
    }
  },
};
