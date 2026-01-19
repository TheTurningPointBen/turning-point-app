from utils.email import send_email
import os

# Set RECIPIENT env var or edit here
recipient = os.getenv('TEST_EMAIL_RECIPIENT') or '<your-email@example.com>'

res = send_email(recipient, 'Test email from Turning Point app', 'This is a test message sent from the app.')
print(res)
