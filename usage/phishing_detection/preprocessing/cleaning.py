import pandas as pd
import re
import unicodedata
from bs4 import BeautifulSoup


class EmailCleaner:
    """
    Production-ready email cleaning pipeline for phishing detection.
    Cleans sender, subject, and body while PRESERVING URLs, !, ? for feature extraction.
    Uses Unicode categories for dynamic emoji/symbol removal.
    """

    def __init__(self, verbose=False):
        """
        Initialize EmailCleaner with optional verbose logging.

        Args:
            verbose (bool): If True, enables detailed logging. If False, minimal logging.
        """
        self.verbose = verbose

        # URL patterns for comprehensive detection
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
            r'\b[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?\b(?:/[^\s<>\"\'\)]*)?'
        ]

        self.combined_url_pattern = '|'.join(f'({p})' for p in self.url_patterns)
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        # Placeholders for URL/email protection
        self.url_placeholder = "___URL_PLACEHOLDER_{}___ "
        self.email_placeholder = "___EMAIL_PLACEHOLDER_{}___ "

        if self.verbose:
            print("[EmailCleaner] Initialized with verbose logging enabled")

    # =========================================================================
    # UNICODE-BASED EMOJI/SYMBOL REMOVAL
    # =========================================================================

    def _remove_unicode_noise(self, text):
        """
        DYNAMIC removal of ALL emojis, symbols, and special characters
        using Unicode character categories.

        KEEPS ONLY:
        - Letters (all languages): L* categories
        - Numbers: N* categories
        - Spaces: Zs category
        - Explicit: ! ? and newlines
        - URL/Email placeholders: underscores in ___PLACEHOLDER___ format

        REMOVES:
        - So (Other symbols): emojis, arrows, geometric shapes
        - Sm (Math symbols): ±, ×, ÷, ≠, etc.
        - Sc (Currency symbols): €, £, ¥, ₹, etc.
        - Sk (Modifier symbols)
        - Po (Other punctuation): except ! and ?
        - Ps, Pe, Pi, Pf (Brackets, quotes)
        - Pd (Dashes): –, —, etc.
        - Pc (Connectors): except _ in placeholders
        - And all other non-letter/number Unicode categories
        """
        if self.verbose:
            print("[_remove_unicode_noise] Starting Unicode noise removal")
            print(f"[_remove_unicode_noise] Input length: {len(text)} characters")

        cleaned_chars = []

        for char in text:
            category = unicodedata.category(char)

            # KEEP these Unicode categories:
            if (category.startswith('L') or  # L* = All letters (Lu, Ll, Lt, Lm, Lo)
                    category.startswith('N') or  # N* = All numbers (Nd, Nl, No)
                    category == 'Zs' or  # Zs = Space separator
                    char in '!?\n' or  # Explicit keeps
                    char == '_'):  # Underscore (for placeholders)

                cleaned_chars.append(char)
            else:
                # REMOVE everything else (emojis, symbols, special punctuation)
                # Replace with space to prevent word concatenation
                cleaned_chars.append(' ')

        result = ''.join(cleaned_chars)

        if self.verbose:
            print(f"[_remove_unicode_noise] Output length: {len(result)} characters")
            print("[_remove_unicode_noise] Unicode noise removal completed")

        return result

    # =========================================================================
    # BODY CLEANING - PRESERVE URLs, !, ?, CASE
    # =========================================================================

    def _clean_html_from_body(self, text):
        """Remove HTML while preserving URLs and structure."""
        if self.verbose:
            print("[_clean_html_from_body] Starting HTML cleaning")
            print(f"[_clean_html_from_body] Input length: {len(text)} characters")

        if pd.isna(text) or text == '':
            if self.verbose:
                print("[_clean_html_from_body] Input is empty or NaN, returning as-is")
            return text

        text = str(text)

        # Quick HTML check
        html_indicators = ['<br', '<div', '<span', '<a href', '<img', '<table',
                           '<font', '<b>', '<i>', '<strong>', '<em>', '</', '< ']
        has_html = any(ind in text.lower() for ind in html_indicators)

        if not has_html:
            if self.verbose:
                print("[_clean_html_from_body] No HTML detected, skipping HTML cleaning")
            return text

        if self.verbose:
            print("[_clean_html_from_body] HTML detected, proceeding with cleaning")

        # Step 1: Normalize malformed HTML
        if self.verbose:
            print("[_clean_html_from_body] Step 1: Normalizing malformed HTML")
        text = re.sub(r'<\s+', '<', text)
        text = re.sub(r'\s+>', '>', text)
        text = re.sub(r'href=([^"\s>]+)', r'href="\1"', text, flags=re.IGNORECASE)
        text = re.sub(r'src=([^"\s>]+)', r'src="\1"', text, flags=re.IGNORECASE)
        text = re.sub(r'<([a-zA-Z][a-zA-Z0-9]*)\s+[^>]*$', r'<\1>', text)
        text = text.replace('< =', '<=').replace('> =', '>=')

        # Step 2: Extract URLs from tags before parsing
        if self.verbose:
            print("[_clean_html_from_body] Step 2: Extracting URLs from HTML tags")
        href_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        text = re.sub(href_pattern, lambda m: f"{m.group(2)} {m.group(1)}" if m.group(2).strip() else m.group(1),
                      text, flags=re.IGNORECASE | re.DOTALL)

        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        text = re.sub(img_pattern, r' \1 ', text, flags=re.IGNORECASE)

        iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\'][^>]*>'
        text = re.sub(iframe_pattern, r' \1 ', text, flags=re.IGNORECASE)

        # Step 3: BeautifulSoup parsing
        if self.verbose:
            print("[_clean_html_from_body] Step 3: Parsing with BeautifulSoup")
        try:
            soup = BeautifulSoup(text, 'html.parser')
            for script in soup(['script', 'style']):
                script.decompose()
            text = soup.get_text(separator=' ')
            if self.verbose:
                print("[_clean_html_from_body] BeautifulSoup parsing successful")
        except Exception as e:
            if self.verbose:
                print(f"[_clean_html_from_body] BeautifulSoup parsing failed: {e}")

        # Step 4: Remove remaining HTML artifacts
        if self.verbose:
            print("[_clean_html_from_body] Step 4: Removing remaining HTML artifacts")
        html_tags = (
            'html|head|body|title|meta|link|style|script|'
            'div|span|p|br|hr|a|img|picture|source|'
            'table|thead|tbody|tfoot|tr|td|th|caption|colgroup|col|'
            'ul|ol|li|dl|dt|dd|'
            'form|input|button|select|option|textarea|label|fieldset|legend|'
            'h1|h2|h3|h4|h5|h6|'
            'strong|b|i|em|u|s|strike|del|ins|sub|sup|small|mark|'
            'iframe|embed|object|param|video|audio|canvas|svg|'
            'font|center|marquee|blink'
        )

        html_tag_pattern = f'</?(?:{html_tags})(?:\\s+[^>]*)?\\/?>|<\\/(?:{html_tags})>'
        text = re.sub(html_tag_pattern, ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'<([a-zA-Z][a-zA-Z0-9]*)\s+[^>]*>', ' ', text)
        text = re.sub(r'<([a-zA-Z][a-zA-Z0-9]*)/>', ' ', text)
        text = re.sub(r'<[^>]*$', '', text)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

        # Step 5: Decode HTML entities
        if self.verbose:
            print("[_clean_html_from_body] Step 5: Decoding HTML entities")
        html_entities = {
            '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>',
            '&quot;': '"', '&apos;': "'", '&#39;': "'", '&ndash;': '-',
            '&mdash;': '—', '&hellip;': '...', '&bull;': '•',
            '&copy;': '©', '&reg;': '®', '&trade;': '™',
        }

        for entity, char in html_entities.items():
            text = text.replace(entity, char)

        text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))) if int(m.group(1)) < 1114112 else m.group(0), text)
        text = re.sub(r'&#x([0-9a-fA-F]+);',
                      lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) < 1114112 else m.group(0), text)
        text = re.sub(r'&[a-zA-Z]{2,8};', ' ', text)
        text = re.sub(r'&#[0-9]{1,6};', ' ', text)

        # Step 6: Clean quoted-printable and whitespace
        if self.verbose:
            print("[_clean_html_from_body] Step 6: Cleaning quoted-printable and whitespace")
        text = re.sub(r'=3C[^=]*?=3E', '', text)
        text = re.sub(r'=3C[^=]*$', '', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.replace('\t', ' ').strip()

        if self.verbose:
            print(f"[_clean_html_from_body] Output length: {len(text)} characters")
            print("[_clean_html_from_body] HTML cleaning completed")

        return text

    def _protect_urls_and_emails(self, text):
        """Replace URLs and emails with placeholders."""
        if self.verbose:
            print("[_protect_urls_and_emails] Starting URL and email protection")

        url_map = {}
        email_map = {}

        # Protect URLs
        urls = re.findall(self.combined_url_pattern, text)
        urls = [url for url_tuple in urls for url in url_tuple if url]

        if self.verbose:
            print(f"[_protect_urls_and_emails] Found {len(urls)} URLs to protect")

        for i, url in enumerate(urls):
            placeholder = self.url_placeholder.format(i)
            url_map[placeholder.strip()] = url
            text = text.replace(url, placeholder, 1)

        # Protect emails
        emails = re.findall(self.email_pattern, text)

        if self.verbose:
            print(f"[_protect_urls_and_emails] Found {len(emails)} email addresses to protect")

        for i, email in enumerate(emails):
            placeholder = self.email_placeholder.format(i)
            email_map[placeholder.strip()] = email
            text = text.replace(email, placeholder, 1)

        if self.verbose:
            print("[_protect_urls_and_emails] URL and email protection completed")

        return text, url_map, email_map

    def _restore_urls_and_emails(self, text, url_map, email_map):
        """Restore protected URLs and emails."""
        if self.verbose:
            print("[_restore_urls_and_emails] Starting URL and email restoration")
            print(f"[_restore_urls_and_emails] Restoring {len(url_map)} URLs and {len(email_map)} emails")

        for placeholder, url in url_map.items():
            text = text.replace(placeholder, url)
        for placeholder, email in email_map.items():
            text = text.replace(placeholder, email)

        if self.verbose:
            print("[_restore_urls_and_emails] URL and email restoration completed")

        return text

    def _remove_noise_from_body(self, text):
        """
        Remove email noise patterns (separators, headers, footers).
        PRESERVE: URLs, !, ?, case (uppercase/lowercase)
        """
        if self.verbose:
            print("[_remove_noise_from_body] Starting noise removal from body")
            print(f"[_remove_noise_from_body] Input length: {len(text)} characters")

        # Separators
        text = re.sub(r'[>=+\-*_~]{10,}', ' ', text)
        text = re.sub(r'>\s*[=+\-]+\s*>', ' ', text)

        # Quote markers
        text = re.sub(r'^\s*>\s*', ' ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*>+\s*', ' ', text, flags=re.MULTILINE)
        text = re.sub(r'(?<=\n)>\s+', ' ', text)

        # Table borders
        text = re.sub(r'\|{2,}', ' ', text)
        text = re.sub(r'^\s*\|[-\s|]+\|\s*$', ' ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\+[-+=\s]+\+\s*$', ' ', text, flags=re.MULTILINE)

        # Repeated dots
        text = re.sub(r'\.{4,}', ' ', text)

        # Unsubscribe/footer patterns
        text = re.sub(r'You are receiving this (mail|email).*?because.*?(\n|$)', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'To unsubscribe.*?(\n|$)', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'Click here to unsubscribe.*?(\n|$)', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(unsubscribe|opt-?out|remove\s+me)\b', ' ', text, flags=re.IGNORECASE)

        # Reply/forwarding headers
        text = re.sub(r'On\s+.+?\s+wrote:\s*', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'-+\s*(Original Message|Forwarded Message)\s*-+', ' ', text, flags=re.IGNORECASE)

        # Copyright/legal
        text = re.sub(r'©|\(c\)\s*\d{4}|copyright\s+\d{4}', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'All rights reserved\.?', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(privacy\s+policy|terms\s+of\s+service)\b', ' ', text, flags=re.IGNORECASE)

        # Only remove excessive colons (still useful)
        text = re.sub(r':{3,}', ' ', text)

        # Email headers in body
        text = re.sub(r'^(From|To|Subject|Date|Cc|Bcc):\s*', ' ', text, flags=re.MULTILINE)
        text = re.sub(r'^(Content-Type|Content-Transfer-Encoding):', ' ', text, flags=re.MULTILINE)

        # Encoding issues
        text = re.sub(r'�+', ' ', text)
        text = re.sub(r'\?{5,}', ' ', text)  # Only excessive question marks (5+)

        if self.verbose:
            print(f"[_remove_noise_from_body] Output length: {len(text)} characters")
            print("[_remove_noise_from_body] Noise removal completed")

        return text

    def _normalize_whitespace(self, text):
        """Normalize excessive whitespace."""
        if self.verbose:
            print("[_normalize_whitespace] Starting whitespace normalization")

        text = re.sub(r'[ \t]{2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = '\n'.join(line.strip() for line in text.split('\n'))
        text = '\n'.join(line for line in text.split('\n') if line.strip())

        if self.verbose:
            print("[_normalize_whitespace] Whitespace normalization completed")

        return text.strip()

    def clean_body(self, text):
        """
        Complete body cleaning pipeline.
        PRESERVES: URLs, !, ?, case (uppercase/lowercase)
        REMOVES: HTML, noise patterns, encoding artifacts, emojis, symbols
        """
        if self.verbose:
            print("\n[clean_body] === Starting body cleaning pipeline ===")

        if pd.isna(text) or text == '':
            if self.verbose:
                print("[clean_body] Input is empty or NaN, returning empty string")
            return ''

        text = str(text)

        if self.verbose:
            print(f"[clean_body] Original body length: {len(text)} characters")

        # Step 1: Remove HTML
        if self.verbose:
            print("[clean_body] Step 1/7: Removing HTML")
        text = self._clean_html_from_body(text)

        # Step 2: Protect URLs/emails
        if self.verbose:
            print("[clean_body] Step 2/7: Protecting URLs and emails")
        protected_text, url_map, email_map = self._protect_urls_and_emails(text)

        # Step 3: Remove noise (but preserve !, ?)
        if self.verbose:
            print("[clean_body] Step 3/7: Removing noise patterns")
        cleaned_text = self._remove_noise_from_body(protected_text)

        # Step 4: DYNAMIC Unicode-based emoji and symbol removal
        if self.verbose:
            print("[clean_body] Step 4/7: Removing emojis and symbols")
        cleaned_text = self._remove_unicode_noise(cleaned_text)

        # Step 5: Normalize whitespace
        if self.verbose:
            print("[clean_body] Step 5/7: Normalizing whitespace")
        cleaned_text = self._normalize_whitespace(cleaned_text)

        # Step 6: Restore URLs/emails
        if self.verbose:
            print("[clean_body] Step 6/7: Restoring URLs and emails")
        final_text = self._restore_urls_and_emails(cleaned_text, url_map, email_map)

        # Step 7: NO LOWERCASING (preserve case for features)
        if self.verbose:
            print("[clean_body] Step 7/7: Preserving original case")
            print(f"[clean_body] Final body length: {len(final_text)} characters")
            print("[clean_body] === Body cleaning pipeline completed ===\n")

        return final_text

    # =========================================================================
    # SUBJECT CLEANING - PRESERVE !, ?, CASE
    # =========================================================================

    def clean_subject(self, subject):
        """
        Clean email subject by removing special characters and noise.
        PRESERVES: !, ?, case (uppercase/lowercase)
        REMOVES: Emojis, symbols dynamically using Unicode categories
        """
        if self.verbose:
            print("\n[clean_subject] === Starting subject cleaning ===")

        if pd.isna(subject) or subject == '':
            if self.verbose:
                print("[clean_subject] Input is empty or NaN, returning empty string")
            return ''

        subject = str(subject)

        if self.verbose:
            print(f"[clean_subject] Original subject length: {len(subject)} characters")

        # Remove prefixes
        if self.verbose:
            print("[clean_subject] Removing Re:/Fwd: prefixes")
        subject = re.sub(r'^(Re|Fwd|RE|FWD):\s*', '', subject)

        # Remove brackets and contents
        if self.verbose:
            print("[clean_subject] Removing brackets and their contents")
        subject = re.sub(r'\[.*?\]', ' ', subject)
        subject = re.sub(r'\(.*?\)', ' ', subject)

        # DYNAMIC Unicode-based emoji and symbol removal
        if self.verbose:
            print("[clean_subject] Removing emojis and symbols")
        subject = self._remove_unicode_noise(subject)

        # Normalize whitespace
        if self.verbose:
            print("[clean_subject] Normalizing whitespace")
        subject = re.sub(r'\s+', ' ', subject).strip()

        # NO LOWERCASING (preserve case)
        if self.verbose:
            print(f"[clean_subject] Final subject length: {len(subject)} characters")
            print("[clean_subject] === Subject cleaning completed ===\n")

        return subject

    # =========================================================================
    # SENDER CLEANING
    # =========================================================================

    def _convert_international_chars(self, text):
        """Convert international/accented characters to ASCII."""
        if self.verbose:
            print("[_convert_international_chars] Converting international characters to ASCII")

        normalized = unicodedata.normalize('NFD', text)
        result = normalized.encode('ascii', 'ignore').decode('ascii')

        if self.verbose:
            print(f"[_convert_international_chars] Converted {len(text)} to {len(result)} characters")

        return result

    def clean_sender(self, sender):
        """
        Clean email sender by extracting name and email.
        Returns format: "name <email@domain.com>" or "<email@domain.com>" or "name"
        Lowercase for consistency in sender features.
        """
        if self.verbose:
            print("\n[clean_sender] === Starting sender cleaning ===")

        if pd.isna(sender) or sender == '':
            if self.verbose:
                print("[clean_sender] Input is empty or NaN, returning empty string")
            return ''

        sender = str(sender)

        if self.verbose:
            print(f"[clean_sender] Original sender: {sender}")

        # Extract email from angle brackets
        if self.verbose:
            print("[clean_sender] Extracting email and name parts")
        email_in_brackets = re.search(r'<([^<>]+)>', sender)
        email_address = None
        name_part = None

        if email_in_brackets:
            email_content = email_in_brackets.group(1).strip()
            if '@' in email_content:
                email_address = email_content
            name_part = sender[:email_in_brackets.start()].strip()
        else:
            # Check if entire string is email
            email_pattern = r'^["\']?([^"\'<>]+@[^"\'<>\s]+)["\']?$'
            email_match = re.match(email_pattern, sender.strip())

            if email_match:
                email_address = email_match.group(1)
            else:
                # Check for quoted email format
                quoted_email_pattern = r'["\']([^"\']+)["\']@([^\s]+)'
                quoted_match = re.search(quoted_email_pattern, sender)

                if quoted_match:
                    local_part = quoted_match.group(1).replace(' ', '')
                    domain_part = quoted_match.group(2)
                    email_address = f"{local_part}@{domain_part}"
                else:
                    # Just a name
                    name_part = sender

        # Clean name part using Unicode-based filtering
        if self.verbose:
            print("[clean_sender] Cleaning name part")
        cleaned_name = ''
        if name_part:
            # First normalize to ASCII (café → cafe)
            nfd = unicodedata.normalize('NFD', name_part)
            ascii_name = nfd.encode('ascii', 'ignore').decode('ascii')

            # Then apply Unicode category filtering
            cleaned_chars = []
            for char in ascii_name:
                category = unicodedata.category(char)

                # KEEP only letters, numbers, and spaces in names
                if (category.startswith('L') or  # Letters
                        category.startswith('N') or  # Numbers
                        category == 'Zs'):  # Spaces
                    cleaned_chars.append(char)
                else:
                    cleaned_chars.append(' ')

            cleaned_name = ''.join(cleaned_chars)

            # Normalize multiple spaces to single space
            cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()

        # Clean email part
        if self.verbose:
            print("[clean_sender] Cleaning email part")
        cleaned_email = ''
        if email_address:
            cleaned_email = email_address.replace(' ', '').replace('"', '').replace("'", '')
            cleaned_email = f'<{cleaned_email}>'

        # Combine
        if cleaned_name and cleaned_email:
            result = f'{cleaned_name} {cleaned_email}'
        elif cleaned_email:
            result = cleaned_email
        elif cleaned_name:
            result = cleaned_name
        else:
            result = ''

        # Lowercase for sender features (consistency in domain/email matching)
        result = result.lower().strip()

        if self.verbose:
            print(f"[clean_sender] Final sender: {result}")
            print("[clean_sender] === Sender cleaning completed ===\n")

        return result

    # =========================================================================
    # URL DETECTION
    # =========================================================================

    def detect_urls(self, text):
        """
        Detect if text contains URLs.
        Returns 1 if URLs found, 0 otherwise.
        """
        if self.verbose:
            print("[detect_urls] Detecting URLs in text")

        if pd.isna(text) or text == '':
            if self.verbose:
                print("[detect_urls] Input is empty or NaN, returning 0")
            return 0

        text = str(text)
        has_urls = bool(re.search(self.combined_url_pattern, text, re.IGNORECASE))

        if self.verbose:
            print(f"[detect_urls] URLs found: {has_urls}")

        return 1 if has_urls else 0

    # =========================================================================
    # MAIN CLEANING METHOD
    # =========================================================================

    def clean_email(self, sender, subject, body):
        """
        Clean a single incoming email.

        PRESERVES FOR FEATURE EXTRACTION:
        - URLs in body/subject
        - ! and ? in body/subject
        - Original case (uppercase/lowercase)
        - Original lengths

        REMOVES:
        - HTML tags
        - Email noise (headers, footers, unsubscribe)
        - Encoding artifacts (�, &nbsp;, etc.)
        - Excessive whitespace
        - ALL emojis and symbols (dynamically via Unicode categories)

        Args:
            sender (str): Raw sender field
            subject (str): Raw subject field
            body (str): Raw body field

        Returns:
            dict: Cleaned email with keys: sender, subject, body, urls
        """
        # Minimal logging when verbose=False - only pipeline start/end
        print("[EmailCleaner] Starting email cleaning pipeline...")

        if self.verbose:
            print("\n" + "=" * 70)
            print("[EmailCleaner] ===== DETAILED EMAIL CLEANING PIPELINE =====")
            print("=" * 70)

        # Validate inputs
        if self.verbose:
            print("[EmailCleaner] Validating input fields")

        if pd.isna(body) or str(body).strip() == '':
            error_msg = "Email body cannot be empty"
            if self.verbose:
                print(f"[EmailCleaner] ERROR: {error_msg}")
            raise ValueError(error_msg)

        if pd.isna(sender) or str(sender).strip() == '':
            error_msg = "Email sender cannot be empty"
            if self.verbose:
                print(f"[EmailCleaner] ERROR: {error_msg}")
            raise ValueError(error_msg)

        if pd.isna(subject) or str(subject).strip() == '':
            error_msg = "Email subject cannot be empty"
            if self.verbose:
                print(f"[EmailCleaner] ERROR: {error_msg}")
            raise ValueError(error_msg)

        if self.verbose:
            print("[EmailCleaner] All input fields validated successfully")

        # Clean each field
        if self.verbose:
            print("[EmailCleaner] Cleaning sender field...")
        cleaned_sender = self.clean_sender(sender)

        if self.verbose:
            print("[EmailCleaner] Cleaning subject field...")
        cleaned_subject = self.clean_subject(subject)

        if self.verbose:
            print("[EmailCleaner] Cleaning body field...")
        cleaned_body = self.clean_body(body)

        # Detect URLs in body
        if self.verbose:
            print("[EmailCleaner] Detecting URLs in cleaned body...")
        has_urls = self.detect_urls(cleaned_body)

        # Final validation
        if self.verbose:
            print("[EmailCleaner] Performing final validation")

        if not cleaned_body or len(cleaned_body.strip()) < 10:
            error_msg = "Cleaned body is too short or empty"
            if self.verbose:
                print(f"[EmailCleaner] ERROR: {error_msg}")
            raise ValueError(error_msg)

        if self.verbose:
            print("[EmailCleaner] Final validation passed successfully")
            print("\n" + "=" * 70)
            print("[EmailCleaner] ===== EMAIL CLEANING COMPLETED SUCCESSFULLY =====")
            print("=" * 70 + "\n")
        else:
            # Minimal logging when verbose=False
            print("[EmailCleaner] Email cleaning pipeline completed successfully.\n")

        return {
            'sender': cleaned_sender,
            'subject': cleaned_subject,
            'body': cleaned_body,
            'urls': has_urls
        }
