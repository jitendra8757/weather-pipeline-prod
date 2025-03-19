# WeatherNow - Weather & Air Quality App 🌤️

A beautiful, modern weather application that provides real-time weather information and air quality data with dynamic themes that change based on weather conditions and time of day.

![WeatherNow Logo](https://raw.githubusercontent.com/your-username/weather-app/main/screenshots/logo.png)

## ✨ Features

- **Real-time Weather Data**: Get current weather conditions for any city worldwide
- **Air Quality Information**: Check air quality index (AQI) and pollutant levels
- **Dynamic Themes**: Beautiful backgrounds that change based on:
  - Weather conditions (sunny, rainy, cloudy, etc.)
  - Time of day (day/night cycles)
- **Location Services**: Automatic location detection
- **Favorites**: Save and quickly access your favorite locations
- **Modern UI**: Glassmorphic design with smooth animations

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- OpenWeatherMap API key ([Get it here](https://openweathermap.org/api))

### Installation

1. Clone the repository or extract the ZIP file:
```bash
git clone https://github.com/your-username/weather-app.git
cd weather-app
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your API key:
```env
OPENWEATHER_API_KEY=your_api_key_here
```

4. Initialize the database:
```bash
python
>>> from app import init_db
>>> init_db()
>>> exit()
```

5. Run the application:
```bash
python app.py
```

6. Open your browser and visit: `http://127.0.0.1:5000`

## 🎨 Features & Usage

### Search for a City
- Enter any city name in the search box
- Click the search button or press Enter

### Get Current Location
- Click the "Get My Location" button
- Allow location access when prompted

### Save Favorite Locations
- Search for a city
- Click the "Save Location" button
- Access saved locations from the dropdown menu

### Weather Information
- Temperature
- Weather conditions
- Humidity
- Wind speed
- Air quality index
- Pollutant levels

## 🌈 Dynamic Themes

The app features beautiful animated backgrounds that change based on:

### Weather Conditions
- Clear Sky (Day/Night)
- Clouds (Day/Night)
- Rain (Day/Night)
- Thunderstorm
- Snow (Day/Night)
- Mist/Fog (Day/Night)
- Dust/Sand

### Time-based Effects
- Dynamic color transitions
- Smooth animations
- Glassmorphic UI elements

## 🛠️ Built With

- **Frontend**:
  - HTML5
  - CSS3 (Animations & Transitions)
  - JavaScript (Vanilla)
  
- **Backend**:
  - Flask (Python web framework)
  - SQLite (Database)
  
- **APIs**:
  - OpenWeatherMap API
  - Geolocation API

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Weather data provided by [OpenWeatherMap](https://openweathermap.org/)
- Icons by [Font Awesome](https://fontawesome.com/)
- Fonts by [Google Fonts](https://fonts.google.com/)
