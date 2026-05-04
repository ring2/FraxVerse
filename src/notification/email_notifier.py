"""
FraxVerse · 邮件推送服务（EmailNotifier）

通过 SMTP 发送邮件通知，支持 QQ邮箱/Gmail/企业邮箱等。
手机 QQ邮箱 APP 收到新邮件会弹出推送通知，类似微信消息体验。

配置方式（.env）：
    SMTP_HOST=smtp.qq.com
    SMTP_PORT=465
    SMTP_USER=your_email@qq.com
    SMTP_PASSWORD=your_authorization_code    # QQ邮箱授权码，非登录密码
    SMTP_TO=your_email@qq.com               # 收件人（可与发件人相同）
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from typing import Literal

from src.config import settings

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    邮件推送器。

    用法：
        notifier = EmailNotifier()
        notifier.send("止损触发", "600519 触发止损 @168.50", priority="high")

    当 SMTP 未配置时，send() 静默跳过并 log warning。
    """

    def __init__(self) -> None:
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._user = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD
        self._to = settings.SMTP_TO
        self._use_ssl = settings.SMTP_USE_SSL

        self._enabled = bool(self._user and self._password and self._to)

        if not self._enabled:
            logger.warning(
                "EmailNotifier 未配置（SMTP_USER / SMTP_PASSWORD / SMTP_TO 缺失），邮件推送已禁用"
            )

    def send(
        self,
        title: str,
        content: str,
        priority: Literal["low", "normal", "high", "urgent"] = "normal",
    ) -> bool:
        """发送邮件通知

        Args:
            title: 邮件标题
            content: 邮件正文（纯文本）
            priority: 优先级（urgent/high → 标题加 ⚠️ 标记）

        Returns:
            是否发送成功
        """
        if not self._enabled:
            logger.debug("EmailNotifier 未配置，跳过邮件发送")
            return False

        # 优先级标记
        prefix_map = {
            "urgent": "🚨 ",
            "high": "⚠️ ",
            "normal": "",
            "low": "[低优先级] ",
        }
        prefix = prefix_map.get(priority, "")
        subject = f"{prefix}{title} — FraxVerse 碎片宇宙"

        body = (
            f"{content}\n\n"
            f"——\n"
            f"FraxVerse 碎片宇宙 · 量化交易系统\n"
            f"{settings.APP_VERSION}"
        )

        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self._user
            msg["To"] = self._to

            ctx = ssl.create_default_context() if self._use_ssl else None

            if self._use_ssl:
                with smtplib.SMTP_SSL(self._host, self._port, context=ctx, timeout=10) as server:
                    server.login(self._user, self._password)
                    server.sendmail(self._user, [self._to], msg.as_string())
            else:
                with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                    if ctx:
                        server.starttls(context=ctx)
                    server.login(self._user, self._password)
                    server.sendmail(self._user, [self._to], msg.as_string())

            logger.info("邮件发送成功: %s → %s", subject, self._to)
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("邮件认证失败，请检查 SMTP_USER/SMTP_PASSWORD（QQ邮箱需使用授权码）")
            return False
        except smtplib.SMTPException as exc:
            logger.error("邮件发送失败: %s", exc)
            return False
        except OSError as exc:
            logger.error("邮件服务器连接失败: %s", exc)
            return False
        except Exception as exc:
            logger.error("邮件发送异常: %s", exc)
            return False


# 单例
_email_notifier: EmailNotifier | None = None


def get_email_notifier() -> EmailNotifier:
    """获取全局 EmailNotifier 实例"""
    global _email_notifier
    if _email_notifier is None:
        _email_notifier = EmailNotifier()
    return _email_notifier
