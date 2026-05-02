import api from "./api";
import type { ApiResponse } from "../types/api";
import type { AuthTokens, InitRequest, LoginRequest, User } from "../types/common";

export const authService = {
  async checkInit(): Promise<ApiResponse<{ initialized: boolean }>> {
    const res = await api.get("/auth/check-init");
    return res.data;
  },

  async init(payload: InitRequest): Promise<ApiResponse<AuthTokens>> {
    const res = await api.post("/auth/init", payload);
    return res.data;
  },

  async login(payload: LoginRequest): Promise<ApiResponse<AuthTokens>> {
    const res = await api.post("/auth/login", payload);
    return res.data;
  },

  async logout(): Promise<ApiResponse<null>> {
    const res = await api.post("/auth/logout");
    return res.data;
  },

  async refresh(refreshToken: string): Promise<ApiResponse<{ access_token: string }>> {
    const res = await api.post("/auth/refresh", { refresh_token: refreshToken });
    return res.data;
  },

  async getProfile(): Promise<ApiResponse<User>> {
    const res = await api.get("/auth/profile");
    return res.data;
  },
};
