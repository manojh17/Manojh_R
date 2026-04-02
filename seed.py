import json
import os
from werkzeug.security import generate_password_hash

data = {
    "projects": [
        {
            "_id": "p1",
            "title": "AgriGPT – Agriculture Chatbot",
            "description": "Multilingual (Tamil/English) voice & text chatbot using Flask + Gemini API with local-first fallback, user profiles, and admin dashboard.",
            "image": "./assets/p1.png",
            "liveLink": "#",
            "sourceLink": "#"
        },
        {
            "_id": "p2",
            "title": "Trust User Recommendation System",
            "description": "ML pipeline for trust prediction among users, with Flask API and interactive UI for insights and recommendations.",
            "image": "./assets/p2.png",
            "liveLink": "https://trust-prediction-among-users-on.onrender.com",
            "sourceLink": "#"
        },
        {
            "_id": "p3",
            "title": "GTEC IT Department Website",
            "description": "A professional, responsive website for the Information Technology department at GTEC. Includes department overview, faculty profiles, labs, events, achievements, and contact details.",
            "image": "./assets/p3.png",
            "liveLink": "#",
            "sourceLink": "#"
        },
        {
            "_id": "p4",
            "title": "EMI Calculator (React)",
            "description": "Clean UX with charts and downloadable amortization reports.",
            "image": "./assets/p4.png",
            "liveLink": "https://emi-calci.vercel.app/",
            "sourceLink": "#"
        }
    ],
    "skills": [
        { "_id": "s1", "category": "Languages", "tags": ["Python", "JavaScript", "HTML", "CSS"] },
        { "_id": "s2", "category": "Frontend", "tags": ["React", "Responsive UI", "Charts", "Accessibility"] },
        { "_id": "s3", "category": "Backend", "tags": ["Flask", "Node & Express", "REST APIs", "Auth"] },
        { "_id": "s4", "category": "AI/ML & Data", "tags": ["GenAI (Gemini)", "OpenAI APIs", "Computer Vision", "Scikit-learn"] },
        { "_id": "s5", "category": "IoT", "tags": ["ESP32-CAM", "Arduino", "Serial/Cloud bridges", "Automation"] },
        { "_id": "s6", "category": "Tools", "tags": ["Git & GitHub", "Render", "Vercel", "PythonAnywhere"] }
    ],
    "experiences": [
        {
            "_id": "e1",
            "role": "Web Development Intern",
            "company": "Joy Innovations Pvt. Ltd. (Vellore)",
            "duration": "Jul 2024 – Aug 2024",
            "description": "Started My first step on career on Web development @joy innovations , Where i learned About webdevelopmnt and some Industrial stuffs."
        }
    ],
    "messages": []
}

# Preserve messages if exists
if os.path.exists('data.json'):
    with open('data.json', 'r') as f:
        existing_data = json.load(f)
        data['messages'] = existing_data.get('messages', [])
        data['admin'] = existing_data.get('admin', {"username": "admin", "password": generate_password_hash("password")})
else:
    data['admin'] = {"username": "admin", "password": generate_password_hash("password")}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
    
print("Data seeded successfully!")
