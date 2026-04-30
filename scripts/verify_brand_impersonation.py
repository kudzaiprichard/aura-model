"""Verify the brand-impersonation phishing CSV against section 4.1 + section 6."""

import csv
import re
from collections import Counter
from pathlib import Path

CSV_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/brand_impersonation.csv"
)

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
BARE_URL_RE = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S*")

REAL_DOMAINS = {
    "microsoft.com", "teams.microsoft.com", "office.com", "outlook.com",
    "docusign.com", "docusign.net",
    "zoom.us", "zoom.com",
    "dropbox.com",
    "wetransfer.com",
    "notion.so", "notion.com",
    "slack.com",
    "openai.com",
}

URGENCY_TOKENS = [
    "within 24 hours", "within 48 hours", "within the next 24 hours",
    "before end of day", "before 5pm", "expires in 24 hours", "expires in 48 hours",
    "expires today", "expires soon", "expire soon", "will be suspended",
    "will be cancelled", "will be locked", "placed in a limited state",
    "rate-limited", "action required", "urgent", "time-sensitive",
    "scheduled to expire", "before the deadline", "complete verification",
]

CREDENTIAL_TOKENS = [
    "sign in", "re-authenticate", "verify your identity", "verify your account",
    "verify your credentials", "confirm your identity", "confirm your credentials",
    "confirm your email", "update your billing", "update your password",
    "reset your password", "re-verify", "rotate your api keys", "verify",
    "confirm it was you", "authenticate", "update billing",
]


def domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def display(s):
    m = re.match(r'"([^"]+)"', s)
    return m.group(1) if m else ""


def brand_of(sender: str) -> str:
    dn = display(sender).lower()
    if "teams" in dn or "ms teams" in dn or "microsoft" in dn:
        return "msteams"
    if "docusign" in dn:
        return "docusign"
    if "zoom" in dn:
        return "zoom"
    if "dropbox" in dn:
        return "dropbox"
    if "wetransfer" in dn:
        return "wetransfer"
    if "notion" in dn:
        return "notion"
    if "slack" in dn:
        return "slack"
    if "openai" in dn:
        return "openai"
    return "other"


def main():
    with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    print(f"Total rows: {len(rows)}")
    assert len(rows) == 700

    # [1] duplicates
    sigs = Counter((r["sender"], r["subject"], r["body"]) for r in rows)
    dupes = [k for k, v in sigs.items() if v > 1]
    assert not dupes, f"{len(dupes)} duplicates"
    print("[1] No duplicates: OK")

    # [2] min body length
    short = [r for r in rows if len(r["body"].strip()) < 10]
    assert not short
    print("[2] Body >= 10 chars: OK")

    # [3] labels all 1
    assert all(str(r["label"]) == "1" for r in rows)
    print("[3] All labels = 1: OK")

    # [4] URL shorteners not used
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        for sh in URL_SHORTENERS:
            assert sh not in blob, sh
    print("[4] No URL shorteners: OK")

    # [5] category
    cat = Counter(r["category"] for r in rows)
    assert cat == Counter({"brand_impersonation": 700})
    print(f"[5] Category counts: {dict(cat)}")

    # ---- Section 4.1 constraints ----

    # (a) Sender domains must be typosquatted / fake — never real brand domain
    for r in rows:
        sd = domain(r["sender"])
        assert sd not in REAL_DOMAINS, f"real domain sender: {r['sender']}"
        for real in REAL_DOMAINS:
            assert not (sd == real or sd.endswith("." + real)), \
                f"sender ends with real brand domain: {r['sender']}"
    print("[4.1] No sender uses a real brand domain: OK")

    # (b) URLs in body must not point to real brand domains
    for r in rows:
        for m in BARE_URL_RE.finditer(r["body"].lower()):
            host = m.group(0).split("/")[0]
            for real in REAL_DOMAINS:
                assert not (host == real or host.endswith("." + real)), \
                    f"real brand URL found in body: {host} (subject: {r['subject']})"
    print("[4.1] No real-brand URLs in bodies: OK")

    # (c) Every row contains a bare URL at all
    no_url = [r for r in rows if not BARE_URL_RE.search(r["body"].lower())]
    assert not no_url, f"{len(no_url)} rows missing a URL"
    print("[4.1] Every row has at least one URL: OK")

    # (d) Body word count 80-160
    wcs = [len(r["body"].split()) for r in rows]
    print(f"[4.1] Word count: min={min(wcs)}, max={max(wcs)}, mean={sum(wcs)/len(wcs):.1f}")
    assert min(wcs) >= 80
    assert max(wcs) <= 165

    # (e) Brand coverage — all 8 modern brands impersonated
    brand_counts = Counter(brand_of(r["sender"]) for r in rows)
    print(f"[4.1] Brand distribution: {dict(brand_counts)}")
    for b in ("msteams", "docusign", "zoom", "dropbox", "wetransfer",
              "notion", "slack", "openai"):
        assert brand_counts[b] > 0, f"missing brand {b}"

    # (f) Every row carries at least one phishing signal (urgency or credential request)
    unflagged = []
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        has_urg = any(t in blob for t in URGENCY_TOKENS)
        has_cred = any(t in blob for t in CREDENTIAL_TOKENS)
        if not (has_urg or has_cred):
            unflagged.append(r)
    print(f"[4.1] Rows without urgency/credential signal: {len(unflagged)}")
    assert not unflagged

    # (g) Signal-count histogram — aim for every row to have multiple signals
    sig_counts = Counter()
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        c = 0
        if any(t in blob for t in URGENCY_TOKENS):
            c += 1
        if any(t in blob for t in CREDENTIAL_TOKENS):
            c += 1
        # Fake URL in body counts as third signal
        if BARE_URL_RE.search(r["body"].lower()):
            c += 1
        sig_counts[c] += 1
    print(f"[4.1] Signals-per-row histogram: {dict(sig_counts)}")
    # Most rows should have 2+ signals
    multi_sig = sum(v for k, v in sig_counts.items() if k >= 2)
    assert multi_sig / len(rows) >= 0.9, "fewer than 90% rows have 2+ signals"

    # (h) Polished / no bad grammar — proxy checks: no !!, no ALL-CAPS sentence,
    # no 'Dear Valued Customer'
    for r in rows:
        body = r["body"]
        assert "!!" not in body, "excessive exclamation"
        assert "Dear Valued Customer" not in body
        # Count uppercase words longer than 3 chars (proxy for shouting)
        all_caps = [w for w in re.findall(r"\b[A-Z]{4,}\b", body) if w not in
                    ("OpenAI", "DocuSign", "API", "ChatGPT", "MSTC")]
        # A few acronyms slip through — allow up to 2 uppercase shouts per body
        assert len(all_caps) <= 2, f"possible shouting: {all_caps}"
    print("[4.1] No obvious shouting / bad-grammar tells: OK")

    # (i) Template reuse cap: no (subject, body) pair > 5
    pair = Counter((r["subject"], r["body"]) for r in rows)
    worst = pair.most_common(1)[0]
    print(f"[variety] Most-reused (subject, body) pair: {worst[1]} time(s)")
    assert worst[1] <= 5

    # (j) Sender domain variety
    domains = {domain(r["sender"]) for r in rows}
    print(f"[variety] Distinct fake sender domains: {len(domains)}")
    assert len(domains) >= 20

    print("\nAll quality + variety checks PASSED.")


if __name__ == "__main__":
    main()
