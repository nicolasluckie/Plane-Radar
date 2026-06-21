"""
Unit tests for services/adsb_client.py.
All tests run without hardware or network access.
"""

import pytest
from unittest.mock import MagicMock, patch

from services.adsb_client import ADSBClient, Aircraft


# ---------------------------------------------------------------------------
# Aircraft dataclass defaults
# ---------------------------------------------------------------------------

class TestAircraftDefaults:
    def test_default_values(self):
        ac = Aircraft()
        assert ac.lat == 0.0
        assert ac.lon == 0.0
        assert ac.nose_deg == 0.0
        assert ac.track_deg == 0.0
        assert ac.gs_knots == 0.0
        assert ac.callsign == ""
        assert ac.type == ""
        assert ac.alt == ""
        assert ac.squawk == ""


# ---------------------------------------------------------------------------
# read_json_float
# ---------------------------------------------------------------------------

class TestReadJsonFloat:
    def setup_method(self):
        self.client = ADSBClient()

    def test_returns_float_for_int(self):
        assert self.client.read_json_float({"gs": 450}, "gs") == 450.0

    def test_returns_float_for_float(self):
        assert self.client.read_json_float({"gs": 450.5}, "gs") == 450.5

    def test_returns_none_for_missing_key(self):
        assert self.client.read_json_float({}, "gs") is None

    def test_returns_none_for_string_value(self):
        assert self.client.read_json_float({"gs": "fast"}, "gs") is None

    def test_returns_none_for_none_value(self):
        assert self.client.read_json_float({"gs": None}, "gs") is None


# ---------------------------------------------------------------------------
# pick_nose_heading
# ---------------------------------------------------------------------------

class TestPickNoseHeading:
    def setup_method(self):
        self.client = ADSBClient()

    def test_prefers_true_heading(self):
        plane = {"true_heading": 180.0, "track": 90.0}
        assert self.client.pick_nose_heading(plane) == 180.0

    def test_falls_back_to_mag_heading(self):
        plane = {"mag_heading": 270.0, "track": 90.0}
        assert self.client.pick_nose_heading(plane) == 270.0

    def test_falls_back_to_track(self):
        plane = {"track": 45.0}
        assert self.client.pick_nose_heading(plane) == 45.0

    def test_returns_zero_when_no_fields(self):
        assert self.client.pick_nose_heading({}) == 0.0


# ---------------------------------------------------------------------------
# pick_track_heading
# ---------------------------------------------------------------------------

class TestPickTrackHeading:
    def setup_method(self):
        self.client = ADSBClient()

    def test_prefers_track(self):
        plane = {"track": 90.0, "true_heading": 180.0}
        assert self.client.pick_track_heading(plane) == 90.0

    def test_falls_back_to_true_heading(self):
        plane = {"true_heading": 180.0}
        assert self.client.pick_track_heading(plane) == 180.0

    def test_returns_zero_when_no_fields(self):
        assert self.client.pick_track_heading({}) == 0.0


# ---------------------------------------------------------------------------
# pick_ground_speed
# ---------------------------------------------------------------------------

class TestPickGroundSpeed:
    def setup_method(self):
        self.client = ADSBClient()

    def test_prefers_gs(self):
        plane = {"gs": 480.0, "tas": 500.0}
        assert self.client.pick_ground_speed(plane) == 480.0

    def test_falls_back_to_tas(self):
        plane = {"tas": 500.0, "ias": 490.0}
        assert self.client.pick_ground_speed(plane) == 500.0

    def test_falls_back_to_ias(self):
        plane = {"ias": 490.0}
        assert self.client.pick_ground_speed(plane) == 490.0

    def test_returns_zero_when_no_fields(self):
        assert self.client.pick_ground_speed({}) == 0.0


# ---------------------------------------------------------------------------
# is_on_ground
# ---------------------------------------------------------------------------

class TestIsOnGround:
    def setup_method(self):
        self.client = ADSBClient()

    def test_true_when_alt_baro_is_ground_string(self):
        assert self.client.is_on_ground({"alt_baro": "ground"}) is True

    def test_false_when_alt_baro_is_numeric(self):
        assert self.client.is_on_ground({"alt_baro": 35000}) is False

    def test_false_when_alt_baro_missing(self):
        assert self.client.is_on_ground({}) is False

    def test_false_when_alt_baro_is_other_string(self):
        assert self.client.is_on_ground({"alt_baro": "unknown"}) is False


# ---------------------------------------------------------------------------
# format_altitude_tag
# ---------------------------------------------------------------------------

class TestFormatAltitudeTag:
    def setup_method(self):
        self.client = ADSBClient()

    def test_ground_returns_gnd(self):
        assert self.client.format_altitude_tag({"alt_baro": "ground"}) == "GND"

    def test_numeric_alt_baro_formatted(self):
        assert self.client.format_altitude_tag({"alt_baro": 35000}) == "35000 ft"

    def test_rounds_altitude(self):
        assert self.client.format_altitude_tag({"alt_baro": 34999.6}) == "35000 ft"

    def test_falls_back_to_alt_geom(self):
        assert self.client.format_altitude_tag({"alt_geom": 10000}) == "10000 ft"

    def test_empty_string_when_no_altitude(self):
        assert self.client.format_altitude_tag({}) == ""


# ---------------------------------------------------------------------------
# copy_json_string_trimmed
# ---------------------------------------------------------------------------

class TestCopyJsonStringTrimmed:
    def setup_method(self):
        self.client = ADSBClient()

    def test_trims_trailing_spaces(self):
        assert self.client.copy_json_string_trimmed({"flight": "AC123   "}, "flight") == "AC123"

    def test_truncates_to_max_len(self):
        result = self.client.copy_json_string_trimmed({"flight": "ABCDEFGHIJK"}, "flight", max_len=5)
        assert result == "ABCDE"

    def test_returns_empty_for_missing_key(self):
        assert self.client.copy_json_string_trimmed({}, "flight") == ""

    def test_returns_empty_for_non_string_value(self):
        assert self.client.copy_json_string_trimmed({"flight": 12345}, "flight") == ""


# ---------------------------------------------------------------------------
# fill_tag_fields
# ---------------------------------------------------------------------------

class TestFillTagFields:
    def setup_method(self):
        self.client = ADSBClient()

    def test_fills_callsign_from_flight(self):
        ac = Aircraft()
        self.client.fill_tag_fields(ac, {"flight": "AC123", "t": "B738", "alt_baro": 35000, "squawk": "1234"})
        assert ac.callsign == "AC123"
        assert ac.type == "B738"
        assert ac.alt == "35000 ft"
        assert ac.squawk == "1234"

    def test_falls_back_callsign_to_hex(self):
        ac = Aircraft()
        self.client.fill_tag_fields(ac, {"hex": "ABC123", "alt_baro": 5000})
        assert ac.callsign == "ABC123"

    def test_empty_callsign_when_neither_field_present(self):
        ac = Aircraft()
        self.client.fill_tag_fields(ac, {})
        assert ac.callsign == ""


# ---------------------------------------------------------------------------
# fetch_update — mocked HTTP
# ---------------------------------------------------------------------------

class TestFetchUpdate:
    def setup_method(self):
        self.client = ADSBClient()

    def test_returns_true_and_populates_aircraft_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ac": [
                {"lat": 43.5, "lon": -79.9, "gs": 480, "track": 90, "true_heading": 90,
                 "flight": "AC001", "t": "B738", "alt_baro": 35000, "squawk": "1234"},
            ]
        }
        with patch("services.adsb_client.requests.get", return_value=mock_response):
            result = self.client.fetch_update(43.6777, -79.6248, 25.0)

        assert result is True
        assert self.client.get_aircraft_count() == 1
        ac = self.client.get_aircraft_list()[0]
        assert ac.lat == 43.5
        assert ac.callsign == "AC001"

    def test_skips_aircraft_missing_lat_lon(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ac": [{"gs": 480}]  # no lat/lon
        }
        with patch("services.adsb_client.requests.get", return_value=mock_response):
            self.client.fetch_update(43.6777, -79.6248, 25.0)

        assert self.client.get_aircraft_count() == 0

    def test_skips_grounded_aircraft(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ac": [
                {"lat": 43.5, "lon": -79.9, "alt_baro": "ground"},
            ]
        }
        with patch("services.adsb_client.requests.get", return_value=mock_response):
            self.client.fetch_update(43.6777, -79.6248, 25.0)

        assert self.client.get_aircraft_count() == 0

    def test_raises_on_network_error(self):
        import requests as req
        with patch("services.adsb_client.requests.get", side_effect=req.RequestException("timeout")):
            with pytest.raises(RuntimeError, match="ADS-B fetch error"):
                self.client.fetch_update(43.6777, -79.6248, 25.0)

    def test_empty_ac_list_returns_true_with_zero_count(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ac": []}
        with patch("services.adsb_client.requests.get", return_value=mock_response):
            result = self.client.fetch_update(43.6777, -79.6248, 25.0)

        assert result is True
        assert self.client.get_aircraft_count() == 0
