"""Generate 1500 modern-technique phishing emails (label=1) across five distinct subtypes.

Follows section 4.3 of online_learning_dataset.md.

Subtypes (300 rows each):
  1. QR code phishing       (category: modern_technique_qr_code)
  2. Cryptocurrency scams   (category: modern_technique_crypto)
  3. AI-generated polished  (category: modern_technique_ai_polished)
  4. Callback phishing      (category: modern_technique_callback)
  5. Multi-stage phishing   (category: modern_technique_multistage)

Each subtype has its own sender pool, subject bank, body bank, phishing-signal gate, and
category label. The subtypes are kept structurally distinct (QR has no URL-in-body
requirement; callback forbids URLs entirely; multi-stage uses Re:/Fwd: prefixes, etc.).
"""

from __future__ import annotations

import csv
import hashlib
import random
import re
import string
from collections import Counter
from pathlib import Path

random.seed(20260418)

OUT_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/modern_technique_phishing.csv"
)


# ------------------------------------------------------------------------------------
# Shared pools
# ------------------------------------------------------------------------------------

FIRST_NAMES = [
    "Sarah", "John", "Emma", "Michael", "Priya", "David", "Rachel", "Tom",
    "Olivia", "James", "Nina", "Marcus", "Ellie", "Hassan", "Amelia", "Dan",
    "Clara", "Theo", "Ruth", "Leo", "Maya", "Jay", "Kate", "Ben", "Liam",
    "Sophie", "Matt", "Aisha", "Chen", "Ravi",
]

LAST_NAMES = [
    "Smith", "Johnson", "Patel", "Chen", "Miller", "Rodriguez", "Wilson",
    "Taylor", "Nguyen", "Brown", "Davis", "Garcia", "Khan", "Kim", "Singh",
    "Foster", "Parker", "Morgan", "Cohen", "Reed", "Nakamura",
]


def pick(seq):
    return random.choice(seq)


def ref_number(prefix="REF", digits=7):
    return f"{prefix}-{''.join(random.choices(string.digits, k=digits))}"


def phone_number():
    area = random.choice(["888", "877", "866", "855", "844", "833"])
    middle = f"{random.randint(200, 999):03d}"
    end = f"{random.randint(0, 9999):04d}"
    return f"+1 ({area}) {middle}-{end}"


def wallet_address():
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))


PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def fill(template: str, ctx: dict) -> str:
    def repl(m):
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))
    return PLACEHOLDER_RE.sub(repl, template)


# ------------------------------------------------------------------------------------
# SUBTYPE 1: QR code phishing
# ------------------------------------------------------------------------------------

QR_SENDERS = [
    '"FedEx Delivery" <tracking@fedex-delivery-portal.co>',
    '"UPS Tracking" <tracking@ups-package-portal.net>',
    '"USPS Notifications" <delivery@usps-track-portal.co>',
    '"DHL Express" <shipment@dhl-shipments.net>',
    '"Microsoft Security" <no-reply@ms-account-verify.co>',
    '"Apple Support" <support@apple-account-portal.net>',
    '"Okta" <no-reply@okta-verify-portal.co>',
    '"Duo Security" <duo@duo-enrolment.net>',
    '"Amazon Delivery" <delivery@amazon-track-portal.co>',
    '"IT Security" <security@it-verify-portal.net>',
]

QR_SUBJECTS = [
    "Scan to verify your account",
    "QR code: complete your setup",
    "Delivery on hold — scan to release",
    "Scan the QR code to confirm your identity",
    "Your package requires signature — scan to release",
    "QR verification needed to restore mailbox access",
    "Complete your multi-factor setup via QR code",
    "Scan to finalise your account recovery",
    "QR code: authorise your recent sign-in",
    "Package delivery update — scan to confirm address",
]

QR_BODIES = [
    (
        "Hello {me},\n\nYour recent sign-in to our service requires one additional verification "
        "step to comply with our updated security policy. Please scan the QR code below with "
        "your mobile phone camera to authorise the session and restore full access.\n\n"
        "[QR CODE IMAGE — scan with your phone camera]\n\nThe QR code must be scanned within "
        "the next 24 hours. Email-based links are not supported for this verification step; "
        "please use your phone so the scan is bound to your mobile device for your protection."
        "\n\nThank you,\nAccount Security"
    ),
    (
        "Hello {me},\n\nWe tried to deliver a package to your address but could not complete "
        "the delivery without a signature. To release the parcel and confirm your delivery "
        "window, please scan the QR code below with your phone camera.\n\n[QR CODE IMAGE — "
        "scan to release the package]\n\nThe scan must be completed within 24 hours. Please "
        "use your phone — the confirmation is bound to the mobile device that scans the code. "
        "Reference: {ref}\n\nThank you,\nDelivery Notifications"
    ),
    (
        "Hi {me},\n\nAs part of our mandatory multi-factor rollout, all users must complete a "
        "one-time device enrolment. The enrolment is initiated by scanning the QR code "
        "below with your mobile phone camera.\n\n[QR CODE IMAGE — scan with your phone]\n\n"
        "Please complete the enrolment by end of day. Accounts that have not enrolled will be "
        "placed in a read-only state until the scan is completed. Reference: {ref}\n\n"
        "Thank you,\nIT Security"
    ),
    (
        "Hello {me},\n\nWe detected a sign-in attempt to your account from a device we don't "
        "recognise and have paused access while we verify. To restore normal access, please "
        "scan the QR code below with your phone to confirm the session.\n\n[QR CODE IMAGE — "
        "scan to authorise]\n\nFor your protection, verification is done via your phone — the "
        "scan binds the approval to a trusted device. The QR code expires in 24 hours. "
        "Reference: {ref}\n\nThank you,\nAccount Security"
    ),
    (
        "Hi {me},\n\nYour mailbox quota was recently exceeded and new messages are being "
        "held. To release the queue and restore normal delivery, please scan the QR code "
        "below from your mobile phone.\n\n[QR CODE IMAGE — scan to release]\n\nThe QR code "
        "expires in 24 hours. Please use your phone camera rather than a desktop scanner — "
        "the confirmation is tied to your mobile device for security.\n\nReference: {ref}\n\n"
        "Thank you,\nMailbox Administration"
    ),
    (
        "Hello {me},\n\nYour recent request to reset your account credentials is almost "
        "complete. The final step is a QR-based verification so we can bind the new "
        "credentials to your phone.\n\n[QR CODE IMAGE — scan with your phone camera]\n\n"
        "Please scan the code with your phone within 24 hours. Desktop scanners are not "
        "accepted for this step — the scan must originate from a mobile device. Reference: "
        "{ref}\n\nThank you,\nAccount Recovery Team"
    ),
    (
        "Hi {me},\n\nA recent transaction on your account was flagged for additional "
        "verification. To authorise the transaction and avoid it being reversed, please scan "
        "the QR code below from your mobile phone.\n\n[QR CODE IMAGE — scan to authorise]\n\n"
        "For your protection, authorisation can only be completed from your phone. The code "
        "is single-use and expires within 24 hours. Reference: {ref}\n\nThank you,\nFraud "
        "Prevention Team"
    ),
]

QR_SUFFIXES = [
    "This verification method is used because email-based confirmation links can be "
    "intercepted or forwarded. The QR scan ties the approval to the device in your hand, "
    "which provides an additional layer of protection for your account going forward.",
    "If you have trouble scanning the code, please retry in a well-lit area and hold your "
    "phone steady about six inches from the screen. Support can assist if the scan "
    "continues to fail after a second attempt from a different location.",
    "Once the scan completes, your phone will display a short confirmation screen. Please "
    "keep the confirmation visible for a few seconds so the binding is fully registered "
    "on our end before you close the session on your device.",
    "For the scan to complete successfully, please use the default camera app rather than "
    "a third-party QR reader. The default camera is pre-authorised by our verification "
    "system and will handle the handshake automatically in the background for you.",
    "We appreciate your patience while we complete this one-time verification step. The "
    "additional check helps us keep your account secure and limits the window in which a "
    "compromised password could be used by someone else without your knowledge.",
]


# ------------------------------------------------------------------------------------
# SUBTYPE 2: Cryptocurrency scams
# ------------------------------------------------------------------------------------

CRYPTO_SENDERS = [
    '"Coinbase" <security@coinbase-alerts.net>',
    '"Coinbase" <no-reply@coinbase-verify.co>',
    '"Binance" <security@binance-alerts.net>',
    '"Binance" <support@binance-secure.co>',
    '"Kraken" <no-reply@kraken-verify.net>',
    '"Kraken Support" <support@kraken-security.co>',
    '"MetaMask" <alerts@metamask-wallet.co>',
    '"MetaMask" <no-reply@metamask-verify.net>',
    '"Trust Wallet" <support@trust-wallet-verify.co>',
    '"Ledger" <security@ledger-verify.net>',
]

CRYPTO_SUBJECTS = [
    "Suspicious login to your crypto wallet",
    "Withdraw your Bitcoin rewards",
    "Urgent: secure your wallet from unauthorised access",
    "Your crypto withdrawal is pending verification",
    "Unusual activity on your Coinbase account",
    "Your Binance account access has been paused",
    "Claim your Ethereum airdrop — expires soon",
    "Action required: verify your MetaMask wallet",
    "Your Kraken withdrawal requires confirmation",
    "Secure your Ledger account after detected threat",
    "New device detected on your wallet — confirm now",
    "Bitcoin staking rewards ready for withdrawal",
]

CRYPTO_BODIES = [
    (
        "Dear {me},\n\nOur security team detected a suspicious sign-in to your wallet from an "
        "IP address we don't recognise. For your protection, withdrawals and transfers have "
        "been paused while we verify the activity.\n\nTo confirm ownership and restore full "
        "access, please verify your wallet here: {url}\n\nCase reference: {ref}. Wallet ID "
        "ending in {wallet_tail}. If you don't verify within 24 hours, the wallet will be "
        "temporarily locked as a precaution.\n\nThank you,\n{brand} Security Team"
    ),
    (
        "Dear {me},\n\nYou are eligible to claim {amount} in staking rewards that accrued on "
        "your {brand} account over the last quarter. The rewards must be claimed before the "
        "end of the month or they will be returned to the pool.\n\nClaim here: {url}\n\n"
        "Reference: {ref}. Destination wallet ending in {wallet_tail}. The claim process "
        "requires a one-time verification — please make sure you have access to your seed "
        "phrase.\n\nBest regards,\n{brand} Rewards Team"
    ),
    (
        "Dear {me},\n\nA withdrawal of {amount} has been initiated from your wallet to an "
        "address we haven't seen before. If you authorised this, no action is needed. If "
        "not, please cancel it immediately.\n\nReview the transaction: {url}\n\nTransaction "
        "reference: {ref}. Origin wallet ending in {wallet_tail}. Cancellation must be "
        "completed within 24 hours — after that the withdrawal will be irreversible.\n\n"
        "Regards,\n{brand} Fraud Prevention"
    ),
    (
        "Hello {me},\n\nAs part of our exchange-wide security review, all users are asked to "
        "re-verify ownership of their wallet within the next 48 hours. Accounts that do not "
        "complete verification will be placed in read-only mode pending manual review.\n\n"
        "Begin verification: {url}\n\nReference: {ref}. Wallet ending in {wallet_tail}. The "
        "process takes under two minutes — please complete it today to avoid any disruption "
        "to pending withdrawals.\n\nThank you,\n{brand} Account Team"
    ),
    (
        "Dear {me},\n\nA new device has been added to your {brand} account. If this was you, "
        "no action is required. If you don't recognise the activity, your account may have "
        "been compromised and we recommend securing it immediately.\n\nReview the device and "
        "secure your wallet: {url}\n\nCase reference: {ref}. Wallet ending in {wallet_tail}. "
        "For your protection, withdrawals have been paused until the device is confirmed.\n\n"
        "Regards,\n{brand} Security"
    ),
    (
        "Hello {me},\n\nYou have a pending airdrop allocation of {amount} tokens connected to "
        "your wallet. The tokens must be claimed within 72 hours or they will be redistributed "
        "to other holders.\n\nClaim: {url}\n\nAllocation reference: {ref}. Eligible wallet "
        "ending in {wallet_tail}. Please make sure the wallet is active and the recovery "
        "phrase is available in case additional verification is required.\n\nRegards,\n"
        "{brand} Token Distribution"
    ),
    (
        "Dear {me},\n\nYour recent withdrawal of {amount} from your {brand} account is "
        "awaiting one final verification step before it is released. This is a standard "
        "check for withdrawals above the daily limit.\n\nComplete verification: {url}\n\n"
        "Reference: {ref}. Destination wallet ending in {wallet_tail}. If the verification "
        "is not completed within 24 hours, the withdrawal will be reversed and the funds "
        "returned to your balance.\n\nBest regards,\n{brand} Withdrawals Team"
    ),
]


CRYPTO_URLS = [
    "coinbase-alerts.net/verify", "coinbase-verify.co/signin",
    "binance-alerts.net/secure", "binance-secure.co/verify",
    "kraken-verify.net/restore", "kraken-security.co/account",
    "metamask-wallet.co/unlock", "metamask-verify.net/signin",
    "trust-wallet-verify.co/restore", "ledger-verify.net/secure",
]

CRYPTO_BRANDS = ["Coinbase", "Binance", "Kraken", "MetaMask", "Trust Wallet", "Ledger"]

CRYPTO_AMOUNTS = [
    "0.125 BTC", "0.3 BTC", "2.4 ETH", "5.8 ETH", "1,250 USDT", "480 USDT",
    "3,200 USDC", "1.75 ETH", "0.08 BTC", "600 USDC",
]

CRYPTO_SUFFIXES = [
    "Please ensure that the recovery phrase for your wallet is stored in a secure, "
    "offline location. Under no circumstances should you share the phrase with anyone, "
    "including members of our own support team or anyone claiming to represent us.",
    "Our support team will never ask you to approve a transaction over email or chat. "
    "All approvals are completed inside your verified session on the {brand} platform "
    "using the secure link above, which is tied to your current authenticated device.",
    "If you believe your wallet has been compromised at any point, please revoke any "
    "connected applications immediately and transfer the balance to a new wallet "
    "created from an offline recovery phrase held in a separate, trusted location.",
    "A full activity log is available inside your account dashboard. Reviewing the log "
    "can help you identify whether the event was initiated by a connected service you "
    "authorised previously or by an unknown third party that should be revoked.",
    "Once the verification is complete, please allow up to two hours for the new "
    "security settings to propagate across all endpoints of our service. You may "
    "continue to receive related alerts during that window, which can be safely ignored.",
]


# ------------------------------------------------------------------------------------
# SUBTYPE 3: AI-generated polished phishing (banks / gov / healthcare)
# ------------------------------------------------------------------------------------

AI_SENDERS = [
    '"IRS Notifications" <notices@irs-tax-portal.co>',
    '"HM Revenue & Customs" <no-reply@hmrc-tax-refund.net>',
    '"SSA Administration" <admin@ssa-service-portal.co>',
    '"Treasury Department" <notices@treasury-updates.net>',
    '"Blue Cross Blue Shield" <no-reply@bcbs-member-portal.co>',
    '"United Healthcare" <member@uhc-member-portal.net>',
    '"NHS Digital" <no-reply@nhs-member-services.co>',
    '"Kaiser Permanente" <member@kp-member-portal.net>',
    '"Capital One" <alerts@capitalone-member.co>',
    '"Chase Alerts" <no-reply@chase-member-alerts.net>',
    '"HSBC" <alerts@hsbc-customer-portal.co>',
    '"Citi Bank" <alerts@citi-member-portal.net>',
]

AI_SUBJECTS = [
    "Your tax refund is ready for collection",
    "Important update to your health insurance coverage",
    "Action required on your tax return {tax_year}",
    "Your benefits statement is available",
    "Update regarding your {tax_year} tax return",
    "Your monthly account statement is ready",
    "Notice: annual premium adjustment effective next cycle",
    "Important: verify your bank account information",
    "Your health insurance enrolment is pending confirmation",
    "Confirmation of your recent tax filing",
    "New secure message from your bank",
    "Important notice regarding your member benefits",
]

AI_BODIES = [
    (
        "Dear {me},\n\nFollowing a review of your {tax_year} tax return, we have determined "
        "that you are entitled to a refund of {amount}. In order to process the payment, we "
        "require that you confirm your bank details through the secure member portal.\n\n"
        "Please complete the form at: {url}\n\nReference number: {ref}. Claim period: "
        "{tax_year}. All communications regarding this refund are also available in your "
        "member portal under the 'Notices' tab.\n\nIf you have any questions, please reach "
        "out through the secure messaging channel in the portal. Please do not respond to "
        "this email directly — replies are not monitored.\n\nKind regards,\n{brand}"
    ),
    (
        "Dear {me},\n\nWe are writing to inform you of an important update to your health "
        "insurance coverage that will take effect in the next enrolment cycle. The update "
        "reflects a change to your plan's preventative-care benefits and requires a short "
        "confirmation from you.\n\nReview and confirm: {url}\n\nMember reference: {ref}. "
        "Plan year: {tax_year}. You will be asked to sign in and verify the details we hold "
        "on file. The process takes approximately four minutes.\n\nIf you have any questions, "
        "please use the secure messaging feature in your member portal.\n\nKind regards,\n"
        "{brand} Member Services"
    ),
    (
        "Dear {me},\n\nYour monthly statement for the period ending {month} has been prepared "
        "and is now available in your online banking portal. Please sign in to review the "
        "statement and confirm that all transactions listed are correct.\n\nAccess your "
        "statement: {url}\n\nStatement reference: {ref}. Account ending in {acct_tail}. "
        "Any disputed transactions should be flagged within 30 days of the statement date.\n"
        "\nIf you have any questions, please reach out through the secure messaging channel "
        "in your online banking.\n\nKind regards,\n{brand}"
    ),
    (
        "Dear {me},\n\nAs part of our annual compliance review, we are asking all members to "
        "verify the bank account information we hold on file. This ensures that any payments "
        "or refunds are directed to the correct account and prevents delays in processing.\n"
        "\nVerify your details at: {url}\n\nReference: {ref}. Member account ending in "
        "{acct_tail}. The verification can be completed in approximately three minutes and "
        "does not require any documents to be uploaded.\n\nWe appreciate your co-operation. "
        "Please do not reply directly to this message — replies are not monitored.\n\n"
        "Kind regards,\n{brand}"
    ),
    (
        "Dear {me},\n\nWe have completed a review of your recent tax filing for {tax_year} "
        "and determined that an adjustment is required. The adjusted figures are available "
        "in your secure online portal along with a short explanation of the change.\n\n"
        "Review the adjustment: {url}\n\nReference number: {ref}. Filing period: {tax_year}. "
        "You will need to acknowledge the adjustment within the standard 30-day window, "
        "otherwise the original figures will be finalised as filed.\n\nKind regards,\n"
        "{brand} Compliance Team"
    ),
    (
        "Dear {me},\n\nThis is a courtesy notice regarding an upcoming premium adjustment "
        "that will take effect in your next billing cycle. The adjustment is the result of "
        "our annual review and is consistent with the policies published in your member "
        "handbook.\n\nReview the details: {url}\n\nMember reference: {ref}. Plan year: "
        "{tax_year}. Please take a moment to review the updated figures and confirm your "
        "current payment method. This helps us avoid any interruption to coverage.\n\n"
        "Kind regards,\n{brand} Member Services"
    ),
    (
        "Dear {me},\n\nWe have received a request to update the contact information on your "
        "account. If the request was initiated by you, no further action is required. If "
        "the change was not authorised by you, please review the activity as soon as "
        "possible.\n\nReview the request: {url}\n\nCase reference: {ref}. Account ending "
        "in {acct_tail}. For your protection, the changes will not be applied until you "
        "confirm them through the secure portal.\n\nKind regards,\n{brand} Account Security"
    ),
]

AI_URLS = [
    "irs-tax-portal.co/refund", "hmrc-tax-refund.net/claim",
    "ssa-service-portal.co/benefits", "treasury-updates.net/notice",
    "bcbs-member-portal.co/plan", "uhc-member-portal.net/plan",
    "nhs-member-services.co/confirm", "kp-member-portal.net/plan",
    "capitalone-member.co/statement", "chase-member-alerts.net/statement",
    "hsbc-customer-portal.co/verify", "citi-member-portal.net/verify",
]

AI_SUFFIXES = [
    "Please ensure that the email address we have on file remains current before "
    "completing the process. Any correspondence regarding this matter will be sent to "
    "the address associated with your member record to keep our records consistent.",
    "For your convenience, this notice is also available inside your member portal "
    "under the Notifications tab. If you prefer, you can review and action the request "
    "directly from within your authenticated session rather than through this message.",
    "If you require assistance at any point during the process, our support team can "
    "be reached through the secure messaging feature in your portal. Please reference "
    "the case number above in any communication so we can locate the record quickly.",
    "We remain committed to handling your information in line with applicable data "
    "protection standards. All submissions are processed over an encrypted connection "
    "and retained for the minimum period required by our internal retention policy.",
    "If the deadline in this notice cannot be met, please request an extension through "
    "the portal before the original date. Extension requests are typically reviewed "
    "within three working days of submission and you will be notified of the outcome.",
]


# ------------------------------------------------------------------------------------
# SUBTYPE 4: Callback phishing — NO URLS, phone number only.
# ------------------------------------------------------------------------------------

CB_SENDERS = [
    '"PayPal Security" <security@paypal-account-services.co>',
    '"PayPal Billing" <billing@paypal-member-center.net>',
    '"Amazon Customer Support" <billing@amazon-account-support.co>',
    '"Amazon Billing" <no-reply@amazon-billing-portal.net>',
    '"Apple Support" <support@apple-billing-support.co>',
    '"Apple Billing" <billing@apple-member-services.net>',
    '"Norton Subscription" <billing@norton-subscription-desk.co>',
    '"Geek Squad" <billing@geeksquad-subscription-desk.net>',
    '"Chase Security" <alerts@chase-card-services.co>',
    '"Bank of America" <alerts@bofa-card-services.net>',
]

CB_SUBJECTS = [
    "Suspicious charge on your account — call us immediately",
    "Unusual activity detected — please contact our support line",
    "Your subscription has been renewed — call to cancel",
    "Recent transaction requires your confirmation",
    "Payment declined — please call to reinstate your account",
    "Large charge pending on your card — call to verify",
    "Your annual subscription will be renewed — call to cancel",
    "Unauthorised charge flagged — immediate action required",
    "Please call to confirm your recent order",
    "Account security alert — call our hotline today",
]

CB_BODIES = [
    (
        "Dear {me},\n\nWe have detected a charge of {amount} on your account that does not "
        "match your usual spending pattern. For your protection, the transaction has been "
        "placed on hold pending your confirmation.\n\nIf you did not authorise this charge, "
        "please call our customer support line immediately to cancel the transaction.\n\n"
        "Customer support: {phone}\nCase reference: {ref}\n\nOur support line is available "
        "24 hours a day. Please have your account number ready when you call. Do not "
        "respond to this email — the case can only be resolved by phone.\n\nKind regards,\n"
        "{brand} Customer Protection"
    ),
    (
        "Dear {me},\n\nYour annual subscription to {brand} has been scheduled for automatic "
        "renewal. The renewal amount of {amount} will be charged to your card on file within "
        "48 hours.\n\nIf you wish to cancel the renewal or make changes to your subscription, "
        "please call our billing support line.\n\nBilling support: {phone}\nReference: "
        "{ref}\n\nOur billing team is available Monday to Sunday from 8am to 10pm local "
        "time. Please do not reply to this email — cancellation requests can only be "
        "processed over the phone.\n\nKind regards,\n{brand} Billing Team"
    ),
    (
        "Dear {me},\n\nA payment of {amount} from your account could not be processed and "
        "the recurring service linked to it has been suspended. To reinstate the service "
        "and update your payment method, please call our support team.\n\nSupport line: "
        "{phone}\nCase reference: {ref}\n\nOur support line is available 24 hours. Please "
        "have your account details ready when calling. Replies to this email are not "
        "monitored and will not resolve the issue.\n\nKind regards,\n{brand} Billing "
        "Support"
    ),
    (
        "Dear {me},\n\nWe detected unusual activity on your account involving a recent "
        "transaction of {amount}. For your protection, we have paused further charges until "
        "we can confirm the activity with you directly.\n\nPlease call our fraud prevention "
        "line as soon as possible.\n\nFraud prevention: {phone}\nCase reference: {ref}\n\n"
        "Our fraud team is available around the clock. Please do not reply to this email — "
        "for security reasons, cases involving card activity are handled over the phone "
        "only.\n\nKind regards,\n{brand} Fraud Prevention"
    ),
    (
        "Dear {me},\n\nYour recent order on {brand} totalling {amount} has been flagged for "
        "confirmation before being shipped. This is a routine check we run on larger orders "
        "to make sure the purchase was authorised by the account holder.\n\nCall our "
        "customer service team: {phone}\nOrder reference: {ref}\n\nOur customer service "
        "team is available Monday to Sunday from 6am to midnight local time. Replies to "
        "this email cannot release the order — please call to confirm.\n\nKind regards,\n"
        "{brand} Order Team"
    ),
    (
        "Dear {me},\n\nWe have been unable to reach you regarding the pending charge of "
        "{amount} on your {brand} account. For your protection, the charge has been "
        "temporarily blocked and your account has been flagged for review.\n\nTo release "
        "the charge or dispute the transaction, please call our support line.\n\nSupport "
        "line: {phone}\nCase reference: {ref}\n\nThe support line is available 24 hours. "
        "Please do not respond to this email — replies are not monitored for this case "
        "type.\n\nKind regards,\n{brand} Account Services"
    ),
    (
        "Dear {me},\n\nYour subscription to {brand} has been extended automatically and the "
        "corresponding charge of {amount} will appear on your statement shortly. If this "
        "renewal was not expected, you can cancel the subscription and request a refund by "
        "calling our billing desk.\n\nBilling desk: {phone}\nReference: {ref}\n\nOur "
        "billing team can be reached during normal business hours. Please do not reply to "
        "this email — cancellations can only be processed over the phone.\n\nKind regards,\n"
        "{brand} Subscription Services"
    ),
]

CB_BRANDS = {
    "paypal": "PayPal",
    "amazon": "Amazon",
    "apple": "Apple",
    "norton": "Norton",
    "geeksquad": "Geek Squad",
    "chase": "Chase",
    "bofa": "Bank of America",
}

CB_AMOUNTS = ["$349.99", "$499.00", "$629.95", "$879.50", "$1,249.00", "$249.99", "$899.00"]

CB_SUFFIXES = [
    "Please have the case reference above to hand when you call so our agent can "
    "access the record quickly. The reference is tied to your account and expires "
    "at the end of the review window noted in our internal records for this case.",
    "If the phone number above is busy, please try again shortly. Call volumes can "
    "be higher in the early part of the day, and wait times are typically shorter "
    "later in the afternoon once the initial morning queue has been worked through.",
    "For your protection, our agents will never ask for your full password or the "
    "three-digit security code printed on the back of your card during the call. "
    "They only need details already known to you through your existing account.",
    "After your call, a written confirmation will be generated and stored against "
    "your account for your records. You can request a copy of the confirmation by "
    "phone at any point within the next ninety days from the date of the call.",
    "This notice is intentionally brief. For detailed information about the case we "
    "recommend speaking with one of our agents, who can walk through the transaction "
    "history and next steps with you directly during a single phone conversation.",
]


# ------------------------------------------------------------------------------------
# SUBTYPE 5: Multi-stage phishing — benign first-contact, references a fake prior.
# ------------------------------------------------------------------------------------

MS_SENDERS = [
    '"Jane Cooper" <jane.cooper@consulting-group-partners.net>',
    '"Mark Hughes" <mark.hughes@strategy-advisory-partners.co>',
    '"Laura Kim" <laura.kim@corporate-consult-partners.net>',
    '"Andrew Walsh" <andrew.walsh@business-advisory-team.co>',
    '"Rachel Moreno" <rachel.moreno@markets-insight-group.net>',
    '"David Chen" <david.chen@exec-advisory-team.co>',
    '"Sophie Turner" <sophie.turner@opportunity-partners.net>',
    "\"James O'Neill\" <james.oneill@procurement-partner-desk.co>",
    '"Emma Richards" <emma.richards@supply-network-group.net>',
    '"Marcus Lane" <marcus.lane@enterprise-solutions-desk.co>',
]

MS_SUBJECTS = [
    "Re: your recent inquiry",
    "Following up on our earlier conversation",
    "Re: the proposal we discussed",
    "As promised — the document from our call",
    "Re: our chat last week",
    "Following up — next steps",
    "Re: quick question from yesterday",
    "Following up on the form you requested",
    "Re: the materials you asked for",
    "Following up on our conversation",
    "Re: our phone call earlier",
    "Following up — the files we discussed",
]

MS_BODIES = [
    (
        "Hi {me},\n\nThanks for the call earlier — sorry I had to run before we finished "
        "walking through the numbers. As promised, I've pulled together the document we "
        "discussed and shared it with you so you can take a closer look before our next "
        "session.\n\nThe document is here: {url}\n\nLet me know if anything is unclear or if "
        "there are sections you'd like me to rework. I'm around most of this week and happy "
        "to hop on a quick call if that's easier.\n\nBest,\n{sender_first}"
    ),
    (
        "Hi {me},\n\nFollowing up on our conversation from last week — I wanted to share the "
        "materials we talked through so you have them in front of you before the meeting on "
        "Thursday. Everything is collected in a single document for convenience.\n\n"
        "Document link: {url}\n\nHappy to walk through any of the sections live if that's "
        "easier. Just drop me a line and we can find a slot later this week.\n\nBest,\n"
        "{sender_first}"
    ),
    (
        "Hi {me},\n\nThanks for getting back to me. As agreed on our call, here's the form "
        "you asked for along with a short cover note explaining the sections that need your "
        "input. The turnaround on my end is quick once you've sent it back.\n\n"
        "Form and cover note: {url}\n\nIf you can have a look in the next couple of days "
        "that would be great — it'll let me slot you in for the follow-up review next week.\n"
        "\nBest,\n{sender_first}"
    ),
    (
        "Hi {me},\n\nFollowing up on the quick question from yesterday — I said I'd send "
        "through the reference document so you could scan it yourself rather than relying on "
        "my summary. It's a short read but worth flagging a couple of points before we talk "
        "again.\n\nDocument: {url}\n\nLet me know your thoughts once you've had a chance to "
        "read. I'd rather discuss the follow-up once you've seen it in full.\n\nBest,\n"
        "{sender_first}"
    ),
    (
        "Hi {me},\n\nReferencing our earlier chat — here's the set of materials I mentioned. "
        "I've attached the main proposal and a short comparison table that shows the "
        "options side-by-side so the trade-offs are clear.\n\nFiles: {url}\n\nTake your time "
        "with it. When you're ready, let me know which option you're leaning towards and I'll "
        "adjust the proposal accordingly. We can catch up by phone later this week if it "
        "helps.\n\nBest,\n{sender_first}"
    ),
    (
        "Hi {me},\n\nFollowing up on our phone call — thanks again for making the time. As "
        "promised, I've put together the summary of what we covered along with the next steps "
        "we agreed on. The document is shared below.\n\nAccess the summary: {url}\n\nIf "
        "anything in the summary doesn't match your recollection, please flag it and I'll "
        "update the doc. Otherwise, I'll get started on the follow-up actions from my "
        "side.\n\nBest,\n{sender_first}"
    ),
    (
        "Hi {me},\n\nThanks for reaching out earlier this week. As we discussed, I've shared "
        "the materials we talked about so you can review them at your own pace. There's a "
        "short intro at the top that summarises the key points if you're short on time.\n\n"
        "Review the materials: {url}\n\nI'll follow up next week if I don't hear from you "
        "before then. No rush on my end — happy to move at your pace.\n\nBest,\n"
        "{sender_first}"
    ),
]

MS_URLS = [
    "consulting-group-partners.net/document",
    "strategy-advisory-partners.co/share",
    "corporate-consult-partners.net/materials",
    "business-advisory-team.co/review",
    "markets-insight-group.net/proposal",
    "exec-advisory-team.co/document",
    "opportunity-partners.net/files",
    "procurement-partner-desk.co/form",
    "supply-network-group.net/share",
    "enterprise-solutions-desk.co/review",
]

MS_SUFFIXES = [
    "No rush on my side — whenever suits. I know the end of the quarter is always "
    "busy, so if you need to push this to next week that is completely fine. Just "
    "flag a convenient window when you have a moment and we can work around you.",
    "If it is easier to discuss live, I am happy to set up a quick call at your "
    "convenience. Otherwise, feel free to reply with your thoughts in writing and "
    "we can take it from there. Either way works for me, and I am flexible on timing.",
    "I have tried to keep the write-up brief so it does not take too long to read. "
    "Let me know if anything needs unpacking and I can follow up with more detail "
    "on any of the sections that you would like me to expand for your review.",
    "Also, a small ask — if you could loop in anyone on your side who should weigh "
    "in, that would help us move through the review a little more smoothly next "
    "week. Nothing pressing, just handy for planning the follow-up on my end.",
    "Looking forward to hearing what you think. Once we have aligned on the "
    "direction I will get the rest of the work scheduled on my end and circle back "
    "with you on the timeline for the remaining pieces once the dates are confirmed.",
]


# ------------------------------------------------------------------------------------
# Shared quality gate + per-subtype gates
# ------------------------------------------------------------------------------------

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
BARE_URL_RE = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S*")
PHONE_RE = re.compile(r"\+?1?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")


def sender_domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def base_checks(row: dict, wc_min: int, wc_max: int) -> bool:
    sender = row["sender"]
    body = row["body"]
    if len(body.strip()) < 10:
        return False
    wc = len(body.split())
    if wc < wc_min or wc > wc_max:
        return False
    blob = f"{row['subject']}\n{body}".lower()
    for sh in URL_SHORTENERS:
        if sh in blob:
            return False
    # Phishing: sender domain must not be a bare commodity address
    sd = sender_domain(sender)
    if sd in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}:
        return False
    return True


def qr_checks(row: dict) -> bool:
    if not base_checks(row, 80, 170):
        return False
    body = row["body"]
    blob = body.lower()
    # Must mention QR code and scanning
    if "qr code" not in blob and "qr-code" not in blob:
        return False
    if "scan" not in blob:
        return False
    # Must reference the phone (phone-camera binding is a QR phishing staple)
    if "phone" not in blob and "mobile" not in blob:
        return False
    return True


def crypto_checks(row: dict) -> bool:
    if not base_checks(row, 80, 170):
        return False
    body = row["body"]
    blob = body.lower()
    # Must contain a URL
    if not BARE_URL_RE.search(blob):
        return False
    # Must mention crypto/wallet concepts
    has_wallet_concept = any(t in blob for t in
                              ["wallet", "bitcoin", "btc ", "eth ", "ethereum",
                               "seed phrase", "airdrop", "staking", "0x"])
    if not has_wallet_concept:
        return False
    # Must reference one of the crypto brands
    if not any(b.lower() in blob for b in CRYPTO_BRANDS):
        return False
    return True


def ai_checks(row: dict) -> bool:
    if not base_checks(row, 100, 200):
        return False
    body = row["body"]
    blob = body.lower()
    if not BARE_URL_RE.search(blob):
        return False
    # Must have a reference number (polished / official feel)
    if not re.search(r"\b(?:REF|CASE|MEM|ACC|CLM)-\d{4,}\b", body) and \
       "reference" not in blob:
        return False
    # Must use bank/gov/health language
    if not any(t in blob for t in
               ["tax", "refund", "member", "insurance", "statement", "account",
                "premium", "benefits", "bank", "treasury", "coverage"]):
        return False
    # Polished: no exclamation, no obvious shouting
    if "!!" in body:
        return False
    return True


def callback_checks(row: dict) -> bool:
    if not base_checks(row, 80, 170):
        return False
    body = row["body"]
    # NO URLs — defining feature of callback phishing
    if BARE_URL_RE.search(body.lower()):
        return False
    # Must have a phone number
    if not PHONE_RE.search(body):
        return False
    # Must have a case reference
    if not re.search(r"[Rr]eference", body):
        return False
    # Must say "call" somewhere
    if "call" not in body.lower():
        return False
    return True


def multistage_checks(row: dict) -> bool:
    if not base_checks(row, 80, 170):
        return False
    body = row["body"]
    blob = body.lower()
    # Must have a URL (the hook)
    if not BARE_URL_RE.search(blob):
        return False
    # Subject must look like a continuation
    s = row["subject"].lower()
    if not (s.startswith("re:") or s.startswith("fwd:") or
            s.startswith("following up") or "as promised" in s or
            "as discussed" in s):
        return False
    # Body must reference a prior interaction
    prior_cues = ["we discussed", "our call", "we talked", "our chat", "last week",
                  "earlier this week", "our conversation", "as agreed", "as promised",
                  "earlier call", "yesterday", "our phone call"]
    if not any(c in blob for c in prior_cues):
        return False
    # Benign tone: no hard urgency tokens that would give the game away on the first email
    hard_urgency = ["will be suspended", "will be locked", "account suspended",
                    "verify immediately", "click here to verify", "reset your password"]
    if any(t in blob for t in hard_urgency):
        return False
    return True


# ------------------------------------------------------------------------------------
# Per-subtype row builders
# ------------------------------------------------------------------------------------

def build_qr():
    sender = pick(QR_SENDERS)
    subj = pick(QR_SUBJECTS)
    body_tpl = pick(QR_BODIES)
    ctx = {"me": pick(FIRST_NAMES), "ref": ref_number("REF")}
    body = fill(body_tpl, ctx) + "\n\n" + pick(QR_SUFFIXES)
    return sender, subj, body, body_tpl, subj, "modern_technique_qr_code"


def build_crypto():
    sender = pick(CRYPTO_SENDERS)
    subj = pick(CRYPTO_SUBJECTS)
    body_tpl = pick(CRYPTO_BODIES)
    # Brand: parse from display name if possible
    display = re.match(r'"([^"]+)"', sender).group(1)
    brand = next((b for b in CRYPTO_BRANDS if b.lower() in display.lower()), "Coinbase")
    ctx = {
        "me": pick(FIRST_NAMES),
        "brand": brand,
        "amount": pick(CRYPTO_AMOUNTS),
        "ref": ref_number("CASE"),
        "url": pick(CRYPTO_URLS),
        "wallet_tail": wallet_address()[-6:],
    }
    body = fill(body_tpl, ctx) + "\n\n" + fill(pick(CRYPTO_SUFFIXES), ctx)
    return sender, subj, body, body_tpl, subj, "modern_technique_crypto"


def build_ai():
    sender = pick(AI_SENDERS)
    subj_tpl = pick(AI_SUBJECTS)
    body_tpl = pick(AI_BODIES)
    display = re.match(r'"([^"]+)"', sender).group(1)
    ctx = {
        "me": pick(FIRST_NAMES),
        "brand": display,
        "amount": f"${random.randint(250, 6500):,}.{random.randint(10, 99)}",
        "ref": ref_number(pick(["REF", "CASE", "MEM", "CLM", "ACC"])),
        "url": pick(AI_URLS),
        "tax_year": random.choice(["2023", "2024", "2025"]),
        "month": pick(["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]),
        "acct_tail": f"{random.randint(1000, 9999)}",
    }
    subj = fill(subj_tpl, ctx)
    body = fill(body_tpl, ctx) + "\n\n" + pick(AI_SUFFIXES)
    return sender, subj, body, body_tpl, subj_tpl, "modern_technique_ai_polished"


def build_callback():
    sender = pick(CB_SENDERS)
    subj = pick(CB_SUBJECTS)
    body_tpl = pick(CB_BODIES)
    # Brand from display
    display = re.match(r'"([^"]+)"', sender).group(1)
    brand = "Account"
    for key, name in CB_BRANDS.items():
        if key in display.lower().replace(" ", ""):
            brand = name
            break
    ctx = {
        "me": pick(FIRST_NAMES),
        "brand": brand,
        "amount": pick(CB_AMOUNTS),
        "phone": phone_number(),
        "ref": ref_number(pick(["CASE", "REF", "TXN"])),
    }
    body = fill(body_tpl, ctx) + "\n\n" + pick(CB_SUFFIXES)
    return sender, subj, body, body_tpl, subj, "modern_technique_callback"


def build_multistage():
    sender = pick(MS_SENDERS)
    subj = pick(MS_SUBJECTS)
    body_tpl = pick(MS_BODIES)
    display = re.match(r'"([^"]+)"', sender).group(1)
    sender_first = display.split()[0]
    ctx = {
        "me": pick(FIRST_NAMES),
        "sender_first": sender_first,
        "url": pick(MS_URLS),
    }
    body = fill(body_tpl, ctx) + "\n\n" + pick(MS_SUFFIXES)
    return sender, subj, body, body_tpl, subj, "modern_technique_multistage"


SUBTYPE_BUILDERS = {
    "qr": (build_qr, qr_checks, 300),
    "crypto": (build_crypto, crypto_checks, 300),
    "ai": (build_ai, ai_checks, 300),
    "callback": (build_callback, callback_checks, 300),
    "multistage": (build_multistage, multistage_checks, 300),
}


# ------------------------------------------------------------------------------------
# Generate
# ------------------------------------------------------------------------------------

def generate():
    rows: list[dict] = []
    seen: set[str] = set()
    template_use: Counter = Counter()

    for subtype, (builder, checker, target_count) in SUBTYPE_BUILDERS.items():
        produced = 0
        attempts = 0
        max_attempts = target_count * 150

        while produced < target_count and attempts < max_attempts:
            attempts += 1
            sender, subject, body, body_tpl, subj_tpl, category = builder()

            key = (subtype, subj_tpl, body_tpl)
            if template_use[key] >= 5:
                continue

            row = {
                "sender": sender,
                "subject": subject,
                "body": body,
                "label": 1,
                "category": category,
            }

            h = hashlib.sha1(f"{sender}\n{subject}\n{body}".encode()).hexdigest()
            if h in seen:
                continue
            if not checker(row):
                continue

            rows.append(row)
            seen.add(h)
            template_use[key] += 1
            produced += 1

        if produced < target_count:
            raise RuntimeError(
                f"Only produced {produced}/{target_count} for {subtype} in {attempts} attempts"
            )

    assert len(rows) == 1500
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
