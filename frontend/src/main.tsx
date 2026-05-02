import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider, App as AntApp } from "antd";
import { fraxTheme } from "./theme/fraxTheme";
import App from "./App";
import { detectDevice } from "./utils/deviceDetect";
import "./index.css";

// --- Device-aware routing (runs BEFORE React renders) ---
// This prevents the flash of wrong layout on mobile.
// React Router's navigate('/dashboard') from LoginPage still goes to PC,
// so LoginPage also uses detectDevice() for its redirect target.
(function boot() {
  const device = detectDevice();
  const path = window.location.pathname;
  const isLogin = path === "/login";

  // Login page is shared — always allowed
  if (isLogin) return;

  if (device === "mobile" && !path.startsWith("/m/")) {
    window.location.href = "/login";
  } else if (device === "desktop" && path.startsWith("/m/")) {
    window.location.href = "/login";
  }
})();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider theme={fraxTheme}>
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>
);
