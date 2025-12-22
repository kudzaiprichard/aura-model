import pandas as pd
import numpy as np
import re
import math
import joblib
from scipy.sparse import hstack

class EmailFeatureExtractor:
    """
    Production-ready feature extraction pipeline for phishing detection.
    Extracts 15 selected engineered features + TF-IDF features from cleaned email.

    SELECTED FEATURES (from statistical analysis):
    1. body_word_count
    2. body_exclamation_count
    3. email_local_length
    4. name_email_consistency
    5. body_url_density
    6. body_url_count
    7. body_entropy
    8. email_digit_ratio
    9. domain_entropy
    10. domain_length
    11. subject_entropy
    12. body_avg_word_length
    13. sender_name_exists
    14. subject_exclamation_count
    15. domain_vowel_consonant_ratio
    """

    def __init__(self, subject_vectorizer_path, body_vectorizer_path, verbose=False):
        """
        Initialize feature extractor with pre-trained components.

        Args:
            subject_vectorizer_path (str): Path to subject_vectorizer.pkl
            body_vectorizer_path (str): Path to body_vectorizer.pkl
            verbose (bool): If True, enables detailed logging. If False, minimal logging.
        """
        self.verbose = verbose

        if self.verbose:
            print("[EmailFeatureExtractor] Initializing feature extractor")
            print(f"[EmailFeatureExtractor] Loading subject vectorizer from: {subject_vectorizer_path}")

        # Load fitted vectorizers
        self.subject_vectorizer = joblib.load(subject_vectorizer_path)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Subject vectorizer loaded successfully")
            print(f"[EmailFeatureExtractor] Loading body vectorizer from: {body_vectorizer_path}")

        self.body_vectorizer = joblib.load(body_vectorizer_path)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Body vectorizer loaded successfully")

        # URL patterns for detection
        self.url_patterns = [
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

        # Combined URL pattern
        self.combined_url_pattern = '|'.join(self.url_patterns)

        if self.verbose:
            print("[EmailFeatureExtractor] Initialization completed successfully")

    # =========================================================================
    # SENDER COMPONENT EXTRACTION
    # =========================================================================

    def _extract_sender_components(self, sender):
        """
        Extract sender_name, sender_email, and sender_domain from sender string.

        Returns:
            tuple: (sender_name, sender_email, sender_domain)
        """
        if self.verbose:
            print("[EmailFeatureExtractor] Extracting sender components")
            print(f"[EmailFeatureExtractor] Input sender: {sender}")

        if pd.isna(sender) or sender.strip() == '':
            if self.verbose:
                print("[EmailFeatureExtractor] Sender is empty or NaN, returning None values")
            return None, None, None

        sender = sender.strip()

        # Pattern: "Name <email@domain.com>"
        pattern = r'(.+?)\s*<(.+?)>'
        match = re.search(pattern, sender)

        if match:
            sender_name = match.group(1).strip()
            sender_email = match.group(2).strip()
            if self.verbose:
                print(f"[EmailFeatureExtractor] Found name and email pattern")
        else:
            # No angle brackets, entire string is email (no name)
            sender_name = None
            sender_email = sender.strip()
            if self.verbose:
                print(f"[EmailFeatureExtractor] No name found, treating as email only")

        # Clean email
        if sender_email:
            sender_email = sender_email.replace('<', '').replace('>', '').strip()

        # Extract domain from email
        if sender_email and '@' in sender_email:
            sender_domain = sender_email.split('@')[-1].strip()
        else:
            sender_domain = None

        if self.verbose:
            print(
                f"[EmailFeatureExtractor] Extracted - Name: {sender_name}, Email: {sender_email}, Domain: {sender_domain}")

        return sender_name, sender_email, sender_domain

    # =========================================================================
    # HELPER FUNCTIONS FOR ENGINEERED FEATURES
    # =========================================================================

    def _calculate_entropy(self, text):
        """Calculate Shannon entropy - measures randomness."""
        if self.verbose:
            print(f"[EmailFeatureExtractor] Calculating entropy for text of length: {len(text) if text else 0}")

        if not text or len(text) == 0:
            if self.verbose:
                print("[EmailFeatureExtractor] Text is empty, returning 0")
            return 0

        freq = {}
        for char in text.lower():
            if char != ' ':
                freq[char] = freq.get(char, 0) + 1

        entropy = 0
        text_len = len([c for c in text if c != ' '])
        if text_len == 0:
            if self.verbose:
                print("[EmailFeatureExtractor] No non-space characters, returning 0")
            return 0

        for count in freq.values():
            probability = count / text_len
            entropy -= probability * math.log2(probability)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Calculated entropy: {entropy:.4f}")

        return entropy

    def _count_urls(self, text):
        """Count URLs in text using comprehensive patterns."""
        if self.verbose:
            print("[EmailFeatureExtractor] Counting URLs in text")

        if pd.isna(text) or text.strip() == '':
            if self.verbose:
                print("[EmailFeatureExtractor] Text is empty, returning 0")
            return 0

        total_urls = 0
        for pattern in self.url_patterns:
            urls = re.findall(pattern, text)
            total_urls += len(urls)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Found {total_urls} URLs")

        return total_urls

    def _get_email_digit_ratio(self, email):
        """Calculate ratio of digits in email local part."""
        if self.verbose:
            print(f"[EmailFeatureExtractor] Calculating digit ratio for email: {email}")

        if pd.isna(email) or email.strip() == '':
            if self.verbose:
                print("[EmailFeatureExtractor] Email is empty, returning 0")
            return 0

        local_part = email.split('@')[0] if '@' in email else email
        if len(local_part) == 0:
            if self.verbose:
                print("[EmailFeatureExtractor] Local part is empty, returning 0")
            return 0

        digit_count = sum(c.isdigit() for c in local_part)
        ratio = digit_count / len(local_part)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Digit ratio: {ratio:.4f}")

        return ratio

    def _get_domain_entropy(self, domain):
        """Calculate entropy of domain (excluding TLD)."""
        if self.verbose:
            print(f"[EmailFeatureExtractor] Calculating domain entropy for: {domain}")

        if pd.isna(domain) or domain.strip() == '':
            if self.verbose:
                print("[EmailFeatureExtractor] Domain is empty, returning 0")
            return 0

        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            main_domain = '.'.join(domain_parts[:-1])
        else:
            main_domain = domain

        entropy = self._calculate_entropy(main_domain.lower())

        if self.verbose:
            print(f"[EmailFeatureExtractor] Domain entropy: {entropy:.4f}")

        return entropy

    def _get_vowel_consonant_ratio(self, domain):
        """Calculate vowel to consonant ratio in domain."""
        if self.verbose:
            print(f"[EmailFeatureExtractor] Calculating vowel/consonant ratio for: {domain}")

        if pd.isna(domain) or domain.strip() == '':
            if self.verbose:
                print("[EmailFeatureExtractor] Domain is empty, returning 0")
            return 0

        domain_clean = re.sub(r'[^a-zA-Z]', '', domain.lower())
        if len(domain_clean) == 0:
            if self.verbose:
                print("[EmailFeatureExtractor] No letters in domain, returning 0")
            return 0

        vowels = sum(1 for char in domain_clean if char in 'aeiou')
        consonants = sum(1 for char in domain_clean if char in 'bcdfghjklmnpqrstvwxyz')

        if consonants == 0:
            if self.verbose:
                print("[EmailFeatureExtractor] No consonants found, returning 0")
            return 0

        ratio = vowels / consonants

        if self.verbose:
            print(f"[EmailFeatureExtractor] Vowel/consonant ratio: {ratio:.4f}")

        return ratio

    def _check_name_email_consistency(self, name, email):
        """Check if sender name appears in email local part."""
        if self.verbose:
            print(f"[EmailFeatureExtractor] Checking consistency between name: {name} and email: {email}")

        if pd.isna(name) or pd.isna(email):
            if self.verbose:
                print("[EmailFeatureExtractor] Name or email is missing, returning 0")
            return 0

        name_clean = re.sub(r'[^a-zA-Z]', '', name.lower())
        email_local = email.split('@')[0] if '@' in email else email
        email_clean = re.sub(r'[^a-zA-Z]', '', email_local.lower())

        if len(name_clean) == 0 or len(email_clean) == 0:
            if self.verbose:
                print("[EmailFeatureExtractor] Cleaned name or email is empty, returning 0")
            return 0

        # Check if any name part appears in email
        name_parts = name_clean.split()
        for part in name_parts:
            if len(part) > 2 and part in email_clean:
                if self.verbose:
                    print(f"[EmailFeatureExtractor] Name part '{part}' found in email, returning 1")
                return 1

        # Check for 3-character substrings
        if len(name_clean) >= 3:
            for i in range(len(name_clean) - 2):
                substring = name_clean[i:i + 3]
                if substring in email_clean:
                    if self.verbose:
                        print(f"[EmailFeatureExtractor] Substring '{substring}' found in email, returning 1")
                    return 1

        if self.verbose:
            print("[EmailFeatureExtractor] No consistency found, returning 0")

        return 0

    # =========================================================================
    # ENGINEERED FEATURE EXTRACTION (15 SELECTED FEATURES)
    # =========================================================================

    def extract_features(self, sender, subject, body):
        """
        Extract 15 selected engineered features from cleaned email.
        Uses ORIGINAL text (with URLs, !, ?, case preserved).

        SELECTED FEATURES:
        1. body_word_count
        2. body_exclamation_count
        3. email_local_length
        4. name_email_consistency
        5. body_url_density
        6. body_url_count
        7. body_entropy
        8. email_digit_ratio
        9. domain_entropy
        10. domain_length
        11. subject_entropy
        12. body_avg_word_length
        13. sender_name_exists
        14. subject_exclamation_count
        15. domain_vowel_consonant_ratio

        Args:
            sender (str): Cleaned sender
            subject (str): Cleaned subject (with !, ?, case preserved)
            body (str): Cleaned body (with URLs, !, ?, case preserved)

        Returns:
            dict: Dictionary with 15 feature values
        """
        if self.verbose:
            print("\n[EmailFeatureExtractor] === Starting feature extraction ===")
            print("[EmailFeatureExtractor] Extracting 15 selected engineered features")

        features = {}

        # =====================================================================
        # SENDER FEATURES (8 features)
        # =====================================================================

        if self.verbose:
            print("[EmailFeatureExtractor] Extracting sender features (7 features)")

        sender_name, sender_email, sender_domain = self._extract_sender_components(sender)

        # 1. email_local_length - Length of email before @
        if sender_email and '@' in sender_email:
            features['email_local_length'] = len(sender_email.split('@')[0])
        else:
            features['email_local_length'] = 0

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 1/15: email_local_length = {features['email_local_length']}")

        # 2. domain_length - Length of domain
        if sender_domain:
            features['domain_length'] = len(sender_domain)
        else:
            features['domain_length'] = 0

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 2/15: domain_length = {features['domain_length']}")

        # 3. email_digit_ratio - Ratio of digits in email local part
        features['email_digit_ratio'] = self._get_email_digit_ratio(sender_email)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 3/15: email_digit_ratio = {features['email_digit_ratio']:.4f}")

        # 4. domain_entropy - Entropy of domain (excluding TLD)
        features['domain_entropy'] = self._get_domain_entropy(sender_domain)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 4/15: domain_entropy = {features['domain_entropy']:.4f}")

        # 5. domain_vowel_consonant_ratio - Vowel/consonant ratio in domain
        features['domain_vowel_consonant_ratio'] = self._get_vowel_consonant_ratio(sender_domain)

        if self.verbose:
            print(
                f"[EmailFeatureExtractor] Feature 5/15: domain_vowel_consonant_ratio = {features['domain_vowel_consonant_ratio']:.4f}")

        # 6. sender_name_exists - Binary flag if sender name exists
        features['sender_name_exists'] = 1 if sender_name is not None else 0

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 6/15: sender_name_exists = {features['sender_name_exists']}")

        # 7. name_email_consistency - Check if name appears in email
        features['name_email_consistency'] = self._check_name_email_consistency(sender_name, sender_email)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 7/15: name_email_consistency = {features['name_email_consistency']}")

        # =====================================================================
        # SUBJECT FEATURES (2 features)
        # =====================================================================

        if self.verbose:
            print("[EmailFeatureExtractor] Extracting subject features (2 features)")

        subject = subject if subject else ''

        # 8. subject_entropy - Shannon entropy
        features['subject_entropy'] = self._calculate_entropy(subject)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 8/15: subject_entropy = {features['subject_entropy']:.4f}")

        # 9. subject_exclamation_count - Count of !
        features['subject_exclamation_count'] = subject.count('!')

        if self.verbose:
            print(
                f"[EmailFeatureExtractor] Feature 9/15: subject_exclamation_count = {features['subject_exclamation_count']}")

        # =====================================================================
        # BODY FEATURES (6 features)
        # =====================================================================

        if self.verbose:
            print("[EmailFeatureExtractor] Extracting body features (6 features)")

        body = body if body else ''

        # 10. body_word_count - Number of words
        body_words = body.split()
        features['body_word_count'] = len(body_words)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 10/15: body_word_count = {features['body_word_count']}")

        # 11. body_url_count - Count URLs in body
        features['body_url_count'] = self._count_urls(body)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 11/15: body_url_count = {features['body_url_count']}")

        # 12. body_url_density - URLs per 100 words
        if features['body_word_count'] > 0:
            features['body_url_density'] = (features['body_url_count'] / features['body_word_count']) * 100
        else:
            features['body_url_density'] = 0

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 12/15: body_url_density = {features['body_url_density']:.4f}")

        # 13. body_exclamation_count - Count of !
        features['body_exclamation_count'] = body.count('!')

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 13/15: body_exclamation_count = {features['body_exclamation_count']}")

        # 14. body_avg_word_length - Average characters per word
        if features['body_word_count'] > 0:
            total_chars = sum(len(word) for word in body_words)
            features['body_avg_word_length'] = total_chars / features['body_word_count']
        else:
            features['body_avg_word_length'] = 0

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 14/15: body_avg_word_length = {features['body_avg_word_length']:.4f}")

        # 15. body_entropy - Shannon entropy
        features['body_entropy'] = self._calculate_entropy(body)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Feature 15/15: body_entropy = {features['body_entropy']:.4f}")
            print("[EmailFeatureExtractor] === Feature extraction completed ===\n")

        return features

    # =========================================================================
    # TEXT CLEANING FOR VECTORIZATION (AFTER FEATURE EXTRACTION)
    # =========================================================================

    def _clean_text_for_vectorization(self, subject, body):
        """
        Clean subject and body for TF-IDF vectorization AFTER feature extraction.

        REMOVES (features already captured):
        1. URLs - already captured in body_url_count, body_url_density
        2. ! and ? - already captured in exclamation_count
        3. Convert to lowercase
        4. Normalize whitespace

        Returns:
            tuple: (subject_clean, body_clean) ready for vectorization
        """
        if self.verbose:
            print("[EmailFeatureExtractor] Cleaning text for TF-IDF vectorization")

        # Clean subject
        subject_clean = subject if subject else ''

        if self.verbose:
            print(f"[EmailFeatureExtractor] Original subject length: {len(subject_clean)} characters")

        # Remove URLs
        subject_clean = re.sub(self.combined_url_pattern, '', subject_clean)

        # Remove ! and ?
        subject_clean = re.sub(r'[!?]+', '', subject_clean)

        # Convert to lowercase
        subject_clean = subject_clean.lower()

        # Normalize whitespace
        subject_clean = re.sub(r'\s+', ' ', subject_clean).strip()

        if self.verbose:
            print(f"[EmailFeatureExtractor] Cleaned subject length: {len(subject_clean)} characters")

        # Clean body
        body_clean = body if body else ''

        if self.verbose:
            print(f"[EmailFeatureExtractor] Original body length: {len(body_clean)} characters")

        # Remove URLs
        body_clean = re.sub(self.combined_url_pattern, '', body_clean)

        # Remove ! and ?
        body_clean = re.sub(r'[!?]+', '', body_clean)

        # Convert to lowercase
        body_clean = body_clean.lower()

        # Normalize whitespace
        body_clean = re.sub(r'\s+', ' ', body_clean).strip()

        if self.verbose:
            print(f"[EmailFeatureExtractor] Cleaned body length: {len(body_clean)} characters")
            print("[EmailFeatureExtractor] Text cleaning for vectorization completed")

        return subject_clean, body_clean

    # =========================================================================
    # TF-IDF VECTORIZATION
    # =========================================================================

    def _vectorize_text(self, subject, body):
        """
        Vectorize subject (unigrams) and body (unigrams + bigrams) using fitted vectorizers.

        Returns:
            tuple: (subject_tfidf_array, body_tfidf_array)
        """
        if self.verbose:
            print("[EmailFeatureExtractor] Starting TF-IDF vectorization")

        # Transform subject (unigrams only)
        if self.verbose:
            print("[EmailFeatureExtractor] Transforming subject with subject vectorizer")
        subject_tfidf = self.subject_vectorizer.transform([subject])

        if self.verbose:
            print(f"[EmailFeatureExtractor] Subject TF-IDF shape: {subject_tfidf.shape}, non-zero: {subject_tfidf.nnz}")

        # Transform body (unigrams + bigrams)
        if self.verbose:
            print("[EmailFeatureExtractor] Transforming body with body vectorizer")
        body_tfidf = self.body_vectorizer.transform([body])

        if self.verbose:
            print(f"[EmailFeatureExtractor] Body TF-IDF shape: {body_tfidf.shape}, non-zero: {body_tfidf.nnz}")
            print("[EmailFeatureExtractor] TF-IDF vectorization completed")

        return subject_tfidf, body_tfidf

    # =========================================================================
    # MAIN PROCESSING METHOD
    # =========================================================================

    def process_email(self, cleaned_email, verbose=False):
        """
        Complete feature extraction pipeline for a single cleaned email.

        Args:
            cleaned_email (dict): Output from EmailCleaner.clean_email()
                                  Keys: 'sender', 'subject', 'body', 'urls'
            verbose (bool): If True, print cleaning steps for debugging.
                           If None, uses instance verbose setting.

        Returns:
            numpy.ndarray: Feature vector ready for model prediction
                          Shape: (1, 7015) - 2000 subject + 5000 body + 15 engineered
        """
        # Use provided verbose or fall back to instance verbose
        if verbose is None:
            verbose = self.verbose

        # Temporarily override instance verbose for this method
        original_verbose = self.verbose
        self.verbose = verbose

        # Minimal logging when verbose=False - only pipeline start/end
        print("[EmailFeatureExtractor] Starting feature extraction pipeline...")

        if self.verbose:
            print("\n" + "=" * 80)
            print("[EmailFeatureExtractor] ===== DETAILED FEATURE EXTRACTION PIPELINE =====")
            print("=" * 80)

        # Extract components (ORIGINAL with URLs, !, ?, case preserved)
        sender = cleaned_email['sender']
        subject = cleaned_email['subject']
        body = cleaned_email['body']

        if self.verbose:
            print("\n[EmailFeatureExtractor] Step 1/6: Validating input")
            print("-" * 80)
            print(f"[EmailFeatureExtractor] Sender: {sender}")
            print(f"[EmailFeatureExtractor] Subject length: {len(subject)} characters")
            print(f"[EmailFeatureExtractor] Body length: {len(body)} characters")
            print(f"[EmailFeatureExtractor] Subject preview: {subject[:100]}...")
            print(f"[EmailFeatureExtractor] Body preview: {body[:200]}...")

        # Step 1: Extract 15 selected engineered features (uses ORIGINAL text)
        if self.verbose:
            print("\n[EmailFeatureExtractor] Step 2/6: Extracting engineered features")
            print("-" * 80)

        engineered_features = self.extract_features(sender, subject, body)

        if self.verbose:
            print("\n[EmailFeatureExtractor] Engineered features extracted:")
            for i, (feat_name, feat_value) in enumerate(engineered_features.items(), 1):
                print(f"  {i:2d}. {feat_name:30s}: {feat_value:.4f}")

        # Convert to ordered array (MUST MATCH TRAINING DATA ORDER - NOT alphabetical!)
        feature_names = [
            'body_word_count',  # Position 7000
            'body_exclamation_count',  # Position 7001
            'email_local_length',  # Position 7002
            'name_email_consistency',  # Position 7003
            'body_url_density',  # Position 7004
            'body_url_count',  # Position 7005
            'body_entropy',  # Position 7006
            'email_digit_ratio',  # Position 7007
            'domain_entropy',  # Position 7008
            'domain_length',  # Position 7009
            'subject_entropy',  # Position 7010
            'body_avg_word_length',  # Position 7011
            'sender_name_exists',  # Position 7012
            'subject_exclamation_count',  # Position 7013
            'domain_vowel_consonant_ratio'  # Position 7014
        ]

        engineered_array = np.array([engineered_features[f] for f in feature_names]).reshape(1, -1)

        if self.verbose:
            print(f"\n[EmailFeatureExtractor] Engineered features array shape: {engineered_array.shape}")

        # Step 2: Clean text for vectorization (remove URLs, !, ?, lowercase)
        if self.verbose:
            print("\n[EmailFeatureExtractor] Step 3/6: Cleaning text for vectorization")
            print("-" * 80)

        subject_clean, body_clean = self._clean_text_for_vectorization(subject, body)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Subject before cleaning: {subject[:100]}...")
            print(f"[EmailFeatureExtractor] Subject after cleaning:  {subject_clean[:100]}...")
            print(f"[EmailFeatureExtractor] Body before cleaning: {body[:200]}...")
            print(f"[EmailFeatureExtractor] Body after cleaning:  {body_clean[:200]}...")

            # Show what was removed
            urls_removed = self._count_urls(body)
            exclamations_removed = body.count('!')
            questions_removed = body.count('?')
            print(f"\n[EmailFeatureExtractor] Removed from body:")
            print(f"  - URLs: {urls_removed}")
            print(f"  - Exclamation marks (!): {exclamations_removed}")
            print(f"  - Question marks (?): {questions_removed}")
            print(f"  - Text lowercased: Yes")

        # Step 3: Vectorize text (uses cleaned text)
        if self.verbose:
            print("\n[EmailFeatureExtractor] Step 4/6: Vectorizing text with TF-IDF")
            print("-" * 80)

        subject_tfidf, body_tfidf = self._vectorize_text(subject_clean, body_clean)

        if self.verbose:
            print(f"[EmailFeatureExtractor] Subject TF-IDF shape: {subject_tfidf.shape}")
            print(f"[EmailFeatureExtractor] Body TF-IDF shape: {body_tfidf.shape}")
            print(f"[EmailFeatureExtractor] Subject non-zero features: {subject_tfidf.nnz}")
            print(f"[EmailFeatureExtractor] Body non-zero features: {body_tfidf.nnz}")

        # Step 4: Combine all features
        # Order: subject_tfidf (2000) + body_tfidf (5000) + engineered (15) = 7015 features
        if self.verbose:
            print("\n[EmailFeatureExtractor] Step 5/6: Combining all features")
            print("-" * 80)

        final_features = hstack([subject_tfidf, body_tfidf, engineered_array])

        if self.verbose:
            print(f"[EmailFeatureExtractor] Final feature vector shape: {final_features.shape}")
            print(f"[EmailFeatureExtractor] Total features: {final_features.shape[1]}")
            print(f"  - Subject TF-IDF: 2000")
            print(f"  - Body TF-IDF: 5000")
            print(f"  - Engineered: 15 (selected features)")

        if self.verbose:
            print("\n[EmailFeatureExtractor] Step 6/6: Converting to dense array")
            print("-" * 80)

        result = final_features.toarray()

        if self.verbose:
            print(f"[EmailFeatureExtractor] Final array shape: {result.shape}")
            print("\n" + "=" * 80)
            print("[EmailFeatureExtractor] ===== FEATURE EXTRACTION PIPELINE COMPLETED =====")
            print("=" * 80 + "\n")
        else:
            # Minimal logging when verbose=False
            print("[EmailFeatureExtractor] Feature extraction pipeline completed successfully.\n")

        # Restore original verbose setting
        self.verbose = original_verbose

        return result

    def get_feature_names(self):
        """
        Get ordered list of all feature names for reference.

        Returns:
            list: All 7015 feature names in correct order
        """
        if self.verbose:
            print("[EmailFeatureExtractor] Generating feature names list")

        # Subject TF-IDF features (2000)
        subject_features = [f'subject_tfidf_{i}' for i in range(len(self.subject_vectorizer.get_feature_names_out()))]

        # Body TF-IDF features (5000)
        body_features = [f'body_tfidf_{i}' for i in range(len(self.body_vectorizer.get_feature_names_out()))]

        # Engineered features (15 selected features - MUST MATCH TRAINING ORDER)
        engineered_features = [
            'body_word_count',  # Position 7000
            'body_exclamation_count',  # Position 7001
            'email_local_length',  # Position 7002
            'name_email_consistency',  # Position 7003
            'body_url_density',  # Position 7004
            'body_url_count',  # Position 7005
            'body_entropy',  # Position 7006
            'email_digit_ratio',  # Position 7007
            'domain_entropy',  # Position 7008
            'domain_length',  # Position 7009
            'subject_entropy',  # Position 7010
            'body_avg_word_length',  # Position 7011
            'sender_name_exists',  # Position 7012
            'subject_exclamation_count',  # Position 7013
            'domain_vowel_consonant_ratio'  # Position 7014
        ]

        all_features = subject_features + body_features + engineered_features

        if self.verbose:
            print(f"[EmailFeatureExtractor] Total feature names: {len(all_features)}")

        return all_features
