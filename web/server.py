"""
Flask web server for Plane Radar.
Serves the radar view at / and aircraft data at /api/aircraft.
"""

import logging
import threading

from flask import Flask, jsonify, render_template_string

logger = logging.getLogger(__name__)
app = Flask(__name__)

# HTML template for radar view
RADAR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Plane Radar</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: #0a0e1c; 
            margin: 0; 
            padding: 20px; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
        }
        h1 { color: #fff; margin: 0 0 20px 0; }
        .radar-container { 
            display: flex; 
            gap: 20px; 
            flex-wrap: wrap; 
            justify-content: center; 
        }
        canvas { 
            border-radius: 50%; 
            background: transparent; 
            position: relative;
            z-index: 10;
        }
        #map {
            width: 240px;
            height: 240px;
            border-radius: 50%;
            overflow: hidden;
            position: absolute;
            z-index: 1;
        }
        .radar-wrapper {
            position: relative;
            width: 240px;
            height: 240px;
        }
        .info { 
            color: #fff; 
            font-size: 14px; 
            max-width: 300px; 
        }
        .aircraft-list { 
            color: #fff; 
            font-size: 12px; 
            max-height: 400px; 
            overflow-y: auto; 
            background: #0a0e1c; 
            padding: 10px; 
            border-radius: 8px; 
        }
        .aircraft-item { 
            padding: 5px; 
            border-bottom: 1px solid #1a1e2c; 
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .aircraft-item:hover {
            background-color: #1a1e2c;
        }
        .aircraft-item.highlighted {
            background-color: #ffc800;
            color: #0a0e1c;
        }
        .aircraft-item.highlighted strong {
            color: #0a0e1c;
        }
        #tooltip {
            position: absolute;
            background: rgba(10, 14, 28, 0.95);
            border: 1px solid #106420;
            color: #fff;
            padding: 10px;
            border-radius: 8px;
            font-size: 12px;
            pointer-events: none;
            display: none;
            z-index: 1000;
            min-width: 150px;
        }
        #tooltip strong {
            color: #ffc800;
        }
    </style>
</head>
<body>
    <h1>Plane Radar</h1>
    <div class="radar-container">
        <div class="radar-wrapper">
            <div id="map"></div>
            <canvas id="radar" width="240" height="240"></canvas>
        </div>
        <div class="info">
            <div id="location">Location: Loading...</div>
            <div id="range">Range: Loading...</div>
            <div id="aircraft-count">Aircraft: Loading...</div>
            <div class="aircraft-list" id="aircraft-list"></div>
        </div>
    </div>
    <div id="tooltip"></div>
    <script>
        const canvas = document.getElementById('radar');
        const ctx = canvas.getContext('2d');
        const tooltip = document.getElementById('tooltip');
        const CENTER_X = 120;
        const CENTER_Y = 120;
        const GRID_OUTER_RADIUS = 107;
        const RING_COUNT = 4;
        
        // Store aircraft positions for hover detection
        let aircraftPositions = [];
        let highlightedIndex = -1;
        
        // Initialize Leaflet map
        const map = L.map('map', {
            center: [{{ center_lat }}, {{ center_lon }}],
            zoom: {{ zoom }},
            zoomControl: false,
            attributionControl: false
        });
        
        // Add CartoDB Dark Matter tiles
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);
        
        // Colors (matching ESP32 theme)
        const COLORS = {
            background: '#0a0e1c',
            grid: '#106420',
            label: '#ffffff',
            center: '#ffffff',
            aircraft: '#ff0000',
            track: '#ff00ff',
            tagType: '#ffc800',
            tagAlt: '#5ac8ff'
        };
        
        function drawGrid() {
            // Clear canvas (transparent for map behind)
            ctx.clearRect(0, 0, 240, 240);
            
            // Rings
            ctx.strokeStyle = COLORS.grid;
            ctx.lineWidth = 2;
            for (let i = 1; i <= RING_COUNT; i++) {
                const r = (GRID_OUTER_RADIUS * i) / RING_COUNT;
                ctx.beginPath();
                ctx.arc(CENTER_X, CENTER_Y, r, 0, Math.PI * 2);
                ctx.stroke();
            }
            
            // Crosshairs
            ctx.beginPath();
            ctx.moveTo(CENTER_X, CENTER_Y - GRID_OUTER_RADIUS);
            ctx.lineTo(CENTER_X, CENTER_Y + GRID_OUTER_RADIUS);
            ctx.moveTo(CENTER_X - GRID_OUTER_RADIUS, CENTER_Y);
            ctx.lineTo(CENTER_X + GRID_OUTER_RADIUS, CENTER_Y);
            ctx.stroke();
            
            // Center dot
            ctx.fillStyle = COLORS.center;
            ctx.beginPath();
            ctx.arc(CENTER_X, CENTER_Y, 2, 0, Math.PI * 2);
            ctx.fill();
            
            // Cardinal labels
            ctx.fillStyle = COLORS.label;
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('N', CENTER_X, 14);
            ctx.fillText('S', CENTER_X, 238);
            ctx.textAlign = 'left';
            ctx.fillText('W', 2, CENTER_Y + 5);
            ctx.textAlign = 'right';
            ctx.fillText('E', 238, CENTER_Y + 5);
        }
        
        function latLonToScreen(lat, lon, centerLat, centerLon, outerKm) {
            const kmPerDeg = 111.0;
            const dxKm = (lon - centerLon) * kmPerDeg;
            const dyKm = (lat - centerLat) * kmPerDeg;
            const pxPerKm = GRID_OUTER_RADIUS / outerKm;
            
            const x = CENTER_X + Math.round(dxKm * pxPerKm);
            const y = CENTER_Y - Math.round(dyKm * pxPerKm);
            return { x, y };
        }
        
        function drawAircraft(ac, centerLat, centerLon, outerKm, index) {
            const pos = latLonToScreen(ac.lat, ac.lon, centerLat, centerLon, outerKm);
            
            // Check if inside outer ring
            const dx = pos.x - CENTER_X;
            const dy = pos.y - CENTER_Y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const maxR = GRID_OUTER_RADIUS - 12;
            
            let drawX = pos.x;
            let drawY = pos.y;
            
            // Use gold color if highlighted
            const isHighlighted = (index === highlightedIndex);
            const aircraftColor = isHighlighted ? '#ffc800' : COLORS.aircraft;
            
            if (dist > maxR) {
                // Draw beyond-ring dot
                const rimR = CENTER_X - 6;
                const angle = Math.atan2(dx, dy);
                drawX = CENTER_X + Math.sin(angle) * rimR;
                drawY = CENTER_Y - Math.cos(angle) * rimR;
                ctx.fillStyle = aircraftColor;
                ctx.beginPath();
                ctx.arc(drawX, drawY, 4, 0, Math.PI * 2);
                ctx.fill();
                
                // Store position for hover
                aircraftPositions.push({ x: drawX, y: drawY, ac: ac, radius: 8, index: index });
                return;
            }
            
            // Draw heading triangle
            const headingRad = ac.nose_deg * Math.PI / 180;
            const noseLen = 8;
            const tailLen = 3;
            const tailHalf = 4;
            
            const tipX = pos.x + Math.sin(headingRad) * noseLen;
            const tipY = pos.y - Math.cos(headingRad) * noseLen;
            
            const baseX = pos.x - Math.sin(headingRad) * tailLen;
            const baseY = pos.y + Math.cos(headingRad) * tailLen;
            
            const wingX = Math.cos(headingRad) * tailHalf;
            const wingY = Math.sin(headingRad) * tailHalf;
            
            ctx.fillStyle = aircraftColor;
            ctx.beginPath();
            ctx.moveTo(tipX, tipY);
            ctx.lineTo(baseX + wingX, baseY + wingY);
            ctx.lineTo(baseX - wingX, baseY - wingY);
            ctx.closePath();
            ctx.fill();
            
            // Draw speed vector
            if (ac.gs_knots > 0) {
                const trackRad = ac.track_deg * Math.PI / 180;
                const speedPx = Math.max(2, (ac.gs_knots * 1.852 * 60 / 3600 * GRID_OUTER_RADIUS / 13.3 * 0.3));
                const ex = tipX + Math.sin(trackRad) * speedPx;
                const ey = tipY - Math.cos(trackRad) * speedPx;
                
                ctx.strokeStyle = isHighlighted ? '#ffc800' : COLORS.track;
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(tipX, tipY);
                ctx.lineTo(ex, ey);
                ctx.stroke();
            }
            
            // Store position for hover (center of aircraft)
            aircraftPositions.push({ x: pos.x, y: pos.y, ac: ac, radius: 12, index: index });
        }
        
        let _fetchOnline = true;

        function _setConnectionStatus(online) {
            if (online === _fetchOnline) return;
            _fetchOnline = online;
            const el = document.getElementById('aircraft-count');
            if (!online) {
                el.textContent = 'Connection lost — retrying…';
                el.style.color = '#f87171';
            } else {
                el.style.color = '';
            }
        }

        async function updateRadar() {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 8000);
            try {
                const response = await fetch('/api/aircraft', { signal: controller.signal });
                clearTimeout(timeoutId);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const data = await response.json();
                _setConnectionStatus(true);

                aircraftPositions = []; // Clear previous positions
                drawGrid();

                data.aircraft.forEach((ac, index) => {
                    drawAircraft(ac, data.center_lat, data.center_lon, data.outer_km, index);
                });

                // Update map center and zoom
                const zoomMap = {0: 11, 1: 12, 2: 13, 3: 14};
                const zoom = zoomMap[data.range_index] || 12;
                map.setView([data.center_lat, data.center_lon], zoom);

                document.getElementById('location').textContent =
                    `Location: ${data.center_lat.toFixed(4)}, ${data.center_lon.toFixed(4)}`;
                document.getElementById('range').textContent =
                    `Range: ${data.range_label}`;
                document.getElementById('aircraft-count').textContent =
                    `Aircraft: ${data.aircraft.length}`;

                const list = document.getElementById('aircraft-list');
                list.innerHTML = data.aircraft.map((ac, index) =>
                    `<div class="aircraft-item" data-index="${index}">
                        <strong>${ac.callsign}</strong> ${ac.type}<br>
                        ${ac.alt} | ${ac.gs_knots.toFixed(0)}kt
                    </div>`
                ).join('');

                // Add hover handlers to list items
                list.querySelectorAll('.aircraft-item').forEach(item => {
                    item.addEventListener('mouseenter', () => {
                        highlightedIndex = parseInt(item.dataset.index);
                        item.classList.add('highlighted');
                        // Redraw radar with highlight
                        aircraftPositions = [];
                        drawGrid();
                        data.aircraft.forEach((ac, idx) => {
                            drawAircraft(ac, data.center_lat, data.center_lon, data.outer_km, idx);
                        });
                    });

                    item.addEventListener('mouseleave', () => {
                        highlightedIndex = -1;
                        item.classList.remove('highlighted');
                        // Redraw radar without highlight
                        aircraftPositions = [];
                        drawGrid();
                        data.aircraft.forEach((ac, idx) => {
                            drawAircraft(ac, data.center_lat, data.center_lon, data.outer_km, idx);
                        });
                    });
                });
            } catch (err) {
                clearTimeout(timeoutId);
                _setConnectionStatus(false);
                // Swallow — previous radar frame stays visible, next interval will retry
            }
        }
        
        // Initial draw
        drawGrid();

        // Update interval from .env
        const fetchIntervalMs = {{ fetch_interval_ms }};
        setInterval(updateRadar, fetchIntervalMs);
        updateRadar();
        
        // Mouse hover detection
        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            let found = false;
            for (const pos of aircraftPositions) {
                const dx = mouseX - pos.x;
                const dy = mouseY - pos.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist < pos.radius) {
                    const ac = pos.ac;
                    tooltip.innerHTML = `
                        <strong>${ac.callsign}</strong> ${ac.type}<br>
                        Alt: ${ac.alt}<br>
                        Speed: ${ac.gs_knots.toFixed(0)} kt<br>
                        Heading: ${ac.nose_deg.toFixed(0)}°<br>
                        Track: ${ac.track_deg.toFixed(0)}°<br>
                        Pos: ${ac.lat.toFixed(4)}, ${ac.lon.toFixed(4)}
                    `;
                    tooltip.style.display = 'block';
                    tooltip.style.left = (e.clientX + 15) + 'px';
                    tooltip.style.top = (e.clientY + 15) + 'px';
                    found = true;
                    break;
                }
            }
            
            if (!found) {
                tooltip.style.display = 'none';
            }
        });
        
        canvas.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
        });
    </script>
</body>
</html>
"""


class WebServer:
    """Flask web server — serves radar view and aircraft JSON API."""

    def __init__(self, host: str, port: int, location, range_manager, fetch_radius_km: float, fetch_interval_ms: int, adsb_client=None) -> None:
        self.host = host
        self.port = port
        self.server_thread = None
        self.running = False
        self.adsb_client = adsb_client
        self.location = location
        self.range_manager = range_manager
        self.fetch_radius_km = fetch_radius_km
        self.fetch_interval_ms = fetch_interval_ms

        # Setup Flask routes
        self._setup_routes()
    
    def _setup_routes(self):
        @app.route('/')
        def index():
            zoom_map = {0: 11, 1: 12, 2: 13, 3: 14}
            zoom = zoom_map.get(self.range_manager.get_range_index(), 12)

            return render_template_string(RADAR_TEMPLATE,
                                         center_lat=self.location.get_lat(),
                                         center_lon=self.location.get_lon(),
                                         zoom=zoom,
                                         fetch_interval_ms=self.fetch_interval_ms)
        
        @app.route('/api/aircraft')
        def api_aircraft():
            if self.adsb_client is None:
                return jsonify({
                    'aircraft': [],
                    'center_lat': self.location.get_lat(),
                    'center_lon': self.location.get_lon(),
                    'outer_km': self.fetch_radius_km,
                    'range_label': f'{self.fetch_radius_km:.0f}km',
                    'range_index': self.range_manager.get_range_index()
                })
            
            try:
                aircraft_list = []
                for i in range(self.adsb_client.get_aircraft_count()):
                    ac = self.adsb_client.get_aircraft_list()[i]
                    aircraft_list.append({
                        'lat': ac.lat,
                        'lon': ac.lon,
                        'nose_deg': ac.nose_deg,
                        'track_deg': ac.track_deg,
                        'gs_knots': ac.gs_knots,
                        'callsign': ac.callsign,
                        'type': ac.type,
                        'alt': ac.alt,
                        'squawk': ac.squawk
                    })
                
                return jsonify({
                    'aircraft': aircraft_list,
                    'center_lat': self.location.get_lat(),
                    'center_lon': self.location.get_lon(),
                    'outer_km': self.fetch_radius_km,
                    'range_label': f'{self.fetch_radius_km:.0f}km',
                    'range_index': self.range_manager.get_range_index()
                })
            except Exception as e:
                return jsonify({
                    'aircraft': [],
                    'center_lat': self.location.get_lat(),
                    'center_lon': self.location.get_lon(),
                    'outer_km': self.fetch_radius_km,
                    'range_label': f'{self.fetch_radius_km:.0f}km',
                    'range_index': self.range_manager.get_range_index(),
                    'error': str(e)
                })
    
    def start(self):
        """Start the web server in a background thread."""
        if self.running:
            return
        
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        logger.info("Web server: http://%s:%d", self.host, self.port)
    
    def _run_server(self):
        """Run Flask server."""
        app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
    
    def stop(self):
        """Stop the web server."""
        self.running = False
        if self.server_thread:
            self.server_thread.join(timeout=1)
