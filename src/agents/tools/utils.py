"""Utility functions for agent tools."""
from datetime import datetime


def get_drink_status(drink_from_year: int | None, drink_to_year: int | None) -> str:
    """Determine drink status for a wine based on drinking window and current year.
    Args:
        drink_from_year: Year wine becomes ready to drink
        drink_to_year: Year wine is past peak
    Returns:
        'ready', 'aging', 'past_peak', or 'unknown'
    """
    current_year = datetime.now().year
    if drink_from_year and drink_to_year:
        if current_year < drink_from_year:
            return "aging"
        elif current_year > drink_to_year:
            return "past_peak"
        else:
            return "ready"
    return "unknown"