import React, { useState } from "react";
import { useTheme } from "../../theme/ThemeContext";

interface ButtonProps {
  variant: "primary" | "ghost" | "danger";
  children: React.ReactNode;
  onClick?: () => void;
  style?: React.CSSProperties;
  fullWidth?: boolean;
}

const MobileButton: React.FC<ButtonProps> = ({
  variant,
  children,
  onClick,
  style,
  fullWidth,
}) => {
  const { colors } = useTheme();
  const [hovered, setHovered] = useState(false);

  const baseStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    padding: "6px 14px",
    borderRadius: colors.radius.md + "px",
    fontSize: 13,
    fontWeight: 500,
    lineHeight: 1.4,
    cursor: onClick ? "pointer" : "default",
    border: "none",
    outline: "none",
    transition: "all 0.15s ease",
    userSelect: "none",
    ...(fullWidth ? { width: "100%" } : {}),
    ...style,
  };

  let variantStyle: React.CSSProperties;

  switch (variant) {
    case "primary":
      variantStyle = {
        background: colors.gradient.primary,
        color: colors.text.inverse,
        boxShadow: colors.btnShadow,
        ...(hovered
          ? {
              transform: "translateY(-1px)",
              boxShadow: colors.btnShadowHover,
            }
          : {}),
      };
      break;
    case "ghost":
      variantStyle = {
        background: "transparent",
        color: colors.text.secondary,
        border: `1px solid ${colors.border.medium}`,
        ...(hovered
          ? {
              background: colors.purple[50],
            }
          : {}),
      };
      break;
    case "danger":
      variantStyle = {
        background: colors.semantic.upBg,
        color: colors.semantic.up,
        ...(hovered
          ? {
              opacity: 0.85,
            }
          : {}),
      };
      break;
    default:
      variantStyle = {};
  }

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ ...baseStyle, ...variantStyle }}
    >
      {children}
    </button>
  );
};

export default MobileButton;
