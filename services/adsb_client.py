"""
ADS-B client ported from adsb_client.cpp.
Fetches aircraft data from adsb.fi API.
"""

import requests
import json
import math
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_BASE = os.environ.get('PLANERADAR_API_BASE', 'https://opendata.adsb.fi/api/v3/lat/')
KM_PER_NM = 1.852
REQUEST_TIMEOUT_MS = 10000
MAX_AIRCRAFT = 50


class Aircraft:
    """Aircraft data structure."""
    
    def __init__(self):
        self.lat = 0.0
        self.lon = 0.0
        self.nose_deg = 0.0
        self.track_deg = 0.0
        self.gs_knots = 0.0
        self.callsign = ""
        self.type = ""
        self.alt = ""
        self.squawk = ""


class ADSBClient:
    """Client for ADS-B API."""
    
    def __init__(self, debug=False, use_mock_data=False):
        self.aircraft = [Aircraft() for _ in range(MAX_AIRCRAFT)]
        self.aircraft_count = 0
        self.debug = debug
        self.use_mock_data = use_mock_data
        self.mock_data = None
        
        if use_mock_data:
            self._load_mock_data()
    
    def _load_mock_data(self):
        """Load mock data from JSON file."""
        try:
            import os
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            mock_file = os.path.join(script_dir, 'data-sample.json')
            
            with open(mock_file, 'r') as f:
                import json
                self.mock_data = json.load(f)
            print(f"Loaded mock data from {mock_file}")
        except Exception as e:
            print(f"Error loading mock data: {e}")
            self.use_mock_data = False
    
    def read_json_float(self, obj, key):
        """Read float from JSON object with fallbacks."""
        if key in obj:
            val = obj[key]
            if isinstance(val, (int, float)):
                return float(val)
        return None
    
    def pick_nose_heading(self, plane):
        """Pick best nose heading from available fields."""
        for key in ['true_heading', 'mag_heading', 'track', 'dir']:
            val = self.read_json_float(plane, key)
            if val is not None:
                return val
        return 0.0
    
    def pick_track_heading(self, plane):
        """Pick best track heading from available fields."""
        for key in ['track', 'true_heading', 'mag_heading', 'dir']:
            val = self.read_json_float(plane, key)
            if val is not None:
                return val
        return 0.0
    
    def pick_ground_speed(self, plane):
        """Pick best ground speed from available fields."""
        for key in ['gs', 'tas', 'ias']:
            val = self.read_json_float(plane, key)
            if val is not None:
                return val
        return 0.0
    
    def is_on_ground(self, plane):
        """Check if aircraft is on ground."""
        alt = plane.get('alt_baro')
        if isinstance(alt, str):
            return alt == 'ground'
        return False
    
    def copy_json_string_trimmed(self, obj, key, max_len=20):
        """Copy string from JSON, trimming trailing spaces."""
        if key in obj and isinstance(obj[key], str):
            s = obj[key].rstrip()
            return s[:max_len]
        return ""
    
    def format_altitude_tag(self, plane):
        """Format altitude tag."""
        alt = plane.get('alt_baro')
        if isinstance(alt, str):
            if alt == 'ground':
                return 'GND'
        else:
            val = self.read_json_float(plane, 'alt_baro')
            if val is None:
                val = self.read_json_float(plane, 'alt_geom')
            if val is not None:
                return f"{int(round(val))} ft"
        return ""
    
    def fill_tag_fields(self, ac, plane):
        """Fill aircraft tag fields."""
        ac.callsign = self.copy_json_string_trimmed(plane, 'flight', 10)
        if not ac.callsign:
            ac.callsign = self.copy_json_string_trimmed(plane, 'hex', 10)
        
        ac.type = self.copy_json_string_trimmed(plane, 't', 8)
        ac.alt = self.format_altitude_tag(plane)
        ac.squawk = self.copy_json_string_trimmed(plane, 'squawk', 4)
    
    def fetch_update(self, center_lat, center_lon, fetch_radius_km):
        """Fetch aircraft update from ADS-B API."""
        if self.use_mock_data and self.mock_data:
            # Use mock data instead of live API
            data = self.mock_data
            print("Using mock data (skipping live API)")
        else:
            # Fetch from live API
            dist_nm = fetch_radius_km / KM_PER_NM
            
            url = f"{API_BASE}{center_lat:.6f}/lon/{center_lon:.6f}/dist/{dist_nm:.1f}"
            
            try:
                response = requests.get(url, timeout=REQUEST_TIMEOUT_MS / 1000)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"ADS-B fetch error: {e}")
                return False
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                return False
        
        ac_list = data.get('ac', [])
        if not ac_list:
            self.aircraft_count = 0
            return True
        
        n = 0
        for plane in ac_list:
            if n >= MAX_AIRCRAFT:
                break
            
            if 'lat' not in plane or 'lon' not in plane:
                continue
            
            if not isinstance(plane['lat'], (int, float)) or not isinstance(plane['lon'], (int, float)):
                continue
            
            if self.is_on_ground(plane):
                continue
            
            ac = self.aircraft[n]
            ac.lat = float(plane['lat'])
            ac.lon = float(plane['lon'])
            ac.nose_deg = self.pick_nose_heading(plane)
            ac.track_deg = self.pick_track_heading(plane)
            ac.gs_knots = self.pick_ground_speed(plane)
            self.fill_tag_fields(ac, plane)
            
            if self.debug:
                print(f"  [{n}] {ac.callsign} | {ac.type} | {ac.alt} | "
                      f"pos[position]:({ac.lat:.4f},{ac.lon:.4f}) | "
                      f"hdg[heading]:{ac.nose_deg:.0f}° | trk[track]:{ac.track_deg:.0f}° | "
                      f"gs[ground_speed]:{ac.gs_knots:.0f}kt")
            
            n += 1
        
        self.aircraft_count = n
        print(f"ADS-B: {n} aircraft")
        return True
    
    def get_aircraft_count(self):
        """Get number of aircraft."""
        return self.aircraft_count
    
    def get_aircraft_list(self):
        """Get aircraft list."""
        return self.aircraft[:self.aircraft_count]
