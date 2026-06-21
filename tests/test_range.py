"""
Unit tests for radar/range.py.
All tests run without hardware access.
"""

import pytest
from radar.range import RangeManager, RANGE_PRESETS, DEFAULT_RANGE_INDEX


class TestRangeManagerInit:
    def test_default_range_index(self):
        rm = RangeManager()
        assert rm.range_index == DEFAULT_RANGE_INDEX

    def test_custom_range_index(self):
        rm = RangeManager(range_index=2)
        assert rm.range_index == 2

    def test_out_of_bounds_index_resets_to_default(self):
        rm = RangeManager(range_index=99)
        assert rm.range_index == DEFAULT_RANGE_INDEX

    def test_default_use_miles_is_false(self):
        assert RangeManager().use_miles is False

    def test_default_show_runways_is_true(self):
        assert RangeManager().show_runways is True


class TestGetCurrentRange:
    def test_returns_correct_preset_for_index(self):
        for i, preset in enumerate(RANGE_PRESETS):
            rm = RangeManager(range_index=i)
            assert rm.get_current_range() == preset

    def test_outer_km_greater_than_ring3_km(self):
        for i in range(len(RANGE_PRESETS)):
            rm = RangeManager(range_index=i)
            r = rm.get_current_range()
            assert r['outer_km'] > r['ring3_km']


class TestGetRangeIndex:
    def test_returns_set_index(self):
        rm = RangeManager(range_index=3)
        assert rm.get_range_index() == 3


class TestFormatRing3Label:
    def test_km_label(self):
        rm = RangeManager(range_index=0, use_miles=False)
        label = rm.format_ring3_label(5.0)
        assert label == "5km"

    def test_miles_label(self):
        rm = RangeManager(range_index=0, use_miles=True)
        label = rm.format_ring3_label(5.0)
        assert label == "3mi"  # 5 / 1.609344 ≈ 3.1 → rounds to 3

    def test_km_label_override_when_use_miles_true(self):
        rm = RangeManager(use_miles=True)
        label = rm.format_ring3_label(10.0, use_miles=False)
        assert label == "10km"

    def test_miles_label_override_when_use_miles_false(self):
        rm = RangeManager(use_miles=False)
        label = rm.format_ring3_label(10.0, use_miles=True)
        assert label == "6mi"  # 10 / 1.609344 ≈ 6.2 → rounds to 6

    def test_rounds_to_nearest_integer(self):
        rm = RangeManager()
        label = rm.format_ring3_label(10.4)
        assert label == "10km"
        label = rm.format_ring3_label(10.6)
        assert label == "11km"


class TestFormatCurrentRing3Label:
    def test_matches_manual_format_call(self):
        for i in range(len(RANGE_PRESETS)):
            rm = RangeManager(range_index=i)
            expected = rm.format_ring3_label(RANGE_PRESETS[i]['ring3_km'])
            assert rm.format_current_ring3_label() == expected


class TestFetchRadiusKm:
    def test_returns_positive_float(self):
        rm = RangeManager(range_index=1)
        result = rm.fetch_radius_km()
        assert isinstance(result, float)
        assert result > 0

    def test_larger_range_index_gives_larger_radius(self):
        rm_small = RangeManager(range_index=0)
        rm_large = RangeManager(range_index=3)
        assert rm_large.fetch_radius_km() > rm_small.fetch_radius_km()
