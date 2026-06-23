"""Unit tests for radar/squawk.py."""

from radar.squawk import SQUAWK_CODES, get_squawk_meaning


class TestGetSquawkMeaning:
    def test_emergency_hijack(self):
        assert get_squawk_meaning("7500") == "HIJ"

    def test_emergency_comms_failure(self):
        assert get_squawk_meaning("7600") == "COM"

    def test_emergency_general(self):
        assert get_squawk_meaning("7700") == "EMG"

    def test_vfr_1200(self):
        assert get_squawk_meaning("1200") == "VFR"

    def test_unknown_code_returns_empty_string(self):
        assert get_squawk_meaning("9999") == ""

    def test_empty_string_returns_empty_string(self):
        assert get_squawk_meaning("") == ""

    def test_all_codes_present_in_dict(self):
        assert isinstance(SQUAWK_CODES, dict)
        assert len(SQUAWK_CODES) > 0

    def test_return_type_is_always_str(self):
        assert isinstance(get_squawk_meaning("7700"), str)
        assert isinstance(get_squawk_meaning("0000"), str)
        assert isinstance(get_squawk_meaning("XXXX"), str)
