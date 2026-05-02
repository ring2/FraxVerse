import React, { useState } from "react";
import { useTheme } from "../../theme/ThemeContext";

interface SectionCardProps {
  title: string;
  action?: { text: string; onClick: () => void };
  children: React.ReactNode;
}

const MobileSectionCard: React.FC<SectionCardProps> = ({
  title,
  action,
  children,
}) => {
  const { colors } = useTheme();
  const [actionHovered, setActionHovered] = useState(false);

  return (
    <div
      style={{
        background: colors.bg.surface,
        border: `1px solid ${colors.border.light}`,
        borderRadius: colors.radius.lg + "px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 14px",
          borderBottom: `1px solid ${colors.border.light}`,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: colors.purple[400],
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: colors.text.primary,
              lineHeight: 1.4,
            }}
          >
            {title}
          </span>
        </div>
        {action && (
          <span
            onClick={action.onClick}
            onMouseEnter={() => setActionHovered(true)}
            onMouseLeave={() => setActionHovered(false)}
            style={{
              fontSize: 12,
              color: colors.purple[500],
              cursor: "pointer",
              padding: "3px 7px",
              borderRadius: colors.radius.sm + "px",
              background: actionHovered ? colors.purple[50] : "transparent",
              userSelect: "none",
              lineHeight: 1.3,
              transition: "background 0.15s ease",
            }}
          >
            {action.text}
          </span>
        )}
      </div>
      <div>{children}</div>
    </div>
  );
};

export default MobileSectionCard;
