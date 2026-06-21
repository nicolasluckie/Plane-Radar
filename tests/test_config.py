"""
Unit tests for config.py.
Tests valid env, default values, and validation errors.
"""

import pytest
from unittest.mock import patch


class TestConfigDefaults:
    def test_defaults_when_no_env_set(self):
        # Patch load_dotenv to a no-op so the .env file is not loaded,
        # and clear env so no PLANERADAR_* vars bleed in from the shell.
        with patch("config.load_dotenv"), \
             patch.dict("os.environ", {}, clear=True):
            from config import load_config
            cfg = load_config()

        assert cfg.lat == 43.6777
        assert cfg.lon == -79.6248
        assert cfg.fetch_interval_ms == 3000
        assert cfg.fetch_radius_km == 25.0
        assert cfg.range_index == 1
        assert cfg.use_miles is False
        assert cfg.show_runways is True
        assert cfg.web_host == "0.0.0.0"
        assert cfg.web_port == 8080
        assert cfg.log_level == "warning"
        assert cfg.log_to_disk is False
        assert cfg.log_path == "/var/log/plane-radar/app.log"
        assert cfg.debug is False
        assert cfg.use_mock_data is False


class TestConfigValidValues:
    def test_custom_lat_lon(self):
        env = {"PLANERADAR_LAT": "51.5074", "PLANERADAR_LON": "-0.1278"}
        with patch.dict("os.environ", env, clear=False):
            from config import load_config
            cfg = load_config()
        assert cfg.lat == pytest.approx(51.5074)
        assert cfg.lon == pytest.approx(-0.1278)

    def test_debug_overrides_log_level_to_debug(self):
        env = {"PLANERADAR_DEBUG": "1", "PLANERADAR_LOG_LEVEL": "warning"}
        with patch.dict("os.environ", env, clear=False):
            from config import load_config
            cfg = load_config()
        assert cfg.log_level == "debug"
        assert cfg.debug is True

    def test_log_to_disk_enabled(self):
        env = {"PLANERADAR_LOG_TO_DISK": "1"}
        with patch.dict("os.environ", env, clear=False):
            from config import load_config
            cfg = load_config()
        assert cfg.log_to_disk is True

    def test_custom_log_path(self):
        env = {"PLANERADAR_LOG_PATH": "/logs/app.log"}
        with patch.dict("os.environ", env, clear=False):
            from config import load_config
            cfg = load_config()
        assert cfg.log_path == "/logs/app.log"

    def test_all_valid_log_levels(self):
        from config import load_config
        for level in ["debug", "info", "warning", "error", "critical"]:
            with patch.dict("os.environ", {"PLANERADAR_LOG_LEVEL": level, "PLANERADAR_DEBUG": "0"}, clear=False):
                cfg = load_config()
            assert cfg.log_level == level

    def test_use_miles_flag(self):
        with patch.dict("os.environ", {"PLANERADAR_USE_MILES": "1"}, clear=False):
            from config import load_config
            cfg = load_config()
        assert cfg.use_miles is True

    def test_all_range_indices(self):
        from config import load_config
        for i in range(4):
            with patch.dict("os.environ", {"PLANERADAR_RANGE_INDEX": str(i)}, clear=False):
                cfg = load_config()
            assert cfg.range_index == i


class TestConfigValidationErrors:
    def test_invalid_lat_raises(self):
        with patch.dict("os.environ", {"PLANERADAR_LAT": "not_a_number"}, clear=False):
            from config import load_config
            with pytest.raises(ValueError, match="PLANERADAR_LAT"):
                load_config()

    def test_invalid_lon_raises(self):
        with patch.dict("os.environ", {"PLANERADAR_LON": "abc"}, clear=False):
            from config import load_config
            with pytest.raises(ValueError, match="PLANERADAR_LON"):
                load_config()

    def test_invalid_range_index_out_of_bounds_raises(self):
        with patch.dict("os.environ", {"PLANERADAR_RANGE_INDEX": "99"}, clear=False):
            from config import load_config
            with pytest.raises(ValueError, match="PLANERADAR_RANGE_INDEX"):
                load_config()

    def test_negative_range_index_raises(self):
        with patch.dict("os.environ", {"PLANERADAR_RANGE_INDEX": "-1"}, clear=False):
            from config import load_config
            with pytest.raises(ValueError, match="PLANERADAR_RANGE_INDEX"):
                load_config()

    def test_invalid_log_level_raises(self):
        with patch.dict("os.environ", {"PLANERADAR_LOG_LEVEL": "verbose"}, clear=False):
            from config import load_config
            with pytest.raises(ValueError, match="PLANERADAR_LOG_LEVEL"):
                load_config()

    def test_invalid_web_port_raises(self):
        with patch.dict("os.environ", {"PLANERADAR_WEB_PORT": "not_a_port"}, clear=False):
            from config import load_config
            with pytest.raises(ValueError, match="PLANERADAR_WEB_PORT"):
                load_config()
