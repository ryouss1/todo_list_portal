"""Re-export from portal_core for backward compatibility."""

from typing import Tuple

from portal_core.core.utils import parse_hhmm_to_utc  # noqa: F401


def seconds_to_hm(seconds: int) -> Tuple[int, int]:
    """Convert seconds to an (hours, minutes) tuple.

    Returns:
        Tuple of (hours, minutes) with sub-minute fractions truncated.

    Example:
        >>> seconds_to_hm(3725)
        (1, 2)
    """
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return h, m
