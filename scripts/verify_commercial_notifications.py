"""Verify the generated commercial notifications CSV against section 6 quality checks."""

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

CSV_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/commercial_notifications.csv"
)

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
TYPOSQUAT_PATTERNS = [
    "paypa1", "amaz0n", "g00gle", "githu8", "microsft", "gith0b", "n0tion",
    "paypai", "lnkedin", "yt0be", "faceb00k",
]
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
DIGIT_IN_DOMAIN = re.compile(r"[a-z][0-9][a-z]|[a-z][0-9]{2,}[a-z]")


def sender_domain(s: str) -> str:
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def brand_name(s: str) -> str:
    return s.split('"')[1] if '"' in s else "?"


def main() -> None:
    with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    print(f"Total rows: {len(rows)}")

    assert len(rows) == 1500, f"Expected 1500, got {len(rows)}"

    # (1) No duplicates on (sender, subject, body)
    sigs = Counter((r["sender"], r["subject"], r["body"]) for r in rows)
    dupes = [k for k, v in sigs.items() if v > 1]
    assert not dupes, f"{len(dupes)} duplicate rows found"
    print("[1] No duplicates: OK")

    # (2) Minimum body length
    short = [r for r in rows if len(r["body"].strip()) < 10]
    assert not short, f"{len(short)} rows with body < 10 chars"
    print("[2] Body length >= 10: OK")

    # (3) No typosquatted domains
    bad_typo = []
    for r in rows:
        blob = f"{r['sender']}\n{r['subject']}\n{r['body']}".lower()
        for pat in TYPOSQUAT_PATTERNS:
            if pat in blob:
                bad_typo.append((pat, r["sender"]))
                break
    assert not bad_typo, f"Typosquatting found: {bad_typo[:5]}"
    print("[3] No typosquatted domains: OK")

    # (4) Label sanity: all should be 0
    non_zero = [r for r in rows if str(r["label"]) != "0"]
    assert not non_zero, f"{len(non_zero)} rows with label != 0"
    print("[4] All labels = 0: OK")

    # (5) No digit-for-letter in sender domain
    bad_dig = []
    for r in rows:
        d = sender_domain(r["sender"])
        if DIGIT_IN_DOMAIN.search(d):
            bad_dig.append(d)
    assert not bad_dig, f"Digit-in-domain senders: {bad_dig[:5]}"
    print("[5] No digit-substituted domains: OK")

    # (6) No URL shorteners
    bad_sh = []
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        for sh in URL_SHORTENERS:
            if sh in blob:
                bad_sh.append(sh)
                break
    assert not bad_sh, f"URL shorteners found: {bad_sh[:5]}"
    print("[6] No URL shorteners: OK")

    # (7) Category balance — only one category here; must equal 1500
    cat_counts = Counter(r["category"] for r in rows)
    assert cat_counts == Counter({"commercial_notifications": 1500}), cat_counts
    print(f"[7] Category counts: {dict(cat_counts)}")

    # (8) Sender variety — at least 10 distinct domains for this subset
    domains = {sender_domain(r["sender"]) for r in rows}
    assert len(domains) >= 10, f"Only {len(domains)} distinct sender domains"
    print(f"[8] Distinct sender domains: {len(domains)}")

    # Brand-type variety
    brands = {brand_name(r["sender"]) for r in rows}
    assert len(brands) >= 10, f"Only {len(brands)} distinct brand types"
    print(f"[variety] Distinct brand types: {len(brands)} -> {sorted(brands)}")

    # At least 5 distinct (substituted) subject strings per brand; the real check is that
    # each brand draws from >= 5 distinct subject-*templates*. Substituted subjects are all
    # distinct by design, so we also verify template diversity via the first 40 chars.
    per_brand_subj = defaultdict(set)
    for r in rows:
        per_brand_subj[brand_name(r["sender"])].add(r["subject"][:40])
    min_subj = min(len(s) for s in per_brand_subj.values())
    print(f"[variety] Min distinct subject-prefixes per brand: {min_subj}")
    assert min_subj >= 5

    # Subtype mix — classify by subject keywords
    def classify(subject: str) -> str:
        s = subject.lower()
        if any(k in s for k in ["invoice", "receipt", "renew", "shipped", "payment", "statement", "plan", "subscription"]):
            return "transactional"
        if any(k in s for k in ["digest", "weekly", "roundup", "summary", "week of", "trending", "highlights", "top ", "picks from"]):
            return "digest"
        if any(k in s for k in ["recommend", "you might", "based on", "picks", "handpicked", "curated", "explore", "similar", "popular"]):
            return "recommendation"
        return "notification"

    subtype_mix = Counter(classify(r["subject"]) for r in rows)
    print(f"[variety] Subtype mix: {dict(subtype_mix)}")
    for st in ("digest", "notification", "recommendation", "transactional"):
        assert subtype_mix[st] > 0, f"Missing subtype: {st}"

    # Template-reuse proxy: no exact (subject, body) pair more than 5 times
    pair_counts = Counter((r["subject"], r["body"]) for r in rows)
    worst = pair_counts.most_common(1)[0]
    print(f"[variety] Most-reused (subject, body) pair used {worst[1]} time(s)")
    assert worst[1] <= 5

    print("\nAll quality checks PASSED.")


if __name__ == "__main__":
    main()
