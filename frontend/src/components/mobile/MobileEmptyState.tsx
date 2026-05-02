import React from "react";
import { useTheme } from "../../theme/ThemeContext";

interface EmptyStateProps {
  icon?: React.ReactNode;
  text: string;
}

const MobileEmptyState: React.FC<EmptyStateProps> = ({ icon, text }) => {
  const { colors } = useTheme();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "60px 20px",
        textAlign: "center",
      }}
    >
      {icon && (
        <div
          style={{
            width: 48,
            height: 48,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: colors.text.tertiary,
            opacity: 0.5,
            marginBottom: 12,
          }}
        >
          {icon}
        </div>
      )}
      <span
        style={{
          fontSize: 13,
          color: colors.text.tertiary,
          lineHeight: 1.5,
        }}
      >
        {text}
      </span>
    </div>
  );
};

export default MobileEmptyState;
