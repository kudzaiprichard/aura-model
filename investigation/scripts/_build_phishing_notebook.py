"""One-shot builder for investigation/phishing_investigation.ipynb.

Running this script writes the notebook to disk. The notebook itself is
the deliverable; this builder exists only to keep large JSON literals out
of the Git diff when we need to regenerate it.
"""

from __future__ import annotations

import json
from pathlib import Path


def md(src: str) -> dict:
    return {
        'cell_type': 'markdown',
        'metadata': {},
        'source': src.splitlines(keepends=True),
    }


def code(src: str) -> dict:
    return {
        'cell_type': 'code',
        'metadata': {},
        'execution_count': None,
        'outputs': [],
        'source': src.splitlines(keepends=True),
    }


CELLS: list[dict] = []


# ============================================================================
# Title + overview
# ============================================================================
CELLS.append(md(
    "# AURA — Phishing Stress Investigation\n"
    "\n"
    "This notebook drives `v1_0` through a **targeted adversarial phishing set** —\n"
    "1600 synthetic emails built from the weakness report in\n"
    "[`00_weakness_report.md`](00_weakness_report.md). Every email in the set applies\n"
    "one or more of the exploit rules **R1–R8** from §6 of that report, which encode\n"
    "the feature/vocabulary blind spots we identified in the training-time model.\n"
    "\n"
    "**Sections**\n"
    "\n"
    "1. Setup — load `v1_0`, the stress CSV, and utility helpers\n"
    "2. Bulk prediction — score the full 1600-row set\n"
    "3. Per-category failure analysis — which lure patterns slip past\n"
    "4. Exploit-rule effectiveness — which rule combinations buy the attacker\n"
    "   the most bypass leverage\n"
    "5. Feature analysis on failures — how the 15 engineered features look on\n"
    "   missed phish vs. the baseline training distribution\n"
    "6. Demo batch selection — pull 10 representative failures per worst category\n"
    "   into `phishing_demo_batch.csv` for the defence demo\n"
    "7. Online-learning demo — fine-tune the failures back into the model and\n"
    "   show before/after recall\n"
))

# ============================================================================
# Section 1 — Setup
# ============================================================================
CELLS.append(md("## 1. Setup"))

CELLS.append(code(
    "import logging\n"
    "import os\n"
    "import sys\n"
    "import warnings\n"
    "from pathlib import Path\n"
    "\n"
    "import matplotlib.pyplot as plt\n"
    "import numpy as np\n"
    "import pandas as pd\n"
    "import seaborn as sns\n"
    "\n"
    "warnings.filterwarnings('ignore')\n"
    "logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(name)s: %(message)s')\n"
    "\n"
    "# Walk up until we find the `inference` package.\n"
    "repo_root = Path.cwd()\n"
    "for _ in range(4):\n"
    "    if (repo_root / 'inference' / '__init__.py').exists():\n"
    "        break\n"
    "    repo_root = repo_root.parent\n"
    "if str(repo_root) not in sys.path:\n"
    "    sys.path.insert(0, str(repo_root))\n"
    "os.environ.setdefault('AURA_MODELS_DIR', str((repo_root / 'models').resolve()))\n"
    "\n"
    "from inference import ModelRegistry, OnlineLearner, PhishingDetector, ValidationError\n"
    "from inference.schema import ENGINEERED_FEATURE_ORDER\n"
    "\n"
    "pd.set_option('display.max_colwidth', 80)\n"
    "pd.set_option('display.width', 200)\n"
    "sns.set_theme(style='whitegrid')\n"
    "\n"
    "BASELINE_VERSION = 'v1_0'\n"
    "THRESHOLD = 0.5\n"
    "registry = ModelRegistry(os.environ['AURA_MODELS_DIR'])\n"
    "detector_v1 = PhishingDetector.load(BASELINE_VERSION)\n"
    "print('loaded detector:', detector_v1.version, '- threshold =', THRESHOLD)\n"
))

CELLS.append(code(
    "stress_csv = repo_root / 'investigation' / '_datasets' / 'phishing_stress.csv'\n"
    "stress = pd.read_csv(stress_csv)\n"
    "print('stress rows :', len(stress))\n"
    "print('categories  :', sorted(stress['category'].unique()))\n"
    "print('tones       :', sorted(stress['tone_profile'].unique()))\n"
    "print('length mix  :', stress['length_bucket'].value_counts().to_dict())\n"
    "stress.head(3)\n"
))

# ============================================================================
# Section 2 — Bulk prediction
# ============================================================================
CELLS.append(md(
    "## 2. Bulk prediction\n"
    "\n"
    "Score the full set on `v1_0`. We collect both the hard label and the\n"
    "phishing probability because the stress set was built to also probe the\n"
    "REVIEW band (§5 of the weakness report) — raw probability matters as much\n"
    "as the binary verdict.\n"
))

CELLS.append(code(
    "emails = [\n"
    "    {'sender': r['sender'], 'subject': r['subject'], 'body': r['body']}\n"
    "    for _, r in stress.iterrows()\n"
    "]\n"
    "results = detector_v1.predict_batch(emails, threshold=THRESHOLD)\n"
    "\n"
    "scored = stress.copy()\n"
    "scored['pred']   = [r.predicted_label for r in results]\n"
    "scored['prob']   = [r.phishing_probability for r in results]\n"
    "scored['missed'] = (scored['pred'] == 0)  # true label is 1 for every row\n"
    "\n"
    "overall_recall = (scored['pred'] == 1).mean()\n"
    "fn_rate        = scored['missed'].mean()\n"
    "print(f'overall recall on stress set : {overall_recall:.4f}')\n"
    "print(f'false-negative rate          : {fn_rate:.4f}  ({scored[\"missed\"].sum()} / {len(scored)})')\n"
    "print(f'mean phishing probability    : {scored[\"prob\"].mean():.4f}')\n"
))

# ============================================================================
# Section 3 — Per-category failure analysis
# ============================================================================
CELLS.append(md(
    "## 3. Per-category failure analysis\n"
    "\n"
    "Which of the 8 adversarial categories causes the most damage?\n"
))

CELLS.append(code(
    "by_cat = scored.groupby('category').agg(\n"
    "    n=('category', 'size'),\n"
    "    missed=('missed', 'sum'),\n"
    "    fn_rate=('missed', 'mean'),\n"
    "    mean_prob=('prob', 'mean'),\n"
    "    p10_prob=('prob', lambda s: float(np.percentile(s, 10))),\n"
    ").sort_values('fn_rate', ascending=False).round(4)\n"
    "by_cat\n"
))

CELLS.append(code(
    "fig, ax = plt.subplots(figsize=(10, 5))\n"
    "ordered = by_cat.sort_values('fn_rate', ascending=True)\n"
    "colors = ['#c0392b' if v >= 0.30 else ('#e67e22' if v >= 0.15 else '#27ae60') for v in ordered['fn_rate']]\n"
    "ax.barh(ordered.index, ordered['fn_rate'], color=colors)\n"
    "ax.set_xlabel('False-negative rate (label=1 predicted as 0)')\n"
    "ax.set_title(f'v1_0 FN rate by adversarial category @ threshold={THRESHOLD}')\n"
    "ax.axvline(0.05, color='grey', linestyle='--', alpha=0.6, label='5% target')\n"
    "for i, v in enumerate(ordered['fn_rate']):\n"
    "    ax.text(v + 0.005, i, f'{v:.0%}', va='center', fontsize=9)\n"
    "ax.legend(loc='lower right')\n"
    "plt.tight_layout()\n"
    "plt.show()\n"
))

CELLS.append(md(
    "### Category × tone heatmap\n"
    "\n"
    "Breaks each category down by the four tone profiles so we can spot which\n"
    "stylistic register buys the attacker the most leverage inside a category.\n"
))

CELLS.append(code(
    "pivot = scored.pivot_table(\n"
    "    index='category', columns='tone_profile', values='missed', aggfunc='mean'\n"
    ").round(3)\n"
    "pivot = pivot.loc[by_cat.index]  # order by overall worst first\n"
    "\n"
    "fig, ax = plt.subplots(figsize=(9, 5))\n"
    "sns.heatmap(pivot, annot=True, fmt='.2f', cmap='Reds', vmin=0, vmax=1,\n"
    "            cbar_kws={'label': 'FN rate'}, ax=ax)\n"
    "ax.set_title('FN rate: category × tone profile')\n"
    "plt.tight_layout()\n"
    "plt.show()\n"
    "pivot\n"
))

CELLS.append(md(
    "### Length-bucket effect\n"
    "\n"
    "A quick look at whether short vs long bodies alter the FN rate per category —\n"
    "the TF-IDF features are bag-of-words, so longer bodies introduce more\n"
    "benign tokens which can dilute the phishing signal.\n"
))

CELLS.append(code(
    "length_pivot = scored.pivot_table(\n"
    "    index='category', columns='length_bucket', values='missed', aggfunc='mean'\n"
    ")[['short', 'medium', 'long']].round(3)\n"
    "length_pivot = length_pivot.loc[by_cat.index]\n"
    "length_pivot\n"
))

# ============================================================================
# Section 4 — Exploit-rule effectiveness
# ============================================================================
CELLS.append(md(
    "## 4. Exploit-rule effectiveness\n"
    "\n"
    "`exploit_rules_applied` on each row lists the hard-rule tags (R1…R8) that\n"
    "the generator actually satisfied for that email. We one-hot that column and\n"
    "check the FN rate conditional on each rule being applied vs. not — this\n"
    "isolates the contribution of individual rules to the bypass rate.\n"
    "\n"
    "Rules reference:\n"
    "\n"
    "- **R1** — strip `!` / `?`\n"
    "- **R2** — ≤1 URL\n"
    "- **R3** — sender local part is a shared-inbox token (triggers `name_email_consistency=1`)\n"
    "- **R4** — fake domain is pronounceable 10–15 chars\n"
    "- **R5** — body length 150–400 words\n"
    "- **R6** — modern OOV vocabulary (docusign, okta, mfa, …)\n"
    "- **R7** — no `!` in subject\n"
    "- **R8** — zero digits in sender local part\n"
))

CELLS.append(code(
    "RULES = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8']\n"
    "\n"
    "rule_flags = scored.copy()\n"
    "for r in RULES:\n"
    "    rule_flags[r] = rule_flags['exploit_rules_applied'].fillna('').str.contains(rf'\\b{r}\\b', regex=True)\n"
    "\n"
    "rule_stats = []\n"
    "for r in RULES:\n"
    "    with_r  = rule_flags[rule_flags[r]]\n"
    "    wo_r    = rule_flags[~rule_flags[r]]\n"
    "    rule_stats.append({\n"
    "        'rule'        : r,\n"
    "        'n_applied'   : len(with_r),\n"
    "        'fn_applied'  : round(with_r['missed'].mean(), 4) if len(with_r) else float('nan'),\n"
    "        'fn_absent'   : round(wo_r['missed'].mean(), 4)   if len(wo_r) else float('nan'),\n"
    "        'delta'       : round((with_r['missed'].mean() if len(with_r) else 0)\n"
    "                              - (wo_r['missed'].mean() if len(wo_r) else 0), 4),\n"
    "    })\n"
    "rule_df = pd.DataFrame(rule_stats).sort_values('fn_applied', ascending=False)\n"
    "rule_df\n"
))

CELLS.append(md(
    "### Compounding effect — how many rules stack on each missed email\n"
    "\n"
    "The attacker's real goal isn't any single rule — it's stacking them.\n"
    "Grouping the FN rate by the count of rules applied lets us see whether\n"
    "'more of the recipe' really does buy more bypass.\n"
))

CELLS.append(code(
    "rule_flags['n_rules'] = rule_flags[RULES].sum(axis=1)\n"
    "stacked = rule_flags.groupby('n_rules').agg(\n"
    "    n=('missed', 'size'),\n"
    "    fn_rate=('missed', 'mean'),\n"
    "    mean_prob=('prob', 'mean'),\n"
    ").round(4)\n"
    "stacked\n"
))

CELLS.append(code(
    "fig, ax = plt.subplots(figsize=(8, 4))\n"
    "ax.plot(stacked.index, stacked['fn_rate'], marker='o', color='#c0392b', label='FN rate')\n"
    "ax.set_xlabel('Number of exploit rules applied')\n"
    "ax.set_ylabel('FN rate', color='#c0392b')\n"
    "ax.tick_params(axis='y', labelcolor='#c0392b')\n"
    "ax2 = ax.twinx()\n"
    "ax2.plot(stacked.index, stacked['mean_prob'], marker='s', color='#2c3e50', alpha=0.7, label='mean p(phish)')\n"
    "ax2.set_ylabel('mean phishing probability', color='#2c3e50')\n"
    "ax2.tick_params(axis='y', labelcolor='#2c3e50')\n"
    "ax.set_title('Rule stacking drives down both the verdict and the probability')\n"
    "plt.tight_layout()\n"
    "plt.show()\n"
))

# ============================================================================
# Section 5 — Feature analysis on failures
# ============================================================================
CELLS.append(md(
    "## 5. Engineered-feature analysis on missed phishing\n"
    "\n"
    "The weakness report called out the 15 engineered features as the part of\n"
    "the model most exposed to these lures. We pull the engineered-feature\n"
    "dictionary from each prediction and compare the distribution on **missed**\n"
    "vs. **caught** phishing — where the model saw the same signal on both and\n"
    "decided differently, that's where the attacker is working.\n"
))

CELLS.append(code(
    "feat_rows = []\n"
    "for r, res in zip(scored.to_dict('records'), results):\n"
    "    row = dict(res.engineered_features)\n"
    "    row['missed'] = r['missed']\n"
    "    row['category'] = r['category']\n"
    "    row['prob'] = res.phishing_probability\n"
    "    feat_rows.append(row)\n"
    "feat_df = pd.DataFrame(feat_rows)\n"
    "\n"
    "missed = feat_df[feat_df['missed']]\n"
    "caught = feat_df[~feat_df['missed']]\n"
    "print(f'missed = {len(missed)}   caught = {len(caught)}')\n"
))

CELLS.append(code(
    "summary = pd.DataFrame({\n"
    "    'missed_mean': missed[list(ENGINEERED_FEATURE_ORDER)].mean().round(4),\n"
    "    'caught_mean': caught[list(ENGINEERED_FEATURE_ORDER)].mean().round(4),\n"
    "})\n"
    "summary['delta'] = (summary['missed_mean'] - summary['caught_mean']).round(4)\n"
    "summary['abs_delta'] = summary['delta'].abs()\n"
    "summary = summary.sort_values('abs_delta', ascending=False)\n"
    "summary[['missed_mean', 'caught_mean', 'delta']]\n"
))

CELLS.append(code(
    "top_feats = summary.head(6).index.tolist()\n"
    "feat_df['outcome'] = np.where(feat_df['missed'], 'missed', 'caught')\n"
    "melt = feat_df[top_feats + ['outcome']].melt(id_vars='outcome', var_name='feature', value_name='value')\n"
    "\n"
    "fig, axes = plt.subplots(2, 3, figsize=(13, 7))\n"
    "for ax, feat in zip(axes.ravel(), top_feats):\n"
    "    sub = melt[melt['feature'] == feat]\n"
    "    sns.violinplot(\n"
    "        data=sub, x='outcome', y='value', ax=ax, cut=0, inner='quartile',\n"
    "        hue='outcome', order=['caught', 'missed'],\n"
    "        palette={'caught': '#27ae60', 'missed': '#c0392b'},\n"
    "        legend=False,\n"
    "    )\n"
    "    ax.set_title(feat)\n"
    "    ax.set_xlabel('outcome')\n"
    "plt.suptitle('Top-6 engineered features — missed vs. caught phishing', y=1.02)\n"
    "plt.tight_layout()\n"
    "plt.show()\n"
))

CELLS.append(md(
    "### Reading this\n"
    "\n"
    "Features with a large `|delta|` between the missed and caught sets are the\n"
    "ones the attacker most successfully flattened. Low `body_exclamation_count`\n"
    "and `subject_exclamation_count` (engineered into the model as punctuation\n"
    "signals) are typical suspects — R1 / R7 in the exploit recipe strip those\n"
    "by construction.\n"
))

# ============================================================================
# Section 6 — Demo batch selection
# ============================================================================
CELLS.append(md(
    "## 6. Demo-batch selection\n"
    "\n"
    "Pull 10 failing examples from each of the **worst four categories** —\n"
    "the ones the defence demo needs to showcase. We bias the sample toward\n"
    "low-confidence misses so the audience sees the model's uncertainty, not\n"
    "edge cases.\n"
))

CELLS.append(code(
    "WORST_N = 4\n"
    "PER_CAT = 10\n"
    "\n"
    "worst_cats = by_cat.head(WORST_N).index.tolist()\n"
    "print('worst categories:', worst_cats)\n"
    "\n"
    "failures = scored[scored['missed']].copy()\n"
    "demo_rows = []\n"
    "rng_demo = np.random.default_rng(20260421)\n"
    "for cat in worst_cats:\n"
    "    pool = failures[failures['category'] == cat].sort_values('prob')  # lowest p(phish) = most confidently missed\n"
    "    if len(pool) >= PER_CAT:\n"
    "        # mix of most-confident misses (first 6) + random draw (next 4)\n"
    "        top = pool.head(6)\n"
    "        rest = pool.iloc[6:].sample(n=min(PER_CAT - 6, len(pool) - 6),\n"
    "                                    random_state=int(rng_demo.integers(0, 1_000_000)))\n"
    "        demo_rows.append(pd.concat([top, rest]))\n"
    "    else:\n"
    "        demo_rows.append(pool)\n"
    "\n"
    "demo_batch = pd.concat(demo_rows, ignore_index=True)\n"
    "demo_cols = ['sender', 'subject', 'body', 'label', 'category', 'tone_profile',\n"
    "             'length_bucket', 'exploit_rules_applied', 'prob', 'pred']\n"
    "demo_batch = demo_batch[demo_cols]\n"
    "print('demo batch size:', len(demo_batch))\n"
    "\n"
    "demo_path = repo_root / 'investigation' / '_datasets' / 'phishing_demo_batch.csv'\n"
    "demo_batch.to_csv(demo_path, index=False)\n"
    "print('wrote', demo_path.relative_to(repo_root))\n"
    "demo_batch.head()\n"
))

# ============================================================================
# Section 7 — Online learning demo
# ============================================================================
CELLS.append(md(
    "## 7. Online-learning demo\n"
    "\n"
    "Feed the demo batch back to the model via `OnlineLearner.partial_fit_batch`\n"
    "and show the before/after recall on the **held-out rest of the stress set**.\n"
    "The holdout is strictly disjoint from the training batch so the numbers are\n"
    "honest.\n"
    "\n"
    "This section writes a new registry version (e.g. `v1_1`), so running the\n"
    "cell twice will create `v1_2`, etc. A cleanup cell at the end rolls\n"
    "`active_version` back to `v1_0`.\n"
))

CELLS.append(code(
    "# Build a class-balanced fine-tune batch: the phishing demos from section 6\n"
    "# plus a matched draw of legitimate emails from the legit stress set. The\n"
    "# OnlineLearner refuses a single-class batch (partial_fit would collapse\n"
    "# the decision boundary), so pairing label=1 with label=0 is required.\n"
    "legit_csv = repo_root / 'investigation' / '_datasets' / 'legitimate_stress.csv'\n"
    "legit_stress = pd.read_csv(legit_csv)\n"
    "legit_balance = legit_stress.sample(n=len(demo_batch), random_state=20260421)\n"
    "\n"
    "train_rows = [\n"
    "    {'sender': r.sender, 'subject': r.subject, 'body': r.body, 'label': int(r.label)}\n"
    "    for r in demo_batch.itertuples()\n"
    "] + [\n"
    "    {'sender': r['sender'], 'subject': r['subject'], 'body': r['body'], 'label': int(r['label'])}\n"
    "    for _, r in legit_balance.iterrows()\n"
    "]\n"
    "\n"
    "# Holdout = rest of the phishing stress set (disjoint from the demo batch)\n"
    "# + the rest of the legitimate stress set (disjoint from the balance draw).\n"
    "train_keys = set(zip(demo_batch['sender'], demo_batch['subject']))\n"
    "holdout_phish = scored[~scored.set_index(['sender', 'subject']).index.isin(train_keys)].copy()\n"
    "legit_holdout = legit_stress.drop(index=legit_balance.index)\n"
    "\n"
    "holdout_df = pd.DataFrame({\n"
    "    'sender':  holdout_phish['sender'].tolist()  + legit_holdout['sender'].tolist(),\n"
    "    'subject': holdout_phish['subject'].tolist() + legit_holdout['subject'].tolist(),\n"
    "    'body':    holdout_phish['body'].tolist()    + legit_holdout['body'].tolist(),\n"
    "})\n"
    "holdout_y = np.concatenate([\n"
    "    holdout_phish['label'].astype(np.int64).to_numpy(),\n"
    "    legit_holdout['label'].astype(np.int64).to_numpy(),\n"
    "])\n"
    "print('train rows  :', len(train_rows), '  (phish + legit balance)')\n"
    "print('  class 1   :', sum(r['label'] == 1 for r in train_rows))\n"
    "print('  class 0   :', sum(r['label'] == 0 for r in train_rows))\n"
    "print('holdout rows:', len(holdout_df))\n"
))

CELLS.append(code(
    "learner = OnlineLearner(registry, holdout_set=(holdout_df, holdout_y))\n"
    "online_result = None\n"
    "try:\n"
    "    online_result = learner.partial_fit_batch(\n"
    "        train_rows,\n"
    "        source_version=BASELINE_VERSION,\n"
    "        max_iter_per_call=15,\n"
    "    )\n"
    "    print('new_version       :', online_result.new_version)\n"
    "    print('batch_size        :', online_result.batch_size)\n"
    "    print('iterations        :', online_result.iterations)\n"
    "    print('oov rate (subject):', round(online_result.oov_rate_subject, 4))\n"
    "    print('oov rate (body)   :', round(online_result.oov_rate_body, 4))\n"
    "    print('before metrics    :', {k: round(v, 4) for k, v in online_result.performance_before.items()})\n"
    "    print('after  metrics    :', {k: round(v, 4) for k, v in online_result.performance_after.items()})\n"
    "except (ValidationError, ValueError) as e:\n"
    "    print('online learning failed:', e)\n"
))

CELLS.append(code(
    "promoted_version = None\n"
    "if online_result is not None:\n"
    "    try:\n"
    "        learner.promote(online_result.new_version, min_delta_f1=-0.05)\n"
    "        promoted_version = online_result.new_version\n"
    "        print('promoted      :', promoted_version)\n"
    "        print('active_version:', registry.active_version())\n"
    "    except ValidationError as e:\n"
    "        print('promotion refused:', e)\n"
))

CELLS.append(md(
    "### Re-score the **full stress set** on the new version\n"
    "\n"
    "Same dataset as section 2, new model. The delta tells us how much of the\n"
    "blind spot a single short fine-tune run can close.\n"
))

CELLS.append(code(
    "if promoted_version is None:\n"
    "    print('no promoted version — skipping after-scoring')\n"
    "    after = None\n"
    "else:\n"
    "    detector_v2 = PhishingDetector.load(promoted_version)\n"
    "    after_results = detector_v2.predict_batch(emails, threshold=THRESHOLD)\n"
    "    after = scored[['sender', 'subject', 'category', 'tone_profile',\n"
    "                    'length_bucket', 'exploit_rules_applied', 'label',\n"
    "                    'pred', 'prob']].copy().rename(\n"
    "        columns={'pred': 'pred_before', 'prob': 'prob_before'})\n"
    "    after['pred_after'] = [r.predicted_label for r in after_results]\n"
    "    after['prob_after'] = [r.phishing_probability for r in after_results]\n"
    "    after['was_missed']   = (after['pred_before'] == 0)\n"
    "    after['now_caught']   = (after['pred_before'] == 0) & (after['pred_after'] == 1)\n"
    "    after['now_missed']   = (after['pred_before'] == 1) & (after['pred_after'] == 0)\n"
    "\n"
    "    print(f'before recall : {(after[\"pred_before\"] == 1).mean():.4f}')\n"
    "    print(f'after  recall : {(after[\"pred_after\"] == 1).mean():.4f}')\n"
    "    print(f'newly caught  : {after[\"now_caught\"].sum()}')\n"
    "    print(f'newly missed  : {after[\"now_missed\"].sum()} (regression if >0)')\n"
))

CELLS.append(code(
    "if promoted_version is not None:\n"
    "    delta = after.groupby('category').agg(\n"
    "        n=('label', 'size'),\n"
    "        recall_before=('pred_before', 'mean'),\n"
    "        recall_after=('pred_after', 'mean'),\n"
    "    ).round(4)\n"
    "    delta['delta'] = (delta['recall_after'] - delta['recall_before']).round(4)\n"
    "    delta = delta.sort_values('delta', ascending=False)\n"
    "    display(delta)\n"
    "\n"
    "    fig, ax = plt.subplots(figsize=(10, 5))\n"
    "    x = np.arange(len(delta))\n"
    "    w = 0.38\n"
    "    ax.bar(x - w/2, delta['recall_before'], width=w, label='v1_0', color='#7f8c8d')\n"
    "    ax.bar(x + w/2, delta['recall_after'],  width=w, label=promoted_version, color='#2980b9')\n"
    "    ax.set_xticks(x)\n"
    "    ax.set_xticklabels(delta.index, rotation=30, ha='right')\n"
    "    ax.set_ylabel('recall on phishing stress set')\n"
    "    ax.set_title(f'Per-category recall: {BASELINE_VERSION} vs. {promoted_version}')\n"
    "    ax.legend()\n"
    "    ax.axhline(1.0, color='grey', linestyle=':', alpha=0.5)\n"
    "    plt.tight_layout()\n"
    "    plt.show()\n"
))

CELLS.append(md(
    "### Clean up — roll the active pointer back to `v1_0`\n"
    "\n"
    "The new `v1_1` directory stays on disk (useful for inspection), but the\n"
    "registry's `active_version` points back at the baseline so subsequent\n"
    "notebook runs and production callers see a consistent model.\n"
))

CELLS.append(code(
    "try:\n"
    "    registry.set_active(BASELINE_VERSION)\n"
    "    print('active_version :', registry.active_version())\n"
    "    print('all versions   :', registry.list_versions())\n"
    "except (ValueError, ValidationError) as e:\n"
    "    print('rollback failed:', e)\n"
))


# ============================================================================
# Assemble + write
# ============================================================================
notebook = {
    'cells': CELLS,
    'metadata': {
        'kernelspec': {
            'display_name': 'Python 3',
            'language': 'python',
            'name': 'python3',
        },
        'language_info': {'name': 'python', 'version': '3.x'},
    },
    'nbformat': 4,
    'nbformat_minor': 5,
}

out = Path(__file__).resolve().parents[1] / 'phishing_investigation.ipynb'
out.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding='utf-8')
print(f'wrote {out} ({len(CELLS)} cells)')
