"""Verify the modern-technique phishing CSV against section 4.3 + section 6."""

import csv
import re
from collections import Counter
from pathlib import Path

CSV_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/modern_technique_phishing.csv"
)

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
BARE_URL_RE = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S*")
PHONE_RE = re.compile(r"\+?1?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")

CATEGORIES = [
    "modern_technique_qr_code",
    "modern_technique_crypto",
    "modern_technique_ai_polished",
    "modern_technique_callback",
    "modern_technique_multistage",
]

CRYPTO_BRANDS = ["Coinbase", "Binance", "Kraken", "MetaMask", "Trust Wallet", "Ledger"]


def sender_domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


# ---- per-subtype verifiers ----

def verify_qr(r):
    blob = r["body"].lower()
    assert "qr code" in blob or "qr-code" in blob, "QR: missing 'qr code'"
    assert "scan" in blob, "QR: missing 'scan'"
    assert "phone" in blob or "mobile" in blob, "QR: missing phone/mobile"


def verify_crypto(r):
    body = r["body"]
    blob = body.lower()
    assert BARE_URL_RE.search(blob), "crypto: missing URL"
    wallet_terms = ["wallet", "bitcoin", "btc ", "eth ", "ethereum",
                    "seed phrase", "airdrop", "staking", "0x"]
    assert any(t in blob for t in wallet_terms), "crypto: missing wallet concept"
    assert any(b.lower() in blob for b in CRYPTO_BRANDS), "crypto: missing brand"


def verify_ai(r):
    body = r["body"]
    blob = body.lower()
    assert BARE_URL_RE.search(blob), "ai: missing URL"
    has_ref = re.search(r"\b(?:REF|CASE|MEM|ACC|CLM)-\d{4,}\b", body) or \
              "reference" in blob
    assert has_ref, "ai: missing reference"
    gov_bank_terms = ["tax", "refund", "member", "insurance", "statement", "account",
                      "premium", "benefits", "bank", "treasury", "coverage"]
    assert any(t in blob for t in gov_bank_terms), "ai: missing gov/bank/health term"
    assert "!!" not in body, "ai: excessive exclamation"


def verify_callback(r):
    body = r["body"]
    blob = body.lower()
    assert not BARE_URL_RE.search(blob), f"callback: URL present {r['subject']}"
    assert PHONE_RE.search(body), "callback: missing phone number"
    assert "reference" in blob, "callback: missing reference"
    assert "call" in blob, "callback: missing 'call'"


def verify_multistage(r):
    body = r["body"]
    blob = body.lower()
    assert BARE_URL_RE.search(blob), "ms: missing URL"
    s = r["subject"].lower()
    assert (s.startswith("re:") or s.startswith("fwd:") or
            s.startswith("following up") or "as promised" in s or
            "as discussed" in s), f"ms: subject not a continuation: {s}"
    prior_cues = ["we discussed", "our call", "we talked", "our chat", "last week",
                  "earlier this week", "our conversation", "as agreed", "as promised",
                  "earlier call", "yesterday", "our phone call"]
    assert any(c in blob for c in prior_cues), "ms: missing prior-interaction cue"
    hard_urgency = ["will be suspended", "will be locked", "account suspended",
                    "verify immediately", "click here to verify", "reset your password"]
    assert not any(t in blob for t in hard_urgency), "ms: hard-urgency token present"


SUBTYPE_VERIFIERS = {
    "modern_technique_qr_code": (verify_qr, 80, 205),
    "modern_technique_crypto": (verify_crypto, 80, 205),
    "modern_technique_ai_polished": (verify_ai, 100, 235),
    "modern_technique_callback": (verify_callback, 80, 205),
    "modern_technique_multistage": (verify_multistage, 80, 205),
}


def main():
    with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    print(f"Total rows: {len(rows)}")
    assert len(rows) == 1500

    # [1] no duplicates
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

    # [4] URL shorteners banned
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        for sh in URL_SHORTENERS:
            assert sh not in blob, f"shortener {sh} in {r['subject']}"
    print("[4] No URL shorteners: OK")

    # [5] category counts
    cat = Counter(r["category"] for r in rows)
    for c in CATEGORIES:
        assert cat[c] == 300, f"{c}: expected 300, got {cat[c]}"
    print(f"[5] Category counts: {dict(cat)}")

    # [6] sender not on commodity domains
    generic = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}
    for r in rows:
        sd = sender_domain(r["sender"])
        assert sd not in generic, f"generic sender: {r['sender']}"
    print("[6] No commodity-domain senders: OK")

    # ---- per-subtype quality ----
    for category, (verifier, wc_min, wc_max) in SUBTYPE_VERIFIERS.items():
        subset = [r for r in rows if r["category"] == category]
        wcs = [len(r["body"].split()) for r in subset]
        print(f"\n--- {category} ({len(subset)} rows) ---")
        print(f"  word count: min={min(wcs)}, max={max(wcs)}, mean={sum(wcs)/len(wcs):.1f}")
        assert min(wcs) >= wc_min, f"{category}: min {min(wcs)} < {wc_min}"
        assert max(wcs) <= wc_max, f"{category}: max {max(wcs)} > {wc_max}"
        for r in subset:
            verifier(r)
        print(f"  subtype checks: OK")

        # sender variety
        domains = {sender_domain(r["sender"]) for r in subset}
        print(f"  distinct sender domains: {len(domains)}")
        assert len(domains) >= 6

        # template reuse cap (subject+body pair)
        pair = Counter((r["subject"], r["body"]) for r in subset)
        worst = pair.most_common(1)[0]
        print(f"  most-reused (subject, body) pair: {worst[1]} time(s)")
        assert worst[1] <= 5

    print("\nAll quality + variety checks PASSED.")


if __name__ == "__main__":
    main()
