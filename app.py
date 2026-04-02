import os
import json
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import jwt
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, static_folder='.')
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretflaskkey_change_me')

# --- DATA STORAGE HELPER ---
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

# Initialize data file if not exists
if not os.path.exists(DATA_FILE):
    save_data(load_data())
else:
    # Ensure certificates key exists in legacy data
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

# --- PUBLIC ROUTES ---
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    data = load_data()
    return jsonify({
        "profile": data.get("profile", {}),
        "projects": data.get("projects", []),
        "skills": data.get("skills", []),
        "experiences": data.get("experiences", []),
        "certificates": data.get("certificates", [])
    })

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    req_data = request.json
    if not req_data or not req_data.get('name') or not req_data.get('email') or not req_data.get('message'):
        return jsonify({'message': 'Please enter all fields'}), 400
    
    data = load_data()
    new_message = {
        "_id": str(uuid.uuid4()),
        "name": req_data['name'],
        "email": req_data['email'],
        "message": req_data['message'],
        "createdAt": datetime.utcnow().isoformat()
    }
    data.setdefault('messages', []).append(new_message)
    save_data(data)
    return jsonify({'message': 'Message sent successfully!'})

# --- ADMIN AUTH ROUTES ---
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    req_data = request.json
    username = req_data.get('username')
    password = req_data.get('password')
    
    env_username = os.getenv('ADMIN_USERNAME', 'admin')
    env_password = os.getenv('ADMIN_PASSWORD', 'admin')
    
    # Also check data.json stored password (if changed via API)
    data = load_data()
    stored = data.get('admin_credentials', {})
    stored_user = stored.get('username', env_username)
    stored_pass = stored.get('password', env_password)

    if username == stored_user and password == stored_pass:
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

# --- ADMIN PROTECTED DATA ROUTES ---
@app.route('/api/admin/data', methods=['GET'])
@token_required
def get_admin_data():
    """Full data including message IDs for admin use."""
    data = load_data()
    return jsonify({
        "profile": data.get("profile", {}),
        "projects": data.get("projects", []),
        "skills": data.get("skills", []),
        "experiences": data.get("experiences", []),
        "certificates": data.get("certificates", []),
        "messages": data.get("messages", [])
    })

@app.route('/api/messages', methods=['GET'])
@token_required
def get_messages():
    data = load_data()
    return jsonify(data.get('messages', []))

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
    if 'profile' not in data:
        data['profile'] = {}
    for k, v in req_data.items():
        data['profile'][k] = v
    save_data(data)
    return jsonify(data['profile'])

# --- GENERIC COLLECTION ROUTES ---
VALID_COLLECTIONS = ['projects', 'skills', 'experiences', 'certificates']

@app.route('/api/<collection>', methods=['POST'])
@token_required
def add_item(collection):
    if collection not in VALID_COLLECTIONS:
        return jsonify({'message': 'Invalid collection'}), 400
    req_data = request.json
    req_data['_id'] = str(uuid.uuid4())
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
    data = load_data()
    items = data.get(collection, [])
    for i, item in enumerate(items):
        if item.get('_id') == item_id:
            req_data['_id'] = item_id
            req_data['createdAt'] = item.get('createdAt', datetime.utcnow().isoformat())
            req_data['updatedAt'] = datetime.utcnow().isoformat()
            items[i] = req_data
            data[collection] = items
            save_data(data)
            return jsonify(req_data)
    return jsonify({'message': 'Item not found'}), 404

@app.route('/api/<collection>/<item_id>', methods=['DELETE'])
@token_required
def delete_item(collection, item_id):
    if collection not in VALID_COLLECTIONS:
        return jsonify({'message': 'Invalid collection'}), 400
    data = load_data()
    items = data.get(collection, [])
    updated_items = [item for item in items if item.get('_id') != item_id]
    if len(items) == len(updated_items):
        return jsonify({'message': 'Item not found'}), 404
    data[collection] = updated_items
    save_data(data)
    return jsonify({'message': f'{collection[:-1].capitalize()} removed'})

if __name__ == '__main__':
    app.run(port=3000, debug=True)
