#!/usr/bin/env python3
"""
Plane Radar - Raspberry Pi version
Ported from ESP32-C3 firmware
"""

import os
import time
import signal
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from display import DisplayDriver
from radar import RadarDisplay
from services import ADSBClient
from services.location import location
from radar.range import range_manager
from web import WebServer

# Configuration
ADSB_FETCH_INTERVAL_MS = int(os.environ.get('PLANERADAR_FETCH_INTERVAL_MS', '3000'))
FETCH_INTERVAL_SEC = ADSB_FETCH_INTERVAL_MS / 1000.0
DEBUG = os.environ.get('PLANERADAR_DEBUG', '0') == '1'
USE_MOCK_DATA = os.environ.get('PLANERADAR_MOCK_DATA', '0') == '1'
WEB_HOST = os.environ.get('PLANERADAR_WEB_HOST', '0.0.0.0')
WEB_PORT = int(os.environ.get('PLANERADAR_WEB_PORT', '8080'))
FETCH_RADIUS_KM = float(os.environ.get('PLANERADAR_FETCH_RADIUS_KM', '25'))


class PlaneRadar:
    """Main application class."""
    
    def __init__(self):
        self.running = True
        
        # Initialize display
        print("Initializing display...")
        self.display = DisplayDriver()
        self.display.init()
        
        # Initialize radar display
        print("Initializing radar...")
        self.radar = RadarDisplay(self.display)
        
        # Initialize ADS-B client
        print("Initializing ADS-B client...")
        self.adsb = ADSBClient(debug=DEBUG, use_mock_data=USE_MOCK_DATA)
        
        # Initialize web server
        print("Starting web server...")
        self.portal = WebServer(host=WEB_HOST, port=WEB_PORT, adsb_client=self.adsb)
        self.portal.start()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("Plane Radar initialized")
        print(f"Location: {location.get_lat():.6f}, {location.get_lon():.6f}")
        print(f"Range: {range_manager.format_current_ring3_label()}")
        print(f"Web server: http://localhost:{WEB_PORT}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\nShutting down...")
        self.running = False
    
    def run(self):
        """Main loop."""
        last_fetch_time = 0
        
        # Initial draw (empty grid)
        self.radar.draw([])
        
        while self.running:
            current_time = time.time()
            
            # Fetch ADS-B data at interval
            if current_time - last_fetch_time >= FETCH_INTERVAL_SEC:
                last_fetch_time = current_time
                
                lat = location.get_lat()
                lon = location.get_lon()
                fetch_radius = FETCH_RADIUS_KM
                
                print(f"Fetching ADS-B data (lat={lat:.4f}, lon={lon:.4f}, radius={fetch_radius:.1f}km)...")
                
                if self.adsb.fetch_update(lat, lon, fetch_radius):
                    aircraft_list = self.adsb.get_aircraft_list()
                    self.radar.refresh_aircraft(aircraft_list)
                else:
                    print("ADS-B fetch failed, keeping previous display")
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.01)
        
        # Cleanup
        self.display.clear()
        print("Plane Radar stopped")


def main():
    """Entry point."""
    try:
        app = PlaneRadar()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
