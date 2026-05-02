import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAuthStore, notifyTokenRefresh } from "./useAuthStore";

// Mock authService
vi.mock("../services/authService", () => ({
  authService: {
    login: vi.fn(),
    init: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  },
}));

import { authService } from "../services/authService";

const JWT_ACCESS =
  "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsImlhdCI6MTc3Njk5MDAwMCwiZXhwIjo5OTk5OTk5OTk5fQ.signature";
const JWT_REFRESH =
  "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJpYXQiOjE3NzY5OTAwMDB9.signature";

describe("useAuthStore", () => {
  beforeEach(() => {
    localStorage.clear();
    // Reset store to initial state
    useAuthStore.setState({
      isAuthenticated: false,
      user: null,
      accessToken: null,
      refreshToken: null,
      isLoading: false,
      isInitialized: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("should store tokens and set authenticated", async () => {
      vi.mocked(authService.login).mockResolvedValue({
        code: 0,
        message: "ok",
        data: {
          access_token: JWT_ACCESS,
          refresh_token: JWT_REFRESH,
          token_type: "bearer",
          expires_in: 1800,
        },
      });

      await useAuthStore.getState().login("admin", "admin123");

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.accessToken).toBe(JWT_ACCESS);
      expect(state.refreshToken).toBe(JWT_REFRESH);
      expect(localStorage.getItem("access_token")).toBe(JWT_ACCESS);
      expect(localStorage.getItem("refresh_token")).toBe(JWT_REFRESH);
      expect(state.user?.username).toBe("admin");
    });

    it("should handle login failure", async () => {
      const apiError = {
        response: { data: { message: "用户名或密码错误" } },
      };
      vi.mocked(authService.login).mockRejectedValue(apiError);

      await expect(
        useAuthStore.getState().login("admin", "wrong")
      ).rejects.toEqual(apiError);

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBe("用户名或密码错误");
    });
  });

  describe("checkAuth", () => {
    it("should authenticate from existing token", async () => {
      localStorage.setItem("access_token", JWT_ACCESS);
      // Re-initialize the store with tokens from localStorage
      useAuthStore.setState({
        accessToken: JWT_ACCESS,
        refreshToken: null,
      });

      await useAuthStore.getState().checkAuth();

      const state = useAuthStore.getState();
      expect(state.isInitialized).toBe(true);
      expect(state.isAuthenticated).toBe(true);
      expect(state.user?.username).toBe("admin");
    });

    it("should mark unauthenticated when no token", async () => {
      await useAuthStore.getState().checkAuth();

      const state = useAuthStore.getState();
      expect(state.isInitialized).toBe(true);
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe("logout", () => {
    it("should clear all tokens and state", async () => {
      vi.mocked(authService.logout).mockResolvedValue({
        code: 0,
        message: "ok",
        data: null,
      });

      // Set logged-in state
      useAuthStore.setState({
        isAuthenticated: true,
        accessToken: JWT_ACCESS,
        refreshToken: JWT_REFRESH,
        user: { id: 1, username: "admin", created_at: new Date().toISOString() },
      });
      localStorage.setItem("access_token", JWT_ACCESS);
      localStorage.setItem("refresh_token", JWT_REFRESH);

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.user).toBeNull();
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
    });
  });

  describe("setTokens / notifyTokenRefresh", () => {
    it("should update tokens and sync localStorage", () => {
      useAuthStore.getState().setTokens(JWT_ACCESS, JWT_REFRESH);

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe(JWT_ACCESS);
      expect(state.refreshToken).toBe(JWT_REFRESH);
      expect(state.isAuthenticated).toBe(true);
      expect(localStorage.getItem("access_token")).toBe(JWT_ACCESS);
      expect(localStorage.getItem("refresh_token")).toBe(JWT_REFRESH);
    });

    it("notifyTokenRefresh should call setTokens correctly", () => {
      notifyTokenRefresh(JWT_ACCESS);

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe(JWT_ACCESS);
      expect(localStorage.getItem("access_token")).toBe(JWT_ACCESS);
    });
  });
});
