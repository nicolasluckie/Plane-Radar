"""
Range presets and configuration ported from radar_range.cpp.
Uses environment variables instead of JSON file.
"""

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


class RangeManager:
    """Manages range presets and distance units."""

    def __init__(self, range_index: int = DEFAULT_RANGE_INDEX, use_miles: bool = False, show_runways: bool = True) -> None:
        self.range_index = range_index
        self.use_miles = use_miles
        self.show_runways = show_runways

        # Validate range index
        if self.range_index >= len(RANGE_PRESETS):
            self.range_index = DEFAULT_RANGE_INDEX
    
    def get_current_range(self) -> dict:
        """Get current range preset."""
        return RANGE_PRESETS[self.range_index]

    def get_range_index(self) -> int:
        """Get current range index."""
        return self.range_index

    def fetch_radius_km(self) -> float:
        """Calculate ADS-B fetch radius (km) for screen edge."""
        from .theme import CENTER_X, BEYOND_RING_SCREEN_MARGIN_PX, GRID_OUTER_RADIUS

        outer_km = self.get_current_range()['outer_km']
        screen_r_px = CENTER_X - BEYOND_RING_SCREEN_MARGIN_PX
        return outer_km * (screen_r_px / GRID_OUTER_RADIUS)

    def format_ring3_label(self, ring3_km: float, use_miles: bool | None = None) -> str:
        """Format ring 3 distance label."""
        if use_miles is None:
            use_miles = self.use_miles

        if use_miles:
            mi = int(round(ring3_km / KM_PER_MILE))
            return f"{mi}mi"
        else:
            km = int(round(ring3_km))
            return f"{km}km"

    def format_current_ring3_label(self) -> str:
        """Format current ring 3 label."""
        return self.format_ring3_label(self.get_current_range()['ring3_km'])
