"""Squawk code meanings shared between display and web interfaces."""

# Common transponder codes and their short meanings
SQUAWK_CODES: dict[str, str] = {
    "0000": "ERR",
    "7500": "HIJ",
    "7600": "COM",
    "7700": "EMG",
    "7777": "MIL",
    "1200": "VFR",
    "2000": "IFR",
    "4000": "DEV",
    "7000": "VFR",
    "0021": "TST",
    "0022": "TST",
    "0023": "TST",
    "7776": "MIL",
    "7701": "EMG",
    "7702": "EMG",
}


def get_squawk_meaning(squawk: str) -> str:
    """Return the shortcode meaning for a squawk code, or empty string if unknown."""
    return SQUAWK_CODES.get(squawk, "")
