import React from "react";
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
  const { colors } = useTheme();

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
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 4,
        background: colors.bg.surface,
        border: `1px solid ${colors.border.light}`,
        borderRadius: colors.radius.lg + "px",
        padding: 14,
      }}
    >
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
