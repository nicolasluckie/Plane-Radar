"""
Range presets and configuration ported from radar_range.cpp.
Uses environment variables instead of JSON file.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Range presets (ring3_km = 3/4 of outer radius)
RING3_TO_OUTER_KM = 4.0 / 3.0

RANGE_PRESETS = [
    {"ring3_km": 5.0, "outer_km": 5.0 * RING3_TO_OUTER_KM},
    {"ring3_km": 10.0, "outer_km": 10.0 * RING3_TO_OUTER_KM},
    {"ring3_km": 15.0, "outer_km": 15.0 * RING3_TO_OUTER_KM},
    {"ring3_km": 25.0, "outer_km": 25.0 * RING3_TO_OUTER_KM},
]

DEFAULT_RANGE_INDEX = 1  # 10 km ring
KM_PER_MILE = 1.609344

# Configuration from environment variables
RANGE_INDEX = int(os.environ.get('PLANERADAR_RANGE_INDEX', str(DEFAULT_RANGE_INDEX)))
USE_MILES = os.environ.get('PLANERADAR_USE_MILES', '0') == '1'
SHOW_RUNWAYS = os.environ.get('PLANERADAR_SHOW_RUNWAYS', '1') == '1'


class RangeManager:
    """Manages range presets and distance units."""
    
    def __init__(self):
        self.range_index = RANGE_INDEX
        self.use_miles = USE_MILES
        self.show_runways = SHOW_RUNWAYS
        
        # Validate range index
        if self.range_index >= len(RANGE_PRESETS):
            self.range_index = DEFAULT_RANGE_INDEX
    
    def get_current_range(self):
        """Get current range preset."""
        return RANGE_PRESETS[self.range_index]
    
    def get_range_index(self):
        """Get current range index."""
        return self.range_index
    
    def fetch_radius_km(self):
        """Calculate ADS-B fetch radius (km) for screen edge."""
        from .theme import CENTER_X, BEYOND_RING_SCREEN_MARGIN_PX, GRID_OUTER_RADIUS
        
        outer_km = self.get_current_range()['outer_km']
        screen_r_px = CENTER_X - BEYOND_RING_SCREEN_MARGIN_PX
        return outer_km * (screen_r_px / GRID_OUTER_RADIUS)
    
    def format_ring3_label(self, ring3_km, use_miles=None):
        """Format ring 3 distance label."""
        if use_miles is None:
            use_miles = self.use_miles
        
        if use_miles:
            mi = int(round(ring3_km / KM_PER_MILE))
            return f"{mi}mi"
        else:
            km = int(round(ring3_km))
            return f"{km}km"
    
    def format_current_ring3_label(self):
        """Format current ring 3 label."""
        return self.format_ring3_label(self.get_current_range()['ring3_km'])


# Global range manager instance
range_manager = RangeManager()
