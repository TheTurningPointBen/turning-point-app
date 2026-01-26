#!/usr/bin/env python3
"""Send a test email using SMTP env vars used by the app.

Reads: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SENDER_EMAIL, SENDER_NAME, ADMIN_EMAIL

Usage:
  python3 scripts/send_test_email.py --to you@example.com --subject "Test" --body "Hello"
"""
import os
import argparse
import sys
from email.message import EmailMessage


def get_env(name, default=None):
    return os.getenv(name, default)


def send_email(to_email: str, subject: str, body: str, verbose: bool = False) -> dict:
    host = get_env('SMTP_HOST')
    port = int(get_env('SMTP_PORT', '587'))
    user = get_env('SMTP_USER')
    password = get_env('SMTP_PASS')
    sender_name = get_env('SENDER_NAME')
    sender_email = get_env('SENDER_EMAIL') or user

    if not (host and user and password and to_email):
        return {'error': 'Missing SMTP configuration or recipient email'}

    msg = EmailMessage()
    msg['Subject'] = subject
    if sender_name:
        msg['From'] = f"{sender_name} <{sender_email}>"
    else:
        msg['From'] = sender_email
    msg['To'] = to_email
    msg.set_content(body)

    try:
        # Use SSL for port 465, otherwise use STARTTLS
        import smtplib
        if port == 465:
            if verbose:
                print(f'Connecting to {host}:{port} using SSL')
            with smtplib.SMTP_SSL(host, port, timeout=10) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            if verbose:
                print(f'Connecting to {host}:{port} using STARTTLS')
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                try:
                    smtp.starttls()
                except Exception:
                    pass
                smtp.login(user, password)
                smtp.send_message(msg)
        return {'ok': True}
    except Exception as e:
        return {'error': str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--to', help='Recipient email. Defaults to ADMIN_EMAIL or SMTP_USER', default=None)
    parser.add_argument('--subject', help='Email subject', default='Turning Point — test email')
    parser.add_argument('--body', help='Email body', default='This is a test message from send_test_email.py')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    recipient = args.to or get_env('ADMIN_EMAIL') or get_env('SMTP_USER')
    if not recipient:
        print('No recipient specified and no ADMIN_EMAIL or SMTP_USER found in env', file=sys.stderr)
        sys.exit(2)

    res = send_email(recipient, args.subject, args.body, verbose=args.verbose)
    if res.get('ok'):
        print(f'Successfully sent test email to {recipient}')
        sys.exit(0)
    else:
        print('Failed to send test email:', res.get('error'), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
from utils.email import send_email
import os

# Set RECIPIENT env var or edit here
recipient = os.getenv('TEST_EMAIL_RECIPIENT') or '<your-email@example.com>'

res = send_email(recipient, 'Test email from Turning Point app', 'This is a test message sent from the app.')
print(res)
