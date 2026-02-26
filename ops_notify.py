# -*- coding: utf-8 -*-
"""
築未科技 — 營運通知 & 自動化模組

功能：
  1. Email 通知（SMTP）— 訂閱到期、付款成功/失敗、配額告警
  2. 用量告警 — 配額 80%/100% 自動通知
  3. 自動續約檢查 — 定期掃描到期訂閱
  4. Webhook 事件通知 — 租戶可設定回調 URL

環境變數：
  SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM
  WEBHOOK_SECRET — Webhook 簽章密鑰
"""
import hashlib
import hmac
import json
import os
import smtplib
import time
import threading
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

# ── SMTP 設定 ──
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.environ.get("SMTP_FROM", "").strip() or SMTP_USER
SMTP_ENABLED = bool(SMTP_USER and SMTP_PASSWORD)

# Webhook
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "zhewei-webhook-secret").strip()

# 告警閾值
QUOTA_WARN_PCT = int(os.environ.get("QUOTA_WARN_PCT", "80"))
QUOTA_CRITICAL_PCT = int(os.environ.get("QUOTA_CRITICAL_PCT", "100"))


# ── Email 發送 ──

def send_email(to: str, subject: str, html_body: str, text_body: str = "") -> dict:
    """發送 Email（SMTP）。"""
    if not SMTP_ENABLED:
        return {"ok": False, "error": "SMTP 未設定（需設定 SMTP_USER + SMTP_PASSWORD）"}
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return {"ok": True, "to": to, "subject": subject}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Email 模板 ──

def _email_wrapper(title: str, content: str) -> str:
    """統一 Email HTML 模板。"""
    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;padding:32px;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <div style="display:inline-block;width:48px;height:48px;background:#0ea5e9;border-radius:12px;line-height:48px;font-size:24px;font-weight:bold;color:white;">築</div>
        <h2 style="margin:12px 0 0;color:white;">{title}</h2>
      </div>
      <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:24px;">
        {content}
      </div>
      <p style="text-align:center;margin-top:24px;font-size:12px;color:#64748b;">
        築未科技 AI 平台 · <a href="https://zhe-wei.net" style="color:#0ea5e9;">zhe-wei.net</a>
      </p>
    </div>"""


def notify_payment_success(email: str, username: str, plan: str, amount: int, order_id: str) -> dict:
    """付款成功通知。"""
    content = f"""
    <p style="color:#6ee7b7;font-size:18px;font-weight:bold;">✅ 付款成功</p>
    <p>親愛的 {username}，</p>
    <p>您的訂閱付款已成功處理：</p>
    <table style="width:100%;margin:16px 0;border-collapse:collapse;">
      <tr><td style="padding:8px 0;color:#94a3b8;">方案</td><td style="padding:8px 0;font-weight:bold;">{plan}</td></tr>
      <tr><td style="padding:8px 0;color:#94a3b8;">金額</td><td style="padding:8px 0;font-weight:bold;">NT${amount:,}</td></tr>
      <tr><td style="padding:8px 0;color:#94a3b8;">訂單號</td><td style="padding:8px 0;font-family:monospace;">{order_id}</td></tr>
    </table>
    <p>您的訂閱已啟用，感謝您的支持！</p>"""
    return send_email(email, f"[築未科技] 付款成功 — {plan}", _email_wrapper("付款成功", content))


def notify_payment_failed(email: str, username: str, plan: str, order_id: str, reason: str = "") -> dict:
    """付款失敗通知。"""
    content = f"""
    <p style="color:#fca5a5;font-size:18px;font-weight:bold;">❌ 付款失敗</p>
    <p>親愛的 {username}，</p>
    <p>您的訂閱付款未能成功處理：</p>
    <table style="width:100%;margin:16px 0;border-collapse:collapse;">
      <tr><td style="padding:8px 0;color:#94a3b8;">方案</td><td style="padding:8px 0;">{plan}</td></tr>
      <tr><td style="padding:8px 0;color:#94a3b8;">訂單號</td><td style="padding:8px 0;font-family:monospace;">{order_id}</td></tr>
      {f'<tr><td style="padding:8px 0;color:#94a3b8;">原因</td><td style="padding:8px 0;color:#fca5a5;">{reason}</td></tr>' if reason else ''}
    </table>
    <p>請檢查您的付款方式後重新嘗試。</p>"""
    return send_email(email, f"[築未科技] 付款失敗 — 請重新嘗試", _email_wrapper("付款失敗", content))


def notify_subscription_expiring(email: str, username: str, plan: str, days_left: int) -> dict:
    """訂閱即將到期通知。"""
    urgency = "⚠️" if days_left <= 3 else "📋"
    content = f"""
    <p style="color:#fde047;font-size:18px;font-weight:bold;">{urgency} 訂閱即將到期</p>
    <p>親愛的 {username}，</p>
    <p>您的 <strong>{plan}</strong> 訂閱將在 <strong style="color:#fde047;">{days_left} 天</strong>後到期。</p>
    <p>到期後將自動降級為免費版，部分功能將受限。</p>
    <p style="margin-top:16px;">
      <a href="https://zhe-wei.net/payment" style="display:inline-block;padding:12px 24px;background:#0ea5e9;color:white;border-radius:8px;text-decoration:none;font-weight:bold;">立即續約</a>
    </p>"""
    return send_email(email, f"[築未科技] 訂閱將在 {days_left} 天後到期", _email_wrapper("訂閱到期提醒", content))


def notify_quota_warning(email: str, username: str, used: int, limit: int, resource: str = "AI 呼叫") -> dict:
    """配額告警通知。"""
    pct = round(used / max(limit, 1) * 100)
    color = "#fca5a5" if pct >= 100 else "#fde047"
    content = f"""
    <p style="color:{color};font-size:18px;font-weight:bold;">{'🚨' if pct >= 100 else '⚠️'} {resource}配額{'已用完' if pct >= 100 else '即將用完'}</p>
    <p>親愛的 {username}，</p>
    <p>您的{resource}配額使用率已達 <strong style="color:{color};">{pct}%</strong>：</p>
    <div style="background:#0f172a;padding:12px;border-radius:8px;margin:16px 0;">
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <span>已使用: {used:,}</span><span>配額: {limit:,}</span>
      </div>
      <div style="background:#334155;border-radius:4px;height:8px;">
        <div style="background:{'#ef4444' if pct >= 100 else '#f59e0b'};border-radius:4px;height:8px;width:{min(100,pct)}%;"></div>
      </div>
    </div>
    <p>{'請升級方案以獲得更多配額。' if pct >= 100 else '請注意使用量。'}</p>"""
    return send_email(email, f"[築未科技] {resource}配額告警 ({pct}%)", _email_wrapper("配額告警", content))


# ── 用量告警檢查 ──

def check_quota_alerts() -> list[dict]:
    """掃描所有用戶的配額使用情況，觸發告警。"""
    alerts = []
    try:
        import usage_metering
        import db_postgres
        users = db_postgres.list_users("superadmin")
        for u in users:
            uid = u.get("id", "")
            email = u.get("email", "")
            username = u.get("username", "")
            plan = u.get("subscription_plan", "free")
            if not email or plan in ("unlimited",):
                continue
            # 取得用量
            try:
                quota_info = usage_metering.check_quota(uid)
                if not quota_info.get("allowed", True):
                    continue
                remaining = quota_info.get("remaining", {})
                quota = quota_info.get("quota", {})
                if isinstance(quota, dict) and quota.get("monthly_calls"):
                    usage_calls = quota_info.get("usage", {}).get("calls", 0)
                    limit_calls = quota["monthly_calls"]
                    pct = round(usage_calls / max(limit_calls, 1) * 100)
                    if pct >= QUOTA_CRITICAL_PCT:
                        result = notify_quota_warning(email, username, usage_calls, limit_calls)
                        alerts.append({"user": username, "pct": pct, "email_sent": result.get("ok", False)})
                    elif pct >= QUOTA_WARN_PCT:
                        result = notify_quota_warning(email, username, usage_calls, limit_calls)
                        alerts.append({"user": username, "pct": pct, "email_sent": result.get("ok", False)})
            except Exception:
                pass
    except Exception:
        pass
    return alerts


# ── 訂閱到期檢查 ──

def check_expiring_subscriptions(days_ahead: int = 7) -> list[dict]:
    """掃描即將到期的訂閱，發送提醒。"""
    results = []
    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, username, email, subscription_plan, subscription_expires_at
               FROM users
               WHERE subscription = 'active'
                 AND subscription_expires_at IS NOT NULL
                 AND subscription_expires_at BETWEEN NOW() AND NOW() + INTERVAL '%s days'
               ORDER BY subscription_expires_at""",
            (days_ahead,),
        )
        rows = cur.fetchall()
        cur.close()
        db_postgres._put_conn(conn)

        for row in rows:
            uid, username, email, plan, expires_at = row
            if not email:
                continue
            days_left = max(0, (expires_at - datetime.now()).days)
            result = notify_subscription_expiring(email, username, plan or "basic", days_left)
            results.append({
                "user": username, "plan": plan, "days_left": days_left,
                "email_sent": result.get("ok", False),
            })
    except Exception:
        pass
    return results


# ── Webhook 事件通知 ──

def send_webhook(url: str, event: str, payload: dict) -> dict:
    """發送 Webhook 通知到租戶指定的 URL。"""
    import urllib.request
    body = json.dumps({
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": payload,
    }, ensure_ascii=False).encode("utf-8")

    # 簽章
    signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

    try:
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Webhook-Signature", signature)
        req.add_header("X-Webhook-Event", event)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"ok": True, "status": resp.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def emit_event(event: str, payload: dict, tenant_slug: str = ""):
    """觸發事件 — 記錄日誌 + 發送 Webhook（如有設定）。"""
    # 記錄事件日誌
    try:
        from structured_logger import get_logger
        log = get_logger("events")
        log.info(f"Event: {event}", event=event, tenant=tenant_slug, **{k: v for k, v in payload.items() if isinstance(v, (str, int, float, bool))})
    except Exception:
        pass

    # 查詢租戶 Webhook URL
    if tenant_slug:
        try:
            import db_postgres
            t = db_postgres.get_tenant_by_slug(tenant_slug)
            if t and t.get("settings"):
                settings = t["settings"] if isinstance(t["settings"], dict) else json.loads(t["settings"] or "{}")
                webhook_url = settings.get("webhook_url", "")
                if webhook_url:
                    send_webhook(webhook_url, event, payload)
        except Exception:
            pass


# ── 定時任務（背景執行）──

_scheduler_running = False


def start_scheduler():
    """啟動背景定時任務（每小時檢查一次）。"""
    global _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True

    def _run():
        while _scheduler_running:
            try:
                now = datetime.now()
                # 每天早上 9 點檢查到期訂閱
                if now.hour == 9 and now.minute < 5:
                    results = check_expiring_subscriptions(7)
                    if results:
                        print(f"📧 訂閱到期提醒已發送: {len(results)} 封")

                # 每 4 小時檢查配額告警
                if now.hour % 4 == 0 and now.minute < 5:
                    alerts = check_quota_alerts()
                    if alerts:
                        print(f"⚠️ 配額告警已發送: {len(alerts)} 封")
            except Exception as e:
                print(f"⚠️ 定時任務錯誤: {e}")

            # 每 5 分鐘檢查一次
            time.sleep(300)

    t = threading.Thread(target=_run, daemon=True, name="ops-scheduler")
    t.start()
    print("⏰ 營運定時任務已啟動")


def stop_scheduler():
    """停止定時任務。"""
    global _scheduler_running
    _scheduler_running = False
