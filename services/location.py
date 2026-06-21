"""
Location storage ported from radar_location.cpp.
Uses environment variables instead of ESP32 Preferences.
"""


class LocationStorage:
    """Manages radar location storage."""

    def __init__(self, lat: float, lon: float) -> None:
        self.lat = lat
        self.lon = lon

    def get_lat(self) -> float:
        """Get latitude."""
        return self.lat

    def get_lon(self) -> float:
        """Get longitude."""
        return self.lon
