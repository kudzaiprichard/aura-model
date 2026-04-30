"""Verify the spear-phishing CSV against section 4.2 + section 6."""

import csv
import re
from collections import Counter
from pathlib import Path

CSV_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/spear_phishing.csv"
)

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
BARE_URL_RE = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S*")
ATTACHMENT_RE = re.compile(r"\b[A-Za-z0-9_\-]+\.(?:pdf|xlsx|docx|zip)\b")

# Known fake domain buckets used by the generator (to classify impersonation type).
COLLEAGUE_DOMAINS = {
    "company-corp.net", "companycorp.co", "company-mail.co", "companyhq.net",
    "company-team.co", "companyofficial.net", "company-group.co",
}
IT_DOMAINS = {
    "it-support-corp.com", "company-it-helpdesk.com", "it-systems-support.net",
    "corporate-it.co", "helpdesk-portal.net", "it-admin-support.co",
    "secure-it-admin.com",
}
HR_DOMAINS = {
    "company-hr-portal.com", "hr-workday-portal.net", "company-hr-admin.co",
    "corporate-hr-team.com", "hr-benefits-portal.net", "hrservices-portal.co",
}
EXEC_DOMAINS = {
    "company-executives.com", "company-ceo-office.net", "ceo-office.co",
    "corporate-leadership.net", "executive-suite.co", "exec-office-corp.com",
}
VENDOR_DOMAINS = {
    "trusted-vendor.co", "billing-vendor.net", "invoice-services.co",
    "procurement-partner.net", "vendor-billing-corp.com", "supplier-invoices.co",
    "corporate-suppliers.net",
}

GENERIC_PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "proton.me",
}

URGENCY_TOKENS = [
    "before end of day", "end of day", "before 5pm", "before close of business",
    "within 24 hours", "within the next 24 hours", "within the next", "today",
    "final reminder", "overdue", "urgent", "time-sensitive",
    "scheduled to expire", "will be suspended", "will be locked",
    "placed in a read-only state", "cannot be skipped",
    "mandatory", "action required",
]

AUTHORITY_TOKENS = [
    "ceo", "cfo", "cto", "coo", "vp finance", "head of finance",
    "leadership", "the exec team", "the board", "the steering committee",
    "confidential", "compliance", "mandatory", "hr compliance", "it security",
    "helpdesk", "accounts receivable", "billing team", "vendor management",
    "board meeting",
]


def domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def display(s):
    m = re.match(r'"([^"]+)"', s)
    return m.group(1) if m else ""


def impersonation_of(sender: str) -> str:
    d = domain(sender)
    if d in COLLEAGUE_DOMAINS:
        return "colleague"
    if d in IT_DOMAINS:
        return "it"
    if d in HR_DOMAINS:
        return "hr"
    if d in EXEC_DOMAINS:
        return "executive"
    if d in VENDOR_DOMAINS:
        return "vendor"
    return "unknown"


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
    assert cat == Counter({"spear_phishing": 800})
    print(f"[5] Category counts: {dict(cat)}")

    # ---- Section 4.2 constraints ----

    # (a) No sender uses a generic commodity domain
    for r in rows:
        sd = domain(r["sender"])
        assert sd not in GENERIC_PERSONAL_DOMAINS, \
            f"generic personal domain as sender: {r['sender']}"
    print("[4.2] No generic personal domains in sender: OK")

    # (b) Every sender domain is a "close but wrong" fake domain from our buckets
    unknown = [r for r in rows if impersonation_of(r["sender"]) == "unknown"]
    assert not unknown, f"{len(unknown)} rows with unknown sender domain bucket"
    print("[4.2] All sender domains are fake/typosquatted: OK")

    # (c) Body 50-160 words
    wcs = [len(r["body"].split()) for r in rows]
    print(f"[4.2] Word count: min={min(wcs)}, max={max(wcs)}, mean={sum(wcs)/len(wcs):.1f}")
    assert min(wcs) >= 50
    assert max(wcs) <= 160

    # (d) Impersonation-type mix: all 5 types present
    imp_counts = Counter(impersonation_of(r["sender"]) for r in rows)
    print(f"[4.2] Impersonation mix: {dict(imp_counts)}")
    for t in ("colleague", "it", "hr", "executive", "vendor"):
        assert imp_counts[t] > 0, f"missing impersonation type {t}"

    # (e) Every row contains a suspicious link or an attachment reference
    missing = []
    for r in rows:
        has_link = bool(BARE_URL_RE.search(r["body"].lower()))
        has_attach = bool(ATTACHMENT_RE.search(r["body"]))
        if not (has_link or has_attach):
            missing.append(r["subject"])
    print(f"[4.2] Rows missing link+attachment: {len(missing)}")
    assert not missing

    # (f) Every row has a first-name greeting ("Hi <First>,")
    no_greeting = [r for r in rows if not re.search(r"^Hi\s+[A-Z][a-z]+,", r["body"])]
    assert not no_greeting, f"{len(no_greeting)} rows missing first-name greeting"
    print("[4.2] Every row starts with 'Hi <First>,': OK")

    # (g) Every row carries urgency or authority signal
    unflagged = 0
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        has_urg = any(t in blob for t in URGENCY_TOKENS)
        has_auth = any(t in blob for t in AUTHORITY_TOKENS)
        if not (has_urg or has_auth):
            unflagged += 1
    print(f"[4.2] Rows without urgency/authority: {unflagged}")
    assert unflagged == 0

    # (h) Signal histogram — most rows should have both urgency and authority
    sig_hist = Counter()
    for r in rows:
        blob = f"{r['subject']}\n{r['body']}".lower()
        c = 0
        if any(t in blob for t in URGENCY_TOKENS):
            c += 1
        if any(t in blob for t in AUTHORITY_TOKENS):
            c += 1
        if BARE_URL_RE.search(r["body"].lower()):
            c += 1
        if ATTACHMENT_RE.search(r["body"]):
            c += 1
        sig_hist[c] += 1
    print(f"[4.2] Signals per row: {dict(sig_hist)}")

    # (i) Template reuse cap
    pair = Counter((r["subject"], r["body"]) for r in rows)
    worst = pair.most_common(1)[0]
    print(f"[variety] Most-reused (subject, body) pair: {worst[1]} time(s)")
    assert worst[1] <= 5

    # (j) Sender domain variety
    domains = {domain(r["sender"]) for r in rows}
    print(f"[variety] Distinct sender domains: {len(domains)}")
    assert len(domains) >= 20

    print("\nAll quality + variety checks PASSED.")


if __name__ == "__main__":
    main()
