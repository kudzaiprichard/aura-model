# AURA v1.0 — Pre-Stress-Test Weakness Report

Scope: analysis of the AURA v1.0 phishing detector (MLP + dual TF-IDF + 15
engineered features), identifying exploitable gaps before the stress-test
dataset is constructed. Targets the model served by
`models/v1_0/production/phishing_detector_mlp_classifier.pkl` and the
vectorisers under `models/pipeline_components/`.

---

## 1. Pipeline at a glance (what the stress test must beat)

- **Raw training corpus**: 8 CSVs, 114,578 rows, combined in
  `01.combine_dataset.ipynb`, dedup on `(sender, subject, body)` in
  `02.data_exploration_cleaning.ipynb`.
- **Cleaning** (notebook 02, cell 66 — `EmailBodyCleaner`): protects URLs
  and email addresses with placeholders, strips HTML tags, MIME headers,
  reply headers (`On X wrote:`), `unsubscribe`/`opt-out`/`remove me` tokens,
  `You are receiving this...`, `Copyright`, `All rights reserved`, emojis,
  and **every Unicode character that is not L*/N*/Zs/!/?/\n/_** (currency
  symbols, dashes, brackets, math symbols — all gone). Case preserved on
  the body; subject cleaned similarly.
- **Engineered features** (notebook 03, then feature-selection-pruned to
  15 — see `inference/schema.py::ENGINEERED_FEATURE_ORDER`):
  `body_word_count, body_exclamation_count, email_local_length,
  name_email_consistency, body_url_density, body_url_count, body_entropy,
  email_digit_ratio, domain_entropy, domain_length, subject_entropy,
  body_avg_word_length, sender_name_exists, subject_exclamation_count,
  domain_vowel_consonant_ratio`.
- **TF-IDF** (notebook 03, cells 18 & 19):
  - subject: 2000 features, unigrams, `min_df=1`, `max_df=0.95`,
    `stop_words='english'`, lowercased.
  - body: 5000 features, **uni- and bi-grams**, `min_df=1`, `max_df=0.95`,
    English stopwords, lowercased.
  - `normalize_for_tfidf` (`inference/preprocessing.py:97`) **deletes every
    URL** (15 patterns) and **every `!` and `?`** from the text before it
    reaches the vectoriser. URLs therefore contribute to
    `body_url_count`/`body_url_density` but **zero tokens to TF-IDF**.
- **Model**: `MLPClassifier(hidden_layer_sizes=(256,128,64), alpha=0.005,
  max_iter=200, early_stopping=False, learning_rate='adaptive',
  solver='adam', activation='relu')`, fit on raw 7015-dim features with
  **no scaler**. Class distribution ≈ 56% phish / 44% legit.
- **Calibration** (notebook 05): best of {isotonic, beta, Platt,
  histogram-binning} by ECE on a 70/30 split of `X_val` (14,868 samples).
  Fitted calibrator lives at `models/pipeline_components/calibrator.pkl`.
- **Online learning** (`inference/online_learner.py`): `partial_fit` on
  MLP weights **only**; the TF-IDF vocabularies are frozen at train time
  and can never grow. An OOV rate >30% raises a log warning but does not
  block the update.

---

## 2. Feature blind spots

The 15 engineered features are all surface, distribution-free signals
over the cleaned body/subject/sender triple. No header inspection, no URL
content analysis, no brand/domain reputation, no attachment signal, no
Unicode class checks. Every feature below is trivially controlled by an
attacker.

| # | Feature | What it measures | How it's gamed |
|---|---|---|---|
| 1 | `body_word_count` | `body.split()` length | Pad with any plausible prose (legal boilerplate, a signature block, a fake "forwarded thread"). 2002–2008 phish bodies in CEAS/TREC/Nigerian cluster at two extremes — 10-word Viagra blurbs and 1000-word 419 letters — so both 80- and 300-word phish look unfamiliar. |
| 2 | `body_exclamation_count` | `body.count('!')` | Drop `!`. Modern phish almost never uses them. Also: the `!` is stripped before TF-IDF anyway, so zero-exclamation phish has no textual counter-signal in the vocabulary. |
| 3 | `email_local_length` | `len(local_part)` | Pick any natural local part. `security@microsoft.com` (8) and `noreply@github.com` (7) land squarely in the legit range. |
| 4 | `name_email_consistency` | substring overlap between display name and local part, **OR** local part in a 20-entry shared-inbox whitelist (`noreply, support, billing, admin, ...`) | This is the most abusable single feature. Spoofing `"Microsoft Security" <support@attacker.tld>` trips the shared-inbox whitelist and is scored **consistent = 1**. Any attacker who sets the display name to match the local part (`"Noreply" <noreply@attacker.com>`) or overlaps any ≥3-char substring also passes. The feature never checks the domain. |
| 5 | `body_url_density` | urls per 100 words | Use 0 or 1 URL embedded in 300+ words of prose and the density collapses toward legit values. Or move the payload into an attachment (PDF, HTML file, `.ics`), a QR code, or a phone-callback — zero URLs, zero signal. |
| 6 | `body_url_count` | count over the 15-pattern list | Same as above, plus: any URL inside an HTML `href` whose display text is bare text gets counted once, identical to a legit newsletter. The feature cannot distinguish one link from twenty, because the **MLP sees `body_url_count` unscaled alongside TF-IDF values in [0,1]** — so a count of 20 is a ~20× outlier that dominates the gradient and pushes the model toward the training-time "20-URL = phish" prior, which is CEAS-era spam, not modern legit newsletters (which often carry 30–80 links). |
| 7 | `body_entropy` | Shannon entropy of body chars (spaces excluded) | Natural English sits near ~4.2 bits. Trivial to land on any target entropy by adding/removing prose. Copy-paste from a real corporate email — entropy matches legit by construction. |
| 8 | `email_digit_ratio` | digit fraction of local part | Use zero digits. `security-alert@microsoft-verify.com` has ratio 0. |
| 9 | `domain_entropy` | Shannon entropy of domain minus TLD | Use a short, low-entropy domain: `ms-365.co`, `g-drive.co`, `okta.help`. All land near legit. Attackers also routinely use compromised legitimate domains (reply-from a hacked WordPress host) — entropy indistinguishable from legit. |
| 10 | `domain_length` | `len(domain)` | Most major SaaS domains (`atlassian.net`, `salesforce.com`, `paypal.com`) are 10–15 chars — any attacker lookalike in that range matches. |
| 11 | `subject_entropy` | entropy of subject | Same story. Copy a real subject line. |
| 12 | `body_avg_word_length` | mean token length | English prose sits at 4.5–5.5. Trivial to match. |
| 13 | `sender_name_exists` | 1 if `Name <email@domain>` regex matches | **Binary**. Every modern phish sets a display name — this feature is effectively a constant 1 on modern attacker traffic, which makes it useless (and if it carries any learned weight, it points toward "phish" only when the attacker *forgets* to set a display name, which never happens). |
| 14 | `subject_exclamation_count` | `subject.count('!')` | Drop `!` from the subject. Modern subjects never use them. |
| 15 | `domain_vowel_consonant_ratio` | vowels / consonants in `[a-z]`-only domain | An attacker picks any pronounceable domain (`microsoft-verify.com`, `google-secure.help`). Ratio matches real brands. |

### Cross-cutting blind spots

- **No homoglyph / IDN / Punycode check.** `google.com` (Cyrillic `о`)
  survives `_extract_sender_components`, passes `_vowel_consonant_ratio`
  (`re.sub(r'[^a-zA-Z]', ...)` silently deletes non-ASCII), and reaches
  the model with domain-level features indistinguishable from the real
  `google.com`.
- **No header/auth signal.** DKIM, SPF, DMARC, `Return-Path`,
  `Authentication-Results`, `Received` chain are never parsed. A sender
  that sets `From: Microsoft Security <security@microsoft.com>` with a
  forged display line goes through untouched — the detector only sees
  the `From:` string.
- **No URL content analysis.** The 15 URL patterns only count. No look
  at link display vs. href mismatch, redirector domains,
  `@`-embedded-userinfo URLs, IP-literal hosts, punycode hosts, shorteners
  (`bit.ly`, `t.co`, `lnkd.in`), or known-brand-in-subdomain
  (`paypal.com.secure-login.xyz`). **URLs are wiped from the text before
  TF-IDF**, so even the hostnames never enter vocabulary.
- **No attachment, no calendar-invite, no QR-code signal.** Any attack
  that moves the payload out of the body text into an attachment, an
  `.ics` invite, or a QR image bypasses every feature except the engineered
  lexical ones.
- **No scaler + unbounded features.** `body_word_count` can be 5000+ and
  `body_url_count` 100+; TF-IDF values are ≤ 1. The MLP was trained with
  `alpha=0.005` and no `StandardScaler` (see `preprocessing.py:8` — the
  omission is explicit). The large-magnitude engineered features dominate
  the first-layer activations, so learned decisions there reflect
  CEAS/TREC-era distributions and collapse on any modern distribution
  that sits outside the training envelope.
- **Online-learning asymmetry.** `OnlineLearner.partial_fit_batch` warms
  the MLP weights on new labelled batches but **cannot expand the TF-IDF
  vocabulary**. So even after feedback is incorporated, any modern word
  (`docusign`, `okta`, `mfa`, `1password`, `onedrive`) stays out-of-vocab
  forever — only the engineered channel can learn the new class, and that
  channel has the blind spots above.

---

## 3. Vocabulary gaps — what the TF-IDF vocabulary is missing

The TF-IDF vocabularies were fit once on the cleaned 2002–2008 corpus
(post URL-strip, post `!?`-strip, post-stopwords, lowercased). They are
frozen in `models/pipeline_components/{subject,body}_vectorizer.pkl`
(189 KB body vocab, 73 KB subject vocab — both small and era-locked).
Categories of modern terms that are almost certainly OOV:

### Legitimate-side OOV (will cause false positives)

- **Cloud and SaaS brand names coined after 2008**: `docusign`, `zoom`,
  `teams`, `slack`, `notion`, `asana`, `airtable`, `figma`, `miro`,
  `loom`, `canva`, `dropbox`, `onedrive`, `gdrive`, `workspace`,
  `office365`, `m365`, `okta`, `auth0`, `1password`, `bitwarden`,
  `datadog`, `pagerduty`, `sentry`, `snowflake`, `databricks`, `vercel`,
  `netlify`, `cloudflare`, `github`, `gitlab`, `bitbucket`, `jira`,
  `confluence`, `stripe`, `shopify`, `patreon`, `substack`, `kickstarter`,
  `twitch`, `discord`, `reddit`, `tiktok`, `instagram` (as sender), `x.com`,
  `linkedin`, `airbnb`, `uber`, `lyft`, `doordash`, `instacart`, `wise`,
  `revolut`, `venmo`, `cashapp`, `chime`, `coinbase`, `binance`.
- **Modern security / account-lifecycle terminology**: `mfa`, `2fa`,
  `otp`, `passkey`, `webauthn`, `totp`, `sso`, `magic link`, `verification
  code`, `authenticator`, `sign-in alert`, `new device`, `unusual activity`,
  `linked account`, `impossible travel`, `password reset`, `reset your
  password` (as trained term — likely present as bigram but the phrase
  is clipped by the stopword drop of `your`), `security key`.
- **Modern transactional terminology**: `estimated delivery`, `tracking
  number`, `one-time code`, `refund issued`, `order shipped`, `invoice
  attached`, `payout`, `ach`, `wire transfer` (likely present but dated),
  `interac`, `sepa`.
- **Modern work / HR terminology**: `standup`, `sprint`, `retro`, `PR
  review`, `merge conflict`, `pull request`, `ci pipeline`, `okr`,
  `performance review`, `benefits enrollment`, `paystub`, `w-2`, `w2` (as
  unigram).
- **Currency / pricing format**: the cleaner deletes `$`, `€`, `£`, `¥`,
  `₹` outright (category `Sc`). Amounts like "$1,499.00" survive only as
  the bare string `1 499 00` — the context that makes it a price is gone.

### Phishing-side OOV (will cause false negatives)

- **OAuth / consent-phishing lexicon**: `oauth`, `consent`, `scope`,
  `app permissions`, `grant access`, `allow`, `tenant`, `application
  permissions`, `azure ad`, `entra`, `graph api`.
- **BEC / invoice-fraud lexicon**: `change of banking details`,
  `updated wire instructions`, `routing number`, `beneficiary`, `eft`,
  `remit to`, `ach details`, `ap contact`.
- **Gift-card / payroll-diversion scam**: `apple gift card`, `amazon
  gift card`, `google play code`, `steam wallet`, `ebay card`, `vanilla
  visa`, `scratch off` (note: `gift` might be in vocab but the compound
  is not).
- **Crypto scam lexicon**: `btc`, `eth`, `usdt`, `wallet address`, `seed
  phrase`, `recovery phrase`, `metamask`, `ledger`, `trezor`, `defi`,
  `airdrop`, `nft`, `rug pull`.
- **MFA-fatigue / push-bombing language**: `push notification`, `approve
  sign-in`, `we sent you a code`, `approve or deny`.
- **Modern-brand impersonation**: the key brands spoofed today
  (Microsoft 365, DocuSign, Adobe Sign, Okta, Dropbox, GitHub, Slack,
  PayPal, Stripe, Shopify, Coinbase, Binance, Netflix, LinkedIn, Amazon
  post-2008 vocabulary, Apple post-2008) are absent as vocabulary. The
  only well-represented post-2000 brand is `cnn` (from CEAS Daily Top 10
  newsletters) and `yahoo` (SpamAssassin Yahoo Groups footer). The model
  has never seen a DocuSign envelope notice.
- **QR / callback-phishing lexicon**: `qr code`, `scan to verify`,
  `voicemail attached`, `call back`, `callback number`, `case id`.

### Deep vocabulary biases (legit-lean and phish-lean tokens the model
over-relies on)

- **Legit-lean (likely trained as strongly legit)**: `debian`,
  `spamassassin`, `apache`, `svn`, `cvs`, `commit`, `wiki`, `enron`,
  `yahoo groups`, `zzzzteana`, `exmh`, `nmh`, `mailman`, `rpm`, `gpg`,
  `perl`, `postfix`, `sendmail`, `listman`, `mhonarc`, `redhat`,
  `r-help`, `sciviews`. Any attacker who embeds `debian`, `spamassassin`,
  `apache`, or `r-help` in their body gets a legit-side push.
- **Phish-lean (likely trained as strongly phish)**: `viagra`, `cialis`,
  `pharmacy`, `replica`, `rolex`, `weight loss`, `mortgage`, `refinance`,
  `diploma`, `nigeria`, `kabila`, `barrister`, `abacha`, `diplomatic`,
  `consignment`, `inheritance`, `beneficiary`, `sir/madam`, `dear friend`,
  `god bless`, `trunk box`. A modern phish that avoids all of these
  tokens loses the phish-lean textual push entirely and must be caught
  by engineered features alone — which, per §2, it won't be.

---

## 4. Training-data gaps — what the eight corpora never saw

Corpus-by-corpus characterisation (derived from samples + the
notebook-01 label distribution):

| Corpus | Era | Label | Character |
|---|---|---|---|
| **TREC_07** | 2007 | 29,399 phish / 24,358 legit | Bulk pharma spam, Nigerian 419, "Brad talking to Billy" pill letters. Legit: Debian mailing lists, OSS project traffic. |
| **CEAS_08** | Aug 2008 | 21,842 phish / 17,312 legit | Same pharma/dating/pump-and-dump spam plus a handful of CNN "Daily Top 10" newsletters. Legit half heavily dominated by SpamAssassin-challenge test mail. |
| **SpamAssassin** | 2002 | 1,718 spam / 4,091 legit | Yahoo Groups mailing lists (`zzzzteana`), IRR, SpamAssassin dev traffic, misc tech discussion. |
| **Nazario** / **Nazario_2** | 2004-era dupes | 1,565 phish each | Classic bank-phish (PayPal, Bank of America, eBay), all with plain-text URLs. Files Nazario and Nazario_2 are **identical duplicates** (same 1565 rows, same memory footprint) — a data-quality bug that has inflated phish class weight. |
| **Nazario_5** | Through 2015 (`DON'T DELETE THIS MESSAGE` folder-internal record dated 2017) | 1,565 phish / 1,500 "legit" | Phish are raw SMTP dumps with full `Received:` headers (the cleaner keeps most of this as prose). "Legit" half is Enron corporate mailing (2001) — BNA Daily Labor Report, internal memos. |
| **Nigerian_Fraud** / **Nigerian_5** | 2002 | 3,332 phish each | ALL-CAPS Nigerian 419 letters. `Nigerian_5`'s legit half is again Enron 2001 (same BNA text as Nazario_5). |

### Entire attack genres absent or under-represented

- **OAuth / consent phishing** (app-permission grants on Microsoft 365 /
  Google Workspace): **0 examples**. Did not exist yet.
- **MFA-fatigue / push bombing**: 0 examples.
- **QR-code phishing ("quishing")**: 0 examples. Body text of a quishing
  email is usually a short legitimate-looking sentence plus an image.
- **Callback / TOAD phishing** (fake invoice with "call this number to
  cancel"): 0 examples.
- **BEC — invoice/wire redirection**: 0 examples. 419 scams are present,
  but the modern BEC pattern (spoofed-internal CFO, terse, no URL, no `!`)
  is not.
- **Spear phishing with open-source reconnaissance** (references to a
  real recent meeting, a real co-worker's name, a real project): 0
  examples. All Nazario phish is generic bulk.
- **Gift-card scam**: 0 examples.
- **Crypto / wallet phishing**: 0 examples.
- **Shipping-lookalike phishing** (fake UPS / FedEx / DHL / Royal Mail /
  Amazon delivery-failure pages): 0 examples for post-2008 brand form.
- **Storage-share phishing** (fake Dropbox/OneDrive/SharePoint
  "document shared with you"): 0 examples.
- **DocuSign / Adobe Sign / PandaDoc envelope impersonation**: 0
  examples.
- **LinkedIn / recruitment bait** (fake job offer, malicious interview
  link): 0 examples.
- **Romance / pig-butchering long-con**: 0 examples of the modern form
  (though some Nazario_5 has similar structure).

### Entire legitimate genres absent or under-represented

- **Modern SaaS notifications**: GitHub PRs, Linear comments, Jira
  assignments, Slack digests, Notion mentions, Figma comments, Stripe
  payouts — **0 examples** in the training corpus.
- **Modern transactional receipts**: Amazon order confirmations (post-2008
  layout), Uber / Lyft trip receipts, DoorDash / Instacart receipts,
  Stripe/Shopify merchant receipts, Apple/Google Pay receipts — **0
  examples** in modern form.
- **Modern newsletters / marketing**: Substack posts, corporate product
  updates (e.g., "New in Linear this week"), brand newsletters with heavy
  tracking URLs (30–80 URLs is normal in a modern Mailchimp send) — **0
  examples**. This is dangerous because the model learned "many URLs =
  phish" from CEAS-era spam.
- **Calendar invites** (`.ics`-bearing meeting requests, all-day OOO
  notices, Google Calendar nudges): 0 examples. The cleaner strips MIME
  headers wholesale, so the `BEGIN:VCALENDAR` structure would be
  mangled anyway.
- **Password-reset / account-verification legitimate email**: 0 modern
  examples. The vocabulary (`one-time code`, `verification code`,
  `magic link`, `approve sign-in`, `we sent you a code`) is either
  partially OOV or dominated by identical vocabulary used in phishing
  training data. The model cannot distinguish a genuine Microsoft
  password-reset email from an impersonation because it never saw either.
- **Professional internal email** in modern form (short all-business
  lines, no signatures stripped, Outlook threading, quoted-printable that
  the cleaner mangles): 0 examples. Enron 2001 is too stylistically
  distant to substitute.
- **HR / benefits / payroll email** (post-2008 style, e.g. ADP, Workday,
  Gusto, Rippling, BambooHR notifications): 0 examples.
- **Marketing with aggressive tone** (Black Friday / flash-sale
  retailer emails, loud subjects with legit intent): under-represented.
  Aggressive subject lines in the training set are almost always phish.

### Structural biases in the training data

- **Nazario and Nazario_2 are identical.** ~1,565 rows duplicated into
  the phish pool before dedup, which dedup on `(sender, subject, body)`
  should have caught — but column-level variations (URL column type
  differs: int vs str) survive dedup in most splits. This over-weights
  the specific 2004-era bank phish towards the phish class.
- **Legit class is tech-nerd-heavy.** Debian, SpamAssassin, Apache SVN,
  R-help, Yahoo Groups, Enron — the legit half is dominated by male,
  US/UK, English, plain-text, ASCII-only mailing-list traffic. **The
  model has no notion of "legitimate marketing" or "legitimate brand
  newsletter" as a genre at all.**
- **Phish class is pharma+419-heavy.** Over 60% of phish examples are
  pharma/Viagra or Nigerian inheritance-scams — two genres that have
  been essentially extinct from enterprise inboxes for a decade.
- **All uppercase = phish.** Nigerian_Fraud and Nigerian_5 are entirely
  ALL-CAPS. The model has likely learned "shouting body text = phish"
  as a strong signal. A modern legitimate email that happens to be
  short and ALL-CAPS for a good reason (a genuine shipping disruption
  alert in all caps, a security page notice, an Emergency Alert System
  forward) gets flagged.
- **Label leakage via `source_dataset`**: thankfully the `source_dataset`
  column is dropped before feature engineering. But anything stylistic
  that identifies a source (Yahoo Groups footer, Debian list footer,
  `-----Original Message-----` artefacts that the cleaner mostly keeps)
  leaks corpus identity and therefore label.

---

## 5. Predicted failure categories

Specific, named email categories where I predict the current model will
misclassify. Each is paired with the mechanism in §2–§4 that drives the
failure, so the stress-test dataset can target it precisely.

### 5.1 False negatives (phish that the model will call legit)

1. **Microsoft 365 OAuth consent phishing.** Short (50–120 words), one
   `https://login.microsoftonline.com/...` URL (real Microsoft hostname,
   attacker-owned tenant), no `!`, neutral prose, display name
   `Microsoft 365`, sender on an attacker-owned domain (e.g.
   `alerts@ms-security-team.com`). → `name_email_consistency`=1 (display
   name word is in local part or whitelist), `body_exclamation_count`=0,
   `body_url_count`=1, `body_entropy` near legit. URL is stripped before
   TF-IDF so `microsoftonline` contributes nothing. Lexical content is
   OOV for the phish-lean tokens. **Predicted: legit, high confidence.**

2. **DocuSign / Adobe Sign envelope impersonation.** HTML-styled email
   with a "Review document" button. Cleaner strips HTML and currency
   symbols; surviving text is "You have a document to review from
   <name>. View completed document. This message was sent via DocuSign."
   — all OOV phish-side (`docusign`, `review`, `completed`, `envelope`
   are not strongly phish-associated in the 2008 vocab). Sender
   `dse@docusign-alerts.net`. **Predicted: legit.**

3. **Okta / 1Password / Auth0 credential-harvest page link.** "We
   detected a new sign-in. If this wasn't you, secure your account." One
   URL. Prose. No exclamation marks. `sender_name_exists`=1,
   `name_email_consistency`=1 if display-name contains `security` and
   sender is `security-alerts@okta-verify.app`. Every token that looks
   suspicious (`okta`, `sign-in`, `secure`) is OOV. **Predicted: legit.**

4. **Invoice-fraud BEC.** "Hi — updated wire instructions attached.
   Please route Friday's payment to the account below. Bank: <X>,
   Routing: 12345, Account: 67890. Thanks, Mark." No URLs, no `!`,
   no HTML, 40 words. Display name matches a real exec. Sender domain
   is a typosquat (e.g. `@companyname-corp.com` vs `@companyname.com`).
   `body_url_count=0` is the strongest legit signal in the whole feature
   set for this email. **Predicted: legit with very high confidence.**

5. **Gift-card / payroll diversion ("Are you available?")**.
   `Sent from iPhone`, 15 words: `"Hi, are you at your desk? I need a
   quick favor — let me know when you're free. — CEO"`. No URLs,
   no `!`, short body, low entropy. **Predicted: legit.** Modern detectors
   catch this on sender-domain reputation; AURA has none.

6. **QR-code phishing body.** "Please scan the attached QR code with
   your mobile device to view the secure document." Body is 15–25 words,
   zero URLs, zero `!`. **Predicted: legit.** AURA never sees the
   image.

7. **Shipping-failure phishing** (DHL / FedEx / UPS / Royal Mail / Amazon
   post-2008 format). "Your package 1Z-... could not be delivered.
   Schedule redelivery: https://dhl-delivery-update.net/xyz". One URL,
   short, neutral tone. Display name `DHL Express`. Sender
   `@dhl-delivery-update.net`. Brand tokens `dhl`, `package`,
   `redelivery` are all either OOV or weakly associated. **Predicted:
   legit.**

8. **Crypto-wallet seed-phrase phishing.** "Your Coinbase wallet needs
   re-verification. Confirm your seed phrase here." One URL, ~30 words.
   All the high-signal tokens (`coinbase`, `wallet`, `seed phrase`) are
   OOV. **Predicted: legit.**

9. **LinkedIn InMail recruitment bait.** "Hi <Name>, I have a Senior
   Engineer opening at a Series B startup — stock options + remote. Are
   you open to a quick chat? Here's the role: <link>". Legitimate-style
   prose, 1 URL, 0 `!`, display name is a plausible recruiter, sender
   on a free-mail domain (`@gmail.com`, `@proton.me`). Every signal is
   legit-coded. **Predicted: legit.**

10. **MFA-fatigue follow-up.** After bombing the victim with push
    prompts, an email: "We noticed you denied a sign-in request. If this
    was you, no action needed. If this wasn't you, verify your account:
    <link>". 30 words, 1 URL, 0 `!`, low entropy, benign prose.
    **Predicted: legit.**

11. **Homoglyph / IDN domain impersonation.** Sender `<support@pаypal.com>`
    (Cyrillic `а`). The `_vowel_consonant_ratio` function deletes the
    Cyrillic letter (`re.sub(r'[^a-zA-Z]', '', ...)`), and
    `domain_entropy` computes over `paypal` which is low-entropy and
    legit-coded. No other check on the domain exists. **Predicted:
    legit.**

12. **Compromised-legitimate-account phishing.** A phish sent from a
    real compromised WordPress/corporate mailbox — sender domain is real,
    display name is real, headers would pass SPF/DKIM (we don't check
    those anyway). Body contains a one-line "can you review this?" + a
    malicious Dropbox link. Every engineered feature says legit.
    **Predicted: legit.**

### 5.2 False positives (legit that the model will call phish)

1. **Aggressive marketing newsletter** (Black Friday / Cyber Monday
   flash sale). Legit retailer: body with 40–80 URLs (one per product
   image + tracking pixel), 5–10 `!` marks, subjects like
   `Last chance! 50% off everything! Ends tonight!`. **Every engineered
   feature screams phish**: high `body_url_count`, high
   `body_url_density`, high `body_exclamation_count`,
   high `subject_exclamation_count`. **Predicted: phish.**

2. **Substack post with embedded tracking links.** 2000-word
   thoughtful essay with ~50 share/track URLs and author-name links.
   Sender: `<author@substack.com>`. Brand token `substack` is OOV.
   `body_url_count` 50+, `body_url_density` high. **Predicted: phish.**

3. **GitHub notification digest.** "Issue #123 was closed by <user>. View
   on GitHub: <link>. You received this because you were mentioned.
   Manage notifications: <link>." Display name `<User> (via GitHub)`,
   sender `notifications@github.com`. Notifications-style email: short
   lines, multiple URLs, impersonal. `github` is OOV; the
   `notifications@` local part hits the shared-inbox whitelist so at
   least `name_email_consistency`=1. But `body_url_count` is high and
   the unfamiliar prose (`issue closed`, `pull request`, `mentioned`)
   gets no legit lift from vocabulary. **Likely REVIEW; can tip to
   phish on the right body.**

4. **Amazon / Shopify / Stripe order confirmation (modern format).**
   HTML-heavy receipt. After cleaning: `Order confirmed Thank you for
   your order Order ID 123 456 Total 99 99 Shipping 4 99 Estimated
   delivery Tue Apr 23 Track package Manage order Return policy`. High
   URL count (view-order, track, receipt, help, unsubscribe), currency
   symbols deleted, brand tokens (`shopify`, `stripe`, `amazon post-2008
   layout terms`) are OOV, exclamation-sparse. `body_url_count` 8–15,
   `body_url_density` moderate-high. **Predicted: phish in many cases
   (especially any template with "Verify your order" in subject).**

5. **Password-reset legitimate email.** "We received a request to reset
   your password for your <brand> account. Click below to continue. If
   you didn't request this, ignore this email." Short, 1 URL, 0 `!`.
   The prose is indistinguishable from credential-harvest phish that
   the model has *never seen* — so the model has to fall back on the
   engineered features, where the feature pattern of a real
   password-reset email (`body_url_count`=1–2, `body_exclamation_count`=0,
   `name_email_consistency`=1 via `noreply` whitelist,
   `body_word_count`~60) matches neither the legit cluster (long tech
   mailing-list prose) nor the phish cluster (pharma spam / 419). **Very
   uncertain — likely REVIEW zone on some, phish on others, especially
   when the sender domain is long (`accounts.google.com` has
   `domain_length`=18).**

6. **Calendar invite forward.** Forwarded `.ics` invite body:
   `BEGIN:VCALENDAR VERSION:2.0 ...` — cleaner strips the colons and
   structure; what's left is a meeting title, attendee list, and one
   webcal:// URL. Webcal URL is counted but stripped from TF-IDF.
   `body_word_count` very low, `body_url_count`=1. Falls into a sparse
   region of feature space. **Uncertain prediction.**

7. **Corporate HR benefits-enrollment email** (Workday / ADP / Gusto
   layout). "Your enrollment window is open. Review your elections in
   Workday. Questions? Contact HR." Multiple URLs, short body, display
   name `Workday`, sender `@myworkday.com` (long domain, hyphen-free).
   Every content token is OOV. Indistinguishable to the model from an
   Okta-credential-harvest lure. **Predicted: phish.**

8. **Short personal email from a new contact.** "Hey — great meeting
   you yesterday, here's the link to the deck I mentioned: <gdrive
   link>. Let me know if you have questions. Best, Mark." Short, one
   URL, neutral prose, sender on `@gmail.com` (free mail, short domain),
   display name `Mark` (single token), `name_email_consistency` unlikely
   to match. **Likely predicted phish** on the basis of a short body
   with one URL and weak legit tokens — this is the same shape as every
   modern spear-phish in the stress-test set.

9. **Legit ALL-CAPS security-alert forward.** e.g. an IT team forwards
   `"URGENT: MAINTENANCE WINDOW TONIGHT 22:00-01:00 UTC. SERVICES WILL
   BE UNAVAILABLE."`. Low word count, all caps. The model has been
   trained to call all-caps short body "phish" because of Nigerian_Fraud.
   **Predicted: phish.**

10. **Legitimate Nigerian business email.** Any real email from a
    Nigerian sender on a Nigerian domain (`@<name>.ng`, `@<name>.com.ng`).
    The model has seen `ng` domains only inside 419 scams. **Predicted:
    phish.**

11. **Mailing-list email from a list that didn't exist in 2008.** A
    Discord/Slack community digest, a Kubernetes SIG mailing list, a
    modern GitHub Discussions email. Many URLs, unfamiliar vocabulary,
    notifications-style sender. The model's learned "legit = Debian
    mailing list" prior does not transfer. **Likely phish or REVIEW.**

12. **Multilingual body** (any non-English, or bilingual). The
    vectorisers dropped stopwords via `stop_words='english'` but have no
    non-English vocabulary. A legitimate German, Spanish, Portuguese,
    Japanese, or Arabic email has essentially 100% OOV content in both
    TF-IDF channels; the engineered features are the only signal. If
    those features happen to land in the phish region, the email gets
    flagged purely for language.

---

## 6. Cross-cutting exploit recipes (for the stress-test generator)

The quickest ways to convert a generic phish into an AURA-evader are:

1. **Delete every `!` and `?`.** Removes the single most discriminative
   engineered feature and reduces TF-IDF difference to zero (the
   cleaner strips them anyway).
2. **Keep `body_url_count` at 1, ideally with a long prose body.** Drops
   `body_url_density` into the legit range.
3. **Pick a display name whose first token is `noreply`, `support`,
   `billing`, `alerts`, `team`, `notifications`, `admin`, `help`,
   `info`, or `updates`.** Instant `name_email_consistency=1` via the
   shared-inbox whitelist.
4. **Use a pronounceable short domain** (`domain_length` 10–15,
   `domain_entropy` ≈ 3, `domain_vowel_consonant_ratio` ≈ 0.6).
5. **Make the body 150–400 words of neutral prose** — lands
   `body_word_count`, `body_avg_word_length`, `body_entropy` in legit
   bounds.
6. **Use modern brand/SaaS vocabulary** (`docusign`, `okta`, `mfa`,
   `1password`). All OOV → engineered features alone decide → per above,
   they decide "legit".

Conversely, to force a false positive on a legit email:

1. **Use aggressive marketing punctuation and tracking URLs** — the
   Black Friday newsletter template.
2. **All-caps body, short, no URL** — spoofs the Nigerian-scam
   engineered-feature shape without the content.
3. **Body on a `.ng` or `.tk` or `.su` domain** — per-corpus artefact
   biases.
4. **Embed strongly phish-coded tokens in otherwise benign prose**:
   `dear friend`, `beneficiary`, `consignment`, `diploma`, `refinance`,
   `mortgage`, `replica`. Every one of these is a TF-IDF term with a
   strong phish lean from 2002–2008 training data.

---

## 7. Summary — where to aim the stress test

The stress-test dataset should be engineered to exercise three
independent failure surfaces, in order of expected severity:

1. **Modern-vocabulary phishing where all 15 engineered features look
   legit** (§5.1 items 1–5, 7–12). Largest blast radius: any clean,
   modern, OAuth/brand-impersonation/BEC phish. This is the category
   the production v1.0 model will miss most often.
2. **Modern-format legitimate email where engineered features pattern-
   match 2008-era phish** (§5.2 items 1–7, 9–12). Will produce the
   damaging false positives that destroy user trust.
3. **Adversarial exploits of specific feature implementations**
   (homoglyphs §5.1 #11, shared-inbox whitelist §6 #3, `body_url_count`
   vs `body_url_density` manipulation §6 #2). These are the
   proof-of-concept evaders that show the scoring logic is fundamentally
   gameable.

The synthetic-generation scripts already under `scripts/` —
`gen_brand_impersonation`, `gen_modern_technique_phishing`,
`gen_spear_phishing`, `gen_commercial_notifications`,
`gen_newsletters_digests`, `gen_personal_conversational`,
`gen_professional_internal`, `gen_retail_transactional` — map neatly
onto the failure categories above, which suggests the team already
suspected the gaps. The stress-test design in the next step should
verify each predicted failure quantitatively and produce a ranked list
of which fix (feature engineering, vocabulary expansion, header parsing,
or online-learning retraining) closes the largest gap per unit of work.
