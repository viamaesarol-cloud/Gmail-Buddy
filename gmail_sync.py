import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from database import save_emails, init_db

SCOPES = ['https://mail.google.com/']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

_service = None

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    global _service
    _service = build('gmail', 'v1', credentials=creds)
    return _service

def parse_sender(sender_raw):
    if '<' in sender_raw:
        parts = sender_raw.split('<')
        name = parts[0].strip().strip('"')
        email_addr = parts[1].replace('>', '').strip()
    else:
        name = sender_raw.strip()
        email_addr = sender_raw.strip()
    return name, email_addr

def get_header(headers, name):
    for h in headers:
        if h['name'].lower() == name.lower():
            return h['value']
    return ''

def sync_emails(max_results=None):
    print("Connecting to Gmail...")
    service = get_gmail_service()
    init_db()

    print("Fetching all emails from inbox...")
    messages = []
    params = {'userId': 'me', 'labelIds': ['INBOX'], 'maxResults': 500}
    results = service.users().messages().list(**params).execute()
    messages += results.get('messages', [])

    while 'nextPageToken' in results:
        results = service.users().messages().list(
            **params, pageToken=results['nextPageToken']
        ).execute()
        messages += results.get('messages', [])
        print(f"  Got {len(messages)} so far...")

    print(f"Total: {len(messages)} emails. Processing...")

    emails = []
    for i, msg in enumerate(messages):
        try:
            full_msg = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = full_msg.get('payload', {}).get('headers', [])
            sender_raw = get_header(headers, 'From')
            subject = get_header(headers, 'Subject') or '(no subject)'
            date_raw = get_header(headers, 'Date')
            snippet = full_msg.get('snippet', '')
            label_ids = full_msg.get('labelIds', [])
            is_read = 0 if 'UNREAD' in label_ids else 1
            labels = ','.join(label_ids)

            sender_name, sender_email = parse_sender(sender_raw)

            emails.append({
                'id': msg['id'],
                'sender': sender_name,
                'sender_email': sender_email.lower(),
                'subject': subject,
                'date': date_raw,
                'snippet': snippet,
                'is_read': is_read,
                'labels': labels,
                'category': 'unchecked'
            })

            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(messages)}...")

        except Exception as e:
            print(f"  Error on message {msg['id']}: {e}")
            continue

    save_emails(emails)
    print(f"Sync complete! {len(emails)} emails saved.")
    return len(emails)

def trash_emails_by_sender(service, sender_email):
    """Move emails to Trash (recoverable)"""
    print(f"Moving to Trash: {sender_email}...")
    total = 0
    all_ids = []
    while True:
        results = service.users().messages().list(
            userId='me', q=f'from:{sender_email} -in:trash', maxResults=500
        ).execute()
        messages = results.get('messages', [])
        if not messages:
            break
        ids = [m['id'] for m in messages]
        all_ids.extend(ids)
        for msg_id in ids:
            try:
                service.users().messages().trash(userId='me', id=msg_id).execute()
                total += 1
            except:
                pass
        print(f"  Moved {total} so far...")
    print(f"Total trashed: {total} from {sender_email}")
    return total, all_ids

def delete_emails_by_sender(service, sender_email):
    """Permanently delete emails (no recovery)"""
    print(f"Permanently deleting: {sender_email}...")
    total_deleted = 0
    while True:
        results = service.users().messages().list(
            userId='me', q=f'from:{sender_email}', maxResults=500
        ).execute()
        messages = results.get('messages', [])
        if not messages:
            break
        ids = [m['id'] for m in messages]
        for i in range(0, len(ids), 1000):
            batch = ids[i:i+1000]
            service.users().messages().batchDelete(
                userId='me', body={'ids': batch}
            ).execute()
            total_deleted += len(batch)
            print(f"  Deleted {total_deleted} so far...")
    print(f"Total deleted: {total_deleted} from {sender_email}")
    return total_deleted

def empty_trash(service):
    """Empty entire Trash"""
    print("Emptying Trash...")
    service.users().messages().emptyTrash(userId='me').execute()
    print("Trash emptied!")
    return True

def archive_emails_by_sender(service, sender_email):
    print(f"Archiving emails from {sender_email}...")
    total = 0
    while True:
        results = service.users().messages().list(
            userId='me',
            q=f'from:{sender_email} in:inbox',
            maxResults=500
        ).execute()
        messages = results.get('messages', [])
        if not messages:
            break
        for msg in messages:
            service.users().messages().modify(
                userId='me', id=msg['id'],
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            total += 1
    print(f"Archived {total} emails.")
    return total

if __name__ == "__main__":
    sync_emails()
