"""Generate 800 spear-phishing emails (label=1) for AURA online-learning augmentation.

Follows section 4.2 of online_learning_dataset.md.

Design:
- 5 impersonation types: colleague, it, hr, executive, vendor.
- Every sender uses a domain that is "close but wrong" — never a generic real domain.
- Bodies reference internal processes, recipient first name, and authority pressure.
- Every row contains a suspicious link or attachment reference.
- Strict section-6 gate plus a per-row phishing-signal gate: urgency/authority + either a
  suspicious link or an attachment reference.
"""

from __future__ import annotations

import csv
import hashlib
import random
import re
from collections import Counter
from pathlib import Path

random.seed(20260418)

OUT_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/spear_phishing.csv"
)


# ------------------------------------------------------------------------------------
# Name pools — used for recipient first names, impersonated colleagues, and execs.
# ------------------------------------------------------------------------------------

FIRST_NAMES = [
    "Sarah", "John", "Emma", "Michael", "Priya", "David", "Rachel", "Tom",
    "Olivia", "James", "Nina", "Marcus", "Ellie", "Hassan", "Amelia", "Dan",
    "Clara", "Theo", "Ruth", "Leo", "Maya", "Jay", "Kate", "Ben", "Liam",
    "Sophie", "Matt", "Aisha", "Chen", "Ravi", "Fatima", "Diego", "Lena",
]

LAST_NAMES = [
    "Smith", "Johnson", "Patel", "Chen", "Miller", "Rodriguez", "Wilson",
    "Taylor", "Nguyen", "Brown", "Davis", "Garcia", "Khan", "Kim", "Singh",
    "O'Brien", "Kowalski", "Andersen", "Foster", "Parker", "Morgan", "Cohen",
    "Reed", "Nakamura", "Mendez", "Okafor", "Romano", "Werner", "Silva",
]

EXEC_TITLES = ["CEO", "CFO", "COO", "CTO", "VP Finance", "VP Operations", "Head of Finance"]

EVENTS = [
    "end of quarter", "fiscal year close", "annual audit", "board meeting",
    "compliance review", "budget freeze", "system maintenance window",
    "mandatory security update", "quarterly review", "year-end close",
]

# "Close but wrong" domain patterns — deliberately look like a real company but aren't.
COLLEAGUE_DOMAINS = [
    "company-corp.net", "companycorp.co", "company-mail.co", "companyhq.net",
    "company-team.co", "companyofficial.net", "company-group.co",
]

IT_DOMAINS = [
    "it-support-corp.com", "company-it-helpdesk.com", "it-systems-support.net",
    "corporate-it.co", "helpdesk-portal.net", "it-admin-support.co",
    "secure-it-admin.com",
]

HR_DOMAINS = [
    "company-hr-portal.com", "hr-workday-portal.net", "company-hr-admin.co",
    "corporate-hr-team.com", "hr-benefits-portal.net", "hrservices-portal.co",
]

EXEC_DOMAINS = [
    "company-executives.com", "company-ceo-office.net", "ceo-office.co",
    "corporate-leadership.net", "executive-suite.co", "exec-office-corp.com",
]

VENDOR_DOMAINS = [
    "trusted-vendor.co", "billing-vendor.net", "invoice-services.co",
    "procurement-partner.net", "vendor-billing-corp.com", "supplier-invoices.co",
    "corporate-suppliers.net",
]


# ------------------------------------------------------------------------------------
# Fake link and attachment references.
# ------------------------------------------------------------------------------------

COLLEAGUE_LINKS = [
    "shared-docs-portal.net/review",
    "internal-review-portal.co/document",
    "team-shared-files.net/open",
    "company-docs-share.co/view",
    "shared-drive-portal.net/file",
]

IT_LINKS = [
    "secure-it-admin.com/update",
    "it-support-corp.com/patch",
    "company-it-helpdesk.com/install",
    "corporate-it.co/signin",
    "helpdesk-portal.net/verify",
]

HR_LINKS = [
    "company-hr-portal.com/signin",
    "hr-workday-portal.net/login",
    "hr-benefits-portal.net/confirm",
    "corporate-hr-team.com/update",
    "hrservices-portal.co/deposit",
]

EXEC_LINKS = [
    "corporate-leadership.net/approval",
    "executive-suite.co/review",
    "company-executives.com/document",
    "exec-office-corp.com/sign",
    "ceo-office.co/transfer",
]

VENDOR_LINKS = [
    "vendor-billing-corp.com/invoice",
    "supplier-invoices.co/view",
    "billing-vendor.net/payment",
    "procurement-partner.net/remittance",
    "invoice-services.co/overdue",
]

ATTACHMENTS = [
    "Invoice_4521.pdf", "Agreement_Q{qn}.pdf", "WireInstructions.pdf",
    "Expense_Report_{month}.xlsx", "DirectDeposit_Form.pdf",
    "SecurityPatch_Instructions.pdf", "Contract_Draft_v{vn}.pdf",
    "Remittance_Advice.pdf", "Board_Memo_{month}.pdf", "Payroll_Summary.xlsx",
    "Approval_Request.pdf",
]


# ------------------------------------------------------------------------------------
# Subject and body banks per impersonation type.
# ------------------------------------------------------------------------------------

SUBJECTS = {
    "colleague": [
        "Quick request — can you handle this?",
        "Urgent: review this before the meeting",
        "Can you help with something quickly?",
        "Favor — need this done today",
        "Are you around? Quick turnaround needed",
        "Following up — please confirm receipt",
        "Can you take a look at this document?",
        "Need your sign-off before 5pm",
        "Quick one — before I send this to leadership",
    ],
    "it": [
        "Your password expires today — reset now",
        "Mandatory security update — action required",
        "Suspicious login detected — verify your account",
        "IT: complete your account re-verification",
        "Action required: install critical security patch",
        "Your VPN access will be revoked — renew now",
        "Mailbox over quota — sign in to clear",
        "Multi-factor authentication enrolment — due today",
        "IT Helpdesk: your ticket requires action",
    ],
    "hr": [
        "HR: please update your direct deposit details",
        "Action required: confirm your tax withholding",
        "Reminder: benefits enrolment closes today",
        "HR: updated employment agreement for your signature",
        "Urgent: payroll discrepancy needs your confirmation",
        "Action required: complete mandatory HR training",
        "HR: your salary review document is ready",
        "Important: annual policy acknowledgement needed",
        "HR: please verify your personal information",
    ],
    "executive": [
        "Quick favour — confidential, please keep this between us",
        "Are you at your desk? I need your help with something",
        "Urgent: wire transfer approval needed",
        "I need you to handle this before the board meeting",
        "Quick request — can't talk, in a meeting",
        "Confidential: please review before leadership call",
        "Need you to process this today — on my phone",
        "Urgent request — please confirm receipt",
        "Need this actioned before close of business",
    ],
    "vendor": [
        "Invoice #4521 payment overdue — action required",
        "Remittance advice — please process immediately",
        "Overdue invoice — 30-day notice",
        "Urgent: updated banking details for vendor payments",
        "Final reminder: outstanding invoice #{inv}",
        "Invoice adjustment — review and approve",
        "Action required: vendor payment on hold",
        "Your vendor account requires verification",
        "Overdue payment notice — please review",
    ],
}


BODIES = {
    # -------------------- COLLEAGUE --------------------
    "colleague": [
        (
            "Hi {me},\n\nI'm between meetings and can't get to this myself. Can you take a quick "
            "look at the document I shared and confirm the numbers on page two before 5pm? "
            "{stakeholder} is expecting a response today.\n\nLink to the document: {url}\n\n"
            "Please don't forward this — it's confidential until we send the final version. "
            "Appreciate the quick turnaround.\n\nThanks,\n{sender_first}"
        ),
        (
            "Hi {me},\n\nQuick one — I've just put the updated {project} agreement together "
            "and need a second pair of eyes before I send it to {stakeholder}. Can you sign in "
            "and review the red-lined sections today?\n\nReview here: {url}\n\nI've marked this "
            "as urgent because the deadline is end of day with {event} coming up. Reply as soon "
            "as you've looked.\n\nThanks,\n{sender_first}"
        ),
        (
            "Hi {me},\n\nCould you handle something for me quickly? I'm on the road and can't "
            "access my laptop. The attached invoice from our vendor needs your sign-off so we "
            "can release payment before {event}.\n\nSigning portal: {url}\nAttachment: "
            "{attachment}\n\nIf you can confirm by end of day that would be a big help. I'll "
            "explain more when I'm back.\n\nThanks,\n{sender_first}"
        ),
        (
            "Hi {me},\n\nFollowing up on our chat from earlier — can you log in and confirm "
            "receipt of the shared folder I just sent? There are a few files in there that "
            "{stakeholder} is asking about and I want to make sure you've got the latest.\n\n"
            "Open here: {url}\n\nWould appreciate a quick reply once you've had a look. Thanks "
            "for the fast turnaround.\n\nBest,\n{sender_first}"
        ),
        (
            "Hi {me},\n\nI need a favour — can you review the draft agreement I've just shared "
            "and sign off on the scope section before I send it to leadership? With {event} "
            "this week, the window to get this over the line is tight.\n\nDocument: {url}\n\n"
            "Please treat this as confidential and don't loop anyone else in yet. I'll send "
            "formal notes once we've aligned.\n\nThanks,\n{sender_first}"
        ),
    ],

    # -------------------- IT --------------------
    "it": [
        (
            "Hi {me},\n\nOur records show your corporate password is scheduled to expire today. "
            "To avoid losing access to your email, VPN, and shared drives, please complete the "
            "password reset before end of day.\n\nReset here: {url}\n\nThis is a mandatory "
            "step for every user as part of our quarterly {event}. Accounts that don't "
            "complete the reset will be locked automatically.\n\nThanks,\nIT Helpdesk"
        ),
        (
            "Hi {me},\n\nOur monitoring system detected a suspicious sign-in to your account "
            "from an unfamiliar device. For your protection, we've paused external access "
            "until you confirm your identity.\n\nVerify your account: {url}\n\nPlease complete "
            "this within 24 hours. If you don't, your mailbox will be placed in a read-only "
            "state and your admin will be notified.\n\nThanks,\nIT Support"
        ),
        (
            "Hi {me},\n\nAs part of a mandatory security patch, we need every user to install "
            "the latest update on their laptop before end of week. This addresses a "
            "critical vulnerability and cannot be skipped.\n\nDownload the patch here: "
            "{url}\nInstructions: {attachment}\n\nYour device will be flagged as non-compliant "
            "if the patch isn't applied in time. Please act today.\n\nThanks,\nIT Security"
        ),
        (
            "Hi {me},\n\nYou have a helpdesk ticket that requires action before it can be "
            "closed. We tried to reach you on chat and email earlier this week.\n\nReview the "
            "ticket and confirm: {url}\n\nTo keep your access in place, please sign in and "
            "complete the verification step today. Tickets unresolved after the cut-off are "
            "escalated to your manager automatically.\n\nThanks,\nIT Helpdesk"
        ),
        (
            "Hi {me},\n\nYour VPN certificate is due to expire as part of the upcoming {event}. "
            "To renew without losing access to internal systems, please sign in and complete "
            "the re-enrolment before 5pm today.\n\nRenew here: {url}\n\nIf the certificate "
            "expires without renewal, remote access to shared drives and internal tools will "
            "be suspended until IT can reissue a new one.\n\nThanks,\nIT Helpdesk"
        ),
    ],

    # -------------------- HR --------------------
    "hr": [
        (
            "Hi {me},\n\nOur payroll system flagged a discrepancy on your direct deposit "
            "details ahead of {event}. To make sure your next pay slip is not delayed, please "
            "sign in and verify your banking information.\n\nUpdate here: {url}\n\nThis is a "
            "mandatory step for all employees this cycle. Any account that doesn't confirm "
            "will be placed on a manual payment schedule and may be delayed by up to two "
            "weeks.\n\nThanks,\nHR Payroll"
        ),
        (
            "Hi {me},\n\nAs part of the annual compliance review, we need every employee to "
            "acknowledge the updated employment agreement before the end of this month. The "
            "agreement is attached along with a short summary of the changes.\n\nReview and "
            "sign: {url}\nAttachment: {attachment}\n\nThis is a standard HR process and "
            "should take under five minutes. Please complete it today.\n\nThanks,\nHR "
            "Department"
        ),
        (
            "Hi {me},\n\nYour mandatory HR training for the quarter is due and has not yet "
            "been completed. To remain in good standing and keep your benefits active, please "
            "finish the course by {event}.\n\nAccess the portal: {url}\n\nEmployees who miss "
            "the deadline are reported to their line manager. If you've already completed the "
            "training, please sign in and confirm the record.\n\nThanks,\nHR Compliance"
        ),
        (
            "Hi {me},\n\nWe've noticed that some of your personal information on file is out "
            "of date. Please sign in to the HR portal and verify your address, emergency "
            "contact, and tax withholding before end of day.\n\nVerify here: {url}\n\nYour "
            "payroll record will be flagged until the details are confirmed. Updates take "
            "effect immediately after you save.\n\nThanks,\nHR Team"
        ),
        (
            "Hi {me},\n\nYour salary review document is now available in the HR portal. "
            "Please sign in and acknowledge the document so we can finalise the adjustment in "
            "your next pay cycle.\n\nReview and acknowledge: {url}\nDocument: {attachment}\n\n"
            "Any review that isn't acknowledged by {event} will be rolled into the next "
            "cycle, which may delay the adjustment by up to one month.\n\nThanks,\nHR Team"
        ),
    ],

    # -------------------- EXECUTIVE --------------------
    "executive": [
        (
            "Hi {me},\n\nI'm tied up in back-to-back meetings and can't pick up calls. I need "
            "your help processing a time-sensitive wire transfer for a confidential "
            "acquisition. Do not discuss this with anyone on the team until I confirm.\n\n"
            "Approve here: {url}\n\nThe paperwork is standard and must be actioned before "
            "{event}. I'll send further details once the transfer is under way.\n\nThanks for "
            "the discretion,\n{sender_first}\n{exec_title}"
        ),
        (
            "Hi {me},\n\nQuick favour — I need you to handle something confidential before the "
            "board meeting. The attached approval document needs your signature so I can "
            "present the updated numbers.\n\nSigning link: {url}\nDocument: {attachment}\n\n"
            "Please treat this as confidential. I'm on my phone and won't be able to respond "
            "to texts quickly, so reply here once it's done.\n\nThanks,\n{sender_first}\n"
            "{exec_title}"
        ),
        (
            "Hi {me},\n\nAre you at your desk? I need a vendor payment processed before close "
            "of business. This is part of the {event} and has to go out today without delay.\n"
            "\nApproval portal: {url}\n\nKeep this between us for now — leadership will be "
            "briefed after the transfer clears. I appreciate the quick response.\n\nBest,\n"
            "{sender_first}\n{exec_title}"
        ),
        (
            "Hi {me},\n\nI need a confidential task handled today. Please review and sign the "
            "attached document so we can finalise the deal terms ahead of the leadership "
            "call.\n\nAccess: {url}\nAttachment: {attachment}\n\nPlease don't loop anyone "
            "else in — I'll handle the communications from my side. Confirm once you've "
            "signed.\n\nThanks,\n{sender_first}\n{exec_title}"
        ),
        (
            "Hi {me},\n\nUrgent — I need you to push this through before {event}. The "
            "approval needs to be on file today and I can't get to my laptop.\n\nDocument "
            "link: {url}\n\nI'm relying on you to keep this confidential and get it done "
            "today. Reply once complete.\n\nThanks,\n{sender_first}\n{exec_title}"
        ),
    ],

    # -------------------- VENDOR --------------------
    "vendor": [
        (
            "Hi {me},\n\nThis is a reminder that invoice #{inv} is 30 days overdue. To "
            "keep your account in good standing and avoid service suspension, please process "
            "the payment within the next 24 hours.\n\nReview and pay: {url}\nInvoice copy: "
            "{attachment}\n\nOur records show the invoice was issued on behalf of your {team} "
            "team during the {event}. Please confirm receipt once the payment is scheduled.\n"
            "\nBest regards,\nAccounts Receivable"
        ),
        (
            "Hi {me},\n\nPlease find attached the remittance advice for invoice #{inv}. Our "
            "bank details have changed as of this month — please update your payment "
            "instructions before the next transfer.\n\nUpdated banking portal: {url}\n"
            "Remittance advice: {attachment}\n\nKindly confirm the new details have been "
            "applied on your side before the end of day.\n\nBest regards,\nBilling Team"
        ),
        (
            "Hi {me},\n\nYour vendor account has been placed on hold pending verification "
            "of your contact and payment details. To avoid disruption to current orders, "
            "please sign in and confirm your information.\n\nVerify account: {url}\n\nThis "
            "is a routine step required ahead of {event}. Accounts not verified by end of "
            "week will be removed from the active supplier list.\n\nBest regards,\nVendor "
            "Management"
        ),
        (
            "Hi {me},\n\nWe've issued a final reminder for invoice #{inv}, which remains "
            "unpaid. To prevent the account being forwarded to collections, please process "
            "the outstanding balance today.\n\nPayment portal: {url}\nInvoice: "
            "{attachment}\n\nIf you believe this is in error, please confirm through the "
            "portal and our team will review the dispute within two business days.\n\nBest "
            "regards,\nAccounts Receivable"
        ),
        (
            "Hi {me},\n\nAn invoice adjustment has been applied to your recent purchase "
            "order. The updated invoice #{inv} is attached along with a short summary of "
            "the changes.\n\nApprove and release: {url}\nUpdated invoice: {attachment}\n\n"
            "To keep the payment schedule aligned with {event}, please approve the "
            "adjustment by end of day.\n\nBest regards,\nBilling Team"
        ),
    ],
}


# ------------------------------------------------------------------------------------
# Plan: sum must equal 800.
# ------------------------------------------------------------------------------------

PLAN = [
    ("colleague", 180),
    ("it", 180),
    ("hr", 160),
    ("executive", 160),
    ("vendor", 120),
]
assert sum(c for _, c in PLAN) == 800


# ------------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------------

def pick(seq):
    return random.choice(seq)


PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def fill(template: str, ctx: dict) -> str:
    def repl(m):
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))
    return PLACEHOLDER_RE.sub(repl, template)


def make_sender(impersonation: str) -> tuple[str, str]:
    """Return (sender_rfc5322, display_first_name_for_sign_off)."""
    if impersonation == "colleague":
        first = pick(FIRST_NAMES)
        last = pick(LAST_NAMES)
        local = f"{first[0].lower()}.{last.lower().replace(chr(39), '')}"
        d = pick(COLLEAGUE_DOMAINS)
        return f'"{first} {last}" <{local}@{d}>', first
    if impersonation == "it":
        d = pick(IT_DOMAINS)
        display = pick([
            "IT Helpdesk", "IT Support", "IT Security", "Corporate IT",
            "Helpdesk", "Systems Team",
        ])
        local = pick(["helpdesk", "it-admin", "support", "security", "noreply"])
        return f'"{display}" <{local}@{d}>', "IT Helpdesk"
    if impersonation == "hr":
        d = pick(HR_DOMAINS)
        display = pick([
            "HR Team", "HR Department", "HR Payroll", "People Operations",
            "Benefits Team", "HR Compliance",
        ])
        local = pick(["hr", "payroll", "benefits", "hr-admin", "compliance"])
        return f'"{display}" <{local}@{d}>', "HR Team"
    if impersonation == "executive":
        first = pick(FIRST_NAMES)
        last = pick(LAST_NAMES)
        local = f"{first[0].lower()}.{last.lower().replace(chr(39), '')}"
        d = pick(EXEC_DOMAINS)
        return f'"{first} {last}" <{local}@{d}>', first
    if impersonation == "vendor":
        d = pick(VENDOR_DOMAINS)
        display = pick([
            "Invoice Dept", "Accounts Receivable", "Billing Team",
            "Vendor Management", "Supplier Relations", "Procurement Partner",
        ])
        local = pick(["billing", "invoice", "accounts", "ap", "vendor-admin"])
        return f'"{display}" <{local}@{d}>', "Accounts Receivable"
    raise ValueError(impersonation)


def links_for(impersonation: str):
    return {
        "colleague": COLLEAGUE_LINKS,
        "it": IT_LINKS,
        "hr": HR_LINKS,
        "executive": EXEC_LINKS,
        "vendor": VENDOR_LINKS,
    }[impersonation]


def build_ctx(impersonation: str, sender_first: str) -> dict:
    me = pick(FIRST_NAMES)
    stakeholder = pick(["leadership", "the exec team", "the CFO", "the board",
                         "the client", "the steering committee"])
    project = pick(["Phoenix", "Atlas", "Horizon", "Orion", "Kestrel", "Helios",
                    "Nimbus", "Beacon", "Vega", "Compass"])
    team = pick(["Engineering", "Operations", "Finance", "Procurement", "Marketing"])
    event = pick(EVENTS)
    month = pick(["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"])
    att_tpl = pick(ATTACHMENTS)
    attachment = att_tpl.format(
        qn=random.randint(1, 4),
        vn=random.randint(2, 8),
        month=month,
    )
    return {
        "me": me,
        "sender_first": sender_first,
        "stakeholder": stakeholder,
        "project": project,
        "team": team,
        "event": event,
        "month": month,
        "url": pick(links_for(impersonation)),
        "attachment": attachment,
        "inv": random.randint(3000, 99999),
        "exec_title": pick(EXEC_TITLES),
    }


# ------------------------------------------------------------------------------------
# Quality gate — section 6 + section 4.2 phishing-signal requirement.
# ------------------------------------------------------------------------------------

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
BARE_URL_RE = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S*")
ATTACHMENT_RE = re.compile(r"\b[A-Za-z0-9_\-]+\.(?:pdf|xlsx|docx|zip)\b")

# Domains that should never appear as spear-phishing sender (real commodity domains).
# The spec says "slightly wrong" - not just a gmail/yahoo throwaway.
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


def sender_domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def passes_checks(row: dict) -> bool:
    sender = row["sender"]
    subject = row["subject"]
    body = row["body"]
    blob = f"{subject}\n{body}".lower()

    if len(body.strip()) < 10:
        return False

    wc = len(body.split())
    # spec 4.2: 50-150 words
    if wc < 50 or wc > 160:
        return False

    # Sender must NOT be a generic personal mailbox
    sd = sender_domain(sender)
    if sd in GENERIC_PERSONAL_DOMAINS:
        return False

    # URL shorteners not allowed
    for sh in URL_SHORTENERS:
        if sh in blob:
            return False

    # Must contain a suspicious link OR an attachment reference
    has_link = bool(BARE_URL_RE.search(blob))
    has_attachment = bool(ATTACHMENT_RE.search(body))
    if not (has_link or has_attachment):
        return False

    # Must contain urgency OR authority pressure (phishing signal)
    has_urgency = any(t in blob for t in URGENCY_TOKENS)
    has_authority = any(t in blob for t in AUTHORITY_TOKENS)
    if not (has_urgency or has_authority):
        return False

    # Must use a first name somewhere in the body (targeted feel).
    # Body should start with "Hi <First>," — approximate via regex for "Hi X,"
    if not re.search(r"^Hi\s+[A-Z][a-z]+,", body):
        return False

    return True


# ------------------------------------------------------------------------------------
# Generate
# ------------------------------------------------------------------------------------

def generate():
    rows: list[dict] = []
    seen: set[str] = set()
    template_use: Counter = Counter()

    for impersonation, target_count in PLAN:
        subjects = SUBJECTS[impersonation]
        bodies = BODIES[impersonation]

        produced = 0
        attempts = 0
        max_attempts = target_count * 150

        while produced < target_count and attempts < max_attempts:
            attempts += 1
            sender, sender_first = make_sender(impersonation)
            subj_tpl = pick(subjects)
            body_tpl = pick(bodies)

            key = (impersonation, subj_tpl, body_tpl)
            if template_use[key] >= 5:
                continue

            ctx = build_ctx(impersonation, sender_first)
            subject = fill(subj_tpl, ctx)
            body = fill(body_tpl, ctx)

            row = {
                "sender": sender,
                "subject": subject,
                "body": body,
                "label": 1,
                "category": "spear_phishing",
            }

            h = hashlib.sha1(f"{sender}\n{subject}\n{body}".encode()).hexdigest()
            if h in seen:
                continue
            if not passes_checks(row):
                continue

            rows.append(row)
            seen.add(h)
            template_use[key] += 1
            produced += 1

        if produced < target_count:
            raise RuntimeError(
                f"Only produced {produced}/{target_count} for {impersonation} in {attempts} attempts"
            )

    assert len(rows) == 800
    return rows


def main():
    rows = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["sender", "subject", "body", "label", "category"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
