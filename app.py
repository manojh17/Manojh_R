import os
import json
import uuid
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, Response, make_response
from flask_cors import CORS
import jwt
from dotenv import load_dotenv

load_dotenv()

SITE_URL = os.getenv('SITE_URL', 'https://manojh.online')

app = Flask(__name__)  # Flask will automatically use templates/ and static/ folders
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretflaskkey_change_me')

# --- DATA STORAGE ---
DATA_FILE = 'data.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "profile": {},
            "projects": [],
            "skills": [],
            "experiences": [],
            "certificates": [],
            "messages": []
        }
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Initialize / migrate data file
if not os.path.exists(DATA_FILE):
    save_data(load_data())
else:
    d = load_data()
    changed = False
    if 'certificates' not in d:
        d['certificates'] = []
        changed = True
    if changed:
        save_data(d)

# --- AUTH MIDDLEWARE ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'No token, authorization denied'}), 401
        try:
            token = token.split(' ')[1] if ' ' in token else token
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return jsonify({'message': 'Token is not valid'}), 401
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
# SEO HEADERS (after every response)
# ─────────────────────────────────────────
@app.after_request
def add_seo_headers(response):
    # Security headers (Google uses HTTPS/security as ranking signal)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Cache static assets aggressively for performance (Core Web Vitals)
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response

# ─────────────────────────────────────────
# ROBOTS.TXT & SITEMAP.XML
# ─────────────────────────────────────────
@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    """Dynamically generate sitemap.xml so Google always gets fresh URLs."""
    data = load_data()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Static pages
    static_pages = [
        {'url': f'{SITE_URL}/', 'priority': '1.0', 'changefreq': 'weekly'},
        {'url': f'{SITE_URL}/projects', 'priority': '0.9', 'changefreq': 'weekly'},
    ]

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page in static_pages:
        xml_parts.append(f'''
  <url>
    <loc>{page["url"]}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{page["changefreq"]}</changefreq>
    <priority>{page["priority"]}</priority>
  </url>''')

    xml_parts.append('\n</urlset>')
    xml_content = ''.join(xml_parts)

    response = make_response(xml_content)
    response.headers['Content-Type'] = 'application/xml; charset=utf-8'
    response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache 1 day
    return response

# ─────────────────────────────────────────
# PAGE ROUTES (render Jinja2 templates)
# ─────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/admin/')
@app.route('/admin/me.html')   # backwards-compat with old onclick link
def admin():
    return render_template('admin/index.html')

# ─────────────────────────────────────────
# PUBLIC API ROUTES
# ─────────────────────────────────────────
@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    data = load_data()
    return jsonify({
        "profile":      data.get("profile", {}),
        "projects":     data.get("projects", []),
        "skills":       data.get("skills", []),
        "experiences":  data.get("experiences", []),
        "certificates": data.get("certificates", [])
    })

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    req_data = request.json
    if not req_data or not req_data.get('name') or not req_data.get('email') or not req_data.get('message'):
        return jsonify({'message': 'Please enter all fields'}), 400
    data = load_data()
    data.setdefault('messages', []).append({
        "_id":       str(uuid.uuid4()),
        "name":      req_data['name'],
        "email":     req_data['email'],
        "message":   req_data['message'],
        "createdAt": datetime.utcnow().isoformat()
    })
    save_data(data)
    return jsonify({'message': 'Message sent successfully!'})

# ─────────────────────────────────────────
# ADMIN AUTH
# ─────────────────────────────────────────
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    req_data = request.json
    username = req_data.get('username')
    password = req_data.get('password')

    # Check data.json-stored credentials first (set via change-password), fall back to .env
    data = load_data()
    stored = data.get('admin_credentials', {})
    valid_user = stored.get('username', os.getenv('ADMIN_USERNAME', 'admin'))
    valid_pass = stored.get('password', os.getenv('ADMIN_PASSWORD', 'admin'))

    if username == valid_user and password == valid_pass:
        token = jwt.encode({'user': username}, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid Credentials'}), 400

@app.route('/api/admin/change-password', methods=['PUT'])
@token_required
def change_password():
    req_data = request.json
    new_username = req_data.get('username')
    new_password = req_data.get('password')
    if not new_username or not new_password:
        return jsonify({'message': 'Username and password required'}), 400
    data = load_data()
    data['admin_credentials'] = {'username': new_username, 'password': new_password}
    save_data(data)
    return jsonify({'message': 'Credentials updated successfully'})

# ─────────────────────────────────────────
# ADMIN DATA API (protected)
# ─────────────────────────────────────────
@app.route('/api/admin/data', methods=['GET'])
@token_required
def get_admin_data():
    data = load_data()
    return jsonify({
        "profile":      data.get("profile", {}),
        "projects":     data.get("projects", []),
        "skills":       data.get("skills", []),
        "experiences":  data.get("experiences", []),
        "certificates": data.get("certificates", []),
        "messages":     data.get("messages", [])
    })

@app.route('/api/messages', methods=['GET'])
@token_required
def get_messages():
    return jsonify(load_data().get('messages', []))

@app.route('/api/messages/<msg_id>', methods=['DELETE'])
@token_required
def delete_message(msg_id):
    data = load_data()
    messages = data.get('messages', [])
    updated = [m for m in messages if m.get('_id') != msg_id]
    if len(messages) == len(updated):
        return jsonify({'message': 'Message not found'}), 404
    data['messages'] = updated
    save_data(data)
    return jsonify({'message': 'Message deleted'})

@app.route('/api/profile', methods=['PUT'])
@token_required
def update_profile():
    req_data = request.json
    data = load_data()
    data.setdefault('profile', {}).update(req_data)
    save_data(data)
    return jsonify(data['profile'])

# ─────────────────────────────────────────
# GENERIC COLLECTION CRUD (protected)
# ─────────────────────────────────────────
VALID_COLLECTIONS = ['projects', 'skills', 'experiences', 'certificates']

@app.route('/api/<collection>', methods=['POST'])
@token_required
def add_item(collection):
    if collection not in VALID_COLLECTIONS:
        return jsonify({'message': 'Invalid collection'}), 400
    req_data = request.json
    req_data['_id']       = str(uuid.uuid4())
    req_data['createdAt'] = datetime.utcnow().isoformat()
    data = load_data()
    data.setdefault(collection, []).append(req_data)
    save_data(data)
    return jsonify(req_data), 201

@app.route('/api/<collection>/<item_id>', methods=['PUT'])
@token_required
def update_item(collection, item_id):
    if collection not in VALID_COLLECTIONS:
        return jsonify({'message': 'Invalid collection'}), 400
    req_data = request.json
    data  = load_data()
    items = data.get(collection, [])
    for i, item in enumerate(items):
        if item.get('_id') == item_id:
            req_data['_id']       = item_id
            req_data['createdAt'] = item.get('createdAt', datetime.utcnow().isoformat())
            req_data['updatedAt'] = datetime.utcnow().isoformat()
            items[i]              = req_data
            data[collection]      = items
            save_data(data)
            return jsonify(req_data)
    return jsonify({'message': 'Item not found'}), 404

@app.route('/api/<collection>/<item_id>', methods=['DELETE'])
@token_required
def delete_item(collection, item_id):
    if collection not in VALID_COLLECTIONS:
        return jsonify({'message': 'Invalid collection'}), 400
    data    = load_data()
    items   = data.get(collection, [])
    updated = [item for item in items if item.get('_id') != item_id]
    if len(items) == len(updated):
        return jsonify({'message': 'Item not found'}), 404
    data[collection] = updated
    save_data(data)
    return jsonify({'message': f'{collection[:-1].capitalize()} removed'})

if __name__ == '__main__':
    app.run(port=3000, debug=True)
