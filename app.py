from flask import Flask, request, jsonify, render_template, g
import requests
from dotenv import load_dotenv
import os
import logging
import sqlite3
from datetime import datetime
import traceback

app = Flask(__name__)

# Load environment variables
load_dotenv()
API_KEY = 'c3cd0b3e22e4080082a35b80adbe8f1f'

# Database configuration
if 'RENDER' in os.environ:
    DATABASE = '/data/weather_app.db'
else:
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weather_app.db')

# API endpoints
GEOCODING_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct"
REVERSE_GEOCODING_URL = "http://api.openweathermap.org/geo/1.0/reverse"
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
AIR_POLLUTION_BASE_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = dict_factory
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    try:
        # Create data directory if on Render
        if 'RENDER' in os.environ:
            os.makedirs('/data', exist_ok=True)
            
        logger.debug(f"Initializing database at {DATABASE}")
        with app.app_context():
            db = get_db()
            with app.open_resource('schema.sql', mode='r') as f:
                script = f.read()
                logger.debug(f"Executing SQL script: {script}")
                db.executescript(script)
            db.commit()
            logger.debug("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def init_challenges():
    db = get_db()
    challenges = [
        {
            'title': 'Weather Novice',
            'description': 'Get started with basic weather tracking',
            'difficulty': 'Easy',
            'category': 'Basics',
            'points': 100,
            'requirements': 'Complete first weather search',
            'track': 'Getting Started'
        },
        {
            'title': 'City Explorer',
            'description': 'Search weather in 3 different cities',
            'difficulty': 'Easy',
            'category': 'Search',
            'points': 200,
            'requirements': '3 unique cities',
            'track': 'Getting Started'
        },
        {
            'title': 'Weather Patterns',
            'description': 'Find cities with 3 different weather conditions',
            'difficulty': 'Medium',
            'category': 'Weather',
            'points': 300,
            'requirements': '3 unique conditions',
            'track': 'Weather Expert'
        },
        {
            'title': 'Global Navigator',
            'description': 'Check weather in 3 different continents',
            'difficulty': 'Medium',
            'category': 'Geography',
            'points': 400,
            'requirements': '3 continents',
            'track': 'Weather Expert'
        },
        {
            'title': 'Weather Master',
            'description': 'Complete all challenges in the Weather Expert track',
            'difficulty': 'Hard',
            'category': 'Achievement',
            'points': 500,
            'requirements': 'All previous challenges',
            'track': 'Weather Expert'
        }
    ]
    
    for challenge in challenges:
        db.execute('''
            INSERT OR IGNORE INTO weather_challenges 
            (title, description, difficulty, category, points, requirements, track)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            challenge['title'],
            challenge['description'],
            challenge['difficulty'],
            challenge['category'],
            challenge['points'],
            challenge['requirements'],
            challenge['track']
        ))
    db.commit()

@app.teardown_appcontext
def teardown_db(exception):
    close_db()

# Initialize database on app startup
@app.before_first_request
def initialize_database():
    if not os.path.exists(DATABASE):
        init_db()
        init_challenges()

def get_location_details(city):
    try:
        logger.debug(f"Attempting to fetch location details for {city}")
        params = {
            'q': city,
            'limit': 5,
            'appid': API_KEY
        }
        logger.debug(f"Making request to {GEOCODING_BASE_URL} with params: {params}")
        
        response = requests.get(
            GEOCODING_BASE_URL,
            params=params,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            },
            timeout=10
        )
        
        logger.debug(f"Response status: {response.status_code}")
        
        if response.status_code == 401:
            logger.error(f"API Key error. Status: {response.status_code}, Response: {response.text}")
            return None, "Invalid API key. Please check your configuration."
            
        response.raise_for_status()
        locations = response.json()
        
        if not locations:
            logger.info(f"No locations found for: {city}")
            return None, "Location not found. Please try a different search term."
        
        location_list = []
        for loc in locations:
            location_info = {
                'name': loc.get('name', ''),
                'local_names': loc.get('local_names', {}),
                'lat': loc.get('lat'),
                'lon': loc.get('lon'),
                'country': loc.get('country', ''),
                'state': loc.get('state', ''),
            }
            location_list.append(location_info)
        
        logger.info(f"Found {len(location_list)} locations")
        return location_list, None
        
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching location data")
        return None, "Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching location data: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error connecting to weather service: {str(e)}"

def get_location_from_coordinates(lat, lon):
    try:
        logger.debug(f"Attempting to fetch location details from coordinates ({lat}, {lon})")
        params = {
            'lat': lat,
            'lon': lon,
            'limit': 1,
            'appid': API_KEY
        }
        
        response = requests.get(
            REVERSE_GEOCODING_URL,
            params=params,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            },
            timeout=10
        )
        
        if response.status_code == 401:
            logger.error(f"API Key error. Status: {response.status_code}, Response: {response.text}")
            return None, "Invalid API key"
            
        response.raise_for_status()
        locations = response.json()
        
        if locations:
            location = locations[0]
            return {
                'name': location.get('name', ''),
                'lat': lat,
                'lon': lon,
                'country': location.get('country', ''),
                'state': location.get('state', '')
            }, None
        
        return None, "Location not found"
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in reverse geocoding: {str(e)}")
        logger.error(traceback.format_exc())
        return None, str(e)

def get_weather_data(lat, lon):
    try:
        logger.debug(f"Attempting to fetch weather data for ({lat}, {lon})")
        params = {
            'lat': lat,
            'lon': lon,
            'appid': API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(
            WEATHER_BASE_URL,
            params=params,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            },
            timeout=10
        )
        
        if response.status_code == 401:
            logger.error(f"API Key error. Status: {response.status_code}, Response: {response.text}")
            return None, "Invalid API key. Please check your configuration."
            
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching weather data")
        return None, "Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error connecting to weather service: {str(e)}"

def get_air_quality(lat, lon):
    try:
        logger.debug(f"Attempting to fetch air quality data for ({lat}, {lon})")
        params = {
            'lat': lat,
            'lon': lon,
            'appid': API_KEY
        }
        
        response = requests.get(
            AIR_POLLUTION_BASE_URL,
            params=params,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            },
            timeout=10
        )
        
        if response.status_code == 401:
            logger.error(f"API Key error. Status: {response.status_code}, Response: {response.text}")
            return None, "Invalid API key. Please check your configuration."
            
        response.raise_for_status()
        data = response.json()
        
        if 'list' in data and len(data['list']) > 0:
            air_data = data['list'][0]
            aqi = air_data['main']['aqi']
            components = air_data['components']
            
            aqi_labels = {
                1: "Good",
                2: "Fair",
                3: "Moderate",
                4: "Poor",
                5: "Very Poor"
            }
            
            return {
                'aqi': aqi,
                'aqi_label': aqi_labels.get(aqi, "Unknown"),
                'components': components
            }, None
        return None, "No air quality data available for this location."
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching air quality data")
        return None, "Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching air quality data: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error connecting to weather service: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/weather', methods=['POST'])
def get_weather():
    try:
        logger.debug("Attempting to fetch weather data")
        data = request.get_json()
        logger.debug(f"Received weather request data: {data}")
        
        city = data.get('city')
        lat = data.get('lat')
        lon = data.get('lon')
        
        if not city and (lat is None or lon is None):
            logger.error("Missing required fields")
            return jsonify({'error': 'Please provide either a city name or coordinates'}), 400
        
        if lat is not None and lon is not None:
            # Get location details from coordinates
            location_info, error = get_location_from_coordinates(lat, lon)
            if error:
                return jsonify({'error': error}), 500
            locations = [location_info]
        else:
            # Get location details from city name
            locations, error = get_location_details(city)
            if error:
                return jsonify({'error': error}), 404 if "not found" in error.lower() else 500
        
        first_location = locations[0]
        lat, lon = first_location['lat'], first_location['lon']
        
        weather_data, weather_error = get_weather_data(lat, lon)
        if weather_error:
            return jsonify({'error': weather_error}), 500
            
        air_quality_data, air_error = get_air_quality(lat, lon)
        if air_error and "not available" not in air_error.lower():
            logger.warning(f"Air quality data error: {air_error}")
            air_quality_data = None
            
        response_data = {
            **weather_data,
            'air_quality': air_quality_data,
            'location_details': locations
        }
        
        logger.info("Successfully processed weather request")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

@app.route('/locations/save', methods=['POST'])
def save_location():
    try:
        logger.debug("Attempting to save location")
        data = request.get_json()
        logger.debug(f"Received location data: {data}")
        
        name = data.get('name')
        lat = data.get('lat')
        lon = data.get('lon')
        country = data.get('country')
        state = data.get('state')
        is_current = data.get('is_current', False)
        
        if not all([name, lat, lon]):
            logger.error("Missing required fields")
            return jsonify({'error': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # If this is current location, update any existing current location
        if is_current:
            logger.debug("Updating current location flag")
            cursor.execute('UPDATE saved_locations SET is_current = 0 WHERE is_current = 1')
        
        # Check if location already exists
        cursor.execute('''
            SELECT id FROM saved_locations 
            WHERE name = ? AND lat = ? AND lon = ?
        ''', (name, lat, lon))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing location
            cursor.execute('''
                UPDATE saved_locations 
                SET country = ?, state = ?, is_current = ?
                WHERE id = ?
            ''', (country, state, is_current, existing['id']))
            msg = 'Location updated successfully'
        else:
            # Insert new location
            cursor.execute('''
                INSERT INTO saved_locations (name, lat, lon, country, state, is_current)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, lat, lon, country, state, is_current))
            msg = 'Location saved successfully'
        
        db.commit()
        logger.debug(msg)
        
        return jsonify({'message': msg}), 201
        
    except Exception as e:
        logger.error(f"Error saving location: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        return jsonify({'error': 'Failed to save location'}), 500

@app.route('/locations/saved', methods=['GET'])
def get_saved_locations():
    try:
        logger.debug("Attempting to fetch saved locations")
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT * FROM saved_locations ORDER BY is_current DESC, created_at DESC')
        locations = cursor.fetchall()
        logger.debug(f"Found {len(locations)} saved locations")
        logger.debug(f"Locations data: {locations}")
        
        return jsonify(locations)
        
    except Exception as e:
        logger.error(f"Error fetching saved locations: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to fetch saved locations'}), 500

@app.route('/locations/delete/<int:location_id>', methods=['DELETE'])
def delete_location(location_id):
    try:
        logger.debug(f"Attempting to delete location with ID {location_id}")
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('DELETE FROM saved_locations WHERE id = ?', (location_id,))
        db.commit()
        
        if cursor.rowcount == 0:
            logger.error("Location not found")
            return jsonify({'error': 'Location not found'}), 404
            
        logger.debug("Location deleted successfully")
        return jsonify({'message': 'Location deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting location: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to delete location'}), 500

@app.route('/challenges')
def get_challenges():
    try:
        db = get_db()
        challenges = db.execute('''
            SELECT * FROM weather_challenges 
            ORDER BY track, points ASC
        ''').fetchall()
        progress = db.execute('SELECT * FROM user_progress').fetchall()
        
        # Group challenges by track
        tracks = {}
        for challenge in challenges:
            track = challenge['track']
            if track not in tracks:
                tracks[track] = []
            
            user_progress = next(
                (p for p in progress if p['challenge_id'] == challenge['id']), 
                {'completed': False, 'score': 0}
            )
            
            challenge_data = {
                **challenge,
                'completed': user_progress['completed'],
                'score': user_progress['score']
            }
            tracks[track].append(challenge_data)
            
        return jsonify({
            'status': 'success',
            'tracks': tracks
        })
    except Exception as e:
        logger.error(f"Error fetching challenges: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to fetch challenges'
        }), 500

@app.route('/progress/update', methods=['POST'])
def update_progress():
    try:
        data = request.get_json()
        challenge_id = data.get('challenge_id')
        completed = data.get('completed', False)
        score = data.get('score', 0)
        
        if not challenge_id:
            return jsonify({
                'status': 'error',
                'message': 'Challenge ID required'
            }), 400
            
        db = get_db()
        db.execute('''
            INSERT OR REPLACE INTO user_progress 
            (challenge_id, completed, score, completed_at)
            VALUES (?, ?, ?, ?)
        ''', (
            challenge_id,
            completed,
            score,
            datetime.now() if completed else None
        ))
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Progress updated'
        })
    except Exception as e:
        logger.error(f"Error updating progress: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to update progress'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
