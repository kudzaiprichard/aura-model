
"""
Script to combine all email datasets and export to JSON format for bulk upload.
"""

import json
import os
from datetime import datetime

from usage.dataset.legitimate import legitimate_emails, legitimate_shipping_notifications, \
    legitimate_subscription_renewals


def extract_sender_parts(sender_string):
    """
    Extract sender email and domain from sender string.

    Args:
        sender_string: Sender string from dataset

    Returns:
        Tuple of (sender_email, sender_domain)
    """
    if '<' in sender_string and '>' in sender_string:
        email = sender_string.split('<')[1].split('>')[0].strip()
    else:
        email = sender_string.strip()

    if '@' in email:
        domain = email.split('@')[1]
    else:
        domain = 'unknown.com'

    return email, domain


def convert_to_upload_format(emails):
    """
    Convert dataset format to upload service format.

    Args:
        emails: List of emails in dataset format

    Returns:
        Dictionary ready for JSON export
    """
    converted_emails = []

    for email in emails:
        sender_email, sender_domain = extract_sender_parts(email['sender'])
        label_str = 'phishing' if email['label'] == 1 else 'legitimate'

        if email['label'] == 1:
            notes = "Identified as phishing during manual review"
        else:
            notes = "Verified as legitimate email from trusted sender"

        converted_email = {
            'sender_email': sender_email,
            'sender_domain': sender_domain,
            'recipient_email': 'user@company.com',
            'subject': email['subject'],
            'body_text': email['body'],
            'label': label_str,
            'notes': notes
        }

        converted_emails.append(converted_email)

    return {'emails': converted_emails}


def export_to_json(data, output_filename, output_dir='../storage/training_data'):
    """
    Export data to JSON file.

    Args:
        data: Dictionary to export
        output_filename: Name of output file
        output_dir: Directory to save file

    Returns:
        Path to exported file
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_path


def generate_summary(data):
    """
    Generate summary statistics for the dataset.

    Args:
        data: Dictionary with 'emails' key

    Returns:
        Dictionary with summary statistics
    """
    emails = data['emails']
    phishing_count = sum(1 for e in emails if e['label'] == 'phishing')
    legitimate_count = sum(1 for e in emails if e['label'] == 'legitimate')

    domains = {}
    for email in emails:
        domain = email['sender_domain']
        domains[domain] = domains.get(domain, 0) + 1

    top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        'total_emails': len(emails),
        'phishing_emails': phishing_count,
        'legitimate_emails': legitimate_count,
        'phishing_percentage': round((phishing_count / len(emails)) * 100, 2),
        'legitimate_percentage': round((legitimate_count / len(emails)) * 100, 2),
        'unique_domains': len(domains),
        'top_10_domains': [{'domain': d, 'count': c} for d, c in top_domains]
    }


def main():
    """Main execution function."""
    print("Combining datasets...")

    from usage.dataset.phishing import (
        phishing_emails,
        phishing_shipping_notifications,
        phishing_subscription_renewals
    )

    all_emails = []
    all_emails.extend(legitimate_emails)
    all_emails.extend(legitimate_shipping_notifications)
    all_emails.extend(legitimate_subscription_renewals)
    all_emails.extend(phishing_emails)
    all_emails.extend(phishing_shipping_notifications)
    all_emails.extend(phishing_subscription_renewals)

    print(f"Combined {len(all_emails)} emails")

    print("Converting to upload format...")
    upload_data = convert_to_upload_format(all_emails)

    print("Generating summary...")
    summary = generate_summary(upload_data)

    print(f"Total: {summary['total_emails']}")
    print(f"Phishing: {summary['phishing_emails']} ({summary['phishing_percentage']}%)")
    print(f"Legitimate: {summary['legitimate_emails']} ({summary['legitimate_percentage']}%)")
    print(f"Unique domains: {summary['unique_domains']}")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print("Exporting to JSON...")
    output_filename = f'training_data_{timestamp}.json'
    output_path = export_to_json(upload_data, output_filename)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Exported to: {output_path}")
    print(f"File size: {file_size_mb:.2f} MB")

    summary_filename = f'training_data_summary_{timestamp}.json'
    summary_path = export_to_json(summary, summary_filename)
    print(f"Summary: {summary_path}")

    print("\nReady for upload via /models/learning interface")


if __name__ == '__main__':
    main()