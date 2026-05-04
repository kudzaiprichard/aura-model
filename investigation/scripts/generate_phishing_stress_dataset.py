"""Generate 1600 phishing emails that exercise AURA v1.0's documented blind
spots.

Every email in every category applies the hard rules R1–R8 from
``investigation/00_weakness_report.md`` §6:

  R1  No ``!`` or ``?`` anywhere in subject or body.
  R2  ``body_url_count`` must be 0 or 1.
  R3  Sender email local part is a shared-inbox whitelist token, so
      ``name_email_consistency`` = 1.
  R4  Sender domain is pronounceable, 10–15 chars, low entropy.
  R5  Body is 150–400 words (medium bucket only — short / long buckets
      intentionally sit outside this to stress ``body_word_count`` and
      ``body_entropy`` at both ends; R5 is only recorded as "applied"
      when the email actually lands in range).
  R6  Modern OOV vocabulary seeded into the body.
  R7  Zero exclamation marks anywhere (reinforcement of R1).
  R8  ``email_digit_ratio`` = 0 — no digits in the local part.

Output: ``investigation/_datasets/phishing_stress.csv`` with schema
``sender, subject, body, label, category, tone_profile, length_bucket,
exploit_rules_applied, notes``.

Banks are module-level so they can be inspected and extended. The template
engine mixes tone profiles × parameter banks × length variation so no two
rows share sentence structure for long.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
RNG = random.Random(20260421)

OUT_PATH = Path(__file__).resolve().parent.parent / '_datasets' / 'phishing_stress.csv'

EMAILS_PER_CATEGORY = 200
LENGTH_DISTRIBUTION = {'short': 60, 'medium': 80, 'long': 60}
TONES = ('cold_automated', 'urgent_corporate', 'friendly_helpful', 'casual_brief')

# Phishing hard-rule R5 word-count band.
R5_MIN_WORDS = 150
R5_MAX_WORDS = 400

# Length-bucket word ranges (LAYER 3).
LENGTH_BUCKET_WORDS = {
    'short': (30, 80),
    'medium': (150, 300),
    'long': (400, 600),
}


# ===========================================================================
# SHARED PARAMETER BANKS  (LAYER 2)
# ===========================================================================

# R3 — email local parts that flip name_email_consistency to 1 via the
# `_SHARED_INBOX_LOCALS` whitelist in inference/preprocessing.py.
SHARED_INBOX_TOKENS: list[str] = [
    'noreply', 'support', 'billing', 'alerts', 'team', 'notifications',
    'admin', 'help', 'info', 'updates',
]

# R6 — modern OOV vocabulary (weakness report §3). The TF-IDF vocab was
# frozen in 2008 so none of these tokens contribute anything to the
# subject / body vectorisers; the engineered features — which R1–R5 have
# already neutralised — are the model's only remaining signal.
MODERN_OOV_TERMS: list[str] = [
    'docusign', 'okta', 'mfa', '1password', 'onedrive', 'workday', 'slack',
    'notion', 'authenticator', 'sso', 'oauth', 'saml', 'webhook', 'api key',
    'zero trust', 'conditional access', 'entra', 'azure ad', 'passkey',
    'webauthn', 'totp', 'otp', 'magic link', 'approve sign-in', 'graph api',
    'tenant', 'scope', 'consent', 'airtable', 'figma', 'miro', 'loom',
    'canva', 'dropbox', 'gdrive', 'office365', 'm365', 'auth0', 'bitwarden',
    'adp', 'gusto', 'atlassian', 'salesforce',
]

# 15+ urgency phrases. No `!` or `?` (R1).
URGENCY_PHRASES: list[str] = [
    'This notice is time sensitive and requires your attention today.',
    'Please review the details below at your earliest convenience.',
    'This request has a short turnaround window.',
    'A response is expected before the end of the business day.',
    'Our records indicate a pending item on your account.',
    'The attached item is flagged for same-day review.',
    'This is a reminder that the deadline is approaching.',
    'Action on this matter is required within one business day.',
    'Prompt handling helps avoid service interruption.',
    'This item was escalated to your queue this morning.',
    'Please treat this as a priority in your workflow today.',
    'Our compliance team asked that this be resolved promptly.',
    'Your attention is requested to keep the audit trail clean.',
    'This workflow cannot advance until the step is completed.',
    'A delay past the cut-off will move this to manual review.',
    'The team is awaiting your confirmation to proceed.',
]

# 15+ calls to action. No `!` or `?`.
CTA_PHRASES: list[str] = [
    'Sign in to your account using the secure link below.',
    'Review the details in your portal.',
    'Confirm the change using the single-use link below.',
    'Open the document in your workspace to continue.',
    'Use the verification link to finish the setup.',
    'Follow the link in your mailbox to acknowledge the notice.',
    'Open the attached record and approve the workflow step.',
    'Continue to your account to verify the activity.',
    'Use the button below to review the flagged item.',
    'Visit your team workspace to access the secure document.',
    'Proceed to your console to check the pending task.',
    'Finish the enrolment step using the link in this message.',
    'Open the request from your inbox to sign it off.',
    'Log in to the portal to see the updated details.',
    'Head over to the secure area to complete the step.',
    'Access your account to resolve the open item.',
]

# 15+ deadline expressions.
DEADLINES: list[str] = [
    'by end of business today',
    'before 5pm local time',
    'within the next 24 hours',
    'by the close of this week',
    'before the end of the day',
    'within one business day',
    'by Friday',
    'before tomorrow morning',
    'no later than 24 hours from this message',
    'during your morning workflow',
    'before your next sync',
    'within this calendar week',
    'by the next payroll cycle',
    'ahead of the compliance review',
    'before the audit window closes',
    'ahead of the quarterly close',
]

# 10+ greetings. Empty strings produce a no-greeting variant (R5 friendly).
GREETINGS: list[str] = [
    'Hi,',
    'Hello,',
    'Hi team,',
    'Dear colleague,',
    'Hi there,',
    'Greetings,',
    'Hello team,',
    'Good morning,',
    'Good afternoon,',
    'Hi all,',
    '',
    '',
]

# 10+ sign-offs.
SIGN_OFFS: list[str] = [
    'Thanks,',
    'Regards,',
    'Best,',
    'Sincerely,',
    'Kind regards,',
    'Thank you,',
    'Warm regards,',
    'Cheers,',
    'Yours,',
    'Best regards,',
    '',
    '',
]

# 40+ filler paragraphs drawn from real corporate / SaaS / IT prose.
# The pool is sampled without replacement within a single email so long
# bodies never repeat a sentence (LAYER 3 requirement).
BODY_FILLERS: list[str] = [
    'Access will remain available while the review is in progress.',
    'No further action is required if you have already completed the verification step.',
    'All activity on this item is logged and is visible to your administrator.',
    'Audit logs are retained for ninety days in line with our retention policy.',
    'A record of this notice will be added to your account activity timeline.',
    'Your existing session remains active across all trusted devices.',
    'Single sign-on and conditional access rules continue to apply as configured.',
    'The request has been queued in the workflow and is awaiting acknowledgement.',
    'The linked action uses the same portal you already use every day.',
    'Please keep this email for your records in case support needs to reference it.',
    'Support can answer any questions via the standard help channel.',
    'This notice was triggered by a routine policy check on your tenant.',
    'The system will re-check the condition after you complete the step.',
    'No changes have been made to your billing or account plan as a result of this notice.',
    'Your workspace permissions remain unchanged while the item is open.',
    'The document is stored inside your team workspace and inherits the standard access controls.',
    'Once acknowledged, this item clears automatically from your queue.',
    'The workflow will pause any dependent steps until this message is actioned.',
    'Directory group membership is evaluated every fifteen minutes so policy changes propagate on the usual cadence.',
    'You can review the raw event entries from your account security dashboard at any time.',
    'Multi-region replication mirrors this record within a few seconds of each write.',
    'Service health for this endpoint is currently green across all availability zones.',
    'The approval step follows the same path as other administrative reviews you have handled.',
    'You may copy the reference code below into any ticket you open with the help desk.',
    'Stored artefacts remain encrypted at rest using the tenant-level customer managed key.',
    'Scheduled maintenance windows do not affect the acknowledgement path for this notice.',
    'Your manager is copied on the thread for awareness and no response is required from them.',
    'Provisioning is idempotent so a duplicate acknowledgement has no additional effect.',
    'Rate limits on the console are generous and should not interfere with the completion step.',
    'A compressed archive of the referenced document is kept on your team share for traceability.',
    'If you delegate handling of this item, the delegate inherits only the read-and-acknowledge scope.',
    'Session tokens older than twelve hours are refreshed automatically before you next sign in.',
    'Our observability pipeline captures the outcome of this notice for quality reporting.',
    'No external parties receive a copy of this message or the linked record.',
    'Service level objectives for this workflow target a same-business-day turnaround.',
    'Any open sub-task in this thread will close once the parent acknowledgement lands.',
    'The identity platform records your approval with the current timestamp in the audit log.',
    'Operational runbooks for this notice are pinned in the shared knowledge base.',
    'Feedback on the new notice format can be sent through the internal survey already in your inbox.',
    'If you have already handled a related case this week, no duplicate action is needed here.',
    'Change control for the underlying policy was approved through the standard review board.',
    'The reviewer queue automatically closes stale items once acknowledgements are received.',
    'Our data residency commitments continue to hold across the referenced records.',
    'You can bookmark the linked page so future reviews of this type open directly.',
    'Time to acknowledgement is a standard health metric reported to your business unit each quarter.',
    'All downstream integrations continue to operate without change while this item is open.',
]

# Corporate / SaaS pattern display names (the local part is always one of
# the shared-inbox tokens so R3 is satisfied regardless of the display name).
DISPLAY_NAMES: list[str] = [
    'Security Team',
    'Account Services',
    'IT Services',
    'Workspace Admin',
    'Compliance Notices',
    'Identity Platform',
    'Accounts Team',
    'Service Desk',
    'Operations',
    'Billing Operations',
    'Access Management',
    'Finance Notices',
    'Platform Updates',
    'Document Services',
    'Collaboration Team',
    'Workplace Notices',
    'Corporate IT',
]

# Legacy phish-coded tokens (weakness report §6); referenced here only for
# documentation — phishing generator does not use them, the legitimate
# generator embeds them under FP6.
LEGACY_PHISH_TOKENS: list[str] = [
    'dear friend', 'beneficiary', 'consignment', 'refinance', 'mortgage',
    'replica', 'diploma',
]


# ===========================================================================
# CATEGORY DEFINITIONS  (brands, fake domains, opening hooks, notes)
# ===========================================================================

CATEGORIES: dict[str, dict] = {
    # -------------------------------------------------------------------
    # 1. OAuth / consent phishing — §5.1 #1
    # -------------------------------------------------------------------
    'oauth_phishing': {
        'notes': (
            'OAuth consent phishing is entirely absent from the 2008 training '
            "corpus; OOV lexicon (oauth, consent, scope, tenant) plus a clean "
            'engineered-feature profile should land it in the legit band.'
        ),
        'brands': [
            'Microsoft 365', 'Azure AD', 'Entra ID', 'Google Workspace',
            'Google OAuth', 'OneLogin', 'Duo Security', 'Okta Identity',
            'Auth0', 'Ping Identity', 'JumpCloud', 'LastPass Business',
            '1Password Business', 'Atlassian Access', 'Slack Enterprise',
            'Dropbox Business', 'Zoom Workplace', 'Salesforce Identity',
            'ServiceNow Now', 'Workday Access', 'AWS IAM Identity',
            'GitHub Enterprise',
        ],
        'fake_domains': [
            'ms365-hub.co', 'entra-login.co', 'ms-access.net', 'gdrive-hub.co',
            'g-signin.net', 'okta-access.co', 'secure-sso.net',
            'sso-portal.co', 'auth-review.co', 'consent-hub.co',
            'tenant-hub.co', 'oauth-hub.net', 'identity-hub.co',
            'login-portal.co', 'entra-hub.co', 'workspace-co.co',
        ],
        'hooks': [
            "A new third-party application has requested access to your {brand} tenant.",
            "Your {brand} account received an oauth consent request that requires approval.",
            "A sso application is pending grant on your {brand} workspace.",
            "An approve sign-in prompt is waiting on your {brand} conditional access policy.",
            "Your {brand} tenant flagged a scope change request for admin approval.",
            "A linked application is attempting to read your {brand} graph api data.",
            "An access grant is queued against your {brand} account under zero trust controls.",
            "Your tenant administrator routed a consent screen approval to your mailbox.",
        ],
        'hook_cta': [
            "Approve or decline the grant from your {brand} console.",
            "Review the scope list inside your conditional access dashboard.",
            "Confirm the consent from your identity portal.",
            "Use the identity admin panel to finish the approval step.",
        ],
    },

    # -------------------------------------------------------------------
    # 2. Brand impersonation — §5.1 #2
    # -------------------------------------------------------------------
    'brand_impersonation': {
        'notes': (
            'Spoofed modern SaaS brand notifications. Brand tokens are OOV '
            'and the engineered-feature profile matches legit receipts.'
        ),
        'brands': [
            'Microsoft', 'Google', 'PayPal', 'DocuSign', 'Adobe', 'Dropbox',
            'AWS', 'Zoom', 'Slack', 'Notion', 'Stripe', 'Shopify',
            'Atlassian', 'GitHub', 'GitLab', 'Coinbase', 'Airbnb', 'Uber',
            'Apple', 'Netflix', 'LinkedIn', 'Microsoft Teams',
        ],
        'fake_domains': [
            'ms-alert.co', 'paypal-hub.co', 'docusign-hub.co',
            'adobe-sign.co', 'dropbox-hub.co', 'aws-billing.co',
            'zoom-meet.co', 'slack-hub.co', 'notion-hub.co',
            'stripe-hub.co', 'shopify-hub.co', 'atlas-hub.co',
            'github-hub.co', 'coinbase-hub.co', 'apple-id-hub.co',
            'netflix-hub.co',
        ],
        'hooks': [
            "A new {brand} document is waiting in your workspace.",
            "Your {brand} account received an updated access notice.",
            "A pending signature request from {brand} requires your acknowledgement.",
            "Your {brand} workspace flagged an unusual sign-in from a new device.",
            "A file shared with you through {brand} is ready for review.",
            "Your {brand} account settings were updated by your administrator.",
            "A billing statement for your {brand} plan is now available.",
            "Your {brand} team completed a new share request to your mailbox.",
        ],
        'hook_cta': [
            "Open the document from your {brand} dashboard.",
            "Verify the session through your {brand} security centre.",
            "Review the change in the {brand} account summary.",
            "Accept the share from inside your {brand} workspace.",
        ],
    },

    # -------------------------------------------------------------------
    # 3. BEC / wire-transfer — §5.1 #4
    # -------------------------------------------------------------------
    'bec_wire_transfer': {
        'notes': (
            'CFO / CEO-voice wire-redirection BEC. Short prose, usually '
            'zero URLs, exactly the shape that lands body_url_count=0 as a '
            'strong legit signal.'
        ),
        'brands': [
            'Finance Operations', 'Corporate Treasury', 'Accounts Payable',
            'Controller Office', 'Group Finance', 'Shared Services',
            'FP and A', 'Treasury Desk', 'Payments Team', 'AP Desk',
            'Office of the CFO', 'Finance Back Office', 'Global Treasury',
            'Vendor Finance', 'Reconciliation Team', 'Corporate Finance',
            'Billing Operations', 'AR Team',
        ],
        'fake_domains': [
            'company-co.co', 'corp-finance.co', 'group-ops.co',
            'shared-ops.co', 'ap-services.co', 'payments-hub.co',
            'cfo-office.co', 'finance-hub.co', 'treasury-hub.co',
            'ar-services.co', 'vendor-hub.co', 'back-office.co',
            'finance-co.co', 'corp-ap.co', 'finance-ops.co',
            'group-ap.co',
        ],
        'hooks': [
            "I need you to action an updated wire for a vendor before the cut-off.",
            "The banking details on one of our vendors have changed and the payment is due.",
            "A routing update landed in my inbox and I need your help pushing it through.",
            "The updated ach details for this week's transfer are in the attached note.",
            "We have a beneficiary change on file that still needs to be reflected in the payment run.",
            "I am travelling today and cannot log in to the portal; can you handle the transfer.",
            "Treasury flagged a payment that needs to go out under the revised remit-to details.",
            "The attached vendor note covers the new routing; please move on it before the banking cut-off.",
        ],
        'hook_cta': [
            "Reply once the payment is queued with the new details.",
            "Confirm when the bank has the updated instructions on file.",
            "Let me know once AP has the remit-to noted.",
            "Ping me back when the transfer is logged against the vendor.",
        ],
    },

    # -------------------------------------------------------------------
    # 4. Spear phishing — §5.1 #9, #12
    # -------------------------------------------------------------------
    'spear_phishing': {
        'notes': (
            'Personalised named-target lure. Short prose, 0 or 1 URL, '
            'often from a freemail-lookalike. Perfect engineered-feature '
            'overlap with modern short personal emails.'
        ),
        'brands': [
            'Senior Recruiter', 'Talent Partner', 'Head of Talent',
            'Engineering Lead', 'Portfolio Manager', 'Editorial Contact',
            'Community Manager', 'Research Lead', 'Partnership Lead',
            'Program Lead', 'Grants Office', 'Operations Lead',
            'Events Producer', 'Research Partner', 'Business Lead',
            'Product Partner',
        ],
        'fake_domains': [
            'talent-hub.co', 'partner-co.co', 'editor-desk.co',
            'community-co.co', 'grants-hub.co', 'events-desk.co',
            'partner-hub.co', 'research-co.co', 'program-hub.co',
            'ops-lead.co', 'product-co.co', 'advisory-co.co',
            'portfolio-co.co', 'editorial-co.co', 'partners-hub.co',
            'team-hub.co',
        ],
        'hooks': [
            "Following up on the introduction from last week — wanted to share a quick note.",
            "Great to meet you at the offsite; here is the brief I mentioned.",
            "Thanks for making time for the call earlier; sharing the next step below.",
            "Circling back after our conversation — here is the material I promised.",
            "Passing along the document from our discussion; quick read on the way.",
            "Following the thread you mentioned in the community; adding a short context note.",
            "Continuing from our exchange at the conference; a small ask on the other side.",
            "Thanks for the review last sprint — sending across the write-up we discussed.",
        ],
        'hook_cta': [
            "The doc is linked above when you have a minute.",
            "A quick acknowledgement is all that is needed from your side.",
            "Keep an eye on the linked brief and send thoughts when ready.",
            "The file covers the next step when you are free to read it.",
        ],
    },

    # -------------------------------------------------------------------
    # 5. MFA / credential harvest — §5.1 #10, §3 MFA lexicon
    # -------------------------------------------------------------------
    'mfa_credential_harvest': {
        'notes': (
            'Fake MFA / authenticator / 2FA prompts. Short body, 1 URL, '
            'all high-signal tokens OOV (mfa, 2fa, authenticator, passkey, '
            'totp).'
        ),
        'brands': [
            'Microsoft Authenticator', 'Google Authenticator', 'Duo Mobile',
            'Okta Verify', 'LastPass Authenticator', '1Password',
            'Authy', 'Microsoft Entra', 'YubiKey Cloud', 'Bitwarden',
            'Passkey Service', 'Azure Conditional Access',
            'Identity Defender', 'Auth0 Guardian', 'SSO Portal',
            'Corporate Identity', 'Mobile Identity', 'Access Guardian',
        ],
        'fake_domains': [
            'mfa-portal.co', 'totp-hub.co', 'auth-sync.co',
            'passkey-hub.co', 'mfa-hub.co', 'mfa-review.co',
            'identity-hub.co', 'access-hub.co', 'otp-hub.co',
            'verify-sso.co', 'mobile-hub.co', 'sso-check.co',
            'entra-hub.co', 'device-hub.co', 'push-sync.co',
            'approve-hub.co',
        ],
        'hooks': [
            "We saw a new mfa prompt on your account that is waiting for your approval.",
            "Your authenticator app asked you to approve a sign-in that we could not match to a device.",
            "A passkey enrolment was started on your account and needs confirmation.",
            "Your 2fa prompt was cancelled before it could complete; please re-approve the session.",
            "A totp code was requested for an unrecognised session on your tenant.",
            "We sent you an approve sign-in notification that was declined; confirm it was not you.",
            "Your magic link expired before the sign-in completed; request a new one from the portal.",
            "A webauthn device was registered on your account and needs verification.",
        ],
        'hook_cta': [
            "Open the link below to confirm or deny the session.",
            "Use the portal to approve the new device enrolment.",
            "Sign in to the identity dashboard to clear the pending prompt.",
            "Review the device registration from the account security page.",
        ],
    },

    # -------------------------------------------------------------------
    # 6. Modern SaaS lure — §5.1 #3, §3 SaaS lexicon
    # -------------------------------------------------------------------
    'modern_saas_lure': {
        'notes': (
            'Okta / 1Password / Workday / DocuSign / Atlassian / Salesforce '
            'credential-harvest lures. All brand tokens OOV.'
        ),
        'brands': [
            'Okta', '1Password', 'OneDrive', 'Workday', 'ADP', 'DocuSign',
            'Atlassian', 'Salesforce', 'Gusto', 'BambooHR', 'Rippling',
            'ServiceNow', 'Notion', 'Figma', 'Linear', 'Asana',
            'Monday', 'ClickUp', 'Airtable', 'Miro', 'Loom', 'Canva',
        ],
        'fake_domains': [
            'okta-portal.co', '1pass-hub.co', 'onedrive-hub.co',
            'workday-hub.co', 'adp-portal.co', 'docusign-hub.co',
            'atlas-hub.co', 'sf-access.co', 'gusto-hub.co',
            'bamboo-hub.co', 'rippling-hub.co', 'snow-hub.co',
            'linear-hub.co', 'asana-hub.co', 'notion-hub.co',
            'figma-hub.co',
        ],
        'hooks': [
            "Your {brand} workspace invited you to a new document.",
            "A {brand} credential is pending rotation on your account.",
            "Your {brand} access request moved forward and needs your confirmation.",
            "A {brand} team shared a restricted file with your mailbox.",
            "Your {brand} account was added to a new group by an administrator.",
            "A {brand} workflow is waiting on your signature in the review queue.",
            "Your {brand} directory sync flagged a policy update for you.",
            "A {brand} dashboard shared an activity report with your inbox.",
        ],
        'hook_cta': [
            "Open the {brand} portal to review the activity.",
            "Sign in to your {brand} account from the link below.",
            "Use the link to acknowledge the {brand} request.",
            "Review the pending action in your {brand} inbox.",
        ],
    },

    # -------------------------------------------------------------------
    # 7. QR-code / no-URL — §5.1 #6
    # -------------------------------------------------------------------
    'qr_code_no_url': {
        'notes': (
            'Zero URLs in body. Payload is described off-channel via QR or '
            'callback. body_url_count = 0 is a strong legit signal in the '
            'training data.'
        ),
        'brands': [
            'Corporate IT', 'Workplace Services', 'Facilities Team',
            'Mobile Services', 'HR Connect', 'IT Helpdesk',
            'Security Operations', 'Shared Services', 'Payroll Desk',
            'Records Office', 'Identity Platform', 'Compliance Desk',
            'Finance Desk', 'Document Services', 'Access Services',
            'Print Services',
        ],
        'fake_domains': [
            'corp-hub.co', 'workplace-co.co', 'facility-co.co',
            'mobile-hub.co', 'hr-connect.co', 'shared-ops.co',
            'records-co.co', 'identity-co.co', 'compliance.co',
            'finance-ops.co', 'docs-center.co', 'access-co.co',
            'print-center.co', 'mail-center.co', 'helpdesk-co.co',
            'corp-desk.co',
        ],
        'hooks': [
            "Your secure document is attached as a qr code and can be opened from your mobile device.",
            "The enrolment step uses the qr code on the attached page; please scan it with your phone.",
            "Voicemail attached; the full message is available after you scan the callback code below.",
            "A case id has been raised on your account; scan the qr code on the attached ticket for details.",
            "The attached invoice includes a qr code that routes you to our payments portal on mobile.",
            "Please scan to verify the attached identity card before your access is refreshed.",
            "The approved document can be scanned from the attached qr sheet using your phone.",
            "A case id and callback number are on the attached sheet; scan the qr code to reach the desk.",
        ],
        'hook_cta': [
            "Use the scan to verify option on the attached sheet.",
            "Open the qr code on your phone to continue.",
            "Scan the attached code to retrieve the document.",
            "Use your mobile scanner to access the next step.",
        ],
    },

    # -------------------------------------------------------------------
    # 8. Homoglyph domain — §5.1 #11
    # -------------------------------------------------------------------
    'homoglyph_domain': {
        'notes': (
            'IDN / Cyrillic lookalike domains. '
            '_vowel_consonant_ratio strips non-ASCII silently, so the '
            'engineered-feature view matches the real brand.'
        ),
        'brands': [
            'PayPal', 'Apple', 'Google', 'Microsoft', 'Adobe', 'Amazon',
            'Dropbox', 'GitHub', 'Netflix', 'Stripe', 'LinkedIn',
            'Coinbase', 'Shopify', 'Slack', 'Notion', 'Atlassian',
        ],
        # Cyrillic and Greek lookalikes for ASCII vowels. Mixed-script in
        # the main label but TLD kept ASCII so the domain parses. All
        # entries sized to 10–15 chars so R4 holds even after the non-
        # ASCII characters are silently dropped by `_vowel_consonant_ratio`.
        'fake_domains': [
            'pаypal.com',         # Cyrillic a
            'gоogle-id.com',      # Cyrillic o
            'microsоft.com',      # Cyrillic o
            'аpple-id.com',       # Cyrillic a
            'аmazon.com',
            'drоpbox.com',
            'netflіx.com',        # Cyrillic i
            'strіpe-hub.com',     # Cyrillic i
            'slack-sеc.com',      # Cyrillic e
            'nоtion-hub.com',
            'gіthub-hub.com',     # Cyrillic i
            'adоbe-hub.com',
            'lіnkedin.com',       # Cyrillic i
            'shоpify.com',
            'cоinbase.com',
            'atlassіan.com',
        ],
        'hooks': [
            "Your {brand} account flagged a new sign-in from an unrecognised device.",
            "Your {brand} workspace updated its security policy and requires acknowledgement.",
            "A pending verification step is open on your {brand} account.",
            "Your {brand} access review is due and has been routed to your inbox.",
            "A device change was recorded on your {brand} account and needs confirmation.",
            "A session on your {brand} profile is waiting on a quick review.",
            "A new recovery method was added to your {brand} account by an administrator.",
            "Your {brand} team initiated a policy refresh that requires your sign-off.",
        ],
        'hook_cta': [
            "Review the activity on your {brand} dashboard.",
            "Verify the session from your {brand} account page.",
            "Use the link to confirm the recent device change.",
            "Open your {brand} security centre to clear the item.",
        ],
    },
}


# ===========================================================================
# TONE PROFILES  (LAYER 1)
# ===========================================================================
#
# Each tone owns skeleton templates (3+). Skeletons are parameterised:
#   {greeting}, {hook}, {cta}, {filler_block}, {oov_seed}, {urgency},
#   {deadline}, {sign_off}, {brand}.
# Category content fills the {hook} and {cta} slots; shared banks fill the
# rest. Rotating across skeletons within the same tone preserves sentence
# structure variation within a consistent voice.

TONE_SKELETONS: dict[str, list[str]] = {
    'cold_automated': [
        (
            '{hook}\n\n'
            '{filler_block}\n\n'
            '{cta}\n\n'
            'Ref: {ref_id}. {oov_seed}.'
        ),
        (
            'Notification from {brand}.\n'
            '{hook}\n'
            '{urgency}\n'
            '{cta}\n'
            '{filler_block}\n'
            'Session id: {ref_id}. Keywords: {oov_seed}.'
        ),
        (
            '{hook}\n\n'
            '{filler_block}\n'
            'Action: {cta}\n'
            'Deadline: {deadline}.\n'
            'Trace: {ref_id} ({oov_seed}).'
        ),
        (
            '-- {brand} automated message --\n'
            '{hook}\n'
            '{filler_block}\n'
            '{cta}\n'
            'Context: {oov_seed}. Case {ref_id}.'
        ),
    ],
    'urgent_corporate': [
        (
            '{greeting}\n\n'
            '{hook} {urgency}\n\n'
            '{cta} {deadline}.\n\n'
            '{filler_block}\n\n'
            'Context for audit: {oov_seed}. Case reference {ref_id}.\n\n'
            '{sign_off}\n{brand}'
        ),
        (
            '{greeting}\n\n'
            'Per the policy review on your {brand} tenant, {hook}\n'
            '{urgency}\n\n'
            '{filler_block}\n\n'
            'Next step: {cta} {deadline}.\n\n'
            '{oov_seed}. Ref {ref_id}.\n\n'
            '{sign_off}'
        ),
        (
            '{greeting}\n\n'
            'This is a compliance notice covering an item on your {brand} account.\n'
            '{hook}\n\n'
            '{filler_block}\n\n'
            '{cta} {deadline}.\n\n'
            'Associated context: {oov_seed}. Notice id {ref_id}.\n\n'
            '{sign_off}'
        ),
    ],
    'friendly_helpful': [
        (
            '{greeting}\n\n'
            'Hope the week is going well. {hook}\n\n'
            '{filler_block}\n\n'
            '{cta} Whenever you have a free minute {deadline} is plenty of time.\n\n'
            'Quick heads up on the {oov_seed} side: {urgency}\n\n'
            '{sign_off}\n{brand}'
        ),
        (
            '{greeting}\n\n'
            "Just checking in on one item. {hook}\n\n"
            '{filler_block}\n\n'
            '{cta} No stress — {deadline} is the outer limit.\n\n'
            'For context, this flows through the {oov_seed} channel. Reference {ref_id}.\n\n'
            '{sign_off}'
        ),
        (
            '{greeting}\n\n'
            'Thanks for keeping on top of these items. {hook}\n'
            '{filler_block}\n'
            '{cta}\n'
            'Aim for {deadline}, and let us know if that is tight.\n'
            'Tagging the usual keywords for your search: {oov_seed}. Ticket {ref_id}.\n\n'
            '{sign_off}'
        ),
    ],
    'casual_brief': [
        (
            'hey\n{hook}\n{cta} {deadline}\nref {ref_id} / {oov_seed}'
        ),
        (
            '{hook}\n{cta}\n— sent from {brand} ({oov_seed})'
        ),
        (
            'quick one —\n{hook}\n{cta}\n{oov_seed}. {ref_id}'
        ),
        (
            '{hook}\n{cta} {deadline}.\n{filler_block}\n{oov_seed}.'
        ),
    ],
}


# Subject skeletons — short, no `!` or `?`, mildly tone-flavoured.
SUBJECT_SKELETONS: dict[str, list[str]] = {
    'cold_automated': [
        '{brand} notice — action required',
        '{brand} automated update',
        'Pending item on your {brand} account',
        '{brand} — reference {ref_id}',
        'Workflow queued on {brand}',
    ],
    'urgent_corporate': [
        '{brand} compliance review — action needed',
        'Time-sensitive: {brand} account review',
        '{brand} policy update requires acknowledgement',
        'Security notice for your {brand} tenant',
        '{brand} audit item pending',
    ],
    'friendly_helpful': [
        'Quick note on your {brand} account',
        'Heads up on {brand} — quick action',
        'Small follow-up from {brand}',
        'Nudge on your {brand} workflow',
        '{brand} — when you have a minute',
    ],
    'casual_brief': [
        '{brand} — quick one',
        'need your eyes on this — {brand}',
        '{brand} action',
        'small ask — {brand}',
        '{brand}',
    ],
}


# ===========================================================================
# HELPERS
# ===========================================================================

def _strip_bang_question(text: str) -> str:
    """Hard enforcement of R1 / R7 — no `!` or `?` anywhere."""
    return text.replace('!', '').replace('?', '')


def _sanitize_for_digits(text: str) -> str:
    """Nothing to strip in the body; R8 applies to the local part only.

    Kept as a named no-op so the call-site reads symmetrically with other
    rule enforcement.
    """
    return text


def _word_count(text: str) -> int:
    return len(text.split())


def _sample_filler_block(rng: random.Random, target_words: int) -> str:
    """Sample filler sentences until the paragraph hits the target word
    count (never by repeating the same sentence — LAYER 3 requirement).
    """
    pool = rng.sample(BODY_FILLERS, k=len(BODY_FILLERS))
    chosen: list[str] = []
    total = 0
    for sentence in pool:
        if total >= target_words:
            break
        chosen.append(sentence)
        total += len(sentence.split())
    return ' '.join(chosen)


def _ref_id(rng: random.Random) -> str:
    # Non-digit reference id (R8 only applies to the sender local part,
    # but alphanumeric tags read more naturally and keep digit density low).
    return '-'.join(''.join(rng.choices('ABCDEFGHJKMNPQRSTUVWXYZ', k=4))
                    for _ in range(2))


def _pick_oov_seed(rng: random.Random, count: int = 4) -> str:
    picks = rng.sample(MODERN_OOV_TERMS, k=count)
    return ', '.join(picks)


def _pick_sender(rng: random.Random, cat_cfg: dict) -> tuple[str, str]:
    """Build a sender string obeying R3 (local = shared-inbox token),
    R4 (pronounceable short domain), R8 (no digits in local).
    Returns (sender_string, domain).
    """
    local = rng.choice(SHARED_INBOX_TOKENS)
    domain = rng.choice(cat_cfg['fake_domains'])
    display_name = rng.choice(DISPLAY_NAMES)
    sender = f'"{display_name}" <{local}@{domain}>'
    return sender, domain


def _build_body(
    rng: random.Random,
    cat_cfg: dict,
    tone: str,
    length_bucket: str,
    brand: str,
    add_url: bool,
    category: str,
) -> str:
    skeleton = rng.choice(TONE_SKELETONS[tone])
    hook_template = rng.choice(cat_cfg['hooks'])
    cta_template = rng.choice(cat_cfg['hook_cta'])
    hook = hook_template.format(brand=brand)
    cta = cta_template.format(brand=brand)

    # Length-bucket target word count within (min, max).
    lo, hi = LENGTH_BUCKET_WORDS[length_bucket]
    # Aim high for long, low for short, middle for medium.
    if length_bucket == 'short':
        target_filler_words = rng.randint(10, 30)
    elif length_bucket == 'medium':
        target_filler_words = rng.randint(60, 130)
    else:  # long
        target_filler_words = rng.randint(350, 550)

    filler_block = _sample_filler_block(rng, target_filler_words)

    # For qr_code_no_url category we never inject a URL into the body.
    url = ''
    if add_url and category != 'qr_code_no_url':
        # Body URL (R2) — at most one. Use the same fake domain family.
        domain = rng.choice(cat_cfg['fake_domains'])
        path = rng.choice(['secure', 'portal', 'review', 'sso', 'verify',
                           'approve', 'sign', 'review-document', 'confirm'])
        url = f'https://{domain}/{path}'
        # Append URL into the filler block so the skeleton itself does
        # not need a URL slot.
        filler_block = f'{filler_block} {url}'

    body = skeleton.format(
        greeting=rng.choice(GREETINGS),
        hook=hook,
        cta=cta,
        filler_block=filler_block,
        urgency=rng.choice(URGENCY_PHRASES),
        deadline=rng.choice(DEADLINES),
        sign_off=rng.choice(SIGN_OFFS),
        brand=brand,
        ref_id=_ref_id(rng),
        oov_seed=_pick_oov_seed(rng),
    )

    # Pad up with extra filler sentences if we are below the length-bucket
    # minimum, or truncate sentences from the tail if we are above the max.
    words = body.split()
    if len(words) < lo:
        extra = _sample_filler_block(rng, lo - len(words) + rng.randint(5, 15))
        body = body + '\n\n' + extra
    words = body.split()
    if len(words) > hi:
        # Truncate on a word boundary, finishing at the nearest sentence
        # terminator to keep the text coherent.
        trimmed = ' '.join(words[:hi])
        # Trim back to the last period / newline to avoid mid-sentence cuts.
        for sep in ('\n', '. '):
            cut = trimmed.rfind(sep)
            if cut > int(hi * 0.6):
                trimmed = trimmed[:cut + len(sep)].strip()
                break
        body = trimmed

    # R6 — guarantee a modern OOV token survives any truncation above. If
    # the trim stripped the `{oov_seed}` tail, append a compact reference
    # line using an OOV term so body_lower always intersects the bank.
    body_lower_check = body.lower()
    if not any(tok in body_lower_check for tok in MODERN_OOV_TERMS):
        body = body + f'\nContext: {_pick_oov_seed(rng, count=2)}.'

    return _strip_bang_question(body).strip()


def _applied_rules(body: str, subject: str, sender: str, category: str,
                   body_url_count: int) -> list[str]:
    """Record which hard rules this email actually satisfies.

    Every phishing row is generated to comply with R1–R8; this function
    returns the subset that *strictly* holds for the concrete email, so
    the investigation notebook Section 4 can attribute failures to the
    rules that are empirically in effect.
    """
    rules: list[str] = []
    if '!' not in body and '?' not in body and '!' not in subject and '?' not in subject:
        rules.append('R1')
    if body_url_count <= 1:
        rules.append('R2')
    # R3 — local part is a shared-inbox token.
    if '<' in sender and '@' in sender:
        local = sender.split('<', 1)[1].split('@', 1)[0].lower().strip()
        if local in SHARED_INBOX_TOKENS:
            rules.append('R3')
        # R8 — no digits in local part.
        if not any(c.isdigit() for c in local):
            rules.append('R8')
    # R4 — pronounceable short domain (10–15 chars).
    if '@' in sender and '<' in sender and '>' in sender:
        domain = sender.split('@', 1)[1].rstrip('>').strip()
        if 10 <= len(domain) <= 15:
            rules.append('R4')
    # R5 — 150–400 words.
    wc = _word_count(body)
    if R5_MIN_WORDS <= wc <= R5_MAX_WORDS:
        rules.append('R5')
    # R6 — modern OOV token present.
    body_lower = body.lower()
    if any(tok in body_lower for tok in MODERN_OOV_TERMS):
        rules.append('R6')
    # R7 — zero `!` anywhere.
    if '!' not in body and '!' not in subject:
        rules.append('R7')
    return rules


# ===========================================================================
# MAIN GENERATION LOOP
# ===========================================================================

def _length_tone_grid(rng: random.Random) -> list[tuple[str, str]]:
    """Produce 200 (length_bucket, tone) assignments respecting
    LENGTH_DISTRIBUTION (60 / 80 / 60) and rotating tones evenly inside
    each bucket.
    """
    assignments: list[tuple[str, str]] = []
    for bucket, n in LENGTH_DISTRIBUTION.items():
        # Tone distribution within the bucket: split n into quarters, with
        # any remainder going to the first few tones.
        per_tone = [n // len(TONES)] * len(TONES)
        for i in range(n % len(TONES)):
            per_tone[i] += 1
        for tone, k in zip(TONES, per_tone):
            assignments.extend([(bucket, tone)] * k)
    rng.shuffle(assignments)
    return assignments


def generate_category(category: str, cat_cfg: dict, rng: random.Random
                      ) -> list[dict]:
    rows: list[dict] = []
    for bucket, tone in _length_tone_grid(rng):
        brand = rng.choice(cat_cfg['brands'])
        sender, _domain = _pick_sender(rng, cat_cfg)
        subject_skel = rng.choice(SUBJECT_SKELETONS[tone])
        subject = subject_skel.format(brand=brand, ref_id=_ref_id(rng))
        subject = _strip_bang_question(subject).strip()

        # R2 — body_url_count must be 0 or 1. Bias 70% -> 1 url, 30% -> 0,
        # except qr_code_no_url which is always 0.
        if category == 'qr_code_no_url':
            add_url = False
        else:
            add_url = rng.random() < 0.7

        body = _build_body(rng, cat_cfg, tone, bucket, brand, add_url, category)

        # Cheap URL count via the same combined pattern used in
        # inference/preprocessing.py — good enough here for rule tagging.
        body_url_count = body.count('http://') + body.count('https://')
        rules = _applied_rules(body, subject, sender, category, body_url_count)
        rows.append({
            'sender': sender,
            'subject': subject,
            'body': body,
            'label': 1,
            'category': category,
            'tone_profile': tone,
            'length_bucket': bucket,
            'exploit_rules_applied': ','.join(rules),
            'notes': cat_cfg['notes'],
        })
    return rows


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    for category, cfg in CATEGORIES.items():
        rows = generate_category(category, cfg, RNG)
        if len(rows) != EMAILS_PER_CATEGORY:
            raise RuntimeError(
                f'category {category} produced {len(rows)} rows, expected '
                f'{EMAILS_PER_CATEGORY}'
            )
        all_rows.extend(rows)

    fieldnames = [
        'sender', 'subject', 'body', 'label', 'category', 'tone_profile',
        'length_bucket', 'exploit_rules_applied', 'notes',
    ]
    with OUT_PATH.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f'wrote {len(all_rows)} rows to {OUT_PATH}')
    # Quick per-category summary.
    from collections import Counter
    cat_count = Counter(r['category'] for r in all_rows)
    for cat, n in cat_count.items():
        print(f'  {cat:26s} {n}')


if __name__ == '__main__':
    main()
