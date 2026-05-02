// FraxVerse EmptyState 通用空状态组件
// 替代零散的「暂无数据」文字，统一视觉风格

import React from "react";
import { Button } from "antd";
import { colors } from '../../theme/colors';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
  loading?: boolean;
}

const DefaultIcon = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <circle cx="32" cy="32" r="28" stroke={colors.border} strokeWidth="2" strokeDasharray="4 4" fill="none" />
    <path d="M22 28l10 10 10-10" stroke={colors.dimmed} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="32" cy="32" r="4" fill={colors.nebula} opacity="0.6" />
  </svg>
);

function EmptyState({ icon, title, description, actionText, onAction, loading }: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "64px 24px",
        minHeight: 200,
        textAlign: "center",
        opacity: loading ? 0.5 : 1,
        transition: "opacity 0.3s",
      }}
    >
      <div style={{ marginBottom: 16, opacity: 0.6 }}>
        {icon || <DefaultIcon />}
      </div>
      <div style={{ fontSize: 16, fontWeight: 500, color: colors.text, marginBottom: description ? 8 : 0 }}>
        {title}
      </div>
      {description && (
        <div style={{ fontSize: 13, color: colors.dimmed, maxWidth: 320, lineHeight: 1.6 }}>
          {description}
        </div>
      )}
      {actionText && onAction && (
        <Button
          type="primary"
          size="middle"
          onClick={onAction}
          loading={loading}
          style={{ marginTop: 20 }}
        >
          {actionText}
        </Button>
      )}
    </div>
  );
}

export default EmptyState;
