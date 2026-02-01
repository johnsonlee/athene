"""US stock market trading day check."""

from __future__ import annotations

from datetime import date, timedelta


def _us_market_holidays(year: int) -> set[date]:
    """Return US stock market holidays for a given year.

    Covers NYSE/NASDAQ observed holidays:
      New Year's Day, MLK Day, Presidents' Day, Good Friday,
      Memorial Day, Juneteenth, Independence Day, Labor Day,
      Thanksgiving, Christmas.
    """
    holidays: set[date] = set()

    # New Year's Day (Jan 1, observed)
    holidays.add(_observed(date(year, 1, 1)))

    # MLK Day — 3rd Monday of January
    holidays.add(_nth_weekday(year, 1, 0, 3))

    # Presidents' Day — 3rd Monday of February
    holidays.add(_nth_weekday(year, 2, 0, 3))

    # Good Friday — 2 days before Easter Sunday
    holidays.add(_easter(year) - timedelta(days=2))

    # Memorial Day — last Monday of May
    holidays.add(_last_weekday(year, 5, 0))

    # Juneteenth (Jun 19, observed)
    holidays.add(_observed(date(year, 6, 19)))

    # Independence Day (Jul 4, observed)
    holidays.add(_observed(date(year, 7, 4)))

    # Labor Day — 1st Monday of September
    holidays.add(_nth_weekday(year, 9, 0, 1))

    # Thanksgiving — 4th Thursday of November
    holidays.add(_nth_weekday(year, 11, 3, 4))

    # Christmas (Dec 25, observed)
    holidays.add(_observed(date(year, 12, 25)))

    return holidays


def is_us_trading_day(d: date | None = None) -> bool:
    """Return True if *d* (default: today) is a US market trading day."""
    if d is None:
        d = date.today()
    # Weekends
    if d.weekday() >= 5:
        return False
    # Holidays
    return d not in _us_market_holidays(d.year)


# ---- helpers ----

def _observed(d: date) -> date:
    """If a holiday falls on Sat, observed Fri; on Sun, observed Mon."""
    if d.weekday() == 5:      # Saturday
        return d - timedelta(days=1)
    if d.weekday() == 6:      # Sunday
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the n-th occurrence of *weekday* (0=Mon) in *month*."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of *weekday* (0=Mon) in *month*."""
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=offset)


def _easter(year: int) -> date:
    """Compute Easter Sunday using the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)
