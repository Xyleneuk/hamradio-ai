import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Location coordinates - London Heathrow default
LAT = 51.4775
LON = -0.4614


def get_utc_time():
    """Get accurate current UTC time from system clock"""
    now    = datetime.now(timezone.utc)
    hour   = now.strftime('%H')
    minute = now.strftime('%M')
    date   = now.strftime('%d %B %Y')
    return {
        'time_utc': now.strftime('%H%M'),
        'date':     date,
        'spoken':   f"the time is {hour} {minute} UTC on {date}"
    }


def get_local_time():
    """Get accurate local UK time from system clock"""
    now_local = datetime.now()
    now_utc   = datetime.now(timezone.utc)
    hour      = now_local.strftime('%H')
    minute    = now_local.strftime('%M')
    date      = now_local.strftime('%d %B %Y')

    # Determine BST or GMT
    offset  = round(
        (now_local - now_utc.replace(tzinfo=None)).total_seconds() / 3600
    )
    tz_name = 'BST' if offset == 1 else 'GMT'

    return {
        'spoken': f"the local time is {hour} {minute} {tz_name} on {date}"
    }


def get_weather():
    """Get current weather from Open-Meteo - free, no API key needed"""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={LAT}&longitude={LON}"
            f"&current=temperature_2m,wind_speed_10m,"
            f"wind_direction_10m,weathercode,relative_humidity_2m"
            f"&wind_speed_unit=mph"
            f"&temperature_unit=celsius"
        )
        response = requests.get(url, timeout=5)
        data     = response.json()
        current  = data['current']

        temp      = round(current['temperature_2m'])
        wind_spd  = round(current['wind_speed_10m'])
        wind_dir  = _degrees_to_compass(current['wind_direction_10m'])
        humidity  = round(current['relative_humidity_2m'])
        condition = _weather_code_to_description(current['weathercode'])

        spoken = (
            f"{condition}, temperature {temp} degrees Celsius, "
            f"wind {wind_dir} at {wind_spd} miles per hour, "
            f"humidity {humidity} percent"
        )

        return {
            'temperature': temp,
            'wind_speed':  wind_spd,
            'wind_dir':    wind_dir,
            'humidity':    humidity,
            'condition':   condition,
            'spoken':      spoken
        }

    except Exception as e:
        print(f"Weather fetch error: {e}")
        return {'spoken': 'weather information unavailable at this time'}


def get_news():
    """Get latest UK news headlines from BBC RSS feed"""
    try:
        response = requests.get(
            'https://feeds.bbci.co.uk/news/rss.xml',
            timeout=5,
            headers={'User-Agent': 'HamRadioAI/1.0'}
        )
        root      = ET.fromstring(response.content)
        items     = root.findall('.//item')[:5]
        headlines = []

        for item in items:
            title = item.find('title')
            if title is not None and title.text:
                headlines.append(title.text.strip())

        if headlines:
            spoken = (
                "Latest BBC news headlines: " +
                ". Next: ".join(headlines[:3])
            )
            return {
                'headlines': headlines,
                'spoken':    spoken
            }
        return {'spoken': 'news unavailable at this time'}

    except Exception as e:
        print(f"News fetch error: {e}")
        return {'spoken': 'news unavailable at this time'}


def _degrees_to_compass(degrees):
    """Convert wind degrees to compass direction"""
    directions = [
        'North', 'North Northeast', 'Northeast', 'East Northeast',
        'East', 'East Southeast', 'Southeast', 'South Southeast',
        'South', 'South Southwest', 'Southwest', 'West Southwest',
        'West', 'West Northwest', 'Northwest', 'North Northwest'
    ]
    return directions[round(degrees / 22.5) % 16]


def _weather_code_to_description(code):
    """Convert WMO weather code to plain English"""
    codes = {
        0:  'clear sky',
        1:  'mainly clear',
        2:  'partly cloudy',
        3:  'overcast',
        45: 'foggy',
        48: 'freezing fog',
        51: 'light drizzle',
        53: 'moderate drizzle',
        55: 'heavy drizzle',
        61: 'light rain',
        63: 'moderate rain',
        65: 'heavy rain',
        71: 'light snow',
        73: 'moderate snow',
        75: 'heavy snow',
        77: 'snow grains',
        80: 'light showers',
        81: 'moderate showers',
        82: 'heavy showers',
        85: 'snow showers',
        86: 'heavy snow showers',
        95: 'thunderstorm',
        96: 'thunderstorm with hail',
        99: 'thunderstorm with heavy hail',
    }
    return codes.get(code, 'conditions unknown')


# Test
if __name__ == '__main__':
    print("UTC time:   ", get_utc_time()['spoken'])
    print("Local time: ", get_local_time()['spoken'])
    print("\nWeather:    ", get_weather()['spoken'])
    print("\nNews:       ", get_news()['spoken'])