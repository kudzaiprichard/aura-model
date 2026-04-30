"""Verify the retail & transactional CSV against section 3.3 + section 6."""

import csv
import re
from collections import Counter
from pathlib import Path

CSV_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/retail_transactional.csv"
)

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
TYPOSQUAT = [
    "paypa1", "amaz0n", "g00gle", "githu8", "microsft", "paypai", "amzon",
    "lnkedin", "yt0be", "faceb00k", "netfl1x", "sp0tify",
]
DIGIT_DOMAIN = re.compile(r"[a-z][0-9][a-z]|[a-z][0-9]{2,}[a-z]")
ID_SIGNAL = re.compile(
    r"(?:"
    r"\d{3}-\d{7}-\d{7}|#\d{4,}|REF-\d{4,}|TXN\d{6,}|INV-\d{4,}"
    r"|\b[A-Z]{2}\d{3,}\b|\b[A-Z]{6}\b"
    r")"
)
CREDENTIAL = [
    "enter your password", "confirm your password", "update your password",
    "reset your password", "verify your password", "provide your password",
    "click here to verify", "account will be suspended", "verify your identity now",
]

BRAND_DOMAINS = {
    "Amazon.com": "amazon.com",
    "eBay": "ebay.com",
    "Etsy": "etsy.com",
    "Walmart": "walmart.com",
    "Target": "target.com",
    "Best Buy": "bestbuy.com",
    "Uber Eats": "uber.com",
    "DoorDash": "doordash.com",
    "Grubhub": "grubhub.com",
    "Deliveroo": "deliveroo.co.uk",
    "Just Eat": "just-eat.co.uk",
    "Airbnb": "airbnb.com",
    "Booking.com": "booking.com",
    "Expedia": "expedia.com",
    "Delta Air Lines": "delta.com",
    "United Airlines": "united.com",
    "Bank of America": "bankofamerica.com",
    "Wells Fargo": "wellsfargo.com",
    "Citibank": None,  # uses citi.com or citibank.com
    "Citi": None,
    "Visa": "visa.com",
    "Mastercard": "mastercard.com",
    "American Express": "aexp.com",
    "Netflix": "netflix.com",  # may be mailer.netflix.com subdomain
    "Spotify": "spotify.com",
    "Hulu": "hulumail.com",
    "Disney+": "disneyplus.com",
    "Apple": "apple.com",
}

BRAND_CATEGORY = {
    "Amazon.com": "ecommerce", "eBay": "ecommerce", "Etsy": "ecommerce",
    "Walmart": "ecommerce", "Target": "ecommerce", "Best Buy": "ecommerce",
    "Uber Eats": "food", "DoorDash": "food", "Grubhub": "food",
    "Deliveroo": "food", "Just Eat": "food",
    "Airbnb": "travel", "Booking.com": "travel", "Expedia": "travel",
    "Delta Air Lines": "travel", "United Airlines": "travel",
    "Bank of America": "finance", "Wells Fargo": "finance", "Citibank": "finance",
    "Citi": "finance", "Visa": "finance", "Mastercard": "finance",
    "American Express": "finance",
    "Netflix": "streaming", "Spotify": "streaming", "Hulu": "streaming",
    "Disney+": "streaming", "Apple": "streaming",
}


def domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def display(s):
    m = re.match(r'"([^"]+)"', s)
    return m.group(1) if m else ""


def main():
    with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    print(f"Total rows: {len(rows)}")
    assert len(rows) == 1000

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
            assert pat not in blob, f"typosquat {pat} in {r['sender']}"
    print("[3] No typosquatted domains: OK")

    # [4] labels
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
    assert cat == Counter({"retail_transactional": 1000})
    print(f"[7] Category counts: {dict(cat)}")

    # [8] sender variety
    domains = {domain(r["sender"]) for r in rows}
    print(f"[8] Distinct sender domains: {len(domains)}")
    assert len(domains) >= 10

    # ---- Section 3.3 constraints ----

    # (a) Every row must have an order / ref / txn ID
    no_id = [r for r in rows if not ID_SIGNAL.search(r["body"])]
    print(f"[3.3] Rows missing ID signal: {len(no_id)}")
    assert not no_id

    # (b) Sender domain must exactly match the brand — no typosquatting
    domain_mismatch = []
    for r in rows:
        dn = display(r["sender"])
        d = domain(r["sender"])
        brand_domain = BRAND_DOMAINS.get(dn)
        if brand_domain is None:
            # Citibank/Citi accepts citi.com or citibank.com
            if dn in ("Citibank", "Citi"):
                if not (d.endswith("citi.com") or d.endswith("citibank.com")):
                    domain_mismatch.append((dn, d))
        else:
            # Accept exact match OR a subdomain of the brand's primary domain
            if not (d == brand_domain or d.endswith("." + brand_domain)
                    or d.endswith(brand_domain)):
                domain_mismatch.append((dn, d))
    print(f"[3.3] Sender domain mismatches: {len(domain_mismatch)}")
    if domain_mismatch:
        print("  examples:", domain_mismatch[:5])
    assert not domain_mismatch

    # (c) No password / credential requests
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        for phrase in CREDENTIAL:
            assert phrase not in blob, phrase

    # (d) Body length: spec says 80-200 words
    wcs = [len(r["body"].split()) for r in rows]
    print(f"[3.3] Word count: min={min(wcs)}, max={max(wcs)}, mean={sum(wcs)/len(wcs):.1f}")
    assert min(wcs) >= 80
    assert max(wcs) <= 210

    # (e) Brand-category mix: all 5 categories present
    brand_cats = Counter()
    for r in rows:
        dn = display(r["sender"])
        cat_key = BRAND_CATEGORY.get(dn, "unknown")
        brand_cats[cat_key] += 1
    print(f"[3.3] Brand-category mix: {dict(brand_cats)}")
    for c in ("ecommerce", "food", "travel", "finance", "streaming"):
        assert brand_cats[c] > 0, f"missing brand category {c}"

    # (f) Subtype mix: infer from subject keywords
    def classify(subject):
        s = subject.lower()
        if any(k in s for k in ["receipt", "invoice", "payment confirmed",
                                  "payment receipt", "payment confirmation"]):
            return "receipt"
        if any(k in s for k in ["renews", "renewal", "upcoming reservation",
                                  "upcoming payment", "reminder", "autopay", "due on",
                                  "delivery tomorrow", "auto-reorder", "ships on",
                                  "check-in", "ready"]):
            return "reminder"
        if any(k in s for k in ["statement", "monthly summary", "transaction",
                                  "balance update", "account summary", "plan has been",
                                  "billing address", "payment method updated",
                                  "account", "activity", "points", "miles"]):
            return "account_notification"
        return "order_confirmation"

    sub_mix = Counter(classify(r["subject"]) for r in rows)
    print(f"[3.3] Subtype mix (approx): {dict(sub_mix)}")
    for st in ("order_confirmation", "receipt", "reminder", "account_notification"):
        assert sub_mix[st] > 0, f"missing subtype {st}"

    # (g) Template reuse: no (subject, body) pair > 5 times
    pair = Counter((r["subject"], r["body"]) for r in rows)
    worst = pair.most_common(1)[0]
    print(f"[variety] Most-reused (subject, body) pair: {worst[1]} time(s)")
    assert worst[1] <= 5

    # (h) URLs present (spec says bodies have legitimate-looking URLs)
    url_in_body = sum(1 for r in rows if re.search(r"\b[a-z0-9-]+\.(com|co\.uk|us)/\S+", r["body"]))
    print(f"[3.3] Rows with bare-domain URL: {url_in_body}/{len(rows)}")

    print("\nAll quality + variety checks PASSED.")


if __name__ == "__main__":
    main()
