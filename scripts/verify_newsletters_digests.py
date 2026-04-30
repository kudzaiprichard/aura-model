"""Verify the newsletters & digests CSV against section 3.5 + section 6."""

import csv
import re
from collections import Counter
from pathlib import Path

CSV_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/newsletters_digests.csv"
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
BARE_URL_RE = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S+")


def domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def display(s):
    m = re.match(r'"([^"]+)"', s)
    return m.group(1) if m else ""


# Known publication display names → publication type.
PUB_TYPE = {
    "TLDR": "tech_newsletter", "TLDR Newsletter": "tech_newsletter",
    "Morning Brew": "tech_newsletter", "Bytes": "tech_newsletter",
    "JavaScript Weekly": "tech_newsletter", "Python Weekly": "tech_newsletter",
    "The Pragmatic Engineer": "tech_newsletter", "Data Elixir": "tech_newsletter",
    "Changelog News": "tech_newsletter",
    "ACM TechNews": "industry_digest", "MIT Tech Review": "industry_digest",
    "Axios Pro Rata": "industry_digest", "The Information": "industry_digest",
    "Wired Daily": "industry_digest",
    "Lenny Rachitsky": "personal_newsletter", "Ben Thompson": "personal_newsletter",
    "Matt Levine": "personal_newsletter", "Casey Newton": "personal_newsletter",
    "Kai Brach": "personal_newsletter",
    "Stack Overflow": "community_digest", "DEV Community": "community_digest",
    "Hacker News Daily": "community_digest", "Product Hunt": "community_digest",
    "Indie Hackers": "community_digest", "Reddit": "community_digest",
}


def classify_subject(subject: str) -> str:
    s = subject.lower().strip()
    # numbered: contains "#<n>" or "vol." or "issue"
    if re.search(r"#\d+", s) or "vol." in s or s.startswith("issue"):
        return "numbered"
    # personal: "what i've been reading", "this week's picks", "thinking about"
    if any(k in s for k in ["what i've been reading", "this week's picks",
                             "a few things from my week", "thinking about",
                             "what i'm reading", "links i enjoyed"]):
        return "personal"
    # date: contains a month name or day-of-week
    months = ["january", "february", "march", "april", "may", "june", "july",
              "august", "september", "october", "november", "december"]
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if any(m in s for m in months) or any(d in s for d in days):
        return "date"
    # topic: "5 things", "top stories in", "links worth"
    if any(k in s for k in ["things you need to know", "top stories", "reads for your",
                             "what's happening", "biggest stories", "links worth",
                             "your time"]):
        return "topic"
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
    assert cat == Counter({"newsletters_digests": 700})
    print(f"[7] Category counts: {dict(cat)}")

    # [8] sender variety
    domains = {domain(r["sender"]) for r in rows}
    print(f"[8] Distinct sender domains: {len(domains)}")
    assert len(domains) >= 10

    # ---- Section 3.5 constraints ----

    # (a) No urgency / verification phrases
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        for phrase in URGENCY:
            assert phrase not in blob, phrase
    print("[3.5] No urgency phrases: OK")

    # (b) No protocol-prefixed URLs (bare domains only)
    for r in rows:
        assert "http://" not in r["body"].lower()
        assert "https://" not in r["body"].lower()
    print("[3.5] No protocol-prefixed URLs: OK")

    # (c) Body length 150-400 words
    wcs = [len(r["body"].split()) for r in rows]
    print(f"[3.5] Word count: min={min(wcs)}, max={max(wcs)}, mean={sum(wcs)/len(wcs):.1f}")
    assert min(wcs) >= 150
    assert max(wcs) <= 400

    # (d) Every body has an unsubscribe footer
    for r in rows:
        assert "unsubscribe" in r["body"].lower(), f"no unsubscribe: {r['subject']}"
    print("[3.5] Every body contains 'unsubscribe': OK")

    # (e) Every body has >= 2 bare-domain URLs (multiple)
    low_url = [r for r in rows if len(BARE_URL_RE.findall(r["body"].lower())) < 2]
    print(f"[3.5] Rows with <2 bare URLs: {len(low_url)}")
    assert not low_url

    # Stronger: spec says multiple URLs — check median is reasonable
    url_counts = [len(BARE_URL_RE.findall(r["body"].lower())) for r in rows]
    print(f"[3.5] Bare-URL count per body: min={min(url_counts)}, "
          f"max={max(url_counts)}, mean={sum(url_counts)/len(url_counts):.1f}")
    assert sum(url_counts) / len(url_counts) >= 3

    # (f) Publication-type mix: all 4 types present
    pub_type_counts = Counter()
    unknown_pubs = set()
    for r in rows:
        dn = display(r["sender"])
        ptype = PUB_TYPE.get(dn)
        if ptype is None:
            unknown_pubs.add(dn)
            pub_type_counts["unknown"] += 1
        else:
            pub_type_counts[ptype] += 1
    print(f"[3.5] Publication type mix: {dict(pub_type_counts)}")
    if unknown_pubs:
        print(f"  unknown display names: {unknown_pubs}")
    for t in ("tech_newsletter", "industry_digest", "personal_newsletter", "community_digest"):
        assert pub_type_counts[t] > 0, f"missing publication type {t}"

    # (g) Subject style mix: all 4 styles present
    style_counts = Counter(classify_subject(r["subject"]) for r in rows)
    print(f"[3.5] Subject style mix: {dict(style_counts)}")
    for s in ("numbered", "date", "topic", "personal"):
        assert style_counts[s] > 0, f"missing subject style {s}"

    # (h) Template reuse cap
    pair = Counter((r["subject"], r["body"]) for r in rows)
    worst = pair.most_common(1)[0]
    print(f"[variety] Most-reused (subject, body) pair: {worst[1]} time(s)")
    assert worst[1] <= 5

    # (i) Multiple topics per body — paragraph count heuristic
    para_counts = [len([p for p in r["body"].split("\n\n") if p.strip()]) for r in rows]
    print(f"[3.5] Paragraphs per body: min={min(para_counts)}, "
          f"max={max(para_counts)}, mean={sum(para_counts)/len(para_counts):.1f}")
    assert min(para_counts) >= 5

    # (j) Publication name mention: every body should mention a known publication name
    # (spec says publication name is mentioned)
    missing_name = 0
    for r in rows:
        dn = display(r["sender"])
        # Some senders are individual authors (Ben Thompson) — map back to pub name
        body_lower = r["body"].lower()
        # Accept either the display name OR the publication name from PUB_NAME_LOOKUP
        candidates = [dn.lower()]
        # Also allow publication brand variants
        for alt in ("tldr", "morning brew", "bytes", "javascript weekly", "python weekly",
                    "the pragmatic engineer", "data elixir", "changelog news",
                    "acm technews", "mit tech review", "axios pro rata",
                    "the information", "wired daily",
                    "lenny's newsletter", "stratechery", "money stuff", "platformer",
                    "dense discovery",
                    "stack overflow", "dev community", "hacker news daily",
                    "product hunt daily", "indie hackers", "reddit popular"):
            candidates.append(alt)
        if not any(c in body_lower for c in candidates):
            missing_name += 1
    print(f"[3.5] Rows missing any publication-name mention: {missing_name}")
    assert missing_name == 0

    print("\nAll quality + variety checks PASSED.")


if __name__ == "__main__":
    main()
