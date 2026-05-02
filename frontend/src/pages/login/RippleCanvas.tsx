import { useEffect, useRef } from "react";
import { useTheme } from "../../theme/ThemeContext";

interface Ripple {
  x: number;
  y: number;
  radius: number;
  maxRadius: number;
  opacity: number;
  fragments: Fragment[];
}

interface Fragment {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  color: string;
}

export default function RippleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ripplesRef = useRef<Ripple[]>([]);
  const { mode } = useTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const isLight = mode === "light";

    const handleClick = (e: MouseEvent | TouchEvent) => {
      const x = "touches" in e ? e.touches[0].clientX : e.clientX;
      const y = "touches" in e ? e.touches[0].clientY : e.clientY;

      // Don't trigger ripple on form elements
      const target = "target" in e ? e.target as HTMLElement : null;
      if (target && (target.tagName === "INPUT" || target.tagName === "BUTTON" || target.closest(".ant-input") || target.closest(".ant-btn"))) {
        return;
      }

      const maxR = Math.max(canvas.width, canvas.height) * 0.4;

      const fragmentCount = 14;
      const fragments: Fragment[] = [];
      const colors = isLight
        ? ["#9B93E4", "#7F77DD", "#CECBF6", "#E6E2FC", "#FFFFFF", "#B8B3EE"]
        : ["#AFA9EC", "#7F77DD", "#534AB7", "#CECBF6", "#FFFFFF", "#9B93E4"];

      for (let i = 0; i < fragmentCount; i++) {
        const angle = (Math.PI * 2 * i) / fragmentCount + (Math.random() - 0.5) * 0.4;
        const speed = Math.random() * 2.5 + 1;
        fragments.push({
          x,
          y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          size: Math.random() * 3.5 + 1,
          opacity: 0.85,
          color: colors[Math.floor(Math.random() * colors.length)],
        });
      }

      ripplesRef.current.push({ x, y, radius: 0, maxRadius: maxR, opacity: 0.5, fragments });
    };

    window.addEventListener("click", handleClick);
    window.addEventListener("touchstart", handleClick, { passive: true });

    let animId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ripplesRef.current = ripplesRef.current.filter((r) => {
        r.radius += 3;
        r.opacity -= 0.01;
        if (r.radius > r.maxRadius) r.opacity = 0;
        if (r.opacity <= 0) return false;

        // Draw ripple ring
        ctx.beginPath();
        ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
        ctx.strokeStyle = isLight
          ? `rgba(127,119,221,${r.opacity * 0.35})`
          : `rgba(175,169,236,${r.opacity * 0.35})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Inner ring
        if (r.radius > 20) {
          ctx.beginPath();
          ctx.arc(r.x, r.y, r.radius * 0.6, 0, Math.PI * 2);
          ctx.strokeStyle = isLight
            ? `rgba(155,147,228,${r.opacity * 0.18})`
            : `rgba(175,169,236,${r.opacity * 0.18})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }

        // Animate fragments
        for (const f of r.fragments) {
          f.x += f.vx;
          f.y += f.vy;
          f.vx *= 0.96;
          f.vy *= 0.96;
          f.opacity -= 0.018;
          if (f.opacity <= 0) continue;

          ctx.beginPath();
          ctx.arc(f.x, f.y, f.size, 0, Math.PI * 2);
          ctx.fillStyle = f.color + Math.round(f.opacity * 255).toString(16).padStart(2, "0");
          ctx.fill();

          // Glow
          ctx.beginPath();
          ctx.arc(f.x, f.y, f.size * 2.5, 0, Math.PI * 2);
          ctx.fillStyle = f.color + Math.round(f.opacity * 25).toString(16).padStart(2, "0");
          ctx.fill();
        }

        return true;
      });

      animId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("click", handleClick);
      window.removeEventListener("touchstart", handleClick);
    };
  }, [mode]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 100,
      }}
    />
  );
}
