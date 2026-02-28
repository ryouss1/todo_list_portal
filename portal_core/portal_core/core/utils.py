from datetime import date, datetime, time, timezone


def parse_hhmm_to_utc(target_date: date, time_str: str) -> datetime:
    """Parse 'HH:MM' string + date into a timezone-aware UTC datetime.

    The time string is interpreted as local time (server timezone),
    then converted to UTC for storage.
    """
    t = time.fromisoformat(time_str)
    local_dt = datetime.combine(target_date, t)
    return local_dt.astimezone(timezone.utc)
