from flask import Flask, render_template, jsonify, request
from gmail_sync import get_gmail_service, sync_emails, delete_emails_by_sender, archive_emails_by_sender, trash_emails_by_sender, empty_trash
from database import get_senders, get_emails_by_sender, set_sender_category, init_db, delete_emails_from_db, init_undo_table, save_undo, get_undo, clear_undo, save_emails
import json
import urllib.request
import urllib.error
import time
import logging
import os
from datetime import datetime

app = Flask(__name__)

# Error Log Setup
log_path = os.path.join(os.path.dirname(__file__), 'error.log')
logging.basicConfig(
    filename=log_path,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_error(msg):
    logging.error(msg)
    print(f"ERROR: {msg}")

def call_gemini(api_key, model, prompt, max_retries=3):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = (attempt + 1) * 15
                print(f"Rate limit hit. Waiting {wait}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                if attempt == max_retries - 1:
                    raise
            else:
                raise
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(5)
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sync')
def api_sync():
    try:
        count = sync_emails(max_results=None)
        return jsonify({'status': 'ok', 'count': count})
    except Exception as e:
        log_error(f"Sync failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/senders')
def api_senders():
    return jsonify(get_senders())

@app.route('/api/emails/<sender_email>')
def api_emails(sender_email):
    return jsonify(get_emails_by_sender(sender_email))

@app.route('/api/category', methods=['POST'])
def api_category():
    data = request.json
    set_sender_category(data['email'], data['category'])
    return jsonify({'status': 'ok'})

@app.route('/api/archive', methods=['POST'])
def api_archive():
    try:
        data = request.json
        service = get_gmail_service()
        count = archive_emails_by_sender(service, data['email'])
        delete_emails_from_db(data['email'])
        return jsonify({'status': 'ok', 'archived': count})
    except Exception as e:
        log_error(f"Archive failed for {data.get('email')}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    data = request.json
    api_key = data.get('apiKey', '')
    model = data.get('model', 'gemini-2.0-flash')
    
    if not api_key:
        return jsonify({'status': 'error', 'message': 'No API key provided'})
    try:
        result = call_gemini(api_key, model, 'Say "OK" in one word.')
        text = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({'status': 'ok', 'message': f'Connected! Model response: {text.strip()}'})
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return jsonify({'status': 'error', 'message': 'Rate limit exceeded. Wait a few minutes and try again.'})
        elif e.code == 403:
            return jsonify({'status': 'error', 'message': 'Invalid API key or access denied.'})
        else:
            return jsonify({'status': 'error', 'message': f'HTTP Error {e.code}'})
    except Exception as e:
        log_error(f"Test connection failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/ai-categorize', methods=['POST'])
def api_ai_categorize():
    data = request.json
    senders = data.get('senders', [])
    api_key = data.get('apiKey', '')
    model = data.get('model', 'gemini-2.0-flash')

    if not api_key:
        return jsonify({'error': 'No API key provided'}), 400
    if not senders:
        return jsonify({'results': []})

    prompt = f"""Categorize these email senders:
{chr(10).join([f"- {s.get('sender', s['email'])} <{s['email']}> ({s['count']} emails)" for s in senders])}

For each sender, assign one category:
- delete: promotions, newsletters, noreply, automated, marketing
- keep: personal, important work, financial, known contacts
- check: unclear, needs review

Return ONLY valid JSON, no explanation:
{{"results": [{{"email": "...", "category": "..."}}]}}"""

    try:
        result = call_gemini(api_key, model, prompt)
        text = result['candidates'][0]['content']['parts'][0]['text']
        clean = text.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(clean)
        for item in parsed['results']:
            set_sender_category(item['email'], item['category'])
        return jsonify(parsed)
    except urllib.error.HTTPError as e:
        msg = f"Gemini API error {e.code}"
        if e.code == 429:
            msg = "Rate limit exceeded. Please wait a few minutes."
        log_error(f"AI categorize failed: {msg}")
        return jsonify({'error': msg}), 500
    except Exception as e:
        log_error(f"AI categorize failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-categories')
def api_export_categories():
    try:
        senders = get_senders()
        categories = [{'email': s['sender_email'], 'name': s['sender'], 'category': s['category']} for s in senders if s.get('category') and s['category'] != 'unchecked']
        return jsonify({'version': '1.1', 'count': len(categories), 'categories': categories})
    except Exception as e:
        log_error(f"Export failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/import-categories', methods=['POST'])
def api_import_categories():
    try:
        data = request.json
        categories = data.get('categories', [])
        count = 0
        for item in categories:
            if item.get('email') and item.get('category'):
                set_sender_category(item['email'], item['category'])
                count += 1
        return jsonify({'status': 'ok', 'imported': count})
    except Exception as e:
        log_error(f"Import failed: {e}")
        return jsonify({'error': str(e)}), 500

import shutil
from datetime import datetime

@app.route('/api/backup')
def api_backup():
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'gmail.db')
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        with open(db_path, 'rb') as f:
            data = f.read()
        import base64
        encoded = base64.b64encode(data).decode()
        return jsonify({'status': 'ok', 'data': encoded, 'filename': f'gmail_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'})
    except Exception as e:
        log_error(f"Backup failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/restore', methods=['POST'])
def api_restore():
    try:
        import base64
        data = request.json
        encoded = data.get('data', '')
        db_bytes = base64.b64decode(encoded)
        # validate SQLite file
        if not db_bytes.startswith(b'SQLite format 3'):
            return jsonify({'error': 'Invalid file: not a SQLite database'}), 400
        db_path = os.path.join(os.path.dirname(__file__), 'gmail.db')
        if os.path.exists(db_path):
            shutil.copy(db_path, db_path + '.bak')
        with open(db_path, 'wb') as f:
            f.write(db_bytes)
        return jsonify({'status': 'ok', 'message': 'Database restored successfully'})
    except Exception as e:
        log_error(f"Restore failed: {e}")
        return jsonify({'error': str(e)}), 500

# ===== UNDO DELETE =====
@app.route('/api/trash', methods=['POST'])
def api_trash():
    try:
        data = request.json
        email = data['email']
        service = get_gmail_service()
        count, ids = trash_emails_by_sender(service, email)
        save_undo(email, ids)
        delete_emails_from_db(email)
        return jsonify({'status': 'ok', 'trashed': count})
    except Exception as e:
        log_error(f"Trash failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/empty-trash', methods=['POST'])
def api_empty_trash():
    try:
        service = get_gmail_service()
        empty_trash(service)
        return jsonify({'status': 'ok'})
    except Exception as e:
        log_error(f"Empty trash failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/delete', methods=['POST'])
def api_delete_v2():
    try:
        data = request.json
        email = data['email']
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', q=f'from:{email}', maxResults=500).execute()
        messages = results.get('messages', [])
        ids = [m['id'] for m in messages]
        save_undo(email, ids)  # save to SQLite
        count = delete_emails_by_sender(service, email)
        delete_emails_from_db(email)
        return jsonify({'status': 'ok', 'deleted': count, 'can_undo': True})
    except Exception as e:
        log_error(f"Delete failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/undo-delete', methods=['POST'])
def api_undo_delete():
    try:
        data = request.json
        email = data['email']
        print(f'UNDO REQUEST for: {email}')
        ids = get_undo(email)
        print(f'IDs to restore: {len(ids) if ids else 0}')
        if not ids:
            return jsonify({'error': 'No undo data available'}), 400
        service = get_gmail_service()
        restored = 0
        for msg_id in ids:
            try:
                service.users().messages().untrash(userId='me', id=msg_id).execute()
                restored += 1
                print(f'Restored: {msg_id}')
            except Exception as ex:
                print(f'Untrash error: {ex}')
        clear_undo(email)
        # re-sync this sender to DB
        try:
            results = service.users().messages().list(
                userId='me', q=f'from:{email}', maxResults=100
            ).execute()
            messages = results.get('messages', [])
            emails_data = []
            for msg in messages:
                try:
                    full = service.users().messages().get(
                        userId='me', id=msg['id'], format='metadata',
                        metadataHeaders=['From','Subject','Date']
                    ).execute()
                    headers = full.get('payload',{}).get('headers',[])
                    def gh(n): return next((h['value'] for h in headers if h['name'].lower()==n.lower()),'')
                    sr = gh('From')
                    sn = sr.split('<')[0].strip().strip('"') if '<' in sr else sr
                    se = sr.split('<')[1].replace('>','').strip() if '<' in sr else sr
                    labels = full.get('labelIds',[])
                    emails_data.append({
                        'id': msg['id'], 'sender': sn, 'sender_email': se.lower(),
                        'subject': gh('Subject') or '(no subject)', 'date': gh('Date'),
                        'snippet': full.get('snippet',''), 'is_read': 0 if 'UNREAD' in labels else 1,
                        'labels': ','.join(labels), 'category': 'unchecked'
                    })
                except: pass
            if emails_data:
                save_emails(emails_data)
        except: pass
        return jsonify({'status': 'ok', 'restored': restored})
    except Exception as e:
        log_error(f"Undo failed: {e}")
        return jsonify({'error': str(e)}), 500

# ===== MULTI ACCOUNT =====
accounts = {}  # name -> token_file

@app.route('/api/accounts')
def api_accounts():
    import glob
    token_files = glob.glob(os.path.join(os.path.dirname(__file__), 'token_*.json'))
    accs = [{'name': os.path.basename(f).replace('token_','').replace('.json',''), 'file': f} for f in token_files]
    # add default
    default_token = os.path.join(os.path.dirname(__file__), 'token.json')
    if os.path.exists(default_token):
        accs.insert(0, {'name': 'Default', 'file': default_token})
    return jsonify(accs)

@app.route('/api/switch-account', methods=['POST'])
def api_switch_account():
    try:
        data = request.json
        token_file = data.get('token_file', 'token.json')
        import gmail_sync
        gmail_sync.TOKEN_FILE = token_file
        gmail_sync._service = None  # reset cached service
        return jsonify({'status': 'ok', 'message': f'Switched to account: {os.path.basename(token_file)}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-account')
def api_add_account():
    try:
        import gmail_sync
        from google_auth_oauthlib.flow import InstalledAppFlow
        SCOPES = ['https://mail.google.com/']
        flow = InstalledAppFlow.from_client_secrets_file(gmail_sync.CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        # save with unique name
        import uuid
        token_name = f'token_{uuid.uuid4().hex[:8]}.json'
        token_path = os.path.join(os.path.dirname(__file__), token_name)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        return jsonify({'status': 'ok', 'token_file': token_path, 'message': 'Account added!'})
    except Exception as e:
        log_error(f"Add account failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/error-log')
def api_error_log():
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                lines = f.readlines()
            return jsonify({'log': ''.join(lines[-50:])})
        return jsonify({'log': 'No errors logged.'})
    except:
        return jsonify({'log': 'Could not read log file.'})

if __name__ == '__main__':
    init_db()
    init_undo_table()
    print("Gmail Manager V1.0 - Starting...")
    print("Open browser at: http://localhost:5000")
    app.run(debug=False, port=5000)
