"""
Location storage ported from radar_location.cpp.
Uses environment variables instead of ESP32 Preferences.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Location from environment variables
LAT = float(os.environ.get('PLANERADAR_LAT', '43.6777'))
LON = float(os.environ.get('PLANERADAR_LON', '-79.6248'))


class LocationStorage:
    """Manages radar location storage."""
    
    def __init__(self):
        self.lat = LAT
        self.lon = LON
    
    def get_lat(self):
        """Get latitude."""
        return self.lat
    
    def get_lon(self):
        """Get longitude."""
        return self.lon


# Global location instance
location = LocationStorage()
