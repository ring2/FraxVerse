/**
 * Device detection utility for FraxVerse.
 * Routes mobile users to /m/ pages and desktop users to / (PC) pages.
 */

export function detectDevice(): "mobile" | "desktop" {
  if (typeof window === "undefined") return "desktop";
  const ua = navigator.userAgent;
  const isMobile =
    /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua) ||
    (/(iPad|Tablet|PlayBook|Silk)/i.test(ua)) ||
    (window.innerWidth < 768);
  return isMobile ? "mobile" : "desktop";
}

/**
 * Call at app entry point. Redirects to the correct route based on device type.
 */
export function detectAndRedirect(): void {
  const device = detectDevice();
  const path = window.location.pathname;
  const isMobileRoute = path.startsWith("/m/");
  const isLoginRoute = path === "/login";

  // Don't redirect from login page
  if (isLoginRoute) return;

  if (device === "mobile" && !isMobileRoute) {
    window.location.href = "/m/dashboard";
  } else if (device === "desktop" && isMobileRoute) {
    window.location.href = "/dashboard";
  }
}
