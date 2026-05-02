import { describe, it, expect, vi, beforeEach } from "vitest";
import { authService } from "./authService";
import api from "./api";

vi.mock("./api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    create: vi.fn().mockReturnThis(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}));

describe("authService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("should call POST /auth/login and return tokens", async () => {
      const mockTokens = {
        access_token: "abc",
        refresh_token: "def",
        token_type: "bearer",
        expires_in: 1800,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockTokens });

      const result = await authService.login({ username: "admin", password: "admin123" });

      expect(api.post).toHaveBeenCalledWith("/auth/login", {
        username: "admin",
        password: "admin123",
      });
      expect(result).toEqual({
        code: 0,
        message: "ok",
        data: mockTokens,
      });
    });

    it("should propagate API errors", async () => {
      const error = new Error("Network error");
      vi.mocked(api.post).mockRejectedValue(error);

      await expect(
        authService.login({ username: "admin", password: "wrong" })
      ).rejects.toThrow("Network error");
    });
  });

  describe("refresh", () => {
    it("should call POST /auth/refresh and return new access_token", async () => {
      const mockResponse = { access_token: "new_token" };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await authService.refresh("old_refresh_token");

      expect(api.post).toHaveBeenCalledWith("/auth/refresh", {
        refresh_token: "old_refresh_token",
      });
      expect(result).toEqual({
        code: 0,
        message: "ok",
        data: mockResponse,
      });
    });
  });

  describe("logout", () => {
    it("should call POST /auth/logout", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: null });

      const result = await authService.logout();

      expect(api.post).toHaveBeenCalledWith("/auth/logout");
      expect(result).toEqual({ code: 0, message: "ok", data: null });
    });
  });
});
