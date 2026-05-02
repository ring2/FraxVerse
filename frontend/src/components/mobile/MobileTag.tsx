import React from "react";
import { useTheme } from "../../theme/ThemeContext";

interface TagProps {
  variant: "purple" | "amber" | "up" | "down";
  children: React.ReactNode;
}

const variantStyles: Record<
  string,
  { bg: string; color: string }
> = {
  purple: { bg: "purple.50", color: "purple.600" },
  amber: { bg: "semantic.amberBg", color: "semantic.amber" },
  up: { bg: "semantic.upBg", color: "semantic.up" },
  down: { bg: "semantic.downBg", color: "semantic.down" },
};

function resolveColor(colors: Record<string, any>, path: string): string {
  const keys = path.split(".");
  let val: any = colors;
  for (const key of keys) {
    val = val[key];
  }
  return val;
}

const MobileTag: React.FC<TagProps> = ({ variant, children }) => {
  const { colors } = useTheme();
  const config = variantStyles[variant];
  const bg = resolveColor(colors, config.bg);
  const textColor = resolveColor(colors, config.color);

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        fontSize: 11,
        fontWeight: 500,
        lineHeight: 1.3,
        padding: "2px 8px",
        borderRadius: 20,
        backgroundColor: bg,
        color: textColor,
      }}
    >
      {children}
    </span>
  );
};

export default MobileTag;
