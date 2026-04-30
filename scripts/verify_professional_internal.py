"""Verify the professional internal CSV against section 3.4 + section 6."""

import csv
import re
from collections import Counter
from pathlib import Path

CSV_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/professional_internal.csv"
)

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
TYPOSQUAT = [
    "paypa1", "amaz0n", "g00gle", "githu8", "microsft", "lnkedin", "yt0be",
    "faceb00k", "paypai",
]
DIGIT_DOMAIN = re.compile(r"[a-z][0-9][a-z]|[a-z][0-9]{2,}[a-z]")
URGENCY = [
    "click here to verify", "urgent action required", "your access will be suspended",
    "account suspended", "verify your account immediately", "verify immediately",
    "click now or lose access", "confirm your password", "enter your password",
    "reset your password now",
]
SUSPICIOUS_LINK = ["http://", "bit.ly", "tinyurl", "t.co/"]

PROJECT_NAMES = [
    "Phoenix", "Atlas", "Horizon", "Kestrel", "Orion", "Helios", "Mercury",
    "Nimbus", "Beacon", "Vega", "Lighthouse", "Compass", "Pioneer", "Summit",
    "Apollo", "Aurora", "Keystone", "Meridian",
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def display(s):
    m = re.match(r'"([^"]+)"', s)
    return m.group(1) if m else ""


def sender_type(sender):
    dn = display(sender).lower()
    if any(k in dn for k in ["hr", "people", "benefits"]):
        return "hr"
    if "— it" in dn or any(k in dn for k in ["it support", "helpdesk", "tech support",
                                              "it operations", "systems team"]):
        return "it"
    return "person"  # colleague or management — cannot distinguish from display name alone


def main():
    with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    print(f"Total rows: {len(rows)}")
    assert len(rows) == 800

    # [1] duplicates
    sigs = Counter((r["sender"], r["subject"], r["body"]) for r in rows)
    dupes = [k for k, v in sigs.items() if v > 1]
    assert not dupes, f"{len(dupes)} duplicates"
    print("[1] No duplicates: OK")

    # [2] min body length
    short = [r for r in rows if len(r["body"].strip()) < 10]
    assert not short
    print("[2] Body >= 10 chars: OK")

    # [3] typosquatted
    for r in rows:
        blob = f"{r['sender']}\n{r['subject']}\n{r['body']}".lower()
        for pat in TYPOSQUAT:
            assert pat not in blob, f"typosquat {pat}"
    print("[3] No typosquatted domains: OK")

    # [4] labels all 0
    assert all(str(r["label"]) == "0" for r in rows)
    print("[4] All labels = 0: OK")

    # [5] digit in sender domain
    for r in rows:
        assert not DIGIT_DOMAIN.search(domain(r["sender"])), r["sender"]
    print("[5] No digit-substituted sender domains: OK")

    # [6] URL shorteners
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        for sh in URL_SHORTENERS:
            assert sh not in blob, sh
    print("[6] No URL shorteners: OK")

    # [7] category
    cat = Counter(r["category"] for r in rows)
    assert cat == Counter({"professional_internal": 800})
    print(f"[7] Category counts: {dict(cat)}")

    # [8] sender variety
    domains = {domain(r["sender"]) for r in rows}
    print(f"[8] Distinct sender domains: {len(domains)}")
    assert len(domains) >= 5

    # ---- Section 3.4 constraints ----

    # (a) No urgency / verification phrases
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        for phrase in URGENCY:
            assert phrase not in blob, phrase
    print("[3.4] No urgency/verification phrases: OK")

    # (b) No suspicious link patterns
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        for pat in SUSPICIOUS_LINK:
            assert pat not in blob, pat
    print("[3.4] No suspicious links: OK")

    # (c) Body length 50-155 words
    wcs = [len(r["body"].split()) for r in rows]
    print(f"[3.4] Word count: min={min(wcs)}, max={max(wcs)}, mean={sum(wcs)/len(wcs):.1f}")
    assert min(wcs) >= 50
    assert max(wcs) <= 155

    # (d) Every row references internal context
    for r in rows:
        blob = r["body"].lower()
        has_project = any(p.lower() in blob for p in PROJECT_NAMES)
        has_link = any(tok in blob for tok in
                       ["confluence", "sharepoint", "docs.google.com", "jira"])
        has_day = any(d.lower() in blob for d in DAYS)
        assert has_project or has_link or has_day, f"no internal context: {r['subject']}"
    print("[3.4] Every row references internal context: OK")

    # (e) Sender type mix: HR, IT, and person-style senders all present
    st_counts = Counter(sender_type(r["sender"]) for r in rows)
    print(f"[3.4] Sender type mix: {dict(st_counts)}")
    for k in ("hr", "it", "person"):
        assert st_counts[k] > 0, f"missing sender type {k}"

    # (f) Subject-variety: look for meeting / document / update / hr-notice / it-notice keywords
    def classify(subject):
        s = subject.lower()
        if any(k in s for k in ["meeting", "sync", "catch-up", "catch up", "1:1",
                                  "call", "invite", "stand-up", "block on calendar",
                                  "schedule a call", "working session", "kick-off",
                                  "reschedule", "calendar check"]):
            return "meeting"
        if any(k in s for k in ["report", "proposal", "draft", "slides", "deck",
                                  "one-pager", "rfc", "budget", "spec",
                                  "retrospective", "notes", "timeline"]):
            return "document"
        if any(k in s for k in ["expense", "leave policy", "outing", "pay slip",
                                  "benefits", "handbook", "review schedule",
                                  "new hires", "wellness", "training", "volunteer",
                                  "office closure", "performance conversation",
                                  "learning budget", "all-hands"]):
            return "hr_notice"
        if any(k in s for k in ["maintenance", "downtime", "vpn", "password",
                                  "wi-fi", "laptops", "system refresh", "slack upgrade",
                                  "phone system", "mfa", "jira maintenance",
                                  "conference room"]):
            return "it_notice"
        if any(k in s for k in ["status update", "weekly update", "announcement",
                                  "new process", "quick update", "sprint summary",
                                  "status report", "milestone", "update from",
                                  "heads up", "end of week", "monthly update"]):
            return "project_update"
        return "other"

    sub_mix = Counter(classify(r["subject"]) for r in rows)
    print(f"[3.4] Subject subtype mix: {dict(sub_mix)}")
    for st in ("meeting", "document", "project_update", "hr_notice", "it_notice"):
        assert sub_mix[st] > 0, f"missing subtype {st}"

    # (g) Template reuse cap: no (subject, body) pair > 5
    pair = Counter((r["subject"], r["body"]) for r in rows)
    worst = pair.most_common(1)[0]
    print(f"[variety] Most-reused (subject, body) pair: {worst[1]} time(s)")
    assert worst[1] <= 5

    # (h) Internal link presence
    link_rows = sum(
        1 for r in rows
        if any(tok in r["body"].lower()
               for tok in ["confluence", "sharepoint", "docs.google.com", "jira"])
    )
    print(f"[3.4] Rows with internal link token: {link_rows}/{len(rows)}")
    assert link_rows >= len(rows) * 0.6, "fewer than 60% rows reference an internal system"

    print("\nAll quality + variety checks PASSED.")


if __name__ == "__main__":
    main()
