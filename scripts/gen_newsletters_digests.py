"""Generate 700 modern newsletter & digest emails (label=0) for AURA online-learning augmentation.

Follows section 3.5 of online_learning_dataset.md and applies the quality checks from section 6.

Design:
- 4 publication types: tech_newsletter, industry_digest, personal_newsletter, community_digest.
- 4 subject styles: numbered, date, topic, personal.
- Each body is assembled from an intro + 3-6 story blocks (headline + short summary + bare
  domain URL) + sign-off + unsubscribe footer. This guarantees multiple topics and multiple
  bare-domain URLs per row while staying in the 150-400-word band.
- Strict section-6 gate: no typosquatting, no URL shorteners, no urgency, no credential
  requests, unsubscribe footer required, word count 150-400.
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
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/newsletters_digests.csv"
)


# ------------------------------------------------------------------------------------
# Publications: the sender, display, and related metadata per publication.
# ------------------------------------------------------------------------------------

PUBLICATIONS = {
    # ---------- tech newsletters ----------
    "tldr": {
        "type": "tech_newsletter",
        "name": "TLDR",
        "senders": ['"TLDR" <dan@tldrnewsletter.com>', '"TLDR Newsletter" <dan@tldrnewsletter.com>'],
        "home": "tldrnewsletter.com",
    },
    "morning_brew": {
        "type": "tech_newsletter",
        "name": "Morning Brew",
        "senders": ['"Morning Brew" <crew@morningbrew.com>'],
        "home": "morningbrew.com",
    },
    "bytes": {
        "type": "tech_newsletter",
        "name": "Bytes",
        "senders": ['"Bytes" <bytes@bytes.dev>'],
        "home": "bytes.dev",
    },
    "js_weekly": {
        "type": "tech_newsletter",
        "name": "JavaScript Weekly",
        "senders": ['"JavaScript Weekly" <peter@cooperpress.com>'],
        "home": "javascriptweekly.com",
    },
    "python_weekly": {
        "type": "tech_newsletter",
        "name": "Python Weekly",
        "senders": ['"Python Weekly" <rahul@pythonweekly.com>'],
        "home": "pythonweekly.com",
    },
    "pragmatic_engineer": {
        "type": "tech_newsletter",
        "name": "The Pragmatic Engineer",
        "senders": ['"The Pragmatic Engineer" <gergely@pragmaticengineer.com>'],
        "home": "pragmaticengineer.com",
    },
    "data_elixir": {
        "type": "tech_newsletter",
        "name": "Data Elixir",
        "senders": ['"Data Elixir" <lon@dataelixir.com>'],
        "home": "dataelixir.com",
    },
    "changelog": {
        "type": "tech_newsletter",
        "name": "Changelog News",
        "senders": ['"Changelog News" <editors@changelog.com>'],
        "home": "changelog.com",
    },

    # ---------- industry digests ----------
    "acm_technews": {
        "type": "industry_digest",
        "name": "ACM TechNews",
        "senders": ['"ACM TechNews" <newsletter@acm.org>'],
        "home": "acm.org",
    },
    "mit_tech_review": {
        "type": "industry_digest",
        "name": "MIT Tech Review",
        "senders": ['"MIT Tech Review" <newsletters@technologyreview.com>'],
        "home": "technologyreview.com",
    },
    "axios": {
        "type": "industry_digest",
        "name": "Axios Pro Rata",
        "senders": ['"Axios Pro Rata" <dan@axios.com>'],
        "home": "axios.com",
    },
    "the_information": {
        "type": "industry_digest",
        "name": "The Information",
        "senders": ['"The Information" <newsletters@theinformation.com>'],
        "home": "theinformation.com",
    },
    "wired_daily": {
        "type": "industry_digest",
        "name": "Wired Daily",
        "senders": ['"Wired Daily" <newsletter@wired.com>'],
        "home": "wired.com",
    },

    # ---------- personal newsletters (substack-style) ----------
    "lenny": {
        "type": "personal_newsletter",
        "name": "Lenny's Newsletter",
        "senders": ['"Lenny Rachitsky" <newsletter@substack.com>'],
        "home": "lennysnewsletter.com",
    },
    "stratechery": {
        "type": "personal_newsletter",
        "name": "Stratechery",
        "senders": ['"Ben Thompson" <ben@stratechery.com>'],
        "home": "stratechery.com",
    },
    "matt_levine": {
        "type": "personal_newsletter",
        "name": "Money Stuff",
        "senders": ['"Matt Levine" <noreply@mail.bloomberg.net>'],
        "home": "bloomberg.com",
    },
    "platformer": {
        "type": "personal_newsletter",
        "name": "Platformer",
        "senders": ['"Casey Newton" <newsletter@platformer.news>'],
        "home": "platformer.news",
    },
    "dense_discovery": {
        "type": "personal_newsletter",
        "name": "Dense Discovery",
        "senders": ['"Kai Brach" <hello@densediscovery.com>'],
        "home": "densediscovery.com",
    },

    # ---------- community digests ----------
    "stackoverflow": {
        "type": "community_digest",
        "name": "Stack Overflow",
        "senders": ['"Stack Overflow" <noreply@stackoverflow.com>'],
        "home": "stackoverflow.com",
    },
    "dev_to": {
        "type": "community_digest",
        "name": "DEV Community",
        "senders": ['"DEV Community" <hello@dev.to>'],
        "home": "dev.to",
    },
    "hacker_news_daily": {
        "type": "community_digest",
        "name": "Hacker News Daily",
        "senders": ['"Hacker News Daily" <noreply@hndigest.com>'],
        "home": "news.ycombinator.com",
    },
    "product_hunt": {
        "type": "community_digest",
        "name": "Product Hunt Daily",
        "senders": ['"Product Hunt" <digest@producthunt.com>'],
        "home": "producthunt.com",
    },
    "indie_hackers": {
        "type": "community_digest",
        "name": "Indie Hackers",
        "senders": ['"Indie Hackers" <hello@indiehackers.com>'],
        "home": "indiehackers.com",
    },
    "reddit_popular": {
        "type": "community_digest",
        "name": "Reddit Popular",
        "senders": ['"Reddit" <noreply@redditmail.com>'],
        "home": "reddit.com",
    },
}


PUBS_BY_TYPE = {}
for k, v in PUBLICATIONS.items():
    PUBS_BY_TYPE.setdefault(v["type"], []).append(k)


# ------------------------------------------------------------------------------------
# Story block pool — (topic, headline, summary, url). Each block provides one
# multi-sentence section of the digest body.
# ------------------------------------------------------------------------------------

STORIES = [
    # --- AI / ML ---
    (
        "ai",
        "OpenAI previews next-generation model capabilities",
        "The company demoed a smaller model that matches GPT-4 on reasoning benchmarks while "
        "running at roughly a quarter of the cost. Early access is limited to enterprise "
        "customers through the API.",
        "openai.com/blog",
    ),
    (
        "ai",
        "Anthropic research on interpretability of large models",
        "A new paper decomposes the internal features of a production-grade language model "
        "and shows that many safety-relevant concepts have surprisingly crisp internal "
        "representations.",
        "anthropic.com/research",
    ),
    (
        "ai",
        "Meta releases open-weights multimodal model",
        "The release pairs a vision encoder with a small language model and is tuned for "
        "on-device inference. Benchmark numbers for document understanding look competitive "
        "with closed-weight offerings.",
        "ai.meta.com/blog",
    ),
    (
        "ai",
        "Arxiv paper: scaling laws for long-context retrieval",
        "Authors at Stanford and DeepMind propose a revised scaling law for retrieval-augmented "
        "generation that explains why most open-source models plateau around 16k tokens in "
        "practical workloads.",
        "arxiv.org/abs/2401.01234",
    ),
    (
        "ai",
        "Hugging Face adds structured-output tools to Inference API",
        "The new feature lets callers pin outputs to a JSON schema without post-hoc validation. "
        "It works with any model family that ships with a Hugging Face-native tokenizer.",
        "huggingface.co/blog",
    ),
    # --- developer / languages ---
    (
        "dev",
        "React team posts roadmap for the next release",
        "Compiler work takes centre stage, along with new server-components defaults and a "
        "sharper deprecation path for class components. Nothing breaks in the interim releases.",
        "react.dev/blog",
    ),
    (
        "dev",
        "Rust 1.87 lands with async trait improvements",
        "Native async trait support is now usable in most production contexts. The release also "
        "includes a substantial cargo overhaul that cuts build times on large workspaces.",
        "blog.rust-lang.org",
    ),
    (
        "dev",
        "TypeScript 5.5 beta available",
        "The update brings inferred type predicates and better narrowing inside template literal "
        "types. A handful of long-standing edge cases in union narrowing are resolved.",
        "devblogs.microsoft.com/typescript",
    ),
    (
        "dev",
        "Python 3.13 release candidate announced",
        "Headline items are the experimental free-threaded build, a tiered JIT, and improved "
        "error messages. The release candidate is a good checkpoint for library maintainers.",
        "python.org/downloads",
    ),
    (
        "dev",
        "Go team outlines generics improvements",
        "Several ergonomic rough edges are addressed in the proposal, including inference "
        "through method calls and better error reporting when type inference fails.",
        "go.dev/blog",
    ),
    (
        "dev",
        "Node.js 22 hits LTS status",
        "The LTS promotion brings native WebSocket client support, improved V8 flags, and a "
        "stable built-in test runner. Upgrade paths from Node 20 should be straightforward.",
        "nodejs.org/en/blog",
    ),
    # --- cloud / infra ---
    (
        "cloud",
        "AWS announces price cuts on egress for most regions",
        "Customers moving data out of S3 will see a meaningful reduction on cross-region and "
        "internet egress. The change applies retroactively for the current billing cycle.",
        "aws.amazon.com/blogs",
    ),
    (
        "cloud",
        "Google Cloud adds new instance family for inference workloads",
        "The new family bundles Nvidia hardware with a memory-optimised host configuration. "
        "Pricing is slightly below comparable GPU SKUs at other providers.",
        "cloud.google.com/blog",
    ),
    (
        "cloud",
        "Azure adds private connectivity for managed AI services",
        "Enterprises can now pin AI service traffic to private virtual networks without routing "
        "through the public internet. The rollout covers the top eight regions first.",
        "azure.microsoft.com/en-us/blog",
    ),
    (
        "cloud",
        "Cloudflare expands R2 with tiered storage",
        "R2 now exposes cold and archival tiers with automatic movement policies. The pricing "
        "page has a handy calculator for working out the cross-tier trade-offs.",
        "blog.cloudflare.com",
    ),
    # --- business / startups ---
    (
        "biz",
        "Stripe reports record quarter as payment volume rises",
        "The company processed a record volume in the quarter, buoyed by strong cross-border "
        "activity. Management noted continued margin improvement on the core card business.",
        "stripe.com/press",
    ),
    (
        "biz",
        "Series B round closes at favourable terms for infra startup",
        "The round is led by a tier-one fund with participation from earlier backers. The "
        "company will use the capital to expand its go-to-market in Europe.",
        "techcrunch.com/startups",
    ),
    (
        "biz",
        "Post-IPO software stocks see modest rally",
        "A handful of recently listed SaaS names traded higher following better-than-expected "
        "forward guidance. Enterprise software is outperforming consumer internet year-to-date.",
        "bloomberg.com/markets",
    ),
    (
        "biz",
        "Analyst note on AI infrastructure spend",
        "A sell-side note projects AI infrastructure spend will continue to outpace software "
        "revenue growth through next year. Capex plans at the three major clouds support the "
        "thesis.",
        "ft.com/companies/technology",
    ),
    # --- research / reports ---
    (
        "research",
        "State of the developer ecosystem report published",
        "The annual report covers language popularity, tooling, and salary bands across over "
        "forty countries. Python retains its top spot and Rust continues its steady climb.",
        "jetbrains.com/research",
    ),
    (
        "research",
        "GitHub Octoverse highlights the year in open source",
        "The report digs into contribution patterns, regional trends, and the rise of AI-assisted "
        "pull-request activity. India overtook Germany in new contributors this year.",
        "github.blog/octoverse",
    ),
    (
        "research",
        "Linux Foundation releases open-source security paper",
        "The paper surveys the state of SBOMs, reproducible builds, and package signing across "
        "major ecosystems. Adoption of sigstore has reached a practical tipping point.",
        "linuxfoundation.org/research",
    ),
    # --- security ---
    (
        "security",
        "Critical vulnerability patched in widely used SSH library",
        "Maintainers released a patch within 24 hours of the disclosure. Most distributions have "
        "already published updated packages and upgrade is strongly recommended.",
        "nvd.nist.gov/vuln",
    ),
    (
        "security",
        "Chrome ships new isolation feature for enterprise tabs",
        "The feature isolates process memory per security principal and reduces the blast radius "
        "of cross-site attacks. Deployment is controlled via group policy.",
        "chromium.org/security",
    ),
    (
        "security",
        "1Password adds passkey support for team accounts",
        "Passkeys are now a first-class credential alongside passwords. Admins can enforce "
        "passkey-preferred sign-in across their workspaces.",
        "1password.com/blog",
    ),
    # --- product / community ---
    (
        "product",
        "Notion rolls out database automations to all workspaces",
        "The feature graduates from beta and is now available on every plan. Templates cover "
        "common patterns like approval flows and weekly check-ins.",
        "notion.so/blog",
    ),
    (
        "product",
        "Figma publishes updated plugin API",
        "The new API surface consolidates several older endpoints and adds granular permission "
        "scopes. Existing plugins continue to work without changes.",
        "figma.com/blog",
    ),
    (
        "community",
        "Stack Overflow highlights questions from the past week",
        "Highest-voted questions this week cover TypeScript narrowing, Postgres JSONB indexing, "
        "and best-practice Python packaging. Each answer has a clear worked example.",
        "stackoverflow.com/questions",
    ),
    (
        "community",
        "DEV Community post of the week on career transitions",
        "A long-form essay from a senior engineer about moving from individual contributor into "
        "staff-level roles has attracted thousands of comments and bookmarks.",
        "dev.to/top",
    ),
    (
        "community",
        "Product Hunt top launches of the week",
        "A new AI-first calendar app tops the charts, followed by a developer-focused note-taking "
        "tool and a community wiki for indie founders.",
        "producthunt.com/topics",
    ),
    (
        "community",
        "Indie Hackers feature on bootstrapped SaaS revenue",
        "Three bootstrapped SaaS founders share the dashboards and growth experiments behind "
        "crossing the quarter-million ARR mark. The common thread is patient distribution work.",
        "indiehackers.com/posts",
    ),
    (
        "community",
        "Reddit popular thread on unexpected career changes",
        "Hundreds of commenters describe the unlikely pivots that landed them in their current "
        "roles. The top answers focus on side projects that turned into full-time work.",
        "reddit.com/r/cscareerquestions",
    ),
]


# Block templates — slight wording variety on how we present the headline.
BLOCK_TEMPLATES = [
    "• {headline}\n{summary}\nRead more: {url}",
    "# {headline}\n{summary}\n{url}",
    "{headline}\n{summary} ({url})",
    "> {headline}\n  {summary}\n  Link: {url}",
    "◆ {headline}\n{summary}\nSource: {url}",
]


# ------------------------------------------------------------------------------------
# Intros and sign-offs — vary per publication type.
# ------------------------------------------------------------------------------------

INTROS = {
    "tech_newsletter": [
        "Hi there, welcome to issue #{issue} of {name}. Here's what's worth your time this "
        "{day} — {count} quick reads across AI, tooling, and shipping.",
        "Good morning. This is {name}, issue #{issue} for {month} {dom}. Grabbing the headlines "
        "that mattered this week so you can skim them in five minutes.",
        "Hey — {name} here. Issue #{issue} covers the biggest moves in AI and developer tools "
        "from the past seven days. Short, skimmable, and as always no ads above the fold.",
    ],
    "industry_digest": [
        "Welcome to {name}, vol. {vol} for {month} {dom}. Today's digest covers the biggest "
        "stories in technology and venture, curated from our newsroom.",
        "Good afternoon — this is {name}, your {day} roundup. The headlines below pull together "
        "{count} stories our editors think will matter most over the next quarter.",
        "Hi subscribers — {name} here with the week's industry digest. Volume {vol}, focused on "
        "enterprise tech, cloud spend, and the AI capex story.",
    ],
    "personal_newsletter": [
        "Hi friends, thanks for reading. This is {name} for {month} {dom} — a handful of links "
        "and thoughts from the week, plus one longer piece at the bottom.",
        "Welcome back to {name}. A shorter edition this week since I was travelling, but a few "
        "pieces below that really stuck with me and are worth your time.",
        "Hey, {name} here. This week I've been thinking about {topic} — you'll see that thread "
        "running through a few of the picks below. As always, reply to this email with thoughts.",
    ],
    "community_digest": [
        "Hi — here's your {day} {name} digest. Top posts and discussions from the community "
        "over the past seven days, curated automatically from what's been getting attention.",
        "Welcome to this week's {name} roundup. Top questions, highest-voted answers, and the "
        "community posts that drew the most engagement — all in one place.",
        "Your weekly {name} highlights are below. We picked {count} items based on votes, "
        "comments, and saves from members like you.",
    ],
}


SIGNOFFS = {
    "tech_newsletter": [
        "That's it for this week. Forward to a colleague if something here was useful — it's "
        "the best way to help us keep the newsletter going.\n\nUntil next {day},\n{name}",
        "See you on {day2}. If you have feedback on any of the picks, hit reply — we read "
        "every response.\n\nThanks for reading,\n{name}",
    ],
    "industry_digest": [
        "That's the digest for this week. Our next issue lands on {day2} at the usual time.\n\n"
        "— The {name} team",
        "Thanks for reading {name}. Forward to a colleague if any of these pieces sparked a "
        "useful conversation.\n\n— The {name} editors",
    ],
    "personal_newsletter": [
        "Thanks for reading. As always, replies to this email come straight to me and I do "
        "my best to write back.\n\nUntil next {day2},\n{name}",
        "That's everything for today. Hit reply if you have pushback, counterpoints, or "
        "links I should read.\n\nCheers,\n{name}",
    ],
    "community_digest": [
        "That's the community roundup for this week. See you on {day2}.\n\n— The {name} team",
        "Thanks for being part of the {name} community. We'll see you in your inbox next "
        "{day2}.\n\n— The {name} team",
    ],
}


# Unsubscribe footers — several variants, all contain the word "unsubscribe"
UNSUB_FOOTERS = [
    "\n\n—\nYou're receiving this because you subscribed to {name}. "
    "Unsubscribe: {home}/unsubscribe | Manage preferences: {home}/preferences",
    "\n\n---\nSent to a subscriber of {name}. If you'd rather not receive these, "
    "unsubscribe at {home}/unsubscribe.",
    "\n\n--\nYou signed up at {home}. Unsubscribe any time: {home}/unsubscribe. "
    "Forward to a friend — they can subscribe at {home}/subscribe.",
    "\n\n—\nThis email was sent to you by {name}. "
    "To stop receiving these, unsubscribe here: {home}/unsubscribe.",
    "\n\n--\n{name} | {home}\nNo longer want these emails? Unsubscribe: {home}/unsubscribe.",
]


# ------------------------------------------------------------------------------------
# Subject templates — four styles.
# ------------------------------------------------------------------------------------

SUBJECTS = {
    "numbered": [
        "Issue #{issue}",
        "{name} #{issue}",
        "Vol. {vol}, {month} {year}",
        "{name} — Issue {issue}",
        "#{issue}: {topic} and more",
        "{name} Vol. {vol}",
    ],
    "date": [
        "Your weekly roundup — {month} {dom}",
        "This week in {topic}",
        "{name}: {day}, {month} {dom}",
        "Weekly digest for {month} {dom}",
        "{month} {dom} — your {day} briefing",
        "This {day}'s top reads",
    ],
    "topic": [
        "5 things you need to know this week",
        "Top stories in {topic}",
        "{count} reads for your {day}",
        "What's happening in {topic}",
        "The biggest stories in {topic} this week",
        "{count} links worth your time",
    ],
    "personal": [
        "What I've been reading",
        "This week's picks",
        "A few things from my week",
        "Thinking about {topic}",
        "What I'm reading this week",
        "Links I enjoyed this week",
    ],
}


TOPICS = [
    "AI", "machine learning", "developer tools", "cloud", "open source",
    "product", "startups", "security", "design", "web performance", "data",
    "engineering leadership", "venture", "infrastructure",
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MONTHS = [
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
]


# ------------------------------------------------------------------------------------
# Plan: sum must equal 700.
# ------------------------------------------------------------------------------------

PLAN = [
    ("tech_newsletter", 250),
    ("industry_digest", 180),
    ("personal_newsletter", 150),
    ("community_digest", 120),
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


def build_ctx(pub_key: str, subject_style: str) -> dict:
    pub = PUBLICATIONS[pub_key]
    return {
        "name": pub["name"],
        "home": pub["home"],
        "issue": random.randint(20, 320),
        "vol": random.randint(2, 18),
        "month": pick(MONTHS),
        "dom": random.randint(1, 28),
        "day": pick(DAYS),
        "day2": pick(DAYS),
        "topic": pick(TOPICS),
        "count": random.choice(["5", "6", "7", "8"]),
        "year": random.choice([2024, 2025, 2026]),
        "style": subject_style,
    }


def build_body(pub_key: str, ctx: dict) -> str:
    pub = PUBLICATIONS[pub_key]
    ptype = pub["type"]

    # 4-6 story blocks; sample distinct stories
    n_blocks = random.randint(4, 6)
    picks = random.sample(STORIES, k=n_blocks)

    block_tpl = pick(BLOCK_TEMPLATES)
    blocks = []
    for topic_key, headline, summary, url in picks:
        blocks.append(block_tpl.format(headline=headline, summary=summary, url=url))

    intro = fill(pick(INTROS[ptype]), ctx)
    signoff = fill(pick(SIGNOFFS[ptype]), ctx)
    footer = fill(pick(UNSUB_FOOTERS), ctx)

    body = intro + "\n\n" + "\n\n".join(blocks) + "\n\n" + signoff + footer
    return body


def build_subject(ctx: dict) -> str:
    style = ctx["style"]
    tpl = pick(SUBJECTS[style])
    return fill(tpl, ctx)


# ------------------------------------------------------------------------------------
# Quality gate
# ------------------------------------------------------------------------------------

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
TYPOSQUAT_PATTERNS = [
    "paypa1", "amaz0n", "g00gle", "githu8", "microsft", "lnkedin", "yt0be",
    "faceb00k", "paypai",
]
DIGIT_IN_DOMAIN = re.compile(r"[a-z][0-9][a-z]|[a-z][0-9]{2,}[a-z]")
URGENCY_PHRASES = [
    "click here to verify", "urgent action required", "your access will be suspended",
    "account suspended", "verify your account immediately", "verify immediately",
    "click now or lose access", "confirm your password", "enter your password",
    "reset your password now",
]
BARE_URL_RE = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S+")


def sender_domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def passes_checks(row: dict) -> bool:
    sender = row["sender"]
    subject = row["subject"]
    body = row["body"]
    blob = f"{sender}\n{subject}\n{body}".lower()

    if len(body.strip()) < 10:
        return False

    wc = len(body.split())
    if wc < 150 or wc > 400:
        return False

    for pat in TYPOSQUAT_PATTERNS:
        if pat in blob:
            return False

    if DIGIT_IN_DOMAIN.search(sender_domain(sender)):
        return False

    for sh in URL_SHORTENERS:
        if sh in blob:
            return False

    # No http(s) protocol — spec says bare-domain URLs only
    if "http://" in blob or "https://" in blob:
        return False

    for phrase in URGENCY_PHRASES:
        if phrase in blob:
            return False

    # Unsubscribe footer required
    if "unsubscribe" not in body.lower():
        return False

    # At least two bare-domain URLs (multiple as per spec)
    urls = BARE_URL_RE.findall(body.lower())
    if len(urls) < 2:
        return False

    # Multiple topics/sections — body must have at least 3 newline-separated blocks
    # beyond the intro/signoff. Use a heuristic: count double-newline-separated paragraphs.
    paragraphs = [p for p in body.split("\n\n") if p.strip()]
    if len(paragraphs) < 5:
        return False

    return True


# ------------------------------------------------------------------------------------
# Generate
# ------------------------------------------------------------------------------------

SUBJECT_STYLES = ("numbered", "date", "topic", "personal")


def generate():
    rows: list[dict] = []
    seen: set[str] = set()
    template_use: Counter = Counter()

    for pub_type, target_count in PLAN:
        pub_keys = PUBS_BY_TYPE[pub_type]
        produced = 0
        attempts = 0
        max_attempts = target_count * 120

        while produced < target_count and attempts < max_attempts:
            attempts += 1
            pub_key = pick(pub_keys)
            pub = PUBLICATIONS[pub_key]
            sender = pick(pub["senders"])

            style = pick(SUBJECT_STYLES)
            ctx = build_ctx(pub_key, style)
            subject = build_subject(ctx)
            body = build_body(pub_key, ctx)

            # Enforce 5-use cap on (pub_key, style, subject) pair so the
            # subject surface stays varied.
            key = (pub_key, style, subject)
            if template_use[key] >= 5:
                continue

            row = {
                "sender": sender,
                "subject": subject,
                "body": body,
                "label": 0,
                "category": "newsletters_digests",
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
                f"Only produced {produced}/{target_count} for {pub_type} in {attempts} attempts"
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
