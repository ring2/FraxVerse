import React, { useState } from "react";
import { useTheme } from "../../theme/ThemeContext";

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: { text: string; type: "up" | "down" | "neutral" };
  valueColor?: string;
}

const MobileMetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  change,
  valueColor,
}) => {
  const { colors, mode } = useTheme();
  const [hovered, setHovered] = useState(false);
  const isLight = mode === "light";

  const changeStyles: Record<string, React.CSSProperties> = {
    up: {
      color: colors.semantic.up,
      backgroundColor: colors.semantic.upBg,
    },
    down: {
      color: colors.semantic.down,
      backgroundColor: colors.semantic.downBg,
    },
    neutral: {
      color: colors.purple[400],
      backgroundColor: colors.purple[50],
    },
  };

  return (
    <div
      className="card-hover"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 4,
        background: isLight
          ? "rgba(255,255,255,0.75)"
          : "rgba(18,18,42,0.7)",
        backdropFilter: "blur(12px) saturate(1.3)",
        WebkitBackdropFilter: "blur(12px) saturate(1.3)",
        border: isLight
          ? "1px solid rgba(255,255,255,0.5)"
          : "1px solid rgba(127,119,221,0.15)",
        borderRadius: 16,
        padding: 14,
        transition: "background 0.35s, transform 0.2s, box-shadow 0.25s",
        transform: hovered ? "translateY(-2px)" : "translateY(0)",
        boxShadow: hovered
          ? isLight
            ? "0 6px 20px rgba(0,0,0,0.05), 0 0 0 1px rgba(127,119,221,0.08)"
            : "0 6px 20px rgba(0,0,0,0.3), 0 0 0 1px rgba(127,119,221,0.12)"
          : "none",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Top accent — thin gradient line */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: "25%",
          right: "25%",
          height: 2,
          background:
            "linear-gradient(90deg, transparent, rgba(127,119,221,0.3), transparent)",
          borderRadius: "0 0 2px 2px",
          opacity: hovered ? 0.8 : 0.3,
          transition: "opacity 0.3s",
        }}
      />

      <span
        style={{
          fontSize: 12,
          color: colors.text.tertiary,
          lineHeight: 1.4,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 22,
          fontWeight: 600,
          color: valueColor ?? colors.text.primary,
          lineHeight: 1.2,
          transition: "color 0.3s",
        }}
      >
        {value}
      </span>
      {change && (
        <span
          style={{
            display: "inline-flex",
            alignSelf: "flex-start",
            fontSize: 11,
            fontWeight: 500,
            padding: "2px 7px",
            borderRadius: 20,
            lineHeight: 1.3,
            ...changeStyles[change.type],
          }}
        >
          {change.text}
        </span>
      )}
    </div>
  );
};

export default MobileMetricCard;
