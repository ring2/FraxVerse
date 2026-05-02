import React, { useState } from "react";
import { useTheme } from "../../theme/ThemeContext";

interface SectionCardProps {
  title: string;
  action?: { text: string; onClick: () => void };
  children: React.ReactNode;
  showLink?: boolean;
  onClickLink?: () => void;
}

const MobileSectionCard: React.FC<SectionCardProps> = ({
  title,
  action,
  children,
  showLink,
  onClickLink,
}) => {
  const { colors, mode } = useTheme();
  const [actionHovered, setActionHovered] = useState(false);
  const [cardHovered, setCardHovered] = useState(false);
  const isLight = mode === "light";

  return (
    <div
      className="card-hover"
      onMouseEnter={() => setCardHovered(true)}
      onMouseLeave={() => setCardHovered(false)}
      style={{
        background: isLight
          ? "rgba(255,255,255,0.75)"
          : "rgba(18,18,42,0.7)",
        backdropFilter: "blur(12px) saturate(1.3)",
        WebkitBackdropFilter: "blur(12px) saturate(1.3)",
        border: isLight
          ? "1px solid rgba(255,255,255,0.5)"
          : "1px solid rgba(127,119,221,0.15)",
        borderRadius: 16,
        overflow: "hidden",
        position: "relative",
        transition: "background 0.35s, box-shadow 0.25s, border-color 0.25s",
        boxShadow: cardHovered
          ? isLight
            ? "0 4px 20px rgba(0,0,0,0.05), 0 0 0 1px rgba(127,119,221,0.08)"
            : "0 4px 20px rgba(0,0,0,0.25), 0 0 0 1px rgba(127,119,221,0.12)"
          : "none",
      }}
    >
      {/* Top accent bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: "linear-gradient(90deg, transparent, #9B93E4, #7F77DD, #9B93E4, transparent)",
          opacity: 0.4,
        }}
      />

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
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: colors.purple[400],
              flexShrink: 0,
              transition: "transform 0.2s",
              transform: cardHovered ? "scale(1.3)" : "scale(1)",
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
              transition: "background 0.15s ease, color 0.15s",
            }}
          >
            {action.text}
          </span>
        )}
        {showLink && !action && (
          <span
            onClick={onClickLink}
            style={{
              fontSize: 12,
              color: colors.purple[500],
              cursor: "pointer",
              padding: "3px 7px",
              borderRadius: colors.radius.sm + "px",
              userSelect: "none",
              lineHeight: 1.3,
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = colors.purple[50];
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
            }}
          >
            查看全部 →
          </span>
        )}
      </div>
      <div>{children}</div>
    </div>
  );
};

export default MobileSectionCard;
