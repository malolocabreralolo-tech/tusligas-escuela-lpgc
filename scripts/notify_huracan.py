#!/usr/bin/env python3
"""
Monitors Huracán matches (mini + pre) from tusligascanarias.mygol.es API.
Compares with previous snapshot and sends Telegram notifications on changes.

Huracán team IDs:
  - 1159: Miniprebenjamín (tournament 85)
  - 1112: Prebenjamín (tournament 87)
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
BASE = "https://tusligascanarias.mygol.es/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

TELEGRAM_TOKEN = "8752766989:AAFWZKVH-cnOPudAsUghHIgsKh-IV47NHLA"
CHAT_IDS = [1556920272]

HURACAN_MINI_ID = 1159  # Tournament 85
HURACAN_PRE_ID = 1112   # Tournament 87

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
SNAPSHOT_FILE = SNAPSHOT_DIR / "huracan_matches.json"


# ── Helpers ───────────────────────────────────────────────────────────────
def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fmt_date(s):
    if not s or s.startswith("0001") or s.startswith("1901"):
        return ""
    return s[:16]


def fmt_date_human(iso):
    """Convert 'YYYY-MM-DDTHH:MM' to 'dom 14/04 18:30'."""
    if not iso:
        return "Sin fecha"
    try:
        dt = datetime.fromisoformat(iso)
        days = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
        return f"{days[dt.weekday()]} {dt.strftime('%d/%m %H:%M')}"
    except Exception:
        return iso


def send_telegram(text):
    # Telegram max message length is 4096 chars — split if needed
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
    """Extract only matches involving Huracán, with team names resolved."""
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
                    "home_name": team_names.get(home, f"#{home}"),
                    "away": away,
                    "away_name": team_names.get(away, f"#{away}"),
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
    """Compare old vs new matches, return list of change descriptions."""
    old_map = {match_key(m): m for m in old_list}
    new_map = {match_key(m): m for m in new_list}
    changes = []

    # New matches
    for key, m in new_map.items():
        if key not in old_map:
            changes.append({
                "type": "new",
                "match": m,
                "msg": f"Nuevo partido: {m['home_name']} vs {m['away_name']}",
            })
            continue

        old = old_map[key]
        diffs = []

        if old["date"] != m["date"]:
            diffs.append(f"Fecha: {fmt_date_human(old['date'])} -> {fmt_date_human(m['date'])}")

        if old["field"] != m["field"]:
            old_f = old["field"] or "Sin campo"
            new_f = m["field"] or "Sin campo"
            diffs.append(f"Campo: {old_f} -> {new_f}")

        if old["status"] != m["status"]:
            diffs.append(f"Estado: {old['status']} -> {m['status']}")

        if old.get("home_score") != m.get("home_score") or old.get("away_score") != m.get("away_score"):
            hs = m.get("home_score")
            vs = m.get("away_score")
            if hs is not None and vs is not None:
                diffs.append(f"Resultado: {m['home_name']} {hs} - {vs} {m['away_name']}")

        if diffs:
            changes.append({
                "type": "changed",
                "match": m,
                "diffs": diffs,
            })

    # Removed matches
    for key, m in old_map.items():
        if key not in new_map:
            changes.append({
                "type": "removed",
                "match": m,
                "msg": f"Partido eliminado: {m['home_name']} vs {m['away_name']}",
            })

    return changes


# ── Build notification message ────────────────────────────────────────────
def build_message(mini_changes, pre_changes):
    lines = []

    if mini_changes:
        lines.append("<b>MINIPREBENJAMIN</b>")
        for c in mini_changes:
            m = c["match"]
            header = f"{m['home_name']} vs {m['away_name']}"
            jornada = m["jornada"]

            if c["type"] == "new":
                lines.append(f"\n  Nuevo partido ({jornada})")
                lines.append(f"  {header}")
                lines.append(f"  {fmt_date_human(m['date'])}")
                if m["field"]:
                    lines.append(f"  {m['field']}")
            elif c["type"] == "changed":
                lines.append(f"\n  Cambio ({jornada})")
                lines.append(f"  {header}")
                for d in c["diffs"]:
                    lines.append(f"  {d}")
            elif c["type"] == "removed":
                lines.append(f"\n  {c['msg']}")

    if pre_changes:
        if mini_changes:
            lines.append("")
        lines.append("<b>PREBENJAMIN</b>")
        for c in pre_changes:
            m = c["match"]
            header = f"{m['home_name']} vs {m['away_name']}"
            jornada = m["jornada"]

            if c["type"] == "new":
                lines.append(f"\n  Nuevo partido ({jornada})")
                lines.append(f"  {header}")
                lines.append(f"  {fmt_date_human(m['date'])}")
                if m["field"]:
                    lines.append(f"  {m['field']}")
            elif c["type"] == "changed":
                lines.append(f"\n  Cambio ({jornada})")
                lines.append(f"  {header}")
                for d in c["diffs"]:
                    lines.append(f"  {d}")
            elif c["type"] == "removed":
                lines.append(f"\n  {c['msg']}")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(f"[{datetime.now().isoformat()}] Checking Huracán matches...")

    try:
        mini_raw = fetch(f"{BASE}/matches/fortournament/85")
        pre_raw = fetch(f"{BASE}/matches/fortournament/87")
        mini_t = fetch(f"{BASE}/tournaments/85")
        pre_t = fetch(f"{BASE}/tournaments/87")
    except Exception as e:
        print(f"ERROR fetching API: {e}", file=sys.stderr)
        sys.exit(1)

    mini_matches = extract_huracan_matches(mini_raw, HURACAN_MINI_ID, mini_t)
    pre_matches = extract_huracan_matches(pre_raw, HURACAN_PRE_ID, pre_t)

    current = {
        "mini": mini_matches,
        "pre": pre_matches,
        "updated": datetime.now().isoformat(),
    }

    print(f"  Mini: {len(mini_matches)} matches | Pre: {len(pre_matches)} matches")

    # Load previous snapshot
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    old = {"mini": [], "pre": []}
    if SNAPSHOT_FILE.exists():
        try:
            old = json.loads(SNAPSHOT_FILE.read_text("utf-8"))
        except Exception:
            pass

    # Compare
    mini_changes = diff_matches(old.get("mini", []), mini_matches)
    pre_changes = diff_matches(old.get("pre", []), pre_matches)

    total = len(mini_changes) + len(pre_changes)

    if total > 0:
        msg = build_message(mini_changes, pre_changes)
        print(f"  {total} changes detected! Sending notification...")
        print(msg)
        send_telegram(msg)
    else:
        print("  No changes.")

    # Save new snapshot
    SNAPSHOT_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), "utf-8")
    print("  Snapshot saved.")


if __name__ == "__main__":
    main()
