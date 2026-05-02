import { describe, it, expect, vi, beforeEach } from "vitest";
import { tradeService } from "./tradeService";
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

describe("tradeService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createOrder", () => {
    it("should call POST /trade/orders with payload", async () => {
      const mockOrder = {
        id: 1,
        client_order_id: "abc-123",
        stock_code: "600519",
        direction: "buy",
        status: "pending",
        volume: 100,
        filled_volume: 0,
        price: "1850.00",
        created_at: "2026-05-02T01:08:41.536337+08:00",
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockOrder });

      const payload = {
        stock_code: "600519",
        direction: "buy" as const,
        order_type: "limit" as const,
        price: 1850,
        volume: 100,
        strategy_type: "momentum",
        reason: "测试下单",
      };

      const result = await tradeService.createOrder(payload);

      expect(api.post).toHaveBeenCalledWith("/trade/orders", payload);
      expect(result).toEqual(mockOrder);
    });

    it("should return null on empty response", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: null });

      const payload = {
        stock_code: "600519",
        direction: "buy" as const,
        order_type: "market" as const,
        price: 0,
        volume: 100,
        strategy_type: "",
        reason: "",
      };

      const result = await tradeService.createOrder(payload);
      expect(result).toBeNull();
    });
  });

  describe("cancelOrder", () => {
    it("should call POST /trade/orders/:id/cancel", async () => {
      vi.mocked(api.post).mockResolvedValue({});

      await tradeService.cancelOrder("42");

      expect(api.post).toHaveBeenCalledWith("/trade/orders/42/cancel");
    });
  });

  describe("updateMode", () => {
    it("should call POST /trade/mode with payload", async () => {
      const mockMode = {
        current_mode: "PAPER",
        confirm_mode: "single",
        emergency_stop: false,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockMode });

      const result = await tradeService.updateMode({ target_mode: "PAPER" });

      expect(api.post).toHaveBeenCalledWith("/trade/mode", {
        target_mode: "PAPER",
      });
      expect(result).toEqual(mockMode);
    });
  });

  describe("emergencyStop", () => {
    it("should call POST /trade/emergency-stop", async () => {
      vi.mocked(api.post).mockResolvedValue({});

      await tradeService.emergencyStop();

      expect(api.post).toHaveBeenCalledWith("/trade/emergency-stop");
    });
  });

  describe("getOrders", () => {
    it("should call GET /trade/orders and return array", async () => {
      const mockOrders = [
        { id: 1, stock_code: "600519", direction: "buy", status: "filled" },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockOrders });

      const result = await tradeService.getOrders();

      expect(api.get).toHaveBeenCalledWith("/trade/orders");
      expect(result).toEqual(mockOrders);
    });

    it("should return empty array on null data", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: null });

      const result = await tradeService.getOrders();

      expect(result).toEqual([]);
    });
  });

  describe("getMode", () => {
    it("should call GET /trade/mode", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { current_mode: "SIMULATION", confirm_mode: "single", emergency_stop: false },
      });

      const result = await tradeService.getMode();

      expect(api.get).toHaveBeenCalledWith("/trade/mode");
      expect(result?.current_mode).toBe("SIMULATION");
    });
  });
});
