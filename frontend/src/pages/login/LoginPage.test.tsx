import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App as AntApp, ConfigProvider } from "antd";
import LoginPage from "../../pages/login/LoginPage";
import { useAuthStore } from "../../stores/useAuthStore";

// Mock authService completely
vi.mock("../../services/authService", () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  },
}));

import { authService } from "../../services/authService";

function renderLoginPage() {
  return render(
    <ConfigProvider>
      <AntApp>
        <MemoryRouter initialEntries={["/login"]}>
          <LoginPage />
        </MemoryRouter>
      </AntApp>
    </ConfigProvider>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    localStorage.clear();
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

  it("should render login form", () => {
    renderLoginPage();

    expect(screen.getByText("碎片宇宙")).toBeInTheDocument();
    expect(screen.getByText("FraxVerse · 交易修心")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("用户名")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("密码")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /登 录/i })).toBeInTheDocument();
  });

  it("should show error on login failure", async () => {
    vi.mocked(authService.login).mockRejectedValue({
      response: { data: { message: "用户名或密码错误" } },
    });

    renderLoginPage();

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("用户名"), "admin");
    await user.type(screen.getByPlaceholderText("密码"), "wrong");
    await user.click(screen.getByRole("button", { name: /登 录/i }));

    await waitFor(() => {
      const state = useAuthStore.getState();
      expect(state.error).toBe("用户名或密码错误");
    });
  });

  it("should call login and navigate on success", async () => {
    vi.mocked(authService.login).mockResolvedValue({
      code: 0,
      message: "ok",
      data: {
        access_token: "mock-token",
        refresh_token: "mock-refresh",
        token_type: "bearer",
        expires_in: 1800,
      },
    });

    renderLoginPage();

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("用户名"), "admin");
    await user.type(screen.getByPlaceholderText("密码"), "admin123");
    await user.click(screen.getByRole("button", { name: /登 录/i }));

    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith({
        username: "admin",
        password: "admin123",
      });
    });

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe("mock-token");
  });
});
