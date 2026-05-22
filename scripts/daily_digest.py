"""Daily Crypto & AI email digest, delivered via SendGrid at 6:30 AM Pacific.

Pulls the most recent Brief from the DB, renders an inline-styled HTML email
(plus plain-text fallback), and ships it to ``DIGEST_EMAIL_TO`` from
``DIGEST_EMAIL_FROM`` using ``SENDGRID_API_KEY``.

Usage:
  backend/.venv/bin/python scripts/daily_digest.py            # send the email
  backend/.venv/bin/python scripts/daily_digest.py --preview  # print HTML, no send
  backend/.venv/bin/python scripts/daily_digest.py --test     # send right now

Exit codes:
  0  email sent (or preview rendered)
  1  no briefs in DB, or SendGrid request failed
  2  SENDGRID_API_KEY / FROM / TO not configured

Schema note: ``Brief.generation_metadata`` does not currently store sentiment,
top movers, or "one thing to watch" data. These sections are derived
heuristically from ``BriefTheme.conviction_score`` and ``categories`` so the
email always renders. When the synthesis pipeline starts emitting structured
sentiment/movers, this script should be updated to read them directly.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from db import SessionLocal  # noqa: E402
from models import Brief, BriefTheme, RawSignal, Source  # noqa: E402

PACIFIC = ZoneInfo("America/Los_Angeles")

# ─── colors ───────────────────────────────────────────────────────────────
BRAND = "#0052FF"
INK = "#0a0b0d"
MUTED = "#6b7280"
FAINT = "#9ca3af"
HAIRLINE = "#e5e7eb"
BG = "#ffffff"
BULL = "#10b981"
BEAR = "#ef4444"

FONT = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, '
    "Helvetica, Arial, sans-serif"
)


# ─── data load ────────────────────────────────────────────────────────────
@dataclass
class KeyEvent:
    text: str
    url: Optional[str]


@dataclass
class Mover:
    asset: str
    change_pct: Optional[float]
    why: str


@dataclass
class LoadedBrief:
    brief: Brief
    events: list[KeyEvent]
    sentiment_score: int  # 0..100 (50 = neutral)
    sentiment_label: str
    sentiment_blurb: str
    movers: list[Mover]
    watch_text: str
    watch_url: Optional[str]


def load_brief() -> Optional[LoadedBrief]:
    """Fetch the latest brief and derive every section the email needs."""
    session = SessionLocal()
    try:
        brief = (
            session.query(Brief).order_by(Brief.generated_at.desc()).first()
        )
        if not brief:
            return None

        rows = (
            session.query(
                BriefTheme, Source.name, RawSignal.title, RawSignal.url
            )
            .join(RawSignal, RawSignal.id == BriefTheme.primary_signal_id)
            .join(Source, Source.id == RawSignal.source_id)
            .filter(BriefTheme.brief_id == brief.id)
            .order_by(BriefTheme.display_order)
            .all()
        )

        events = [
            KeyEvent(text=theme.title, url=url) for theme, _, _, url in rows
        ]

        sentiment_score, sentiment_label, sentiment_blurb = _derive_sentiment(
            rows
        )
        movers = _derive_movers(rows)
        watch_text, watch_url = _derive_watch(rows, brief)

        return LoadedBrief(
            brief=brief,
            events=events[:6],
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            sentiment_blurb=sentiment_blurb,
            movers=movers,
            watch_text=watch_text,
            watch_url=watch_url,
        )
    finally:
        session.close()


def _derive_sentiment(rows) -> tuple[int, str, str]:
    """Approximate sentiment from average conviction score across themes.

    conviction_score is 1..5; map mean to a 0..100 bull index.
    Lacking explicit polarity, we treat high conviction as 'directional' and
    label it bullish/bearish based on category keywords; default neutral.
    """
    scores = [t.conviction_score for t, _, _, _ in rows if t.conviction_score]
    if not scores:
        return 50, "neutral", "No structured sentiment signal in today's brief."
    mean = sum(scores) / len(scores)
    bull_idx = int(round((mean / 5.0) * 100))

    bull_kw = {"bullish", "rally", "breakout", "approval", "inflows"}
    bear_kw = {"bearish", "sell-off", "outflow", "ban", "hack", "exploit"}
    bull_hits = bear_hits = 0
    for theme, _, _, _ in rows:
        cats = theme.categories or []
        body = (theme.body or "").lower()
        for k in bull_kw:
            if k in body or k in cats:
                bull_hits += 1
        for k in bear_kw:
            if k in body or k in cats:
                bear_hits += 1

    if bull_hits > bear_hits + 1:
        label = "bullish"
        blurb = (
            f"Conviction-weighted tone leans bullish "
            f"({bull_hits} bullish vs {bear_hits} bearish cues across "
            f"{len(rows)} themes)."
        )
        bull_idx = max(bull_idx, 60)
    elif bear_hits > bull_hits + 1:
        label = "bearish"
        blurb = (
            f"Conviction-weighted tone leans bearish "
            f"({bear_hits} bearish vs {bull_hits} bullish cues across "
            f"{len(rows)} themes)."
        )
        bull_idx = min(bull_idx, 40)
    else:
        label = "neutral"
        blurb = (
            f"Mixed tone — {bull_hits} bullish and {bear_hits} bearish cues "
            f"across {len(rows)} themes."
        )
    return bull_idx, label, blurb


def _derive_movers(rows) -> list[Mover]:
    """No price data on Brief/Theme yet — return empty list and let the renderer
    show a graceful 'no structured mover data' line.

    When the pipeline adds explicit mover rows, switch to reading them here.
    """
    return []


def _derive_watch(rows, brief: Brief) -> tuple[str, Optional[str]]:
    """Highest-conviction theme = 'one thing to watch'. Fall back to summary."""
    if not rows:
        return brief.summary[:280], None
    sorted_rows = sorted(
        rows,
        key=lambda r: (r[0].conviction_score or 0),
        reverse=True,
    )
    top_theme, _, _, url = sorted_rows[0]
    body = top_theme.body or top_theme.title
    return body, url


# ─── rendering helpers ────────────────────────────────────────────────────
def build_subject(loaded: LoadedBrief) -> str:
    d = loaded.brief.brief_date
    # brief_date is a date; format in Pacific to match the 6:30 AM cadence.
    return f"Daily Crypto & AI Debrief — {d.strftime('%A, %B %-d')}"


def _section_label(text: str) -> str:
    return (
        f'<div style="font-family:{FONT};font-size:11px;font-weight:700;'
        f"letter-spacing:1.5px;text-transform:uppercase;color:{BRAND};"
        f'margin:0 0 12px 0;">{escape(text)}</div>'
    )


def _section_wrap(inner_html: str) -> str:
    return (
        f'<tr><td style="padding:0 0 24px 0;'
        f'border-bottom:1px solid {HAIRLINE};">{inner_html}</td></tr>'
        f'<tr><td style="padding:24px 0 0 0;"></td></tr>'
    )


def render_header(loaded: LoadedBrief) -> str:
    b = loaded.brief
    date_str = b.brief_date.strftime("%A, %B %-d, %Y")
    return (
        f'<div style="font-family:{FONT};font-size:13px;font-weight:800;'
        f"letter-spacing:3px;text-transform:uppercase;color:{BRAND};"
        f'margin:0 0 8px 0;">MERKAVIAN INTELLIGENCE</div>'
        f'<div style="font-family:{FONT};font-size:14px;color:{MUTED};'
        f'margin:0 0 4px 0;">Daily Brief &middot; {escape(date_str)} '
        f'&middot; 6:30 AM PT</div>'
        f'<div style="font-family:{FONT};font-size:12px;color:{FAINT};'
        f'margin:0 0 0 0;">{b.input_signal_count} signals &middot; '
        f"{escape(b.model_used)}</div>"
    )


def render_tldr(loaded: LoadedBrief) -> str:
    return (
        _section_label("TL;DR")
        + f'<p style="font-family:{FONT};font-size:15px;line-height:1.55;'
        f'color:{INK};margin:0;">{escape(loaded.brief.summary)}</p>'
    )


def render_events(loaded: LoadedBrief) -> str:
    if not loaded.events:
        items_html = (
            f'<li style="font-family:{FONT};font-size:14px;color:{MUTED};">'
            f"No themes in this brief.</li>"
        )
    else:
        items = []
        for ev in loaded.events:
            text_html = escape(ev.text)
            if ev.url:
                inner = (
                    f'<a href="{escape(ev.url, quote=True)}" '
                    f'style="color:{BRAND};text-decoration:underline;">'
                    f"{text_html}</a>"
                )
            else:
                inner = text_html
            items.append(
                f'<li style="font-family:{FONT};font-size:14px;line-height:1.5;'
                f'color:{INK};margin:0 0 10px 0;">'
                f'<span style="margin-right:6px;">&#128204;</span>{inner}</li>'
            )
        items_html = "".join(items)
    return (
        _section_label("Key events today")
        + f'<ul style="margin:0;padding:0 0 0 4px;list-style:none;">'
        f"{items_html}</ul>"
    )


def render_sentiment(loaded: LoadedBrief) -> str:
    # Three-band bar. Width allocation:
    #   bull_pct from sentiment_score (0..100 where 100 = max bullish)
    #   bear_pct from (100 - sentiment_score)
    #   neutral fills the band around 50.
    s = max(0, min(100, loaded.sentiment_score))
    if s >= 60:
        bull_pct, neutral_pct, bear_pct = s, 100 - s, 0
    elif s <= 40:
        bull_pct, neutral_pct, bear_pct = 0, s, 100 - s
    else:
        # narrow neutral
        bull_pct = max(0, s - 40)
        bear_pct = max(0, 60 - s)
        neutral_pct = 100 - bull_pct - bear_pct

    def _cell(pct: int, color: str, label: str) -> str:
        if pct <= 0:
            return ""
        return (
            f'<td width="{pct}%" style="background:{color};height:10px;'
            f'font-size:0;line-height:0;" aria-label="{label}">&nbsp;</td>'
        )

    bar = (
        '<table role="presentation" width="100%" cellpadding="0" '
        'cellspacing="0" style="border-collapse:collapse;'
        'border-radius:6px;overflow:hidden;margin:0 0 10px 0;">'
        f"<tr>{_cell(bear_pct, BEAR, 'bearish')}"
        f"{_cell(neutral_pct, FAINT, 'neutral')}"
        f"{_cell(bull_pct, BULL, 'bullish')}</tr></table>"
    )
    legend = (
        f'<div style="font-family:{FONT};font-size:11px;color:{FAINT};'
        f'display:flex;justify-content:space-between;margin:0 0 12px 0;">'
        f"<span>Bearish</span><span>Neutral</span><span>Bullish</span></div>"
    )
    blurb = (
        f'<p style="font-family:{FONT};font-size:14px;line-height:1.5;'
        f'color:{INK};margin:0;">{escape(loaded.sentiment_blurb)}</p>'
    )
    return _section_label("Sentiment") + bar + legend + blurb


def render_movers(loaded: LoadedBrief) -> str:
    if not loaded.movers:
        return (
            _section_label("Top movers")
            + f'<p style="font-family:{FONT};font-size:13px;line-height:1.5;'
            f'color:{MUTED};margin:0;">No structured price-mover data in '
            f"today's brief. (Pipeline does not yet emit mover rows — "
            f"check the news/onchain feeds inline.)</p>"
        )
    head = (
        f'<tr>'
        f'<th align="left" style="font-family:{FONT};font-size:11px;'
        f'font-weight:700;color:{FAINT};text-transform:uppercase;'
        f'padding:6px 8px;border-bottom:1px solid {HAIRLINE};">Asset</th>'
        f'<th align="right" style="font-family:{FONT};font-size:11px;'
        f'font-weight:700;color:{FAINT};text-transform:uppercase;'
        f'padding:6px 8px;border-bottom:1px solid {HAIRLINE};">Change</th>'
        f'<th align="left" style="font-family:{FONT};font-size:11px;'
        f'font-weight:700;color:{FAINT};text-transform:uppercase;'
        f'padding:6px 8px;border-bottom:1px solid {HAIRLINE};">Why</th>'
        f"</tr>"
    )
    rows = []
    for m in loaded.movers:
        change_str = (
            f"{m.change_pct:+.1f}%" if m.change_pct is not None else "—"
        )
        color = (
            BULL
            if (m.change_pct or 0) > 0
            else BEAR
            if (m.change_pct or 0) < 0
            else INK
        )
        rows.append(
            f"<tr>"
            f'<td style="font-family:{FONT};font-size:14px;color:{INK};'
            f'padding:8px;">{escape(m.asset)}</td>'
            f'<td align="right" style="font-family:{FONT};font-size:14px;'
            f'color:{color};font-weight:600;padding:8px;">{change_str}</td>'
            f'<td style="font-family:{FONT};font-size:13px;color:{MUTED};'
            f'padding:8px;">{escape(m.why)}</td>'
            f"</tr>"
        )
    table = (
        '<table role="presentation" width="100%" cellpadding="0" '
        'cellspacing="0" style="border-collapse:collapse;">'
        f"{head}{''.join(rows)}</table>"
    )
    return _section_label("Top movers") + table


def render_watch(loaded: LoadedBrief) -> str:
    body = escape(loaded.watch_text)
    if loaded.watch_url:
        body += (
            f' <a href="{escape(loaded.watch_url, quote=True)}" '
            f'style="color:{BRAND};text-decoration:underline;">[source]</a>'
        )
    return (
        _section_label("One thing to watch")
        + f'<p style="font-family:{FONT};font-size:14px;line-height:1.55;'
        f'color:{INK};margin:0;">{body}</p>'
    )


def render_footer(from_addr: str) -> str:
    unsubscribe = (
        f'<a href="mailto:{escape(from_addr, quote=True)}'
        f'?subject=unsubscribe" '
        f'style="color:{MUTED};text-decoration:underline;">Unsubscribe</a>'
    )
    return (
        f'<tr><td style="padding:8px 0 0 0;font-family:{FONT};font-size:11px;'
        f'color:{FAINT};text-align:center;">Merkavian Intelligence '
        f"&middot; {unsubscribe}</td></tr>"
    )


def render_html(loaded: LoadedBrief, from_addr: str) -> str:
    sections = [
        render_header(loaded),
        render_tldr(loaded),
        render_events(loaded),
        render_sentiment(loaded),
        render_movers(loaded),
        render_watch(loaded),
    ]
    body_rows = "".join(
        _section_wrap(s) if i > 0 else _section_wrap(s)
        for i, s in enumerate(sections)
    )
    # Remove trailing divider/spacer of the last section by closing cleanly.
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Daily Crypto &amp; AI Debrief</title></head>"
        f'<body style="margin:0;padding:0;background:{BG};">'
        '<table role="presentation" width="100%" cellpadding="0" '
        f'cellspacing="0" style="background:{BG};">'
        '<tr><td align="center" style="padding:32px 16px;">'
        '<table role="presentation" width="600" cellpadding="0" '
        'cellspacing="0" style="max-width:600px;width:100%;'
        f'background:{BG};">'
        f"{body_rows}"
        f"{render_footer(from_addr)}"
        "</table></td></tr></table></body></html>"
    )


def render_text(loaded: LoadedBrief) -> str:
    b = loaded.brief
    lines: list[str] = []
    lines.append("MERKAVIAN INTELLIGENCE")
    lines.append(
        f"Daily Brief · {b.brief_date.strftime('%A, %B %-d, %Y')} · 6:30 AM PT"
    )
    lines.append(f"{b.input_signal_count} signals · {b.model_used}")
    lines.append("")
    lines.append("TL;DR")
    lines.append(b.summary)
    lines.append("")
    lines.append("KEY EVENTS TODAY")
    if loaded.events:
        for ev in loaded.events:
            line = f"  - {ev.text}"
            if ev.url:
                line += f"\n    {ev.url}"
            lines.append(line)
    else:
        lines.append("  (no themes)")
    lines.append("")
    lines.append("SENTIMENT")
    lines.append(
        f"  {loaded.sentiment_label.upper()} "
        f"(bull index {loaded.sentiment_score}/100)"
    )
    lines.append(f"  {loaded.sentiment_blurb}")
    lines.append("")
    lines.append("TOP MOVERS")
    if loaded.movers:
        for m in loaded.movers:
            change = (
                f"{m.change_pct:+.1f}%" if m.change_pct is not None else "—"
            )
            lines.append(f"  {m.asset:<8} {change:<8} {m.why}")
    else:
        lines.append("  (no structured mover data)")
    lines.append("")
    lines.append("ONE THING TO WATCH")
    lines.append(f"  {loaded.watch_text}")
    if loaded.watch_url:
        lines.append(f"  {loaded.watch_url}")
    lines.append("")
    lines.append("--")
    lines.append("Merkavian Intelligence")
    return "\n".join(lines)


# ─── send ────────────────────────────────────────────────────────────────
def send(
    html: str,
    text: str,
    subject: str,
    *,
    api_key: str,
    to_addr: str,
    from_addr: str,
) -> tuple[int, str]:
    """Ship the email via SendGrid. Returns (status_code, body)."""
    # Lazy import so --preview works on machines without sendgrid installed yet.
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Header

    msg = Mail(
        from_email=from_addr,
        to_emails=to_addr,
        subject=subject,
        plain_text_content=text,
        html_content=html,
    )
    msg.header = Header(
        "List-Unsubscribe", f"<mailto:{from_addr}?subject=unsubscribe>"
    )
    client = SendGridAPIClient(api_key)
    resp = client.send(msg)
    body = ""
    try:
        body = resp.body.decode("utf-8") if isinstance(resp.body, bytes) else str(resp.body)
    except Exception:
        body = ""
    return resp.status_code, body


# ─── main ────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Daily crypto/AI email digest.")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print rendered HTML to stdout and exit. Does not send.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send the email right now using the latest brief.",
    )
    args = parser.parse_args()

    loaded = load_brief()
    if not loaded:
        print(
            "error: no briefs in the database — run the synthesize-brief "
            "skill first",
            file=sys.stderr,
        )
        return 1

    from_addr = os.environ.get("DIGEST_EMAIL_FROM", "").strip()
    to_addr = os.environ.get("DIGEST_EMAIL_TO", "").strip()
    api_key = os.environ.get("SENDGRID_API_KEY", "").strip()

    html = render_html(loaded, from_addr or "digest@example.invalid")
    text = render_text(loaded)
    subject = build_subject(loaded)

    if args.preview:
        sys.stdout.write(html)
        if not html.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    # send / cron path
    missing = []
    if not api_key:
        missing.append("SENDGRID_API_KEY")
    if not to_addr:
        missing.append("DIGEST_EMAIL_TO")
    if not from_addr:
        missing.append("DIGEST_EMAIL_FROM")
    if missing:
        print(
            "error: missing required env var(s): "
            + ", ".join(missing)
            + f"\n       set them in {BACKEND_DIR / '.env'} and re-run "
            f"`python3 scripts/daily_digest.py --test`.",
            file=sys.stderr,
        )
        return 2

    try:
        status, body = send(
            html,
            text,
            subject,
            api_key=api_key,
            to_addr=to_addr,
            from_addr=from_addr,
        )
    except Exception as exc:
        print(f"error: SendGrid send failed: {exc}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if 200 <= status < 300:
        print(f"[{now}] digest sent  status={status}  to={to_addr}")
        return 0
    print(
        f"[{now}] digest FAILED status={status}  to={to_addr}\n{body}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
