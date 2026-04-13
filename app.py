import os
import json
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, Response, make_response
from flask_cors import CORS
import jwt
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()

SITE_URL = os.getenv('SITE_URL', 'https://manojh.online')

app = Flask(__name__)  # Flask will automatically use templates/ and static/ folders
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretflaskkey_change_me')

# ─────────────────────────────────────────
# MONGODB CONNECTION
# ─────────────────────────────────────────
MONGO_URI = os.getenv('MONGO_URI', '')

if not MONGO_URI or '<password>' in MONGO_URI:
    raise RuntimeError(
        "\n\n❌  MONGO_URI is not set or still contains the placeholder.\n"
        "    Please update .env with your real MongoDB Atlas connection string.\n"
        "    Example: MONGO_URI=mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/manojh_portfolio\n"
    )

client = MongoClient(MONGO_URI)
db = client.get_default_database()   # uses the DB name in the URI

# Collection handles
col_profile      = db['profile']
col_projects     = db['projects']
col_skills       = db['skills']
col_experiences  = db['experiences']
col_certificates = db['certificates']
col_messages     = db['messages']
col_admin        = db['admin_credentials']

# Map collection name → handle (for generic CRUD routes)
COLLECTIONS = {
    'projects':     col_projects,
    'skills':       col_skills,
    'experiences':  col_experiences,
    'certificates': col_certificates,
}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def _clean(doc):
    """Remove MongoDB internal _id (ObjectId) and return plain dict."""
    if doc is None:
        return None
    doc.pop('_id', None)  # drop ObjectId; we use our own string 'id' field
    return doc

def _clean_list(docs):
    return [_clean(d) for d in docs]


# ─────────────────────────────────────────
# ONE-TIME DATA SEEDER  (runs on startup)
# Seeds data.json → MongoDB if collections are empty.
# ─────────────────────────────────────────
DATA_FILE = 'data.json'

def _seed_from_json():
    if not os.path.exists(DATA_FILE):
        return

    print("🌱  Checking if seed from data.json is needed …")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    seeded = False

    # Profile (stored as a single document with field 'singleton': True)
    if col_profile.count_documents({}) == 0 and data.get('profile'):
        profile = dict(data['profile'])
        profile['singleton'] = True
        col_profile.insert_one(profile)
        print("   ✅  profile seeded")
        seeded = True

    # Collections
    for key, col in COLLECTIONS.items():
        if col.count_documents({}) == 0 and data.get(key):
            col.insert_many([dict(item) for item in data[key]])
            print(f"   ✅  {key} seeded ({len(data[key])} docs)")
            seeded = True

    # Messages
    if col_messages.count_documents({}) == 0 and data.get('messages'):
        col_messages.insert_many([dict(m) for m in data['messages']])
        print(f"   ✅  messages seeded ({len(data['messages'])} docs)")
        seeded = True

    # Admin credentials
    if col_admin.count_documents({}) == 0:
        stored = data.get('admin_credentials', {})
        col_admin.insert_one({
            'singleton': True,
            'username': stored.get('username', os.getenv('ADMIN_USERNAME', 'admin')),
            'password': stored.get('password', os.getenv('ADMIN_PASSWORD', 'admin')),
        })
        print("   ✅  admin_credentials seeded")
        seeded = True

    if seeded:
        print("🌱  Seed complete. You can safely delete data.json if desired.\n")
    else:
        print("🌱  MongoDB already has data — skipping seed.\n")

_seed_from_json()


# ─────────────────────────────────────────
# AUTH MIDDLEWARE
# ─────────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'No token, authorization denied'}), 401
        try:
            token = token.split(' ')[1] if ' ' in token else token
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except Exception:
            return jsonify({'message': 'Token is not valid'}), 401
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────
# SEO HEADERS
# ─────────────────────────────────────────
@app.after_request
def add_seo_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.path in ('/', '/projects'):
        # HTML pages: allow caching for a short time, always revalidate
        response.headers['Cache-Control'] = 'public, max-age=3600, must-revalidate'
        response.headers['X-Robots-Tag'] = 'index, follow'
    elif request.path in ('/robots.txt', '/sitemap.xml'):
        response.headers['X-Robots-Tag'] = 'noindex'
    return response


# ─────────────────────────────────────────
# ROBOTS.TXT & SITEMAP.XML
# ─────────────────────────────────────────
@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')


@app.route('/sitemap.xml')
def sitemap():
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    static_pages = [
        {'url': f'{SITE_URL}/', 'priority': '1.0', 'changefreq': 'weekly'},
        {'url': f'{SITE_URL}/projects', 'priority': '0.9', 'changefreq': 'weekly'},
    ]
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        ' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
        ' xmlns:xhtml="http://www.w3.org/1999/xhtml">'
    )
    for i, page in enumerate(static_pages):
        img_block = ''
        if i == 0:  # Homepage: include profile image for Google Images
            img_block = f'''
    <image:image>
      <image:loc>{SITE_URL}/static/assets/dp.JPG</image:loc>
      <image:title>Manojh R – Full-Stack Developer &amp; AI/ML Engineer</image:title>
      <image:caption>Portfolio photo of Manojh R, Full-Stack Web Developer and AI/ML Engineer from Tamil Nadu, India</image:caption>
    </image:image>'''
        xml_parts.append(f'''
  <url>
    <loc>{page["url"]}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{page["changefreq"]}</changefreq>
    <priority>{page["priority"]}</priority>{img_block}
  </url>''')
    xml_parts.append('\n</urlset>')
    response = make_response(''.join(xml_parts))
    response.headers['Content-Type'] = 'application/xml; charset=utf-8'
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


# ─────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/projects')
def projects():
    return render_template('projects.html')


@app.route('/admin/')
@app.route('/admin/me.html')
def admin():
    return render_template('admin/index.html')


# ─────────────────────────────────────────
# PUBLIC API ROUTES
# ─────────────────────────────────────────
@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    profile = _clean(col_profile.find_one({'singleton': True}))
    if profile:
        profile.pop('singleton', None)

    return jsonify({
        "profile":      profile or {},
        "projects":     _clean_list(col_projects.find()),
        "skills":       _clean_list(col_skills.find()),
        "experiences":  _clean_list(col_experiences.find()),
        "certificates": _clean_list(col_certificates.find()),
    })


@app.route('/api/contact', methods=['POST'])
def submit_contact():
    req_data = request.json
    if not req_data or not req_data.get('name') or not req_data.get('email') or not req_data.get('message'):
        return jsonify({'message': 'Please enter all fields'}), 400

    col_messages.insert_one({
        "id":        str(uuid.uuid4()),
        "name":      req_data['name'],
        "email":     req_data['email'],
        "message":   req_data['message'],
        "createdAt": datetime.utcnow().isoformat(),
    })
    return jsonify({'message': 'Message sent successfully!'})


# ─────────────────────────────────────────
# ADMIN AUTH
# ─────────────────────────────────────────
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    req_data = request.json
    username = req_data.get('username')
    password = req_data.get('password')

    creds = col_admin.find_one({'singleton': True})
    valid_user = creds.get('username', os.getenv('ADMIN_USERNAME', 'admin')) if creds else os.getenv('ADMIN_USERNAME', 'admin')
    valid_pass = creds.get('password', os.getenv('ADMIN_PASSWORD', 'admin')) if creds else os.getenv('ADMIN_PASSWORD', 'admin')

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

    col_admin.update_one(
        {'singleton': True},
        {'$set': {'username': new_username, 'password': new_password}},
        upsert=True
    )
    return jsonify({'message': 'Credentials updated successfully'})


# ─────────────────────────────────────────
# ADMIN DATA API (protected)
# ─────────────────────────────────────────
@app.route('/api/admin/data', methods=['GET'])
@token_required
def get_admin_data():
    profile = _clean(col_profile.find_one({'singleton': True}))
    if profile:
        profile.pop('singleton', None)

    messages = _clean_list(col_messages.find())
    # normalise: old messages used '_id' string field; new ones use 'id'
    for m in messages:
        if 'id' not in m and '_id' in m:
            m['id'] = m.pop('_id')

    return jsonify({
        "profile":      profile or {},
        "projects":     _clean_list(col_projects.find()),
        "skills":       _clean_list(col_skills.find()),
        "experiences":  _clean_list(col_experiences.find()),
        "certificates": _clean_list(col_certificates.find()),
        "messages":     messages,
    })


@app.route('/api/messages', methods=['GET'])
@token_required
def get_messages():
    messages = _clean_list(col_messages.find())
    for m in messages:
        if 'id' not in m and '_id' in m:
            m['id'] = m.pop('_id')
    return jsonify(messages)


@app.route('/api/messages/<msg_id>', methods=['DELETE'])
@token_required
def delete_message(msg_id):
    # Support both old '_id' string field and new 'id' field
    result = col_messages.delete_one({'$or': [{'id': msg_id}, {'_id': msg_id}]})
    if result.deleted_count == 0:
        return jsonify({'message': 'Message not found'}), 404
    return jsonify({'message': 'Message deleted'})


@app.route('/api/profile', methods=['PUT'])
@token_required
def update_profile():
    req_data = request.json
    req_data.pop('_id', None)
    req_data.pop('singleton', None)

    col_profile.update_one(
        {'singleton': True},
        {'$set': req_data},
        upsert=True
    )
    profile = _clean(col_profile.find_one({'singleton': True}))
    profile.pop('singleton', None)
    return jsonify(profile)


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
    string_id             = str(uuid.uuid4())
    req_data['_id']       = string_id
    req_data['createdAt'] = datetime.utcnow().isoformat()

    # pymongo will overwrite req_data['_id'] with ObjectId after insert_one,
    # so we query back using the string ID we stored in the document.
    COLLECTIONS[collection].insert_one(req_data)
    doc = _clean(COLLECTIONS[collection].find_one({'_id': string_id})) or {}
    doc.setdefault('_id', string_id)
    return jsonify(doc), 201


@app.route('/api/<collection>/<item_id>', methods=['PUT'])
@token_required
def update_item(collection, item_id):
    if collection not in VALID_COLLECTIONS:
        return jsonify({'message': 'Invalid collection'}), 400

    req_data = request.json
    req_data.pop('_id', None)

    col = COLLECTIONS[collection]
    existing = col.find_one({'_id': item_id})
    if not existing:
        return jsonify({'message': 'Item not found'}), 404

    req_data['_id']       = item_id
    req_data['createdAt'] = existing.get('createdAt', datetime.utcnow().isoformat())
    req_data['updatedAt'] = datetime.utcnow().isoformat()

    col.replace_one({'_id': item_id}, req_data)
    return jsonify(_clean(col.find_one({'_id': item_id})))


@app.route('/api/<collection>/<item_id>', methods=['DELETE'])
@token_required
def delete_item(collection, item_id):
    if collection not in VALID_COLLECTIONS:
        return jsonify({'message': 'Invalid collection'}), 400

    result = COLLECTIONS[collection].delete_one({'_id': item_id})
    if result.deleted_count == 0:
        return jsonify({'message': 'Item not found'}), 404
    return jsonify({'message': f'{collection[:-1].capitalize()} removed'})


if __name__ == '__main__':
    app.run(port=3000, debug=True)
