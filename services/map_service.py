import logging
import requests

logger = logging.getLogger(__name__)

def geocode_address(address):
    """
    Geocodes an address to latitude and longitude using OpenStreetMap Nominatim API.
    Nominatim requires a user-agent header.
    Returns (lat, lng) or (None, None)
    """
    if not address:
        return None, None
        
    url = "https://nominatim.openstreetmap.org/search"
    headers = {
        'User-Agent': 'OnsiteServiceManagementSystem/1.0'
    }
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lng = float(data[0]['lon'])
                return lat, lng
    except Exception as e:
        logger.error(f"Geocoding failed for address '{address}': {e}")
        
    return 0.0, 0.0
