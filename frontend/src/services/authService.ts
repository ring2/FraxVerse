import api from "./api";
import type { ApiResponse, TokenResponse, LoginRequest, SetupRequest } from "../types/api-extended";

export const authService = {
  async checkInit(): Promise<ApiResponse<{ initialized: boolean }>> {
    const res = await api.get("/auth/status");
    return { code: 0, message: "ok", data: { initialized: res.data?.initialized ?? false } };
  },

  async init(payload: SetupRequest): Promise<ApiResponse<TokenResponse>> {
    const res = await api.post("/auth/setup", payload);
    return {
      code: 0,
      message: "ok",
      data: res.data as TokenResponse,
    };
  },

  async login(payload: LoginRequest): Promise<ApiResponse<TokenResponse>> {
    const res = await api.post("/auth/login", payload);
    return {
      code: 0,
      message: "ok",
      data: res.data as TokenResponse,
    };
  },

  async logout(): Promise<ApiResponse<null>> {
    await api.post("/auth/logout");
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
};
