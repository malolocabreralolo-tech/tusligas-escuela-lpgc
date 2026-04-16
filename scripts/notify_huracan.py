#!/usr/bin/env python3
"""
Monitors Huracán matches from tusligascanarias.mygol.es API.
Compares with previous snapshot and sends Telegram notifications on changes.

Defaults to monitoring miniprebenjamín only, but can also watch prebenjamín
through environment variables.
"""

import html as htmllib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
BASE = "https://tusligascanarias.mygol.es/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

HURACAN_MINI_ID = 1159  # Tournament 85
HURACAN_PRE_ID = 1112   # Tournament 87

WATCH_MINI = os.getenv("WATCH_HURACAN_MINI", "true").lower() in ("1", "true", "yes", "on")
WATCH_PRE = os.getenv("WATCH_HURACAN_PRE", "false").lower() in ("1", "true", "yes", "on")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()


def _parse_chat_id(value):
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return value


CHAT_IDS = [
    cid for cid in (_parse_chat_id(x) for x in os.getenv("TELEGRAM_CHAT_IDS", "1556920272").split(","))
    if cid is not None
]

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
SNAPSHOT_FILE = SNAPSHOT_DIR / "huracan_matches.json"
STATUS_LABELS = {
    1: "pendiente",
    5: "programado",
    10: "descansa",
    20: "finalizado",
}


# ── Helpers ───────────────────────────────────────────────────────────────
BYE_NAME = "Descansa"


def fetch(url, retries=3, backoff=2.0):
    """GET JSON with retries on transient failures."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise last_err


def esc(s):
    """Escape text for Telegram HTML parse_mode."""
    return htmllib.escape(str(s), quote=False)


def fmt_date(s):
    if not s or s.startswith("0001") or s.startswith("1901"):
        return ""
    return s[:16]


def fmt_date_human(iso):
    if not iso:
        return "Sin fecha"
    try:
        dt = datetime.fromisoformat(iso)
        days = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
        return f"{days[dt.weekday()]} {dt.strftime('%d/%m %H:%M')}"
    except Exception:
        return iso


def status_label(value):
    return STATUS_LABELS.get(value, str(value))


def send_telegram(text):
    if not TELEGRAM_TOKEN:
        print("WARN: TELEGRAM_TOKEN missing — notification skipped.", file=sys.stderr)
        return

    chunks = []
    if len(text) <= 4000:
        chunks = [text]
    else:
        lines = text.split("\n")
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) + 1 > 4000:
                chunks.append(chunk)
                chunk = line
            else:
                chunk = chunk + "\n" + line if chunk else line
        if chunk:
            chunks.append(chunk)

    for chat_id in CHAT_IDS:
        for chunk in chunks:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = json.dumps({
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
            })
            try:
                urllib.request.urlopen(req, timeout=15)
            except Exception as e:
                print(f"Error sending to {chat_id}: {e}", file=sys.stderr)


# ── Extract Huracán matches ──────────────────────────────────────────────
def extract_huracan_matches(jornadas, team_id, teams_data):
    team_names = {}
    for t in teams_data.get("teams", []):
        team_names[t["id"]] = t["name"]

    matches = []
    for jornada in jornadas:
        jname = jornada.get("name", "")
        for m in jornada.get("matches", []):
            home = m.get("idHomeTeam") or -1
            away = m.get("idVisitorTeam") or -1
            if home == team_id or away == team_id:
                matches.append({
                    "jornada": jname,
                    "home": home,
                    "home_name": BYE_NAME if home == -1 else team_names.get(home, f"#{home}"),
                    "away": away,
                    "away_name": BYE_NAME if away == -1 else team_names.get(away, f"#{away}"),
                    "date": fmt_date(m.get("startTime", "")),
                    "field": (m.get("field") or {}).get("name", "") or "",
                    "status": m.get("status", 5),
                    "home_score": m.get("homeScore"),
                    "away_score": m.get("visitorScore"),
                })
    return matches


# ── Diff logic ────────────────────────────────────────────────────────────
def match_key(m):
    return f"{m['jornada']}_{m['home']}_{m['away']}"


def diff_matches(old_list, new_list):
    old_map = {match_key(m): m for m in old_list}
    new_map = {match_key(m): m for m in new_list}
    changes = []

    for key, m in new_map.items():
        if key not in old_map:
            changes.append({"type": "new", "match": m})
            continue

        old = old_map[key]
        diffs = []

        if old["date"] != m["date"]:
            diffs.append(f"Fecha: {fmt_date_human(old['date'])} → {fmt_date_human(m['date'])}")

        if old["field"] != m["field"]:
            old_f = old["field"] or "Sin campo"
            new_f = m["field"] or "Sin campo"
            diffs.append(f"Campo: {old_f} → {new_f}")

        if old["status"] != m["status"]:
            diffs.append(f"Estado: {status_label(old['status'])} → {status_label(m['status'])}")

        if old.get("home_score") != m.get("home_score") or old.get("away_score") != m.get("away_score"):
            hs = m.get("home_score")
            vs = m.get("away_score")
            if hs is not None and vs is not None:
                diffs.append(f"Resultado: {m['home_name']} {hs} - {vs} {m['away_name']}")

        if diffs:
            changes.append({"type": "changed", "match": m, "diffs": diffs})

    for key, m in old_map.items():
        if key not in new_map:
            changes.append({"type": "removed", "match": m})

    return changes


# ── Build notification message ────────────────────────────────────────────
def build_section(title, changes):
    lines = [f"<b>{esc(title)}</b>"]
    for c in changes:
        m = c["match"]
        fixture = f"{esc(m['home_name'])} vs {esc(m['away_name'])}"
        jornada = esc(m["jornada"])

        if c["type"] == "new":
            lines.append(f"\n• Nuevo partido · {jornada}")
            lines.append(f"  {fixture}")
            lines.append(f"  {esc(fmt_date_human(m['date']))}")
            if m["field"]:
                lines.append(f"  {esc(m['field'])}")
        elif c["type"] == "changed":
            lines.append(f"\n• Cambio detectado · {jornada}")
            lines.append(f"  {fixture}")
            for d in c["diffs"]:
                lines.append(f"  {esc(d)}")
        elif c["type"] == "removed":
            lines.append(f"\n• Partido eliminado o no visible")
            lines.append(f"  {fixture}")

    return lines


def build_message(mini_changes, pre_changes):
    lines = ["<b>Alerta Huracán</b>"]
    if mini_changes:
        lines.extend(build_section("MINIPREBENJAMÍN", mini_changes))
    if pre_changes:
        if len(lines) > 1:
            lines.append("")
        lines.extend(build_section("PREBENJAMÍN", pre_changes))
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(f"[{datetime.now().isoformat()}] Checking Huracán matches...")
    print(f"  Telegram token: {'set' if TELEGRAM_TOKEN else 'MISSING'} | chat ids: {len(CHAT_IDS)}")

    if "--test" in sys.argv:
        print("  Test mode: sending verification message…")
        send_telegram(
            "<b>Alerta Huracán · prueba</b>\nMensaje de verificación del bot. "
            "Si ves esto, las notificaciones funcionan."
        )
        return

    try:
        old = {"mini": [], "pre": []}
        if SNAPSHOT_FILE.exists():
            try:
                old = json.loads(SNAPSHOT_FILE.read_text("utf-8"))
            except Exception:
                pass

        current = {"mini": [], "pre": [], "updated": datetime.now().isoformat()}
        mini_changes = []
        pre_changes = []

        if WATCH_MINI:
            mini_raw = fetch(f"{BASE}/matches/fortournament/85")
            mini_t = fetch(f"{BASE}/tournaments/85")
            current["mini"] = extract_huracan_matches(mini_raw, HURACAN_MINI_ID, mini_t)
            mini_changes = diff_matches(old.get("mini", []), current["mini"])

        if WATCH_PRE:
            pre_raw = fetch(f"{BASE}/matches/fortournament/87")
            pre_t = fetch(f"{BASE}/tournaments/87")
            current["pre"] = extract_huracan_matches(pre_raw, HURACAN_PRE_ID, pre_t)
            pre_changes = diff_matches(old.get("pre", []), current["pre"])

    except Exception as e:
        print(f"ERROR fetching API: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Mini watched: {WATCH_MINI} | Pre watched: {WATCH_PRE}")
    print(f"  Mini changes: {len(mini_changes)} | Pre changes: {len(pre_changes)}")

    total = len(mini_changes) + len(pre_changes)
    if total > 0:
        msg = build_message(mini_changes, pre_changes)
        print(f"  {total} changes detected! Sending notification...")
        print(msg)
        send_telegram(msg)
    else:
        print("  No changes.")

    SNAPSHOT_DIR.mkdir(exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), "utf-8")
    print("  Snapshot saved.")


if __name__ == "__main__":
    main()
