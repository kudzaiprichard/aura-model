"""Generate 700 modern brand-impersonation phishing emails (label=1) for AURA augmentation.

Follows section 4.1 of online_learning_dataset.md.

Design:
- 8 target brands that post-date the 2007-2008 training corpus.
- Every sender uses a typosquatted or fake domain — never the real brand domain.
- Bodies are polished (no spelling errors, no obviously bad grammar) and reference real
  product features.
- Every row carries at least one clear phishing signal: urgency phrase, fake-domain URL,
  or credential request. The sender domain itself also counts as a signal.
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
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/brand_impersonation.csv"
)


# Real brand domains — senders and URLs MUST NOT use these.
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


# ------------------------------------------------------------------------------------
# Per-brand definitions: senders (typosquatted/fake), subjects, bodies, fake URLs.
# ------------------------------------------------------------------------------------

BRANDS = {
    "msteams": {
        "display": "Microsoft Teams",
        "senders": [
            '"Microsoft Teams" <security@microsft-teams-alert.com>',
            '"Microsoft Teams" <no-reply@teams-microsoft.co>',
            '"MS Teams Security" <alerts@ms-teams-security.net>',
            '"Microsoft Teams" <notifications@microsoftteams-auth.com>',
            '"Teams Admin" <admin@teams-ms365.net>',
            '"Microsoft 365" <service@ms365-teams.co>',
        ],
        "fake_urls": [
            "microsft-teams-alert.com/verify",
            "teams-microsoft.co/signin",
            "ms-teams-security.net/account",
            "microsoftteams-auth.com/login",
            "teams-ms365.net/confirm",
            "ms365-teams.co/validate",
        ],
    },
    "docusign": {
        "display": "DocuSign",
        "senders": [
            '"DocuSign" <no-reply@docusign-secure.net>',
            '"DocuSign" <envelope@docu-sign.co>',
            '"DocuSign Electronic Signature" <dse@docusign-verify.com>',
            '"DocuSign Notifications" <alerts@docusign-alerts.net>',
            '"DocuSign" <documents@docusignonline.co>',
            '"DocuSign eSignature" <no-reply@docusign-delivery.net>',
        ],
        "fake_urls": [
            "docusign-secure.net/sign",
            "docu-sign.co/envelope",
            "docusign-verify.com/review",
            "docusign-alerts.net/document",
            "docusignonline.co/signin",
            "docusign-delivery.net/open",
        ],
    },
    "zoom": {
        "display": "Zoom",
        "senders": [
            '"Zoom" <support@zoom-verify.com>',
            '"Zoom Meetings" <no-reply@zoom-meeting.net>',
            '"Zoom Account Security" <security@zoom-secure.co>',
            '"Zoom Meetings" <alerts@zoommeeting-alert.com>',
            '"Zoom Recordings" <recordings@zoomrecording.net>',
            '"Zoom Support" <support@zoom-helpdesk.co>',
        ],
        "fake_urls": [
            "zoom-verify.com/activate",
            "zoom-meeting.net/join",
            "zoom-secure.co/signin",
            "zoommeeting-alert.com/account",
            "zoomrecording.net/recording",
            "zoom-helpdesk.co/support",
        ],
    },
    "dropbox": {
        "display": "Dropbox",
        "senders": [
            '"Dropbox" <noreply@dropb0x-share.com>',
            '"Dropbox" <share@dropbox-share.net>',
            '"Dropbox Support" <support@dropbox-files.co>',
            '"Dropbox" <files@dropbx-cloud.com>',
            '"Dropbox Delivery" <delivery@dropbox-delivery.net>',
            '"Dropbox Business" <admin@dropbox-workspace.co>',
        ],
        "fake_urls": [
            "dropb0x-share.com/file",
            "dropbox-share.net/download",
            "dropbox-files.co/view",
            "dropbx-cloud.com/shared",
            "dropbox-delivery.net/open",
            "dropbox-workspace.co/signin",
        ],
    },
    "wetransfer": {
        "display": "WeTransfer",
        "senders": [
            '"WeTransfer" <no-reply@wetransfer-delivery.net>',
            '"WeTransfer" <transfer@we-transfer.co>',
            '"WeTransfer Support" <support@wetransfer-files.com>',
            '"WeTransfer" <files@wetransfer-secure.net>',
            '"WeTransfer" <noreply@we-transfer-mail.co>',
            '"WeTransfer Plus" <admin@wetransfer-plus.net>',
        ],
        "fake_urls": [
            "wetransfer-delivery.net/download",
            "we-transfer.co/download",
            "wetransfer-files.com/open",
            "wetransfer-secure.net/files",
            "we-transfer-mail.co/receive",
            "wetransfer-plus.net/account",
        ],
    },
    "notion": {
        "display": "Notion",
        "senders": [
            '"Notion" <alerts@notion-workspace.co>',
            '"Notion" <notifications@notion-alerts.net>',
            '"Notion Team" <team@notion-docs.com>',
            '"Notion" <no-reply@mynotion-app.net>',
            '"Notion" <workspace@notion-team.co>',
            '"Notion" <hello@notion-login.net>',
        ],
        "fake_urls": [
            "notion-workspace.co/signin",
            "notion-alerts.net/verify",
            "notion-docs.com/share",
            "mynotion-app.net/login",
            "notion-team.co/invite",
            "notion-login.net/account",
        ],
    },
    "slack": {
        "display": "Slack",
        "senders": [
            '"Slack" <security@slack-verification.com>',
            '"Slack" <alerts@slack-alert.net>',
            '"Slack Admin" <admin@slack-workspace.co>',
            '"Slack" <no-reply@slack-notifications.net>',
            '"Slack" <channels@slackchannels.co>',
            '"Slack Team" <team@slack-team-access.net>',
        ],
        "fake_urls": [
            "slack-verification.com/verify",
            "slack-alert.net/signin",
            "slack-workspace.co/account",
            "slack-notifications.net/review",
            "slackchannels.co/activate",
            "slack-team-access.net/confirm",
        ],
    },
    "openai": {
        "display": "OpenAI",
        "senders": [
            '"OpenAI" <billing@openai-account.net>',
            '"OpenAI" <support@openai-billing.com>',
            '"OpenAI Account" <no-reply@openai-verify.co>',
            '"OpenAI" <team@open-ai.net>',
            '"OpenAI" <security@openai-secure.com>',
            '"OpenAI API" <api@openai-platform.co>',
        ],
        "fake_urls": [
            "openai-account.net/billing",
            "openai-billing.com/review",
            "openai-verify.co/confirm",
            "open-ai.net/account",
            "openai-secure.com/signin",
            "openai-platform.co/api",
        ],
    },
}


# ------------------------------------------------------------------------------------
# Per-brand subject and body banks.
# ------------------------------------------------------------------------------------

SUBJECTS = {
    "msteams": [
        "Action required: verify your Microsoft Teams account",
        "Unusual sign-in activity on your Teams account",
        "New Teams message waiting — review now",
        "Your Microsoft Teams account will be suspended",
        "Important: re-authenticate your Teams workspace",
        "You have a missed Teams call — recording ready",
        "Security alert: confirm your Teams credentials",
        "Microsoft Teams: new shared channel invite",
        "Your Teams password expires today",
        "Verify your Teams account to continue",
    ],
    "docusign": [
        "Your DocuSign document requires signature",
        "You have a document waiting from your colleague",
        "Signature required: agreement pending",
        "Action required: review and sign your document",
        "Your DocuSign envelope is ready for review",
        "Completed envelope: download your signed copy",
        "Reminder: signature needed within 48 hours",
        "New document shared with you via DocuSign",
        "Please sign this agreement from your manager",
        "DocuSign: pending signature — urgent",
    ],
    "zoom": [
        "Your Zoom meeting recording is ready",
        "Unusual activity on your Zoom account",
        "Action required: verify your Zoom account",
        "Your Zoom subscription will be cancelled",
        "New Zoom meeting invite from your manager",
        "Your Zoom password expires today",
        "Zoom account locked — verification needed",
        "You missed a scheduled Zoom call",
        "Re-authenticate your Zoom account to continue",
        "Zoom security update: action required",
    ],
    "dropbox": [
        "Someone shared a file with you via Dropbox",
        "Your Dropbox storage is almost full",
        "New file shared: review pending",
        "Dropbox: document shared by your colleague",
        "Action required: confirm your Dropbox account",
        "Shared folder waiting for your review",
        "Dropbox security alert — sign in to review",
        "Your Dropbox account access expires soon",
        "New shared document from your team",
        "Dropbox: unusual sign-in detected",
    ],
    "wetransfer": [
        "Files have been shared with you via WeTransfer",
        "Your WeTransfer download expires in 24 hours",
        "New transfer waiting for your review",
        "WeTransfer: large file ready to download",
        "Reminder: files from your colleague expiring soon",
        "Action required: verify to access your files",
        "A colleague sent you files via WeTransfer",
        "Your WeTransfer Plus account requires review",
        "Important: files pending your download",
        "WeTransfer: documents shared with you",
    ],
    "notion": [
        "You've been invited to a Notion workspace",
        "New page shared with you on Notion",
        "Notion: verify your workspace access",
        "Reminder: complete your Notion workspace setup",
        "Action required: confirm your Notion account",
        "Notion: unusual sign-in to your workspace",
        "Your Notion workspace subscription expires soon",
        "New comment on your Notion page",
        "Notion: re-authenticate your account",
        "Someone shared a database with you on Notion",
    ],
    "slack": [
        "Unusual activity detected on your Slack workspace",
        "Action required: verify your Slack credentials",
        "You have been mentioned in a new channel",
        "Slack: re-authenticate your workspace",
        "Your Slack account will be suspended",
        "New direct message waiting — sign in to review",
        "Slack security alert: confirm your identity",
        "Important: your Slack workspace needs verification",
        "New file shared in your workspace",
        "Slack: password change required",
    ],
    "openai": [
        "Action required: update your OpenAI billing details",
        "Your OpenAI API usage exceeded limits",
        "Your OpenAI account will be suspended",
        "OpenAI: verify your account to continue",
        "Unusual sign-in to your OpenAI account",
        "Payment failed — update OpenAI billing",
        "OpenAI: re-authenticate your account",
        "Important update to your OpenAI subscription",
        "Your OpenAI API key needs verification",
        "OpenAI account security alert",
    ],
}


# Each body template uses {url} and {first}. Reference real product features.
BODIES = {
    "msteams": [
        (
            "Hello,\n\nWe detected an unusual sign-in to your Microsoft Teams account from a "
            "new device. For your protection, we've temporarily restricted access to shared "
            "channels and chat history until you confirm your identity.\n\nTo restore full "
            "access, please verify your account within the next 24 hours:\n\n{url}\n\nIf you "
            "don't complete verification, your Teams workspace will be locked and your "
            "messages archived. This is a routine security measure.\n\nThank you,\nMicrosoft "
            "Teams Security"
        ),
        (
            "Hi,\n\nYour Microsoft Teams password is scheduled to expire today. To avoid "
            "losing access to your chats, calls, and shared files, please sign in and reset "
            "your password before end of day.\n\nReset here: {url}\n\nIf you don't update "
            "your credentials before expiry, your account will be temporarily suspended and "
            "you'll need to contact your IT administrator to restore access.\n\nThank you,"
            "\nMicrosoft Teams Account Team"
        ),
        (
            "Hello,\n\nYou have a new message waiting in a shared Teams channel. The sender "
            "has marked it as important and is expecting a response today.\n\nTo review the "
            "message and the attached document, sign in to your Teams account:\n\n{url}\n\n"
            "If you don't respond within 48 hours, the message will be archived and the "
            "shared channel access will be revoked for security reasons.\n\nRegards,\n"
            "Microsoft Teams"
        ),
        (
            "Hi,\n\nA colleague has invited you to a new shared channel in Microsoft Teams. "
            "The channel contains documents, meeting recordings, and an active conversation "
            "from your project group.\n\nAccept the invite and sign in here:\n\n{url}\n\n"
            "Please confirm your credentials to activate the shared channel — the invite "
            "expires in 24 hours.\n\nThank you,\nMicrosoft Teams Admin"
        ),
        (
            "Hello,\n\nOur security system flagged recent sign-in attempts on your Microsoft "
            "Teams account. Some of them were blocked automatically, but we need you to "
            "re-authenticate to make sure your account hasn't been compromised.\n\nConfirm "
            "your identity here: {url}\n\nFor your protection, call recording and message "
            "history will remain restricted until you complete verification.\n\nThank you,\n"
            "Microsoft Teams Security Team"
        ),
    ],
    "docusign": [
        (
            "Hello,\n\nYou have a document waiting for your signature in DocuSign. The "
            "sender has requested that you review and sign within 48 hours to keep the "
            "agreement on schedule.\n\nReview and sign here:\n\n{url}\n\nPlease sign in to "
            "your DocuSign account to access the envelope. If you don't complete the "
            "signature before the deadline, the document will be returned to the sender.\n\n"
            "Thank you,\nDocuSign Electronic Signature Service"
        ),
        (
            "Hi,\n\nAn urgent agreement from your manager is waiting for your signature in "
            "DocuSign. This document is time-sensitive and the counterparty is expecting the "
            "executed version today.\n\nSign the envelope here:\n\n{url}\n\nYou'll be asked "
            "to confirm your credentials before accessing the document. Please sign before "
            "5pm to avoid delays.\n\nRegards,\nDocuSign Notifications"
        ),
        (
            "Hello,\n\nThis is a reminder that you have a pending signature request in "
            "DocuSign. The document expires in 24 hours if no action is taken.\n\nReview the "
            "envelope: {url}\n\nSign in to DocuSign to view the document, check the "
            "counterparty details, and complete your signature. Once signed, both parties "
            "will receive the completed envelope automatically.\n\nThank you,\nDocuSign "
            "eSignature"
        ),
        (
            "Hi,\n\nThe completed version of an agreement you recently signed is now "
            "available. To download the executed envelope, please verify your identity and "
            "sign in to your DocuSign account.\n\nOpen your signed copy: {url}\n\nFor "
            "security reasons, the download link will expire in 48 hours. Please retrieve "
            "the document before then.\n\nRegards,\nDocuSign"
        ),
        (
            "Hello,\n\nA new document has been shared with you via DocuSign. The sender has "
            "selected you as a required signer and the envelope is ready for your review.\n\n"
            "Review and sign: {url}\n\nSigning is quick — just verify your email and follow "
            "the prompts. The sender will be notified automatically once you've completed "
            "your signature.\n\nThank you,\nDocuSign"
        ),
    ],
    "zoom": [
        (
            "Hi,\n\nYour Zoom meeting recording is ready to view. The session from earlier "
            "today has been processed and transcribed, and is now available in your "
            "account.\n\nView the recording: {url}\n\nTo access the recording you'll be "
            "asked to sign in and confirm your credentials. The link expires in 48 hours — "
            "please download or save the recording before then.\n\nRegards,\nZoom Recordings"
        ),
        (
            "Hello,\n\nWe detected unusual sign-in activity on your Zoom account from a "
            "device we don't recognise. To protect your meetings and recordings, your "
            "account has been placed in a limited state until you verify your identity.\n\n"
            "Verify here: {url}\n\nPlease complete verification within 24 hours to avoid "
            "your account being locked.\n\nThank you,\nZoom Account Security"
        ),
        (
            "Hi,\n\nYour Zoom password is set to expire today. To keep your scheduled "
            "meetings, recurring invites, and account preferences in place, please reset "
            "your password before end of day.\n\nReset your password: {url}\n\nIf you miss "
            "today's deadline, your account will be suspended and you'll need to contact "
            "support to restore access.\n\nRegards,\nZoom Account Team"
        ),
        (
            "Hello,\n\nYour manager has scheduled a Zoom meeting with you for later today. "
            "The meeting includes a shared document and a pre-read from the team.\n\nJoin "
            "and review the pre-read: {url}\n\nSign in to your Zoom account to accept the "
            "invite and preview the agenda. Please confirm your attendance within the next "
            "few hours.\n\nRegards,\nZoom Meetings"
        ),
        (
            "Hi,\n\nYour Zoom subscription is due for renewal and our records show the "
            "payment method on file has expired. To keep uninterrupted access to recordings, "
            "cloud storage, and your scheduled meetings, please update your billing "
            "details.\n\nUpdate billing: {url}\n\nIf no action is taken within 48 hours, "
            "your subscription will be cancelled and recordings older than 30 days may be "
            "deleted.\n\nThank you,\nZoom Billing"
        ),
    ],
    "dropbox": [
        (
            "Hi,\n\nA colleague has shared a large file with you via Dropbox. The document "
            "is marked as confidential and has been set to expire after the first download.\n"
            "\nAccess the file: {url}\n\nPlease sign in to your Dropbox account to view the "
            "file. You'll be asked to confirm your email before the download begins.\n\n"
            "Regards,\nDropbox"
        ),
        (
            "Hello,\n\nWe noticed a sign-in attempt to your Dropbox account from a new "
            "device and blocked it automatically. To make sure your files stay secure, "
            "please confirm it was you within 24 hours.\n\nReview the activity: {url}\n\n"
            "If you don't confirm, sharing links from your account will be paused and "
            "shared folders will be hidden until you verify your identity.\n\nThank you,"
            "\nDropbox Support"
        ),
        (
            "Hi,\n\nYour Dropbox storage is almost full and sync has been paused for your "
            "shared folders. To keep your team's files syncing, please review your storage "
            "and upgrade or free up space.\n\nReview your account: {url}\n\nSign in and "
            "confirm your credentials to access the storage dashboard. Sync will resume "
            "automatically once you're within your plan limits.\n\nRegards,\nDropbox "
            "Business"
        ),
        (
            "Hello,\n\nA shared folder from your team has been updated with new documents. "
            "The folder includes project files, presentations, and a link to a meeting "
            "recording from earlier this week.\n\nOpen the folder: {url}\n\nYou'll be asked "
            "to sign in to Dropbox to view the folder. Access expires in 72 hours if you "
            "don't open it before then.\n\nThank you,\nDropbox"
        ),
        (
            "Hi,\n\nAn important document has been shared with you via Dropbox. The sender "
            "has requested that you review and acknowledge within 24 hours.\n\nReview: "
            "{url}\n\nSign in to your Dropbox account to view the document. You'll see "
            "the sender's comments and be able to leave your own before the deadline.\n\n"
            "Regards,\nDropbox Delivery"
        ),
    ],
    "wetransfer": [
        (
            "Hi,\n\nA colleague has sent you files via WeTransfer. The transfer contains "
            "several documents and a video recording, and is available to download for the "
            "next 24 hours.\n\nDownload the files: {url}\n\nPlease confirm your email to "
            "start the download. Once the link expires, the files will be permanently "
            "deleted from our servers.\n\nRegards,\nWeTransfer"
        ),
        (
            "Hello,\n\nYour WeTransfer download is about to expire. The sender shared "
            "{n_files} files with you two days ago, and the transfer will be removed in "
            "the next 24 hours.\n\nAccess before it expires: {url}\n\nSign in to confirm "
            "your email and start the download. Once the link expires, the sender will need "
            "to re-upload the files.\n\nRegards,\nWeTransfer Support"
        ),
        (
            "Hi,\n\nAn important transfer from a colleague is waiting for your review. The "
            "sender marked the files as urgent and requested confirmation once you've "
            "received them.\n\nOpen the transfer: {url}\n\nVerify your email to access the "
            "files. The sender will be notified automatically once you've confirmed "
            "receipt.\n\nThank you,\nWeTransfer"
        ),
        (
            "Hello,\n\nA large file has been shared with you via WeTransfer Plus. The "
            "transfer is protected with a confirmation step, so you'll be asked to sign in "
            "before the download starts.\n\nDownload here: {url}\n\nThe files are available "
            "for 48 hours from the original upload time. Please complete the download "
            "before then.\n\nRegards,\nWeTransfer Plus"
        ),
        (
            "Hi,\n\nThis is a reminder that you have unopened files on WeTransfer. The "
            "sender shared {n_files} documents with you {days} days ago and the transfer "
            "will expire soon.\n\nDownload the files: {url}\n\nSign in to confirm your "
            "identity and access the transfer. Once the link expires the files cannot be "
            "recovered.\n\nThank you,\nWeTransfer"
        ),
    ],
    "notion": [
        (
            "Hi,\n\nYou've been invited to a Notion workspace by a colleague. The workspace "
            "contains shared documents, databases, and a meeting-notes space used by your "
            "team.\n\nAccept the invite: {url}\n\nSign in to Notion to activate the "
            "workspace. The invite expires in 48 hours — please accept before then to keep "
            "your access.\n\nRegards,\nNotion"
        ),
        (
            "Hello,\n\nWe detected a sign-in attempt to your Notion workspace from a new "
            "device and blocked it. To confirm it was you and restore normal access, "
            "please verify your account within 24 hours.\n\nVerify here: {url}\n\nIf we "
            "don't hear from you, your workspace will be locked and a verification email "
            "sent to your admin.\n\nThank you,\nNotion"
        ),
        (
            "Hi,\n\nA colleague has shared a new page with you on Notion. The page contains "
            "project notes, a status dashboard, and a shared database of tasks.\n\nOpen the "
            "page: {url}\n\nSign in to your Notion account to view the page. You'll be able "
            "to comment, assign tasks, and add to the database once you've confirmed your "
            "access.\n\nRegards,\nNotion Team"
        ),
        (
            "Hello,\n\nYour Notion workspace subscription is due for renewal and the "
            "payment on file has failed. To keep your shared databases and documents "
            "accessible, please update your billing details before the grace period "
            "ends.\n\nUpdate billing: {url}\n\nIf no action is taken, your workspace will "
            "be downgraded to the free plan and the block limit will be enforced.\n\n"
            "Thank you,\nNotion"
        ),
        (
            "Hi,\n\nA new comment has been added to a page you own on Notion. The comment "
            "is from a collaborator and includes a proposed change to the shared "
            "database.\n\nReview the comment: {url}\n\nSign in to Notion to view the full "
            "context and respond. The page stays locked for new comments until you review "
            "this one.\n\nRegards,\nNotion"
        ),
    ],
    "slack": [
        (
            "Hi,\n\nWe detected unusual activity on your Slack workspace — several sign-in "
            "attempts from unfamiliar locations in the past hour. For your protection, "
            "we've temporarily paused new channel access until you confirm your identity.\n"
            "\nVerify here: {url}\n\nIf you don't respond within 24 hours, your account "
            "will be suspended and workspace admins will be notified.\n\nThank you,\nSlack "
            "Security"
        ),
        (
            "Hello,\n\nYou've been mentioned in a new channel in your Slack workspace. The "
            "sender is asking for a response today and has marked the thread as a "
            "priority.\n\nSign in to review: {url}\n\nVerify your credentials to open the "
            "channel. Direct messages and mentions will remain queued until you confirm "
            "access.\n\nRegards,\nSlack"
        ),
        (
            "Hi,\n\nYour Slack workspace is due for a scheduled re-authentication. This is "
            "a routine security check required for all accounts on our Enterprise Grid "
            "tier.\n\nRe-authenticate: {url}\n\nPlease confirm your identity by end of day "
            "to avoid your account being paused. The process takes under a minute.\n\n"
            "Thank you,\nSlack Admin"
        ),
        (
            "Hello,\n\nA colleague has shared a new file in your Slack workspace. The file "
            "was posted in a channel you were recently added to, and is marked as "
            "time-sensitive by the sender.\n\nReview the file: {url}\n\nSign in to Slack "
            "and verify your access to the channel. The file will be removed automatically "
            "after 48 hours if not downloaded.\n\nRegards,\nSlack"
        ),
        (
            "Hi,\n\nAs part of our quarterly workspace review, your Slack password needs to "
            "be updated. Accounts that don't complete the rotation will be placed in a "
            "read-only state until the update is done.\n\nUpdate your password: {url}\n\n"
            "Sign in through the link above to finish the rotation before end of day. This "
            "applies to all users on the paid plan.\n\nThank you,\nSlack"
        ),
    ],
    "openai": [
        (
            "Hello,\n\nWe were unable to process the payment method on file for your OpenAI "
            "account. Your API access has been placed in a limited state until billing is "
            "resolved.\n\nUpdate your billing details: {url}\n\nSign in to confirm your "
            "account and add an updated payment method. If no action is taken within 48 "
            "hours, your subscription will be cancelled and API keys will be revoked.\n\n"
            "Thank you,\nOpenAI Billing"
        ),
        (
            "Hi,\n\nYour OpenAI API usage exceeded the configured monthly limit, and new "
            "requests are being rate-limited. To restore normal API access, review and "
            "adjust your billing preferences.\n\nReview limits: {url}\n\nSign in to your "
            "OpenAI account to confirm your identity and access the usage dashboard. "
            "Changes take effect immediately.\n\nRegards,\nOpenAI"
        ),
        (
            "Hello,\n\nWe detected an unusual sign-in to your OpenAI account from a new "
            "location. For your protection, API access has been paused and active keys "
            "flagged pending review.\n\nVerify here: {url}\n\nConfirm your identity within "
            "24 hours to restore access. If you don't recognise the sign-in, you can also "
            "rotate your API keys after verification.\n\nThank you,\nOpenAI Account "
            "Security"
        ),
        (
            "Hi,\n\nYour OpenAI subscription is due for renewal and our records show the "
            "card on file has expired. To keep your ChatGPT Plus access and uninterrupted "
            "API keys, please update your billing details.\n\nUpdate billing: {url}\n\n"
            "Sign in and confirm your account. If no action is taken in the next 48 hours, "
            "the subscription will be cancelled at the end of the current cycle.\n\n"
            "Regards,\nOpenAI"
        ),
        (
            "Hello,\n\nAs part of a quarterly security review, we're asking all OpenAI API "
            "users to re-verify their accounts. Accounts that don't complete the check will "
            "have their API keys rotated and will need to regenerate them from the "
            "dashboard.\n\nComplete verification: {url}\n\nSign in through the link above "
            "to confirm your identity. The process takes under two minutes.\n\nThank you,"
            "\nOpenAI"
        ),
    ],
}


# ------------------------------------------------------------------------------------
# Per-brand suffix pools — appended to each body to hit 80-word minimum while
# keeping brand-consistent phrasing.
# ------------------------------------------------------------------------------------

SUFFIXES = {
    "msteams": [
        "This email was sent automatically by the Microsoft Teams security service and "
        "cannot be replied to directly. If you believe you received this in error, contact "
        "your workspace administrator.",
        "For your protection, we recommend reviewing the recent-devices list in your "
        "account settings after you verify. Unrecognised devices can be removed in a single "
        "click from the same page.",
        "Microsoft Teams periodically reviews sign-in activity for all enterprise accounts. "
        "Keeping your verified-device list current helps us prevent unauthorised access to "
        "chats and call recordings.",
        "If you didn't expect this message, you can still click through to the account "
        "page and end any active session on an unfamiliar device. Your workspace admin will "
        "be notified automatically.",
        "Thank you for helping keep your Microsoft Teams workspace secure. Completing this "
        "step also updates your recovery options so future sign-in issues can be resolved "
        "faster.",
    ],
    "docusign": [
        "DocuSign uses industry-standard encryption and audit logs for every signature "
        "event. Completing your signature adds your certificate to the envelope and notifies "
        "all counterparties automatically.",
        "If you don't recognise this envelope or the sender, you can decline it from the "
        "same page and the sender will receive a notification. Declined envelopes are kept "
        "on file for compliance.",
        "Your signed copy is stored in your DocuSign account and can be downloaded any time "
        "from the Documents tab. The envelope history shows every action taken by each "
        "signer.",
        "DocuSign never asks you to share your password by email. Please only sign in "
        "through the verification link in this message and report any suspicious messages "
        "to your administrator.",
        "Signing in through the verification link ensures the envelope is linked to the "
        "correct account and counterparty. This keeps the audit trail accurate for both "
        "parties.",
    ],
    "zoom": [
        "Zoom regularly reviews meeting recordings and account activity to help protect "
        "your workspace. Keeping your verified-device list current also helps ensure "
        "meeting invites reach you on the right devices.",
        "If you didn't request this change, you can still follow the link to secure your "
        "account and sign out from any active sessions. Your administrator will be notified "
        "automatically.",
        "Once verified, you'll have immediate access to your upcoming meetings, recordings, "
        "and shared settings. The process is designed to take less than two minutes from "
        "start to finish.",
        "For your protection, Zoom will pause new meeting invites and recording access "
        "until verification is complete. This is a standard step for accounts on the Pro "
        "and Business tiers.",
        "This notification was generated automatically by the Zoom account service. Replies "
        "to this address are not monitored — please use the verification link above to "
        "complete any actions on your account.",
    ],
    "dropbox": [
        "Dropbox uses encryption at rest and in transit to protect your files. Once "
        "verified, your shared folders will resume syncing automatically and any pending "
        "transfers will complete in the background.",
        "For your protection, Dropbox regularly reviews recent sign-ins for every account. "
        "Keeping your verified-device list current helps us notify you quickly if anything "
        "looks out of place.",
        "If you don't recognise this activity, you can still sign in through the link to "
        "secure your account and rotate your session tokens. Your team admin will be "
        "notified automatically.",
        "Completing verification also refreshes your sharing permissions and makes sure "
        "the shared-folder members list is accurate. This helps the team avoid access "
        "issues on collaborative files.",
        "This message was generated automatically by the Dropbox account service and "
        "cannot be replied to directly. For any questions, contact your workspace admin or "
        "open a ticket through the help centre.",
    ],
    "wetransfer": [
        "WeTransfer uses encrypted storage for every transfer and automatically removes "
        "files after the expiry period. Completing verification ensures the sender receives "
        "confirmation that the files were delivered to the right inbox.",
        "If the transfer link expires before you download, the sender will need to "
        "re-upload the files. You can request a new transfer from the same sender at any "
        "time from their profile page.",
        "Large transfers are protected with an extra verification step for Plus and Pro "
        "accounts. This reduces the risk of files being opened on an unverified device or "
        "forwarded outside the intended recipient list.",
        "For your protection, WeTransfer keeps a short log of the devices used to download "
        "each transfer. The sender can review the log after the transfer expires if they "
        "need to confirm receipt.",
        "This email was generated automatically by the WeTransfer delivery service. If you "
        "believe you received it in error, you can still open the link and decline the "
        "transfer. The sender will be notified.",
    ],
    "notion": [
        "Notion uses role-based permissions for every workspace. Completing verification "
        "ensures the right access level is applied to your account and that shared pages "
        "remain available to the intended collaborators.",
        "If you don't recognise the workspace invite, you can still follow the link to "
        "review the sender and decline. Declined invites are kept in the workspace log for "
        "audit purposes.",
        "Once your account is verified, shared databases and pages resume syncing in real "
        "time. Any comments added while your workspace was paused will be delivered in the "
        "order they were posted.",
        "Notion regularly reviews sign-in activity across enterprise workspaces. Keeping "
        "your verified-device list current helps us notify you quickly if anything looks "
        "out of place on your account.",
        "This notification was generated automatically by the Notion workspace service and "
        "cannot be replied to directly. For questions, reach out to your workspace admin "
        "through the sidebar.",
    ],
    "slack": [
        "Slack uses device-level verification for workspaces on the paid plans. Completing "
        "this step refreshes your sign-in tokens and makes sure mentions and direct messages "
        "reach the right device.",
        "If you didn't expect this message, you can still follow the link to review the "
        "recent sign-in attempts and end any active sessions from unfamiliar devices. Your "
        "admin will be notified automatically.",
        "Once verification is complete, your workspace returns to normal and any queued "
        "mentions will be delivered. The verified-device list can be reviewed at any time "
        "from your account preferences.",
        "For your protection, Slack periodically reviews sign-in activity and pauses new "
        "channel access when something looks unusual. This helps keep workspaces safe from "
        "unauthorised access.",
        "This email was sent automatically by the Slack workspace service. Replies to this "
        "address are not monitored — please use the verification link above to complete "
        "any actions on your account.",
    ],
    "openai": [
        "OpenAI reviews billing and sign-in activity regularly to help keep enterprise "
        "accounts secure. Completing verification refreshes your account state and makes "
        "sure any rate-limit holds are cleared automatically.",
        "If you don't recognise this message, you can still follow the link to review "
        "recent activity and rotate any API keys that may have been exposed. All changes "
        "take effect immediately.",
        "Once verification is complete, your API access returns to normal and any failed "
        "requests can be replayed from the dashboard. The usage meter resets on the next "
        "billing cycle.",
        "For your protection, OpenAI pauses new API requests when a billing issue or "
        "unusual sign-in is detected. This is a routine step to help prevent unauthorised "
        "use of your keys.",
        "This notification was generated automatically by the OpenAI account service and "
        "cannot be replied to directly. For billing questions, contact support through the "
        "help centre link on your dashboard.",
    ],
}


# ------------------------------------------------------------------------------------
# Plan: sum must equal 700.
# ------------------------------------------------------------------------------------

PLAN = [
    ("msteams", 90),
    ("docusign", 90),
    ("zoom", 90),
    ("dropbox", 90),
    ("wetransfer", 90),
    ("notion", 90),
    ("slack", 90),
    ("openai", 70),
]
assert sum(c for _, c in PLAN) == 700


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


# ------------------------------------------------------------------------------------
# Quality gate — section 6 + phishing-signal requirement.
# ------------------------------------------------------------------------------------

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]

URGENCY_TOKENS = [
    "within 24 hours", "within 48 hours", "within the next 24 hours", "before end of day",
    "before 5pm", "expires in 24 hours", "expires in 48 hours", "expires today",
    "expires soon", "expire soon", "will be suspended", "will be cancelled",
    "will be locked", "account has been placed in a limited state",
    "placed in a limited state", "rate-limited", "in a limited state",
    "action required", "urgent", "time-sensitive", "scheduled to expire",
    "due for a scheduled re-authentication", "complete verification",
    "complete the rotation", "before the deadline",
]

CREDENTIAL_TOKENS = [
    "sign in", "re-authenticate", "verify your identity", "verify your account",
    "verify your credentials", "confirm your identity", "confirm your credentials",
    "confirm your email", "update your billing", "update your password",
    "reset your password", "re-verify", "rotate your api keys", "verify",
    "confirm it was you", "authenticate", "update billing",
]


def sender_domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def passes_checks(row: dict, fake_domains: set[str]) -> bool:
    sender = row["sender"]
    subject = row["subject"]
    body = row["body"]
    blob = f"{subject}\n{body}".lower()

    if len(body.strip()) < 10:
        return False

    wc = len(body.split())
    # spec 4.1: 80-150 words
    if wc < 80 or wc > 160:
        return False

    # 1. Sender domain must NOT be a real brand domain
    sd = sender_domain(sender)
    if sd in REAL_DOMAINS:
        return False
    # Ensure no real brand base is the direct domain (e.g., 'microsoft.com'
    # itself — subdomains like mail.microsoft.com would also be a fail, but we
    # construct these intentionally fake, so just guard against exact real-domain
    # matches and known registrable real-brand domains).
    for real in REAL_DOMAINS:
        if sd == real or sd.endswith("." + real):
            return False

    # 2. URL shorteners not allowed (makes the phishing too obvious / spec ban)
    for sh in URL_SHORTENERS:
        if sh in blob:
            return False

    # 3. Any URL in the body must belong to a fake domain — never a real brand domain
    # Bare-domain check: find bare-url tokens and check each.
    for m in re.finditer(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)+)/\S*", blob):
        host = m.group(1)
        for real in REAL_DOMAINS:
            if host == real or host.endswith("." + real):
                return False

    # 4. Must contain at least one phishing signal in body/subject text.
    has_urgency = any(t in blob for t in URGENCY_TOKENS)
    has_credential = any(t in blob for t in CREDENTIAL_TOKENS)
    has_fake_url = any(fd in blob for fd in fake_domains)
    signals = sum([has_urgency, has_credential, has_fake_url])
    if signals < 1:
        return False

    # 5. At least one of: urgency OR credential (these are the textual tells)
    if not (has_urgency or has_credential):
        return False

    return True


# Build the set of fake domain strings (for signal detection) from the brand table.
FAKE_DOMAINS = set()
for b in BRANDS.values():
    for s in b["senders"]:
        d = sender_domain(s)
        if d:
            FAKE_DOMAINS.add(d)
    for u in b["fake_urls"]:
        host = u.split("/")[0]
        FAKE_DOMAINS.add(host)


# ------------------------------------------------------------------------------------
# Generate
# ------------------------------------------------------------------------------------

def generate():
    rows: list[dict] = []
    seen: set[str] = set()
    template_use: Counter = Counter()

    for brand_key, target_count in PLAN:
        brand = BRANDS[brand_key]
        subjects = SUBJECTS[brand_key]
        bodies = BODIES[brand_key]
        senders = brand["senders"]
        fake_urls = brand["fake_urls"]

        produced = 0
        attempts = 0
        max_attempts = target_count * 120

        while produced < target_count and attempts < max_attempts:
            attempts += 1
            sender = pick(senders)
            subj_tpl = pick(subjects)
            body_tpl = pick(bodies)

            key = (brand_key, subj_tpl, body_tpl)
            if template_use[key] >= 5:
                continue

            ctx = {
                "url": pick(fake_urls),
                "n_files": random.choice(["3", "4", "5", "6", "7", "8"]),
                "days": random.choice(["2", "3"]),
            }
            subject = subj_tpl  # subjects have no placeholders
            suffix = pick(SUFFIXES[brand_key])
            body = fill(body_tpl, ctx) + "\n\n" + suffix

            row = {
                "sender": sender,
                "subject": subject,
                "body": body,
                "label": 1,
                "category": "brand_impersonation",
            }

            h = hashlib.sha1(f"{sender}\n{subject}\n{body}".encode()).hexdigest()
            if h in seen:
                continue
            if not passes_checks(row, FAKE_DOMAINS):
                continue

            rows.append(row)
            seen.add(h)
            template_use[key] += 1
            produced += 1

        if produced < target_count:
            raise RuntimeError(
                f"Only produced {produced}/{target_count} for {brand_key} in {attempts} attempts"
            )

    assert len(rows) == 700
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
