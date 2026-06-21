#!/usr/bin/env python3
"""
Plane Radar - Raspberry Pi version
Ported from ESP32-C3 firmware
"""

import logging
import logging.handlers
import os
import signal
import sys
import time

from config import load_config

logger = logging.getLogger(__name__)


def setup_logging(level: str, log_to_disk: bool, log_path: str) -> None:
    """Configure application-wide logging."""
    numeric_level = getattr(logging, level.upper(), logging.WARNING)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if log_to_disk:
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


class PlaneRadar:
    """Main application class."""

    def __init__(self, cfg) -> None:
        self.running = True

        from display import DisplayDriver
        from radar import RadarDisplay
        from radar.range import RangeManager
        from services import ADSBClient
        from services.adsb_client import RateLimitError
        from services.location import LocationStorage
        from web import WebServer

        self._RateLimitError = RateLimitError

        # Create singletons from config
        location = LocationStorage(lat=cfg.lat, lon=cfg.lon)
        range_manager = RangeManager(
            range_index=cfg.range_index,
            use_miles=cfg.use_miles,
            show_runways=cfg.show_runways,
        )

        # Initialize display
        logger.info("Initializing display...")
        self.display = DisplayDriver()
        self.display.init()

        # Initialize radar display
        logger.info("Initializing radar...")
        self.radar = RadarDisplay(self.display, location, range_manager)

        # Initialize ADS-B client
        logger.info("Initializing ADS-B client...")
        self.adsb = ADSBClient(
            api_base=cfg.api_base,
            debug=cfg.debug,
            use_mock_data=cfg.use_mock_data,
        )

        # Initialize web server
        logger.info("Starting web server...")
        self.portal = WebServer(
            host=cfg.web_host,
            port=cfg.web_port,
            location=location,
            range_manager=range_manager,
            fetch_radius_km=cfg.fetch_radius_km,
            fetch_interval_ms=cfg.fetch_interval_ms,
            adsb_client=self.adsb,
        )
        self.portal.start()

        self._location = location
        self._range_manager = range_manager
        self._cfg = cfg

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Plane Radar initialized")
        logger.info("Location: %.6f, %.6f", cfg.lat, cfg.lon)
        logger.info("Range: %s", range_manager.format_current_ring3_label())
        logger.info("Web server: http://localhost:%d", cfg.web_port)

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.info("Shutting down...")
        self.running = False

    def run(self) -> None:
        """Main loop."""
        last_fetch_time = 0.0
        fetch_interval_sec = self._cfg.fetch_interval_ms / 1000.0
        backoff_sec = 0.0
        _BACKOFF_INITIAL = 30.0
        _BACKOFF_MAX = 120.0

        # Initial draw (empty grid)
        self.radar.draw([])

        while self.running:
            current_time = time.time()

            # Fetch ADS-B data at interval (or backoff interval after rate limit)
            effective_interval = backoff_sec if backoff_sec > 0 else fetch_interval_sec
            if current_time - last_fetch_time >= effective_interval:
                last_fetch_time = current_time

                lat = self._location.get_lat()
                lon = self._location.get_lon()
                fetch_radius = self._cfg.fetch_radius_km

                logger.debug(
                    "Fetching ADS-B data (lat=%.4f, lon=%.4f, radius=%.1fkm)...",
                    lat,
                    lon,
                    fetch_radius,
                )

                try:
                    self.adsb.fetch_update(lat, lon, fetch_radius)
                    aircraft_list = self.adsb.get_aircraft_list()
                    logger.debug("ADS-B: %d aircraft", len(aircraft_list))
                    if self._cfg.use_mock_data:
                        logger.debug("Using mock data (skipping live API)")
                    self.radar.refresh_aircraft(aircraft_list)
                    self.portal.push_update(aircraft_list)
                    backoff_sec = 0.0
                except self._RateLimitError as e:
                    backoff_sec = min(max(backoff_sec * 2, _BACKOFF_INITIAL), _BACKOFF_MAX)
                    logger.warning(
                        "Rate limited by ADS-B API — backing off %.0fs: %s",
                        backoff_sec,
                        e,
                    )
                except RuntimeError as e:
                    logger.error("ADS-B fetch failed: %s", e)

            # Small sleep to prevent CPU spinning
            time.sleep(0.01)

        # Cleanup
        self.display.clear()
        logger.info("Plane Radar stopped")


def main() -> None:
    """Entry point."""
    # Bootstrap logging before load_config so any config errors are captured
    cfg = load_config()
    setup_logging(cfg.log_level, cfg.log_to_disk, cfg.log_path)

    try:
        app = PlaneRadar(cfg)
        app.run()
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
