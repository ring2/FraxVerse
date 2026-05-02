import React from "react";
import { useTheme } from "../../theme/ThemeContext";

interface AgentBubbleProps {
  agent: "hunter" | "detector" | "sentiment" | "judge";
  name: string;
  text: string;
}

const agentConfig: Record<
  string,
  { avatarChar: string; color: string }
> = {
  hunter: { avatarChar: "H", color: "#E8735A" },
  detector: { avatarChar: "D", color: "#5F56C8" },
  sentiment: { avatarChar: "S", color: "#E8A840" },
  judge: { avatarChar: "J", color: "#4DB899" },
};

const MobileAgentBubble: React.FC<AgentBubbleProps> = ({
  agent,
  name,
  text,
}) => {
  const { colors } = useTheme();
  const config = agentConfig[agent];

  return (
    <div
      style={{
        display: "flex",
        gap: 10,
        padding: "10px 14px",
        alignItems: "flex-start",
      }}
    >
      <div
        style={{
          width: 17,
          height: 17,
          borderRadius: "50%",
          backgroundColor: config.color,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 10,
          fontWeight: 600,
          color: "#FFFFFF",
          lineHeight: 1,
          flexShrink: 0,
          marginTop: 2,
        }}
      >
        {config.avatarChar}
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 3,
          minWidth: 0,
        }}
      >
        <span
          style={{
            fontSize: 12,
            fontWeight: 500,
            color: colors.text.secondary,
            lineHeight: 1.3,
          }}
        >
          {name}
        </span>
        <span
          style={{
            fontSize: 14,
            color: colors.text.primary,
            lineHeight: 1.5,
            wordBreak: "break-word",
          }}
        >
          {text}
        </span>
      </div>
    </div>
  );
};

export default MobileAgentBubble;
