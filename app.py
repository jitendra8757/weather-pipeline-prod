from flask import Flask, request, jsonify, render_template, g
import requests
from dotenv import load_dotenv
import os
import logging
import sqlite3
import traceback
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# API configuration
API_KEY = 'c3cd0b3e22e4080082a35b80adbe8f1f'

# Database configuration
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'weather.db')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info(f"Database path: {DATABASE}")

def dict_factory(cursor, row):
    """Convert database row objects to a dictionary"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_db():
    """Get database connection with row factory"""
    if 'db' not in g:
        try:
            # Ensure the database directory exists
            ensure_db_directory()
            
            g.db = sqlite3.connect(
                DATABASE,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            # Use dict_factory for JSON serialization
            g.db.row_factory = dict_factory
            logger.debug("Database connection established")
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting database connection: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    return g.db

def close_db(e=None):
    """Close the database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def ensure_db_directory():
    """Ensure database directory exists and is writable"""
    try:
        logger.info(f"Checking database directory: {os.path.dirname(DATABASE)}")
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        
        # Test if directory is writable by creating a temp file
        test_file = os.path.join(os.path.dirname(DATABASE), '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.info("Database directory is writable")
        except (IOError, OSError) as e:
            logger.error(f"Database directory is not writable: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Failed to ensure database directory: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def init_db():
    """Initialize the database schema"""
    try:
        logger.info("Initializing database")
        db = get_db()
        cursor = db.cursor()

        # Create saved_locations table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                country TEXT,
                state TEXT,
                is_current BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        db.commit()
        logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def initialize_database():
    """Ensure database exists and is initialized before first request"""
    try:
        ensure_db_directory()
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

# Initialize database on startup
with app.app_context():
    initialize_database()

# Register database connection close handler
app.teardown_appcontext(close_db)

# API endpoints
GEOCODING_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct"
REVERSE_GEOCODING_URL = "http://api.openweathermap.org/geo/1.0/reverse"
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
AIR_POLLUTION_BASE_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

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
        
        # Validate coordinates
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError("Invalid coordinates provided")
            
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
            logger.error("Invalid API key")
            raise Exception("Weather service authentication failed")
        
        response.raise_for_status()
        data = response.json()
        
        if 'main' not in data or 'weather' not in data:
            raise ValueError("Invalid weather data received")
            
        return data, None
        
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching weather data")
        return None, "Weather service timeout. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {str(e)}")
        return None, "Unable to connect to weather service"
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return None, str(e)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return None, "An unexpected error occurred"

def get_air_quality(lat, lon):
    try:
        logger.debug(f"Attempting to fetch air quality data for ({lat}, {lon})")
        
        # Validate coordinates
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError("Invalid coordinates provided")
            
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
            logger.error("Invalid API key")
            raise Exception("Air quality service authentication failed")
            
        response.raise_for_status()
        data = response.json()
        
        if 'list' not in data or not data['list']:
            raise ValueError("Invalid air quality data received")
            
        current_data = data['list'][0]
        if 'main' not in current_data or 'components' not in current_data:
            raise ValueError("Incomplete air quality data")
            
        aqi = current_data['main']['aqi']
        components = current_data['components']
        
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
        
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching air quality data")
        return None, "Air quality service timeout. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching air quality data: {str(e)}")
        return None, "Unable to connect to air quality service"
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return None, str(e)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return None, "An unexpected error occurred"

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
    """Save a location to the database"""
    db = None
    try:
        logger.debug("Attempting to save location")
        data = request.get_json()
        logger.debug(f"Received location data: {data}")
        
        # Validate required fields
        name = str(data.get('name', '')).strip()
        try:
            lat = float(data.get('lat', 0))
            lon = float(data.get('lon', 0))
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid coordinates: {e}")
            return jsonify({'error': 'Invalid coordinates'}), 400
            
        country = str(data.get('country', '')).strip()
        state = str(data.get('state', '')).strip()
        is_current = bool(data.get('is_current', False))
        
        if not name or not lat or not lon:
            logger.error("Missing required fields")
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Get database connection
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
            logger.info(f"Updated location {name} ({lat}, {lon})")
        else:
            # Insert new location
            cursor.execute('''
                INSERT INTO saved_locations (name, lat, lon, country, state, is_current)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, lat, lon, country, state, is_current))
            msg = 'Location saved successfully'
            logger.info(f"Saved new location {name} ({lat}, {lon})")
        
        db.commit()
        return jsonify({'message': msg}), 201
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        if db:
            db.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
        
    except Exception as e:
        logger.error(f"Error saving location: {str(e)}")
        logger.error(traceback.format_exc())
        if db:
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
    """Delete a saved location"""
    db = None
    try:
        logger.debug(f"Attempting to delete location {location_id}")
        
        # Get database connection
        db = get_db()
        cursor = db.cursor()
        
        # Check if location exists
        cursor.execute('SELECT id FROM saved_locations WHERE id = ?', (location_id,))
        location = cursor.fetchone()
        
        if not location:
            logger.error(f"Location {location_id} not found")
            return jsonify({'error': 'Location not found'}), 404
            
        # Delete the location
        cursor.execute('DELETE FROM saved_locations WHERE id = ?', (location_id,))
        db.commit()
        
        logger.info(f"Deleted location {location_id}")
        return jsonify({'message': 'Location deleted successfully'}), 200
        
    except sqlite3.Error as e:
        logger.error(f"Database error while deleting location: {str(e)}")
        if db:
            db.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting location: {str(e)}")
        logger.error(traceback.format_exc())
        if db:
            db.rollback()
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

# Add temporary data export endpoint
@app.route('/export-data', methods=['GET'])
def export_data():
    """Temporary endpoint to export data"""
    try:
        db = get_db()
        cursor = db.cursor()
        data = {'export_date': datetime.now().isoformat()}
        
        # Get saved locations
        try:
            cursor.execute('SELECT * FROM saved_locations')
            data['saved_locations'] = cursor.fetchall()
            logger.info(f"Found {len(data['saved_locations'])} saved locations")
        except sqlite3.OperationalError as e:
            logger.error(f"Error fetching saved_locations: {str(e)}")
            data['saved_locations'] = []
        
        # Get weather challenges if table exists
        try:
            cursor.execute('SELECT * FROM weather_challenges')
            data['weather_challenges'] = cursor.fetchall()
            logger.info(f"Found {len(data['weather_challenges'])} challenges")
        except sqlite3.OperationalError:
            logger.info("weather_challenges table not found")
            data['weather_challenges'] = []
        
        # Get user progress if table exists
        try:
            cursor.execute('SELECT * FROM user_progress')
            data['user_progress'] = cursor.fetchall()
            logger.info(f"Found {len(data['user_progress'])} progress records")
        except sqlite3.OperationalError:
            logger.info("user_progress table not found")
            data['user_progress'] = []
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add temporary init endpoint
@app.route('/init-db', methods=['GET'])
def init_db_endpoint():
    """Temporary endpoint to initialize database"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Create tables
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS saved_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                country TEXT,
                state TEXT,
                is_current BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0,
                score INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS weather_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                difficulty TEXT CHECK(difficulty IN ('Easy', 'Medium', 'Hard')) NOT NULL,
                points INTEGER DEFAULT 100,
                category TEXT NOT NULL,
                requirements TEXT NOT NULL,
                track TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        db.commit()
        return jsonify({'message': 'Database initialized successfully'})
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
