from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient
from bson import ObjectId
import os
import random
import json
import time
import traceback

# Get the absolute path to the directory containing this file
basedir = os.path.abspath(os.path.dirname(__file__))

# Initialize Flask app with explicit template folder path
app = Flask(__name__, 
            template_folder=os.path.join(basedir, 'templates'),
            static_folder=os.path.join(basedir, 'static'))

# Set a secret key for session
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

# Print debug info about directories
print(f"Current directory: {os.getcwd()}")
print(f"Base directory: {basedir}")
print(f"Template folder: {os.path.join(basedir, 'templates')}")
print(f"Static folder: {os.path.join(basedir, 'static')}")

# Initialize MongoDB connection variables at module level
client = None
db = None
collection = None

# Connect to MongoDB with robust retry logic
def connect_to_mongodb():
    global client, db, collection  # Use global to modify these variables
    
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("ERROR: MONGO_URI environment variable is not set")
        return False
    
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"MongoDB connection attempt {attempt+1}/{max_retries}")
            client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=30000,
                socketTimeoutMS=45000,
                maxPoolSize=1
            )
            # Force a connection to verify it's working
            client.admin.command('ping')
            print("MongoDB connection successful!")
            db = client['WordInfo']
            collection = db['Phonograms']
            
            # Verify collection access
            print(f"Checking collection access. Collection type: {type(collection)}")
            test_find = collection.find_one()
            print(f"Test find result type: {type(test_find)}")
            
            return True
        except Exception as e:
            print(f"MongoDB connection error on attempt {attempt+1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("All connection attempts failed.")
                return False

# Try to connect to MongoDB at startup
mongodb_connected = connect_to_mongodb()

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

def get_phonogram_data(phonogram_list):
    """Helper function to get phonogram data from MongoDB"""
    global collection
    if collection is None:
        print("Collection is None, attempting to reconnect...")
        if not connect_to_mongodb():
            print("Failed to reconnect to MongoDB")
            return []
    
    try:
        phonogram_data = list(collection.find({"phonogram": {"$in": phonogram_list}}))
        print(f"Found {len(phonogram_data)} phonograms from list of {len(phonogram_list)}")
        return phonogram_data
    except Exception as e:
        print(f"Error fetching phonogram data: {e}")
        return []

@app.route('/')
def home():
    """
    Fetch phonograms grouped by lessons and render the home page.
    """
    try:
        # Ensure we have a MongoDB connection
        global collection
        if collection is None and not connect_to_mongodb():
            return "Database connection is currently unavailable. Please try again later.", 503
        
        lessons = []
        # Iterate through the predefined lesson structure
        for lesson_data in lessons_structure:
            try:
                lesson_number = lesson_data['lesson']
                phonograms = lesson_data['phonograms']
                
                print(f"Processing lesson {lesson_number} with phonograms: {phonograms}")
                
                # Fetch phonograms from MongoDB that match the current lesson's phonograms
                phonogram_data = get_phonogram_data(phonograms)
                
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
                print(f"Successfully processed lesson {lesson_number} with {len(lesson_phonograms)} phonograms")
                
            except Exception as e:
                print(f"Error processing lesson {lesson_data['lesson']}: {e}")
                traceback.print_exc()
                
        return render_template('index.html', lessons=lessons)
    
    except Exception as e:
        print(f"Error in home route: {e}")
        traceback.print_exc()
        return "An unexpected error occurred. Please try again later.", 500

@app.route('/start-session', methods=['POST'])
def start_session():
    """
    Start a session with selected phonograms and optional randomization.
    """
    try:
        # Ensure we have a MongoDB connection
        global collection
        if collection is None and not connect_to_mongodb():
            return jsonify({"error": "Database connection is currently unavailable."}), 503
                
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
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/session')
def session_view():
    """
    Render the session page with the selected phonograms.
    """
    try:
        phonograms = session.get('phonograms', [])
        
        if not phonograms:
            return "No phonograms selected for this session. <a href='/'>Return to home</a>", 400
            
        return render_template('session.html', phonograms=phonograms)
        
    except Exception as e:
        print(f"Error in session view: {e}")
        traceback.print_exc()
        return "An error occurred while loading the session. Please go back and try again.", 500

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
