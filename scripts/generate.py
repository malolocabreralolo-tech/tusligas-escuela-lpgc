#!/usr/bin/env python3
"""
Fetches fresh match data from tusligascanarias.mygol.es API
and injects it into index.html, preserving all CSS/JS design.

Tournaments:
  85 → Minibenjamín (MINI_MATCHES, MT)
  87 → Prebenjamín  (PRE_MATCHES, PT)
"""

import json
import re
import sys
import urllib.request
import urllib.error

BASE = "https://tusligascanarias.mygol.es/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fmt_date(s):
    """Convert ISO timestamp to 'YYYY-MM-DDTHH:MM', or '' if unset."""
    if not s or s.startswith("0001") or s.startswith("1901"):
        return ""
    return s[:16]


def transform_matches(jornadas_data):
    """Convert API jornada list to compact HTML format."""
    result = []
    for jornada in jornadas_data:
        name = jornada.get("name", "")
        group_id = jornada.get("idGroup", 0)
        matches = []
        for m in jornada.get("matches", []):
            status = m.get("status", 5)
            home = m.get("idHomeTeam") or -1
            away = m.get("idVisitorTeam") or -1
            d = fmt_date(m.get("startTime", ""))
            field = m.get("field") or {}
            f = (field.get("name") or "") if field else ""
            matches.append({"h": home, "v": away, "d": d, "s": status, "f": f})
        result.append({"n": name, "g": group_id, "m": matches})
    return result


def build_mt(tournament_data):
    """Build MT = {teamId: "Team Name"} from tournament 85."""
    mt = {}
    for team in tournament_data.get("teams", []):
        mt[team["id"]] = team["name"]
    return mt


def build_pt(tournament_data, existing_pt=None):
    """Build PT = {teamId: {n:"Name", g:"A"|"B"}} using teamGroups mapping."""
    pt = {}
    # Build group letter map: idGroup -> last letter of name ("GRUPO A" -> "A")
    group_letter = {}
    for g in tournament_data.get("groups", []):
        name = g.get("name", "")
        letter = name.strip()[-1].upper() if name.strip() else "A"
        if letter not in ("A", "B", "C", "D"):
            letter = "A"
        group_letter[g["id"]] = letter

    # Build team -> group mapping from teamGroups
    team_group = {}
    for tg in tournament_data.get("teamGroups", []):
        tid = tg["idTeam"]
        gid = tg["idGroup"]
        team_group[tid] = group_letter.get(gid, "A")

    for team in tournament_data.get("teams", []):
        tid = team["id"]
        g = team_group.get(tid, "A")
        pt[tid] = {"n": team["name"], "g": g}

    return pt


def extract_existing_pt(html):
    """Extract existing PT dict from HTML for group fallback."""
    m = re.search(r'const PT=(\{.*?\});', html, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {}


def js_const(name, value):
    return f"const {name}={json.dumps(value, ensure_ascii=False, separators=(',', ':'))};"


def main():
    print("Fetching match and team data from mygol.es API...")
    try:
        mini_raw = fetch(f"{BASE}/matches/fortournament/85")
        pre_raw = fetch(f"{BASE}/matches/fortournament/87")
        mini_t = fetch(f"{BASE}/tournaments/85")
        pre_t = fetch(f"{BASE}/tournaments/87")
    except urllib.error.URLError as e:
        print(f"ERROR: Network request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    existing_pt = extract_existing_pt(html)

    mini_matches = transform_matches(mini_raw)
    pre_matches = transform_matches(pre_raw)
    mt = build_mt(mini_t)
    pt = build_pt(pre_t, existing_pt)

    new_data = "\n".join([
        js_const("MINI_MATCHES", mini_matches),
        js_const("PRE_MATCHES", pre_matches),
        "",
        "// ── STATIC TEAMS ──────────────────────────────────────────",
        js_const("MT", mt),
        js_const("PT", pt),
        "",
    ])

    # Verify the data section marker exists before replacing
    if not re.search(r'const MINI_MATCHES=', html):
        print("ERROR: Could not find 'const MINI_MATCHES=' in index.html — HTML structure may have changed.", file=sys.stderr)
        sys.exit(1)

    # Replace everything from "const MINI_MATCHES=" up to "const NOW = new Date();"
    new_html = re.sub(
        r'const MINI_MATCHES=.*?(?=const NOW = new Date\(\);)',
        new_data + "\n",
        html,
        flags=re.DOTALL,
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_html)

    print(
        f"Done! MINI: {len(mini_matches)} jornadas | "
        f"PRE: {len(pre_matches)} jornadas | "
        f"MT: {len(mt)} teams | PT: {len(pt)} teams"
    )


if __name__ == "__main__":
    main()
