"""
Alert Sender for Factory 5 Production Monitor.

Supports:
  - Email via SMTP (Gmail, Outlook, or any SMTP server)
  - WhatsApp via Twilio API (requires free Twilio account + WhatsApp sandbox)

Usage from Streamlit:
    from utils.alert_sender import send_email_alert, send_whatsapp_alert, build_alert_message
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import datetime
import io


# ─────────────────────────────────────────────────────────────────────────────
# Message builder
# ─────────────────────────────────────────────────────────────────────────────

def build_alert_message(df, total, n_on, n_off, n_mnt, uptime,
                         cell_df=None, short=False) -> str:
    """
    Build a human-readable alert message from current dashboard state.
    short=True  → concise version for WhatsApp
    short=False → full version for email body
    """
    now  = datetime.datetime.now().strftime("%d %b %Y  %H:%M")
    pct  = lambda n: f"{round(n/total*100) if total else 0}%"

    # Machines currently OFF or in MAINTENANCE
    problem_machines = df[df["Status"].isin(["OFF", "MAINTENANCE"])]["Machine"].tolist()

    if short:
        lines = [
            f"🏭 *Factory 5 – Production Monitor*",
            f"📅 {now}",
            f"",
            f"✅ Running: {n_on}/{total}  ({pct(n_on)})",
            f"🔴 OFF: {n_off}   🟡 Maintenance: {n_mnt}",
            f"📈 Uptime: {uptime}%",
        ]
        if problem_machines:
            lines.append(f"")
            lines.append(f"⚠️ *Machines requiring attention:*")
            for m in problem_machines[:8]:
                status = df[df["Machine"] == m].iloc[0]["Status"]
                icon   = "🔴" if status == "OFF" else "🟡"
                lines.append(f"  {icon} {m}")
            if len(problem_machines) > 8:
                lines.append(f"  ... and {len(problem_machines)-8} more")
        lines.append(f"")
        lines.append(f"_Sent by Factory 5 Production Monitor_")
        return "\n".join(lines)

    else:
        # Full email body (HTML)
        rows = ""
        import re
        def base(n): return re.sub(r'\s*\d+\s*$', '', n).strip()
        seen = set()
        for _, row in df.iterrows():
            b = base(row["Machine"])
            if b in seen: continue
            seen.add(b)
            color = {"ON":"#22c55e","OFF":"#ef4444","MAINTENANCE":"#f59e0b"}.get(row["Status"],"#94a3b8")
            rows += (f'<tr><td style="padding:6px 10px;border-bottom:1px solid #1e2d45">{row["Machine"]}</td>'
                     f'<td style="padding:6px 10px;border-bottom:1px solid #1e2d45;color:{color};font-weight:bold">{row["Status"]}</td>'
                     f'<td style="padding:6px 10px;border-bottom:1px solid #1e2d45">{row.get("Zone","—")}</td>'
                     f'<td style="padding:6px 10px;border-bottom:1px solid #1e2d45">{row.get("Operator_Count","—")}</td></tr>')

        cell_rows = ""
        if cell_df is not None and not cell_df.empty:
            for _, r in cell_df.iterrows():
                cap = f"{int(r['Capacity']):,}" if hasattr(r['Capacity'],'__float__') and r['Capacity']==r['Capacity'] else "—"
                cell_rows += (f'<tr><td style="padding:6px 10px;border-bottom:1px solid #1e2d45">{r["Cell"]}</td>'
                              f'<td style="padding:6px 10px;border-bottom:1px solid #1e2d45;color:#3b82f6;font-weight:bold">{cap} pcs/day</td>'
                              f'<td style="padding:6px 10px;border-bottom:1px solid #1e2d45">{r.get("Top_Desc","—") or "—"}</td></tr>')

        html = f"""
<html><body style="background:#0a0e17;color:#e2e8f0;font-family:Arial,sans-serif;padding:20px">
<div style="max-width:700px;margin:auto">
  <div style="background:linear-gradient(90deg,#111827,#1a2235);border-top:3px solid #3b82f6;
              border-radius:12px;padding:24px 28px;margin-bottom:20px">
    <h2 style="color:#e2e8f0;margin:0 0 4px">🏭 Factory 5 — Production Status Report</h2>
    <p style="color:#64748b;margin:0;font-size:13px">Area 1 · Section 5 · {now}</p>
  </div>

  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">
    <div style="background:#111827;border-radius:10px;padding:16px;text-align:center">
      <div style="color:#64748b;font-size:11px;margin-bottom:6px">TOTAL MACHINES</div>
      <div style="color:#3b82f6;font-size:28px;font-weight:bold">{total}</div></div>
    <div style="background:#111827;border-radius:10px;padding:16px;text-align:center">
      <div style="color:#64748b;font-size:11px;margin-bottom:6px">RUNNING (ON)</div>
      <div style="color:#22c55e;font-size:28px;font-weight:bold">{n_on}</div></div>
    <div style="background:#111827;border-radius:10px;padding:16px;text-align:center">
      <div style="color:#64748b;font-size:11px;margin-bottom:6px">UPTIME RATE</div>
      <div style="color:{"#22c55e" if uptime>=70 else "#ef4444"};font-size:28px;font-weight:bold">{uptime}%</div></div>
  </div>

  {"<div style='background:#ef444420;border:1px solid #ef4444;border-radius:10px;padding:14px;margin-bottom:20px'><p style='color:#ef4444;font-weight:bold;margin:0 0 8px'>⚠️ Machines Requiring Attention:</p><ul style='margin:0;padding-left:20px;color:#e2e8f0'>" + "".join(f"<li>{m}</li>" for m in problem_machines) + "</ul></div>" if problem_machines else ""}

  <h3 style="color:#3b82f6;font-size:13px;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Machine Status</h3>
  <table style="width:100%;border-collapse:collapse;background:#111827;border-radius:10px;overflow:hidden;margin-bottom:20px">
    <thead><tr style="background:#0d1520">
      <th style="padding:8px 10px;color:#64748b;font-size:11px;text-align:left">Machine</th>
      <th style="padding:8px 10px;color:#64748b;font-size:11px">Status</th>
      <th style="padding:8px 10px;color:#64748b;font-size:11px">Zone</th>
      <th style="padding:8px 10px;color:#64748b;font-size:11px">Operators</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>

  {"<h3 style='color:#3b82f6;font-size:13px;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px'>Cell Capacity</h3><table style='width:100%;border-collapse:collapse;background:#111827;border-radius:10px;overflow:hidden;margin-bottom:20px'><thead><tr style='background:#0d1520'><th style='padding:8px 10px;color:#64748b;font-size:11px;text-align:left'>Cell</th><th style='padding:8px 10px;color:#64748b;font-size:11px'>Capacity</th><th style='padding:8px 10px;color:#64748b;font-size:11px;text-align:left'>Top Product</th></tr></thead><tbody>" + cell_rows + "</tbody></table>" if cell_rows else ""}

  <p style="color:#64748b;font-size:11px;text-align:center;border-top:1px solid #1e2d45;padding-top:14px;margin-top:20px">
    Sent automatically by Factory 5 Production Monitor · Production Planning Dept
  </p>
</div></body></html>"""
        return html


# ─────────────────────────────────────────────────────────────────────────────
# Email sender
# ─────────────────────────────────────────────────────────────────────────────

def send_email_alert(smtp_server: str, smtp_port: int,
                     sender_email: str, sender_password: str,
                     recipient_email: str,
                     subject: str, html_body: str,
                     pdf_bytes: bytes = None) -> tuple[bool, str]:
    """
    Send an HTML email alert with optional PDF attachment.
    Returns (success: bool, message: str)
    
    Common SMTP settings:
      Gmail:   smtp.gmail.com  port 587  (use App Password)
      Outlook: smtp.office365.com  port 587
      Yahoo:   smtp.mail.yahoo.com  port 587
    """
    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = sender_email
        msg["To"]      = recipient_email

        # HTML body
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt)

        # PDF attachment
        if pdf_bytes:
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_part.add_header("Content-Disposition", "attachment",
                                 filename=f"Factory5_Report_{now_str}.pdf")
            msg.attach(pdf_part)

        # Send
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_bytes())

        return True, "✅ Email sent successfully!"

    except smtplib.SMTPAuthenticationError:
        return False, ("❌ Authentication failed. For Gmail: use an App Password "
                       "(Google Account → Security → 2-Step → App Passwords)")
    except smtplib.SMTPConnectError:
        return False, f"❌ Cannot connect to {smtp_server}:{smtp_port}. Check server/port."
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp sender via Twilio
# ─────────────────────────────────────────────────────────────────────────────

def send_whatsapp_alert(account_sid: str, auth_token: str,
                        from_number: str, to_number: str,
                        message: str) -> tuple[bool, str]:
    """
    Send a WhatsApp message via Twilio.
    Returns (success: bool, message: str)

    Setup (free):
      1. Sign up at twilio.com (free trial gives $15 credit)
      2. Go to Messaging → Try it out → Send a WhatsApp message
      3. Follow sandbox setup (send join code from your WhatsApp)
      4. From number: whatsapp:+14155238886 (Twilio sandbox)
      5. Your Account SID and Auth Token are in the Twilio Console dashboard
    """
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            from_=f"whatsapp:{from_number}",
            to=f"whatsapp:{to_number}",
            body=message,
        )
        return True, f"✅ WhatsApp sent! Message SID: {msg.sid}"
    except ImportError:
        return False, "❌ Twilio not installed. Run: pip install twilio"
    except Exception as e:
        err = str(e)
        if "authenticate" in err.lower() or "401" in err:
            return False, "❌ Invalid Twilio credentials. Check Account SID and Auth Token."
        if "unverified" in err.lower() or "sandbox" in err.lower():
            return False, ("❌ Recipient not in Twilio sandbox. Ask them to send "
                           "'join <sandbox-word>' to the Twilio WhatsApp number first.")
        return False, f"❌ Twilio error: {err}"


# ─────────────────────────────────────────────────────────────────────────────
# SMTP presets helper
# ─────────────────────────────────────────────────────────────────────────────

SMTP_PRESETS = {
    "Gmail":   ("smtp.gmail.com",      587),
    "Outlook": ("smtp.office365.com",  587),
    "Yahoo":   ("smtp.mail.yahoo.com", 587),
    "Custom":  ("",                      0),
}
