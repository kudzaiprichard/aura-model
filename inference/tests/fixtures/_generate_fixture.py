"""Parity fixture generator.

This script transcribes the training-side formulas VERBATIM from the notebooks
(see NOTEBOOK_CONTRACT.md §1, §2) and emits training_parity.json.

It is deliberately standalone: it does NOT import from inference.* so the
parity test can compare independent implementations.

Run once from the repo root (the directory containing `_datasets/` and
`models/`):
    python inference/tests/fixtures/_generate_fixture.py
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import unicodedata
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


# --- NOTEBOOK_CONTRACT §2.1 — 15 URL patterns (feature notebook cell 5) ---
URL_PATTERNS = [
    r'https?://[^\s<>\"\'\)]+',
    r'ftp://[^\s<>\"\'\)]+',
    r'ftps://[^\s<>\"\'\)]+',
    r'sftp://[^\s<>\"\'\)]+',
    r'www\.[^\s<>\"\'\)]+',
    r'file://[^\s<>\"\'\)]+',
    r'ssh://[^\s<>\"\'\)]+',
    r'telnet://[^\s<>\"\'\)]+',
    r'git://[^\s<>\"\'\)]+',
    r'svn://[^\s<>\"\'\)]+',
    r'mailto:[^\s<>\"\'\)]+',
    r'news:[^\s<>\"\'\)]+',
    r'nntp://[^\s<>\"\'\)]+',
    r'irc://[^\s<>\"\'\)]+',
    r'webcal://[^\s<>\"\'\)]+',
]

ENGINEERED_FEATURE_ORDER = [
    'body_word_count', 'body_exclamation_count', 'email_local_length',
    'name_email_consistency', 'body_url_density', 'body_url_count',
    'body_entropy', 'email_digit_ratio', 'domain_entropy', 'domain_length',
    'subject_entropy', 'body_avg_word_length', 'sender_name_exists',
    'subject_exclamation_count', 'domain_vowel_consonant_ratio',
]


# NOTEBOOK_CONTRACT §2.3 — shared-inbox whitelist. Must match the set used by
# `check_name_email_consistency` in the feature notebook and
# `inference.preprocessing._SHARED_INBOX_LOCALS`.
SHARED_INBOX_LOCALS = frozenset({
    'noreply', 'donotreply', 'mailerdaemon', 'postmaster', 'newsletter',
    'digest', 'notifications', 'notification', 'receipts', 'support',
    'alerts', 'hello', 'contact', 'info', 'team', 'help', 'news', 'updates',
    'billing', 'admin',
})


# --- NOTEBOOK_CONTRACT §2.2 — normalize_text_for_tfidf (cell 11) ---
def normalize_text_for_tfidf(text, url_patterns):
    if pd.isna(text) or text.strip() == '':
        return ''
    combined_url_pattern = '|'.join(url_patterns)
    text = re.sub(combined_url_pattern, '', text)
    text = re.sub(r'[!?]+', '', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


# --- NOTEBOOK_CONTRACT §2.3 — engineered feature formulas (cell 5) ---
def extract_sender_components(sender):
    if pd.isna(sender) or sender.strip() == '':
        return None, None, None
    sender = sender.strip()
    pattern = r'(.+?)\s*<(.+?)>'
    match = re.search(pattern, sender)
    if match:
        sender_name = match.group(1).strip()
        sender_email = match.group(2).strip()
    else:
        sender_name = None
        sender_email = sender.strip()
    if sender_email:
        sender_email = sender_email.replace('<', '').replace('>', '').strip()
    if sender_email and '@' in sender_email:
        sender_domain = sender_email.split('@')[-1].strip()
    else:
        sender_domain = None
    return sender_name, sender_email, sender_domain


def calculate_entropy(text):
    if not text or len(text) == 0:
        return 0
    freq = {}
    for char in text.lower():
        if char != ' ':
            freq[char] = freq.get(char, 0) + 1
    entropy = 0
    text_len = len([c for c in text if c != ' '])
    if text_len == 0:
        return 0
    for count in freq.values():
        probability = count / text_len
        entropy -= probability * math.log2(probability)
    return entropy


def get_email_local_length(email):
    if email is None or pd.isna(email) or email.strip() == '':
        return 0
    if '@' in email:
        return len(email.split('@')[0])
    return 0


def get_email_digit_ratio(email):
    if email is None or pd.isna(email) or email.strip() == '':
        return 0
    local_part = email.split('@')[0] if '@' in email else email
    if len(local_part) == 0:
        return 0
    digit_count = sum(c.isdigit() for c in local_part)
    return digit_count / len(local_part)


def get_domain_entropy(domain):
    if domain is None or pd.isna(domain) or domain.strip() == '':
        return 0
    parts = domain.split('.')
    if len(parts) >= 2:
        main_domain = '.'.join(parts[:-1])
    else:
        main_domain = domain
    return calculate_entropy(main_domain.lower())


def get_vowel_consonant_ratio(domain):
    if domain is None or pd.isna(domain) or domain.strip() == '':
        return 0
    domain_clean = re.sub(r'[^a-zA-Z]', '', domain.lower())
    if len(domain_clean) == 0:
        return 0
    vowels = sum(1 for c in domain_clean if c in 'aeiou')
    consonants = sum(1 for c in domain_clean if c in 'bcdfghjklmnpqrstvwxyz')
    if consonants == 0:
        return 0
    return vowels / consonants


def check_name_email_consistency(name, email):
    if name is None or email is None or pd.isna(name) or pd.isna(email):
        return 0
    name_clean = re.sub(r'[^a-zA-Z]', '', name.lower())
    email_local = email.split('@')[0] if '@' in email else email
    email_clean = re.sub(r'[^a-zA-Z]', '', email_local.lower())
    if len(name_clean) == 0 or len(email_clean) == 0:
        return 0
    # Shared-inbox local parts (noreply/support/newsletter/...) are role
    # accounts; the display-name mismatch is not a phishing signal.
    if email_clean in SHARED_INBOX_LOCALS:
        return 1
    name_parts = name_clean.split()
    for part in name_parts:
        if len(part) > 2 and part in email_clean:
            return 1
    if len(name_clean) >= 3:
        for i in range(len(name_clean) - 2):
            substring = name_clean[i:i + 3]
            if substring in email_clean:
                return 1
    return 0


def count_urls(text, url_patterns):
    if pd.isna(text) or text.strip() == '':
        return 0
    total = 0
    for p in url_patterns:
        total += len(re.findall(p, text))
    return total


def get_avg_word_length(text):
    if pd.isna(text) or text.strip() == '':
        return 0
    words = text.split()
    if len(words) == 0:
        return 0
    return sum(len(w) for w in words) / len(words)


def compute_engineered_features(sender, subject, body):
    """Produce exactly the 15 features in ENGINEERED_FEATURE_ORDER."""
    subject = '' if pd.isna(subject) else subject
    body = '' if pd.isna(body) else body

    name, email, domain = extract_sender_components(sender)

    body_word_count = int(len(body.split())) if isinstance(body, str) else 0
    body_exclamation_count = int(body.count('!')) if isinstance(body, str) else 0
    email_local_length = get_email_local_length(email)
    name_email_consistency = check_name_email_consistency(name, email)
    body_url_count = count_urls(body, URL_PATTERNS)
    if body_word_count == 0:
        body_url_density = 0.0
    else:
        body_url_density = (body_url_count / body_word_count) * 100
    body_entropy = calculate_entropy(body)
    email_digit_ratio = get_email_digit_ratio(email)
    domain_entropy = get_domain_entropy(domain)
    domain_length = 0 if domain is None else len(domain)
    subject_entropy = calculate_entropy(subject)
    body_avg_word_length = get_avg_word_length(body)
    sender_name_exists = 1 if name is not None else 0
    subject_exclamation_count = int(subject.count('!')) if isinstance(subject, str) else 0
    domain_vowel_consonant_ratio = get_vowel_consonant_ratio(domain)

    return {
        'body_word_count': float(body_word_count),
        'body_exclamation_count': float(body_exclamation_count),
        'email_local_length': float(email_local_length),
        'name_email_consistency': float(name_email_consistency),
        'body_url_density': float(body_url_density),
        'body_url_count': float(body_url_count),
        'body_entropy': float(body_entropy),
        'email_digit_ratio': float(email_digit_ratio),
        'domain_entropy': float(domain_entropy),
        'domain_length': float(domain_length),
        'subject_entropy': float(subject_entropy),
        'body_avg_word_length': float(body_avg_word_length),
        'sender_name_exists': float(sender_name_exists),
        'subject_exclamation_count': float(subject_exclamation_count),
        'domain_vowel_consonant_ratio': float(domain_vowel_consonant_ratio),
    }


# --------------------------------------------------------------------------
# Sampling and output
# --------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    try:
        out = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=Path(__file__).resolve().parent,
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return 'unknown'


def _pick_rows(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Pick 20 rows stratified by label with required diversity."""
    criteria = []

    def add(mask, note):
        idx = df.index[mask]
        if len(idx) == 0:
            return
        criteria.append((note, int(rng.choice(idx))))

    body = df['body'].fillna('').astype(str)
    subject = df['subject'].fillna('').astype(str)
    sender = df['sender'].fillna('').astype(str)

    has_url = body.str.contains(r'https?://|www\.', regex=True, na=False)
    add(has_url & (df['label'] == 1), 'url_phish')
    add(has_url & (df['label'] == 0), 'url_legit')

    short_body = body.str.split().str.len() < 50
    add(short_body & (df['label'] == 0), 'short_legit')
    add(short_body & (df['label'] == 1), 'short_phish')

    long_body = body.str.split().str.len() > 200
    add(long_body & (df['label'] == 0), 'long_legit')
    add(long_body & (df['label'] == 1), 'long_phish')

    missing_name = ~sender.str.contains('<', na=False)
    add(missing_name & (df['label'] == 0), 'no_name_legit')
    add(missing_name & (df['label'] == 1), 'no_name_phish')

    has_html_residue = body.str.contains(r'<[a-zA-Z]', regex=True, na=False)
    add(has_html_residue & (df['label'] == 1), 'html_residue_phish')

    high_punct = subject.str.count('!') >= 2
    add(high_punct & (df['label'] == 1), 'high_punct_phish')

    seen = {idx for _, idx in criteria}
    for lbl in (0, 1):
        pool = df.index[df['label'] == lbl].difference(list(seen)).tolist()
        k = 10 - sum(1 for _, idx in criteria if df.loc[idx, 'label'] == lbl)
        k = max(0, k)
        for pick in rng.choice(pool, size=min(k, len(pool)), replace=False):
            criteria.append(('fill', int(pick)))
            seen.add(int(pick))

    while len(criteria) > 20:
        criteria.pop()
    ordered_indices = [idx for _, idx in criteria]
    return df.loc[ordered_indices].copy()


def main():
    repo_root = Path(__file__).resolve().parents[3]
    cleaned_csv = repo_root / '_datasets' / 'processed' / 'cleaned_email_dataset.csv'
    subject_vec_path = repo_root / 'models' / 'pipeline_components' / 'subject_vectorizer.pkl'
    body_vec_path = repo_root / 'models' / 'pipeline_components' / 'body_vectorizer.pkl'
    out_path = Path(__file__).with_name('training_parity.json')

    df = pd.read_csv(cleaned_csv, usecols=['sender', 'subject', 'body', 'label'])
    df = df.dropna(subset=['label']).reset_index(drop=True)
    df['label'] = df['label'].astype(int)

    rng = np.random.default_rng(20260415)
    sample = _pick_rows(df, rng)

    subject_vec = joblib.load(subject_vec_path)
    body_vec = joblib.load(body_vec_path)

    records = []
    for i, (_, row) in enumerate(sample.iterrows()):
        sender = '' if pd.isna(row['sender']) else str(row['sender'])
        subject = '' if pd.isna(row['subject']) else str(row['subject'])
        body = '' if pd.isna(row['body']) else str(row['body'])

        norm_subject = normalize_text_for_tfidf(subject, URL_PATTERNS)
        norm_body = normalize_text_for_tfidf(body, URL_PATTERNS)

        engineered = compute_engineered_features(sender, subject, body)

        subj_tfidf = subject_vec.transform([norm_subject])
        body_tfidf = body_vec.transform([norm_body])

        subj_nonzero = [[int(idx), float(val)]
                        for idx, val in zip(subj_tfidf.indices, subj_tfidf.data)]
        body_nonzero = [[int(idx), float(val)]
                        for idx, val in zip(body_tfidf.indices, body_tfidf.data)]

        records.append({
            'id': i,
            'label': int(row['label']),
            'sender': sender,
            'subject': subject,
            'body': body,
            'normalized': {'subject': norm_subject, 'body': norm_body},
            'engineered_features': engineered,
            'subject_tfidf_nonzero': subj_nonzero,
            'body_tfidf_nonzero': body_nonzero,
        })

    fixture = {
        'metadata': {
            'engineered_feature_order': ENGINEERED_FEATURE_ORDER,
            'subject_tfidf_dim': 2000,
            'body_tfidf_dim': 5000,
            'total_features': 7015,
            'vectorizer_fingerprint': {
                'subject': _sha256(subject_vec_path),
                'body': _sha256(body_vec_path),
            },
            'notebook_commit': _git_head(),
            'source_dataset': str(cleaned_csv.relative_to(repo_root)).replace('\\', '/'),
        },
        'records': records,
    }

    out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Wrote {out_path} with {len(records)} records')


if __name__ == '__main__':
    main()
