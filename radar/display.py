"""
Radar display rendering ported from radar_display.cpp.
Maintains exact pixel-for-pixel visualization.
"""

import math

from . import theme


class RadarDisplay:
    """Radar display renderer."""

    def __init__(self, display_driver, location, range_manager) -> None:
        self.display = display_driver
        self.location = location
        self.range_manager = range_manager
        self.init_palette()

    def init_palette(self):
        """Initialize color palette from RGB values."""
        theme.COLOR_BACKGROUND = self.display.color565(theme.BG_R, theme.BG_G, theme.BG_B)
        theme.COLOR_GRID = self.display.color565(theme.GRID_R, theme.GRID_G, theme.GRID_B)
        theme.COLOR_LABEL = self.display.color565(255, 255, 255)
        theme.COLOR_CENTER = self.display.color565(255, 255, 255)

        # Use RGB directly (kernel overlay handles color format)
        theme.COLOR_AIRCRAFT = self.display.color565(
            theme.AIRCRAFT_R, theme.AIRCRAFT_G, theme.AIRCRAFT_B
        )

        theme.COLOR_TRACK_VECTOR = self.display.color565(
            theme.TRACK_R, theme.TRACK_G, theme.TRACK_B
        )
        theme.COLOR_TAG_TYPE = self.display.color565(
            theme.TAG_TYPE_R, theme.TAG_TYPE_G, theme.TAG_TYPE_B
        )
        theme.COLOR_TAG_ALTITUDE = self.display.color565(
            theme.TAG_ALT_R, theme.TAG_ALT_G, theme.TAG_ALT_B
        )
        theme.COLOR_TAG_SQUAWK = self.display.color565(
            theme.TAG_SQUAWK_R, theme.TAG_SQUAWK_G, theme.TAG_SQUAWK_B
        )
        theme.COLOR_RUNWAY = self.display.color565(theme.RUNWAY_R, theme.RUNWAY_G, theme.RUNWAY_B)
        theme.COLOR_RUNWAY_LABEL = self.display.color565(
            theme.RUNWAY_LABEL_R, theme.RUNWAY_LABEL_G, theme.RUNWAY_LABEL_B
        )

    def offset_km_from_center(self, lat, lon):
        """Calculate offset from center in km."""
        km_per_deg = 111.0
        center_lat_rad = math.radians(self.location.get_lat())
        dx_km = (lon - self.location.get_lon()) * km_per_deg * math.cos(center_lat_rad)
        dy_km = (lat - self.location.get_lat()) * km_per_deg
        dist_km = math.sqrt(dx_km * dx_km + dy_km * dy_km)
        return dx_km, dy_km, dist_km

    def inner_ring_max_km(self):
        """Calculate max distance for inner ring."""
        outer_km = self.range_manager.get_current_range()["outer_km"]
        inset_ratio = (
            theme.GRID_OUTER_RADIUS - theme.AIRCRAFT_INSIDE_RING_INSET_PX
        ) / theme.GRID_OUTER_RADIUS
        return outer_km * inset_ratio

    def lat_lon_to_screen(self, lat, lon):
        """Convert lat/lon to screen coordinates."""
        outer_km = self.range_manager.get_current_range()["outer_km"]
        px_per_km = theme.GRID_OUTER_RADIUS / outer_km

        dx_km, dy_km, _ = self.offset_km_from_center(lat, lon)

        x = theme.CENTER_X + int(round(dx_km * px_per_km))
        y = theme.CENTER_Y - int(round(dy_km * px_per_km))
        return x, y

    def is_inside_outer_ring_km(self, dist_km):
        """Check if distance is inside outer ring."""
        return dist_km <= self.inner_ring_max_km()

    def dist_sq_from_center(self, x, y):
        """Calculate squared distance from center."""
        dx = x - theme.CENTER_X
        dy = y - theme.CENTER_Y
        return dx * dx + dy * dy

    def is_inside_outer_ring(self, x, y):
        """Check if point is inside outer ring."""
        max_r = theme.GRID_OUTER_RADIUS - theme.AIRCRAFT_INSIDE_RING_INSET_PX
        return self.dist_sq_from_center(x, y) <= max_r * max_r

    def beyond_ring_edge_dot_from_lat_lon(self, lat, lon):
        """Calculate screen position for beyond-ring dot."""
        dx_km, dy_km, dist_km = self.offset_km_from_center(lat, lon)

        if dist_km < 0.01:
            return None
        if self.is_inside_outer_ring_km(dist_km):
            return None

        cx, cy = theme.CENTER_X, theme.CENTER_Y
        rim_r = theme.CENTER_X - theme.BEYOND_RING_SCREEN_MARGIN_PX
        angle_rad = math.atan2(dx_km, dy_km)

        x = cx + int(round(math.sin(angle_rad) * rim_r))
        y = cy - int(round(math.cos(angle_rad) * rim_r))
        return x, y

    def speed_line_length_px(self, gs_knots):
        """Calculate speed vector length in pixels."""
        if gs_knots <= 0:
            return 0

        km_per_knot_per_horizon = 1.852 * theme.AIRCRAFT_TRACK_HORIZON_SEC / 3600.0
        px = (
            gs_knots
            * km_per_knot_per_horizon
            * theme.GRID_OUTER_RADIUS
            / theme.AIRCRAFT_TRACK_REF_OUTER_KM
            * theme.AIRCRAFT_TRACK_LENGTH_SCALE
        )

        length = int(px + 0.5)
        if length < theme.AIRCRAFT_SPEED_LINE_MIN_PX:
            return theme.AIRCRAFT_SPEED_LINE_MIN_PX
        return length

    def nose_tip(self, cx, cy, heading_deg):
        """Calculate nose tip position."""
        rad = math.radians(heading_deg)
        x = cx + int(round(math.sin(rad) * theme.AIRCRAFT_NOSE_LEN_PX))
        y = cy - int(round(math.cos(rad) * theme.AIRCRAFT_NOSE_LEN_PX))
        return x, y

    def draw_heading_triangle(self, cx, cy, heading_deg, color):
        """Draw aircraft heading triangle."""
        rad = math.radians(heading_deg)
        sin_h = math.sin(rad)
        cos_h = math.cos(rad)

        tip_x, tip_y = self.nose_tip(cx, cy, heading_deg)

        base_x = cx - int(round(sin_h * theme.AIRCRAFT_TAIL_LEN_PX))
        base_y = cy + int(round(cos_h * theme.AIRCRAFT_TAIL_LEN_PX))

        wing_x = int(round(cos_h * theme.AIRCRAFT_TAIL_HALF_PX))
        wing_y = int(round(sin_h * theme.AIRCRAFT_TAIL_HALF_PX))

        self.display.triangle(
            tip_x, tip_y, base_x + wing_x, base_y + wing_y, base_x - wing_x, base_y - wing_y, color
        )

    def draw_speed_vector(self, cx, cy, heading_deg, track_deg, gs_knots, color):
        """Draw speed vector line."""
        length = self.speed_line_length_px(gs_knots)
        if length <= 0:
            return

        tip_x, tip_y = self.nose_tip(cx, cy, heading_deg)

        rad = math.radians(track_deg)
        ex = tip_x + int(round(math.sin(rad) * length))
        ey = tip_y - int(round(math.cos(rad) * length))

        # Clip to outer ring
        if not self.is_inside_outer_ring(ex, ey):
            # Simple clipping: if outside, don't draw
            return

        self.display.line(
            tip_x, tip_y, ex, ey, color, width=int(theme.AIRCRAFT_TRACK_LINE_HALF_WIDTH * 2)
        )

    def draw_grid_ring(self, cx, cy, r, color):
        """Draw grid ring."""
        if r <= 0:
            return
        thickness = max(1, int(theme.GRID_STROKE_HALF_WIDTH * 2))
        for i in range(thickness):
            if r - i > 0:
                self.display.circle(cx, cy, r - i, color, width=1)

    def draw_rings(self, cx, cy, outer_radius):
        """Draw concentric rings."""
        for i in range(1, theme.RING_COUNT + 1):
            r = (outer_radius * i) // theme.RING_COUNT
            self.draw_grid_ring(cx, cy, r, theme.COLOR_GRID)

    def draw_crosshairs(self, cx, cy, radius, color):
        """Draw crosshairs."""
        width = int(theme.GRID_STROKE_HALF_WIDTH * 2)
        self.display.line(cx, cy - radius, cx, cy + radius, color, width)
        self.display.line(cx - radius, cy, cx + radius, cy, color, width)

    def draw_center_dot(self, cx, cy):
        """Draw center dot."""
        self.display.fill_circle(cx, cy, theme.CENTER_DOT_RADIUS, theme.COLOR_CENTER)

    def draw_cardinal_labels(self):
        """Draw N/S/E/W labels."""
        cx, cy = theme.CENTER_X, theme.CENTER_Y
        edge = theme.SIZE - 1

        # Use bold font for cardinal labels
        font = self.display.font_bold

        # N (centered horizontally at top, bumped right 1px)
        bbox = font.getbbox("N")
        text_width = bbox[2] - bbox[0]
        self.display.text(
            "N",
            cx - text_width // 2 + 1,
            theme.CARDINAL_NORTH_OFFSET_Y,
            theme.COLOR_LABEL,
            font=font,
        )

        # S (centered horizontally at bottom, bumped right 1px)
        bbox = font.getbbox("S")
        text_width = bbox[2] - bbox[0]
        self.display.text(
            "S",
            cx - text_width // 2 + 1,
            edge + theme.CARDINAL_SOUTH_OFFSET_Y - 14,
            theme.COLOR_LABEL,
            font=font,
        )

        # W (centered vertically at left, bumped up 3px)
        bbox = font.getbbox("W")
        text_height = bbox[3] - bbox[1]
        self.display.text("W", 0, cy - text_height // 2 - 3, theme.COLOR_LABEL, font=font)

        # E (centered vertically at right, bumped left 3px, up 2px)
        bbox = font.getbbox("E")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        self.display.text(
            "E", edge - text_width - 3, cy - text_height // 2 - 2, theme.COLOR_LABEL, font=font
        )

    def draw_scale_label(self, cx, cy, outer_radius):
        """Draw scale label with black background."""
        label = self.range_manager.format_current_ring3_label()
        font = self.display.font_bold if self.display.font_bold else self.display.font

        # Get text bounding box
        bbox = font.getbbox(label)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center horizontally at right edge, bumped up 2px
        bg_padding = 2
        box_width = text_width + bg_padding * 2
        box_height = text_height + bg_padding * 2

        # Position the box
        box_x = cx + outer_radius - theme.SCALE_GAP_FROM_OUTER_RING - box_width
        box_y = cy - box_height // 2 - 2

        # Draw black background rectangle
        self.display.rect(
            box_x, box_y, box_width, box_height, theme.COLOR_BACKGROUND, fill=theme.COLOR_BACKGROUND
        )

        # Draw text centered in the box
        text_x = box_x + bg_padding
        text_y = box_y + bg_padding
        self.display.text(label, text_x, text_y, theme.COLOR_GRID, font=font)

    def draw_static_grid(self):
        """Draw static grid elements."""
        cx, cy = theme.CENTER_X, theme.CENTER_Y
        grid_r = theme.GRID_OUTER_RADIUS

        self.display.fill(theme.COLOR_BACKGROUND)
        self.draw_rings(cx, cy, grid_r)
        self.draw_crosshairs(cx, cy, grid_r, theme.COLOR_GRID)
        self.draw_center_dot(cx, cy)
        self.draw_scale_label(cx, cy, grid_r)

    def draw_beyond_ring_dot(self, x, y):
        """Draw beyond-ring dot."""
        self.display.fill_circle(x, y, theme.BEYOND_RING_DOT_RADIUS_PX, theme.COLOR_AIRCRAFT)

    def _check_collision(self, rect, existing_rects):
        """Check if a rectangle collides with any existing rectangles."""
        x1, y1, w1, h1 = rect
        for x2, y2, w2, h2 in existing_rects:
            if not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1):
                return True
        return False

    def draw_aircraft_tag(self, x, y, aircraft, existing_tags=None):
        """Draw aircraft tag with collision detection."""
        if existing_tags is None:
            existing_tags = []

        font_bold = self.display.font_bold if self.display.font_bold else self.display.font
        font_regular = self.display.font

        # Tag dimensions (approximate, now 4 lines tall)
        tag_width = 40
        tag_height = 40
        gap = theme.AIRCRAFT_NOSE_LEN_PX + theme.AIRCRAFT_LABEL_GAP_PX

        # Try different positions: right, left, above, below
        positions = [
            (x + gap, y - 10),  # Right (default)
            (x - gap - tag_width, y - 10),  # Left
            (x - tag_width // 2, y - gap - tag_height),  # Above
            (x - tag_width // 2, y + gap),  # Below
        ]

        # Find a non-colliding position
        tag_x, tag_y = positions[0]
        for px, py in positions:
            # Check if this position would collide
            test_rect = (px, py, tag_width, tag_height)
            if not self._check_collision(test_rect, existing_tags):
                tag_x, tag_y = px, py
                break

        # Add this tag's bounding box to existing tags
        existing_tags.append((tag_x, tag_y, tag_width, tag_height))

        # Draw the tag at the chosen position
        if aircraft.callsign:
            self.display.text(aircraft.callsign, tag_x, tag_y, theme.COLOR_LABEL, font=font_bold)

        if aircraft.type:
            self.display.text(
                aircraft.type, tag_x, tag_y + 12, theme.COLOR_TAG_TYPE, font=font_regular
            )

        if aircraft.alt:
            self.display.text(
                aircraft.alt, tag_x, tag_y + 24, theme.COLOR_TAG_ALTITUDE, font=font_bold
            )

        if aircraft.squawk:
            self.display.text(
                aircraft.squawk, tag_x, tag_y + 36, theme.COLOR_TAG_SQUAWK, font=font_bold
            )

    def draw_aircraft(self, aircraft_list):
        """Draw all aircraft."""
        # Separate into inside-ring and beyond-ring
        inside_items = []
        beyond_dots = []

        for ac in aircraft_list:
            dx_km, dy_km, dist_km = self.offset_km_from_center(ac.lat, ac.lon)

            if self.is_inside_outer_ring_km(dist_km):
                x, y = self.lat_lon_to_screen(ac.lat, ac.lon)
                inside_items.append((ac, x, y, self.dist_sq_from_center(x, y)))
            else:
                dot_pos = self.beyond_ring_edge_dot_from_lat_lon(ac.lat, ac.lon)
                if dot_pos:
                    beyond_dots.append((dot_pos, self.dist_sq_from_center(*dot_pos)))

        # Sort beyond dots by distance (far first)
        beyond_dots.sort(key=lambda x: x[1], reverse=True)
        for (x, y), _ in beyond_dots:
            self.draw_beyond_ring_dot(x, y)

        # Sort inside items by distance (far first)
        inside_items.sort(key=lambda x: x[3], reverse=True)

        # Track tag bounding boxes for collision detection
        existing_tags = []

        # Draw speed vectors and triangles
        for ac, x, y, _ in inside_items:
            self.draw_speed_vector(
                x, y, ac.nose_deg, ac.track_deg, ac.gs_knots, theme.COLOR_TRACK_VECTOR
            )
            self.draw_heading_triangle(x, y, ac.nose_deg, theme.COLOR_AIRCRAFT)

        # Draw tags on top with collision detection
        for ac, x, y, _ in inside_items:
            self.draw_aircraft_tag(x, y, ac, existing_tags)

    def draw(self, aircraft_list):
        """Draw complete radar display."""
        self.init_palette()
        self.draw_static_grid()
        self.display.save_buffer()  # Save static grid
        self.draw_aircraft(aircraft_list)
        self.draw_cardinal_labels()  # Draw on top of aircraft
        self.display.show()

    def refresh_aircraft(self, aircraft_list):
        """Refresh aircraft only without redrawing static grid."""
        self.init_palette()
        self.display.restore_buffer()  # Restore static grid
        self.draw_aircraft(aircraft_list)
        self.draw_cardinal_labels()  # Draw on top of aircraft
        self.display.show()
