"""
Centralized configuration for Plane Radar.
Reads and validates all PLANERADAR_* environment variables in one place.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

_VALID_LOG_LEVELS = {"debug", "info", "warning", "error", "critical"}
_RANGE_PRESET_COUNT = 4


@dataclass
class Config:
    # Location
    lat: float
    lon: float

    # ADS-B
    fetch_interval_ms: int
    fetch_radius_km: float
    api_base: str

    # Display
    range_index: int
    use_miles: bool
    show_runways: bool

    # Web server
    web_host: str
    web_port: int

    # Logging
    log_level: str
    log_to_disk: bool
    log_path: str

    # Dev / debug
    debug: bool
    use_mock_data: bool


def _get_float(key: str, default: float) -> float:
    val = os.environ.get(key, str(default))
    try:
        return float(val)
    except ValueError:
        raise ValueError(f"{key} must be a number, got: {val!r}")


def _get_int(key: str, default: int) -> int:
    val = os.environ.get(key, str(default))
    try:
        return int(val)
    except ValueError:
        raise ValueError(f"{key} must be an integer, got: {val!r}")


def _get_bool(key: str, default: bool) -> bool:
    return os.environ.get(key, "1" if default else "0") == "1"


def load_config() -> Config:
    """Read and validate all environment variables. Raises ValueError on invalid input."""
    load_dotenv()
    debug = _get_bool("PLANERADAR_DEBUG", False)

    log_level = os.environ.get("PLANERADAR_LOG_LEVEL", "warning").lower()
    if log_level not in _VALID_LOG_LEVELS:
        raise ValueError(
            f"PLANERADAR_LOG_LEVEL must be one of {sorted(_VALID_LOG_LEVELS)}, got: {log_level!r}"
        )
    if debug:
        log_level = "debug"

    range_index = _get_int("PLANERADAR_RANGE_INDEX", 1)
    if not (0 <= range_index < _RANGE_PRESET_COUNT):
        raise ValueError(
            f"PLANERADAR_RANGE_INDEX must be 0–{_RANGE_PRESET_COUNT - 1}, got: {range_index}"
        )

    return Config(
        lat=_get_float("PLANERADAR_LAT", 43.6777),
        lon=_get_float("PLANERADAR_LON", -79.6248),
        fetch_interval_ms=_get_int("PLANERADAR_FETCH_INTERVAL_MS", 3000),
        fetch_radius_km=_get_float("PLANERADAR_FETCH_RADIUS_KM", 25.0),
        api_base=os.environ.get(
            "PLANERADAR_API_BASE", "https://opendata.adsb.fi/api/v3/lat/"
        ),
        range_index=range_index,
        use_miles=_get_bool("PLANERADAR_USE_MILES", False),
        show_runways=_get_bool("PLANERADAR_SHOW_RUNWAYS", True),
        web_host=os.environ.get("PLANERADAR_WEB_HOST", "0.0.0.0"),
        web_port=_get_int("PLANERADAR_WEB_PORT", 8080),
        log_level=log_level,
        log_to_disk=_get_bool("PLANERADAR_LOG_TO_DISK", False),
        log_path=os.environ.get(
            "PLANERADAR_LOG_PATH", "/var/log/plane-radar/app.log"
        ),
        debug=debug,
        use_mock_data=_get_bool("PLANERADAR_MOCK_DATA", False),
    )
