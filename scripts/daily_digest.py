"""Daily Crypto & AI email digest, delivered via Resend at 7:10 AM Pacific.

Pulls the most recent Brief from the DB, classifies each theme into CRYPTO /
AI / OTHER by its primary source, renders an inline-styled HTML email (plus
plain-text fallback), and ships it via Resend.

Recipients = ``DIGEST_EMAIL_TO`` (a comma-separated baseline list, e.g.
``jacksongeiger@berkeley.edu``) plus every active row in the ``subscribers``
table (unsubscribed_at IS NULL). Uses ``RESEND_API_KEY`` and ``DIGEST_EMAIL_FROM``.

Usage:
  backend/.venv/bin/python scripts/daily_digest.py            # send the email
  backend/.venv/bin/python scripts/daily_digest.py --preview  # print HTML, no send
  backend/.venv/bin/python scripts/daily_digest.py --test     # send right now

Exit codes:
  0  email sent (or preview rendered)
  1  no briefs in DB, or Resend request failed
  2  RESEND_API_KEY / FROM / TO not configured

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
from models import Brief, BriefTheme, RawSignal, Source, Subscriber  # noqa: E402

PACIFIC = ZoneInfo("America/Los_Angeles")

# ─── headline classification ──────────────────────────────────────────────
# Source.name -> bucket. Sources not listed are bucketed by source_type:
#   on_chain / prediction_market / crypto_price -> "crypto"
#   macro / unknown                              -> "other"
AI_SOURCE_NAMES = {
    "OpenAI", "Google AI", "TechCrunch AI", "The Verge AI", "VentureBeat AI",
}
CRYPTO_SOURCE_NAMES = {
    "CoinDesk", "The Block", "Decrypt", "Bankless",
}


def classify_source(source_name: str, source_type: str) -> str:
    if source_name in AI_SOURCE_NAMES:
        return "ai"
    if source_name in CRYPTO_SOURCE_NAMES:
        return "crypto"
    if source_type in ("on_chain", "prediction_market", "crypto_price"):
        return "crypto"
    return "other"


# Public dashboard URL surfaced in the footer (env-overridable).
def dashboard_url() -> str:
    return os.environ.get(
        "DIGEST_DASHBOARD_URL", "https://192-18-128-170.nip.io/dashboard"
    )

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
    source_name: str = ""
    bucket: str = "other"  # "crypto" | "ai" | "other"


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
                BriefTheme,
                Source.name,
                Source.source_type,
                RawSignal.title,
                RawSignal.url,
            )
            .join(RawSignal, RawSignal.id == BriefTheme.primary_signal_id)
            .join(Source, Source.id == RawSignal.source_id)
            .filter(BriefTheme.brief_id == brief.id)
            .order_by(BriefTheme.display_order)
            .all()
        )

        # Build classified events. Source.source_type is the SourceType enum;
        # cast to str via .value so the classifier doesn't depend on SQLAlchemy
        # internals.
        events: list[KeyEvent] = []
        for theme, src_name, src_type, _title, url in rows:
            stype = src_type.value if hasattr(src_type, "value") else str(src_type)
            events.append(
                KeyEvent(
                    text=theme.title,
                    url=url,
                    source_name=src_name or "",
                    bucket=classify_source(src_name or "", stype),
                )
            )

        # _derive_sentiment expects 4-tuples; remap to keep its contract.
        sentiment_rows = [
            (theme, name, title, url) for theme, name, _st, title, url in rows
        ]
        sentiment_score, sentiment_label, sentiment_blurb = _derive_sentiment(
            sentiment_rows
        )
        movers = _derive_movers(sentiment_rows)
        watch_text, watch_url = _derive_watch(sentiment_rows, brief)

        return LoadedBrief(
            brief=brief,
            events=events[:12],  # widened from 6 — sections split needs more
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
        f'&middot; 7:10 AM PT</div>'
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


def _render_event_item(ev: KeyEvent) -> str:
    text_html = escape(ev.text)
    if ev.url:
        inner = (
            f'<a href="{escape(ev.url, quote=True)}" '
            f'style="color:{BRAND};text-decoration:underline;">'
            f"{text_html}</a>"
        )
    else:
        inner = text_html
    src = escape(ev.source_name) if ev.source_name else ""
    src_html = (
        f'<span style="font-family:{FONT};font-size:11px;color:{FAINT};'
        f'margin-left:6px;">&middot; {src}</span>'
        if src else ""
    )
    return (
        f'<li style="font-family:{FONT};font-size:14px;line-height:1.5;'
        f'color:{INK};margin:0 0 10px 0;">'
        f'<span style="margin-right:6px;">&#128204;</span>{inner}{src_html}</li>'
    )


def _render_events_bucket(label: str, events: list[KeyEvent]) -> str:
    if not events:
        items_html = (
            f'<li style="font-family:{FONT};font-size:13px;color:{MUTED};'
            f'list-style:none;">No notable items today.</li>'
        )
    else:
        items_html = "".join(_render_event_item(ev) for ev in events)
    return (
        _section_label(label)
        + f'<ul style="margin:0;padding:0 0 0 4px;list-style:none;">'
        f"{items_html}</ul>"
    )


def render_crypto_section(loaded: LoadedBrief) -> str:
    items = [ev for ev in loaded.events if ev.bucket == "crypto"]
    return _render_events_bucket("Today's headlines &mdash; Crypto", items)


def render_ai_section(loaded: LoadedBrief) -> str:
    items = [ev for ev in loaded.events if ev.bucket == "ai"]
    return _render_events_bucket("Today's headlines &mdash; AI", items)


def render_other_section(loaded: LoadedBrief) -> str:
    items = [ev for ev in loaded.events if ev.bucket == "other"]
    return _render_events_bucket("Other signals", items)


# Kept for backward compatibility / one-shot debugging; not used in render_html.
def render_events(loaded: LoadedBrief) -> str:
    return _render_events_bucket("Key events today", loaded.events)


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
    label_color = (
        BULL if loaded.sentiment_label == "bullish"
        else BEAR if loaded.sentiment_label == "bearish"
        else FAINT
    )
    score_line = (
        f'<div style="font-family:{FONT};margin:0 0 8px 0;">'
        f'<span style="font-size:24px;font-weight:700;color:{INK};">'
        f"{s} / 100</span>"
        f'<span style="font-size:12px;font-weight:600;color:{label_color};'
        f'text-transform:uppercase;letter-spacing:0.15em;margin-left:10px;">'
        f"{escape(loaded.sentiment_label)}</span></div>"
    )
    return _section_label("Market sentiment") + score_line + bar + legend + blurb


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


def render_dashboard_cta() -> str:
    url = dashboard_url()
    return (
        f'<div style="text-align:center;padding:8px 0 0 0;">'
        f'<a href="{escape(url, quote=True)}" '
        f'style="display:inline-block;background:{BRAND};color:#ffffff;'
        f'font-family:{FONT};font-size:14px;font-weight:600;'
        f'text-decoration:none;padding:12px 24px;border-radius:6px;'
        f'letter-spacing:0.02em;">View full dashboard &rarr;</a></div>'
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
        render_crypto_section(loaded),
        render_ai_section(loaded),
        render_other_section(loaded),
        render_sentiment(loaded),
        render_dashboard_cta(),
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
        f"Daily Brief · {b.brief_date.strftime('%A, %B %-d, %Y')} · 7:10 AM PT"
    )
    lines.append(f"{b.input_signal_count} signals · {b.model_used}")
    lines.append("")
    lines.append("TL;DR")
    lines.append(b.summary)
    lines.append("")

    def _bucket_text(label: str, bucket: str) -> None:
        items = [ev for ev in loaded.events if ev.bucket == bucket]
        lines.append(label)
        if not items:
            lines.append("  (no notable items today)")
        else:
            for ev in items:
                tag = f" [{ev.source_name}]" if ev.source_name else ""
                lines.append(f"  - {ev.text}{tag}")
                if ev.url:
                    lines.append(f"    {ev.url}")
        lines.append("")

    _bucket_text("HEADLINES — CRYPTO", "crypto")
    _bucket_text("HEADLINES — AI", "ai")
    _bucket_text("OTHER SIGNALS", "other")

    lines.append("MARKET SENTIMENT")
    lines.append(
        f"  {loaded.sentiment_score}/100 · {loaded.sentiment_label.upper()}"
    )
    lines.append(f"  {loaded.sentiment_blurb}")
    lines.append("")
    lines.append(f"View full dashboard: {dashboard_url()}")
    lines.append("")
    lines.append("--")
    lines.append("Merkavian Intelligence")
    return "\n".join(lines)


# ─── recipient list ──────────────────────────────────────────────────────
def build_recipients(baseline: str) -> list[str]:
    """Combine the baseline DIGEST_EMAIL_TO list with active subscribers.

    Baseline is a comma-separated env value; subscribers come from the DB
    (unsubscribed_at IS NULL). De-duplicated case-insensitively, baseline
    preserved first so it always ships even if the DB is unreachable.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in baseline.split(","):
        addr = raw.strip()
        key = addr.lower()
        if addr and key not in seen:
            seen.add(key)
            out.append(addr)
    try:
        session = SessionLocal()
        try:
            for (email,) in session.query(Subscriber.email).filter(
                Subscriber.unsubscribed_at.is_(None)
            ):
                key = (email or "").strip().lower()
                if email and key not in seen:
                    seen.add(key)
                    out.append(email)
        finally:
            session.close()
    except Exception as exc:
        # Don't let DB issues block the email to the baseline.
        print(
            f"warning: failed to load subscribers, sending to baseline only: {exc}",
            file=sys.stderr,
        )
    return out


# ─── send ────────────────────────────────────────────────────────────────
def send(
    html: str,
    text: str,
    subject: str,
    *,
    api_key: str,
    to_addrs: list[str],
    from_addr: str,
) -> tuple[int, str]:
    """Ship the email via Resend. Returns (status_code, body).

    Resend accepts a list in `to`; recipients see only their own address
    when no BCC is used. Free tier handles small lists fine; for >50
    recipients we should batch.
    """
    # Lazy import so --preview works on machines without resend installed yet.
    import resend  # type: ignore[import-not-found]

    resend.api_key = api_key
    params: dict = {
        "from": from_addr,
        "to": to_addrs,
        "subject": subject,
        "html": html,
        "text": text,
        "headers": {
            "List-Unsubscribe": f"<mailto:{from_addr}?subject=unsubscribe>",
        },
    }
    try:
        resp = resend.Emails.send(params)
    except Exception as exc:
        return 0, f"resend exception: {exc}"
    # Successful Resend send returns {"id": "..."}; treat as 200.
    msg_id = resp.get("id") if isinstance(resp, dict) else None
    if msg_id:
        return 200, f'{{"id":"{msg_id}"}}'
    return 0, f"resend non-id response: {resp!r}"


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
    to_baseline = os.environ.get("DIGEST_EMAIL_TO", "").strip()
    api_key = os.environ.get("RESEND_API_KEY", "").strip()

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
        missing.append("RESEND_API_KEY")
    if not to_baseline:
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

    recipients = build_recipients(to_baseline)
    if not recipients:
        print("error: no recipients resolved", file=sys.stderr)
        return 2

    try:
        status, body = send(
            html,
            text,
            subject,
            api_key=api_key,
            to_addrs=recipients,
            from_addr=from_addr,
        )
    except Exception as exc:
        print(f"error: Resend send failed: {exc}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    to_summary = (
        f"{recipients[0]}+{len(recipients) - 1}"
        if len(recipients) > 1
        else recipients[0]
    )
    if 200 <= status < 300:
        print(f"[{now}] digest sent  status={status}  to={to_summary}  body={body}")
        return 0
    print(
        f"[{now}] digest FAILED status={status}  to={to_summary}\n{body}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
