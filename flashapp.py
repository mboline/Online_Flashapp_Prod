import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import os
import random
import json

# Load environment variables
load_dotenv()

# Get the absolute path to the directory containing this file
basedir = os.path.abspath(os.path.dirname(__file__))

# Initialize Flask app with explicit template folder path
app = Flask(__name__, 
            template_folder=os.path.join(basedir, 'templates'),
            static_folder=os.path.join(basedir, 'static'))

# Set a secret key for session
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

# Connect to MongoDB using environment variables
""" mongo_uri = os.environ.get("MONGO_URI")  # MongoDB connection string
if not mongo_uri:
    raise ValueError("MONGO_URI is not set in the environment variables.")
client = MongoClient(mongo_uri)
db = client['WordInfo']
collection = db['Phonograms'] """

mongo_uri = os.environ.get("MONGO_URI")
if not mongo_uri:
    raise ValueError("MONGO_URI is not set in the environment variables.")

# More robust connection handling
max_retries = 3
retry_delay = 2  # seconds
for attempt in range(max_retries):
    try:
        print(f"MongoDB connection attempt {attempt+1}/{max_retries}")
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000
        )
        # Force a connection to verify it's working
        client.admin.command('ping')
        print("MongoDB connection successful!")
        db = client['WordInfo']
        collection = db['Phonograms']
        break  # Connection successful, exit the retry loop
    except Exception as e:
        print(f"MongoDB connection error on attempt {attempt+1}: {e}")
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        else:
            print("All connection attempts failed.")
            # Consider using a fallback or mock data for development/testing
            # Or re-raise the exception if you want to fail the application startup
            raise

# Add debugging for template path
print(f"Current directory: {os.getcwd()}")
print(f"Template folder: {app.template_folder}")
print(f"Does template folder exist: {os.path.exists(app.template_folder)}")
print(f"Template path: {os.path.join(app.template_folder, 'index.html')}")
print(f"Does template exist: {os.path.exists(os.path.join(app.template_folder, 'index.html'))}")

# Predefined lesson structure
lessons_structure = [
    {'lesson': 1, 'phonograms': ['a', 'c', 'd', 'f']},
    {'lesson': 2, 'phonograms': ['g', 'o', 's', 'qu']},
    {'lesson': 3, 'phonograms': ['b', 'e', 'h', 'i']},
    {'lesson': 4, 'phonograms': ['j', 'k', 'l', 'm']},
    {'lesson': 5, 'phonograms': ['n', 'p', 'r', 't']},
    {'lesson': 6, 'phonograms': ['u', 'v', 'w', 'x']},
    {'lesson': 7, 'phonograms': ['y', 'z']},
    {'lesson': 8, 'phonograms': ['er', 'ir', 'ur', 'wor', 'ear']},
    {'lesson': 9, 'phonograms': ['sh', 'th', 'ee']},
    {'lesson': 10, 'phonograms': ['ay', 'ai', 'ow', 'ou']},
    {'lesson': 11, 'phonograms': ['aw', 'au', 'ew', 'ui']},
    {'lesson': 12, 'phonograms': ['oy', 'oi', 'oo', 'ch']},
    {'lesson': 13, 'phonograms': ['ng', 'ea', 'ar', 'ck']},
    {'lesson': 14, 'phonograms': ['ed', 'or', 'wh', 'oa']},
    {'lesson': 15, 'phonograms': ['ey', 'eigh', 'ei', 'igh']},
    {'lesson': 16, 'phonograms': ['ie', 'kn', 'gn', 'wr']},
    {'lesson': 17, 'phonograms': ['ph', 'dge', 'oe', 'tch']},
    {'lesson': 18, 'phonograms': ['ti', 'si', 'ci', 'ough']}
]

@app.route('/')
def home():
    """
    Fetch phonograms grouped by lessons and render the home page.
    """
    lessons = []

    # Iterate through the predefined lesson structure
    for lesson_data in lessons_structure:
        lesson_number = lesson_data['lesson']
        phonograms = lesson_data['phonograms']

        # Fetch phonograms from MongoDB that match the current lesson's phonograms
        phonogram_data = list(collection.find({"phonogram": {"$in": phonograms}}))

        # Create a dictionary to map phonograms to their data for easy sorting
        phonogram_map = {p['phonogram']: p for p in phonogram_data}

        # Sort the phonograms based on the order in the lessons_structure array
        lesson_phonograms = []
        for phonogram in phonograms:
            if phonogram in phonogram_map:
                lesson_phonograms.append({
                    "phonogram": phonogram,
                    "audio_url": phonogram_map[phonogram].get("phonogram_url", ""),
                    "image_url": phonogram_map[phonogram].get("phonogram_png", "")
                })

        # Add the lesson and its phonograms to the lessons list
        lessons.append({
            "lesson": lesson_number,
            "phonograms": lesson_phonograms
        })

    return render_template('index.html', lessons=lessons)

@app.route('/start-session', methods=['POST'])
def start_session():
    """
    Start a session with selected phonograms and optional randomization.
    """
    try:
        # Get selected phonograms and randomization preference
        selected_phonograms = request.json.get('selected_phonograms', [])
        randomize = request.json.get('randomize', False)

        print("Selected Phonograms:", selected_phonograms)
        print("Randomize:", randomize)

        # Validate input
        if not selected_phonograms:
            print("Error: No phonograms selected.")
            return jsonify({"error": "No phonograms selected."}), 400

        # Fetch phonograms from MongoDB in the order they appear in selected_phonograms
        phonograms = []
        for index, phonogram_id in enumerate(selected_phonograms):
            result = collection.find_one({"phonogram": phonogram_id})
            if result:
                # Convert ObjectId to string
                result['_id'] = str(result['_id'])
                # Store the original position (1-based) before any randomization
                original_position = index + 1
                phonograms.append({
                    "phonogram": result.get("phonogram", ""),
                    "audio_url": result.get("phonogram_url", ""),
                    "image_url": result.get("phonogram_png", ""),
                    "original_position": original_position
                })

        print("Fetched Phonograms (ordered):", phonograms)

        # Only randomize if specifically requested
        if randomize and phonograms:
            phonograms = random.sample(phonograms, len(phonograms))
            print("Randomized Phonograms:", phonograms)

        # Store in Flask session
        session['phonograms'] = phonograms
        
        return jsonify({"success": True, "redirect": "/session"})
    
    except Exception as e:
        print(f"Error in /start-session: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/session')
def session_view():
    """
    Render the session page with the selected phonograms.
    """
    phonograms = session.get('phonograms', [])
    
    if not phonograms:
        return "No phonograms selected for this session. <a href='/'>Return to home</a>", 400

    return render_template('session.html', phonograms=phonograms)

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
