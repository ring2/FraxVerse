import { describe, it, expect, vi, beforeEach } from "vitest";
import { notificationService } from "./notificationService";
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

describe("notificationService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("markRead", () => {
    it("should call POST /notifications/:id/read", async () => {
      vi.mocked(api.post).mockResolvedValue({});

      await notificationService.markRead("42");

      expect(api.post).toHaveBeenCalledWith("/notifications/42/read");
    });
  });

  describe("getNotifications", () => {
    it("should call GET /notifications/", async () => {
      const mockData = [
        { id: "1", title: "test", is_read: false, created_at: "2026-01-01" },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockData });

      const result = await notificationService.getNotifications();

      expect(api.get).toHaveBeenCalledWith("/notifications/");
      expect(result).toHaveLength(1);
    });

    it("should return empty array on null", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: null });

      const result = await notificationService.getNotifications();
      expect(result).toEqual([]);
    });
  });
});
