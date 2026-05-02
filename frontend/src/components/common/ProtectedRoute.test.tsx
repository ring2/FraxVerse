import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import { useAuthStore } from "../../stores/useAuthStore";

function TestApp({ initialPath }: { initialPath: string }) {
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/protected"
          element={
            <ProtectedRoute>
              <div data-testid="protected-content">Protected</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div data-testid="login-page">Login</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
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
  });

  it("should not render children when not initialized", () => {
    render(<TestApp initialPath="/protected" />);
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("should render children when authenticated", () => {
    useAuthStore.setState({
      isAuthenticated: true,
      isInitialized: true,
      user: { id: 1, username: "admin", created_at: new Date().toISOString() },
      accessToken: "some-token",
    });

    render(<TestApp initialPath="/protected" />);

    expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    expect(screen.queryByTestId("login-page")).not.toBeInTheDocument();
  });

  it("should redirect to /login when not authenticated and initialized", () => {
    useAuthStore.setState({
      isAuthenticated: false,
      isInitialized: true,
    });

    render(<TestApp initialPath="/protected" />);

    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });
});
