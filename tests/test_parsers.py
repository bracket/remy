"""Tests for remy.parsers module, specifically parse_datetime_with_arithmetic."""

import pytest
from datetime import datetime, timezone

from remy.exceptions import RemyError
from remy.parsers import parse_datetime_with_arithmetic


# ============================================================================
# Plain Datetime Strings (No Arithmetic)
# ============================================================================

def test_parse_plain_date():
    """Test parsing a plain date string."""
    result = parse_datetime_with_arithmetic('2024-01-31')
    expected = datetime(2024, 1, 31, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected
    assert result.tzinfo == timezone.utc


def test_parse_plain_datetime():
    """Test parsing a plain datetime string."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00')
    expected = datetime(2024, 1, 31, 15, 30, 0, tzinfo=timezone.utc)
    assert result == expected
    assert result.tzinfo == timezone.utc


def test_parse_datetime_with_timezone_positive():
    """Test parsing datetime with positive timezone offset."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00+05:00')
    # Should be converted to UTC (subtract 5 hours)
    expected = datetime(2024, 1, 31, 10, 30, 0, tzinfo=timezone.utc)
    assert result == expected
    assert result.tzinfo == timezone.utc


def test_parse_datetime_with_timezone_negative():
    """Test parsing datetime with negative timezone offset."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00-08:00')
    # Should be converted to UTC (add 8 hours)
    expected = datetime(2024, 1, 31, 23, 30, 0, tzinfo=timezone.utc)
    assert result == expected
    assert result.tzinfo == timezone.utc


def test_parse_datetime_midnight():
    """Test parsing datetime at midnight."""
    result = parse_datetime_with_arithmetic('2024-01-31 00:00:00')
    expected = datetime(2024, 1, 31, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_leap_year():
    """Test parsing datetime on leap year date."""
    result = parse_datetime_with_arithmetic('2024-02-29')
    expected = datetime(2024, 2, 29, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Datetime Arithmetic - Addition
# ============================================================================

def test_parse_datetime_plus_days():
    """Test parsing datetime with days addition."""
    result = parse_datetime_with_arithmetic('2024-01-31 + 7 days')
    expected = datetime(2024, 2, 7, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected
    assert result.tzinfo == timezone.utc


def test_parse_datetime_plus_weeks():
    """Test parsing datetime with weeks addition."""
    result = parse_datetime_with_arithmetic('2024-12-25 + 2 weeks')
    expected = datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_plus_months():
    """Test parsing datetime with months addition."""
    result = parse_datetime_with_arithmetic('2024-01-31 + 1 month')
    expected = datetime(2024, 2, 29, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_plus_years():
    """Test parsing datetime with years addition."""
    result = parse_datetime_with_arithmetic('2024-01-31 + 1 year')
    expected = datetime(2025, 1, 31, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_plus_hours():
    """Test parsing datetime with hours addition."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 + 2 hours')
    expected = datetime(2024, 1, 31, 17, 30, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_plus_minutes():
    """Test parsing datetime with minutes addition."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 + 45 minutes')
    expected = datetime(2024, 1, 31, 16, 15, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_plus_seconds():
    """Test parsing datetime with seconds addition."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 + 90 seconds')
    expected = datetime(2024, 1, 31, 15, 31, 30, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Datetime Arithmetic - Subtraction
# ============================================================================

def test_parse_datetime_minus_days():
    """Test parsing datetime with days subtraction."""
    result = parse_datetime_with_arithmetic('2024-01-31 - 7 days')
    expected = datetime(2024, 1, 24, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_minus_weeks():
    """Test parsing datetime with weeks subtraction."""
    result = parse_datetime_with_arithmetic('2024-12-25 - 2 weeks')
    expected = datetime(2024, 12, 11, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_minus_months():
    """Test parsing datetime with months subtraction."""
    result = parse_datetime_with_arithmetic('2024-03-31 - 1 month')
    expected = datetime(2024, 2, 29, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_minus_years():
    """Test parsing datetime with years subtraction."""
    result = parse_datetime_with_arithmetic('2024-01-31 - 1 year')
    expected = datetime(2023, 1, 31, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_minus_hours():
    """Test parsing datetime with hours subtraction."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 - 2 hours')
    expected = datetime(2024, 1, 31, 13, 30, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_minus_minutes():
    """Test parsing datetime with minutes subtraction."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 - 45 minutes')
    expected = datetime(2024, 1, 31, 14, 45, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_minus_seconds():
    """Test parsing datetime with seconds subtraction."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 - 90 seconds')
    expected = datetime(2024, 1, 31, 15, 28, 30, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Chained Arithmetic Operations
# ============================================================================

def test_parse_datetime_chained_operations():
    """Test parsing datetime with chained arithmetic operations."""
    result = parse_datetime_with_arithmetic('2024-01-31 - 1 week + 3 days')
    # 2024-01-31 - 7 days = 2024-01-24
    # 2024-01-24 + 3 days = 2024-01-27
    expected = datetime(2024, 1, 27, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_chained_different_units():
    """Test parsing datetime with chained operations using different units."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 + 2 hours - 30 minutes')
    # 2024-01-31 15:30:00 + 2 hours = 2024-01-31 17:30:00
    # 2024-01-31 17:30:00 - 30 minutes = 2024-01-31 17:00:00
    expected = datetime(2024, 1, 31, 17, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_complex_chained():
    """Test parsing datetime with complex chained operations."""
    result = parse_datetime_with_arithmetic('2024-01-31 + 1 month - 2 days + 3 hours')
    # 2024-01-31 + 1 month = 2024-02-29
    # 2024-02-29 - 2 days = 2024-02-27
    # 2024-02-27 + 3 hours = 2024-02-27 03:00:00
    expected = datetime(2024, 2, 27, 3, 0, 0, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Time Format Timedeltas
# ============================================================================

def test_parse_datetime_plus_time_hhmm():
    """Test parsing datetime with HH:MM time format."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 + 01:30')
    expected = datetime(2024, 1, 31, 17, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_plus_time_hhmmss():
    """Test parsing datetime with HH:MM:SS time format."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 + 02:15:45')
    expected = datetime(2024, 1, 31, 17, 45, 45, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_plus_time_mm_only():
    """Test parsing datetime with :MM time format (minutes only)."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 + :45')
    expected = datetime(2024, 1, 31, 16, 15, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_minus_time_hhmm():
    """Test parsing datetime with HH:MM time format subtraction."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 - 01:30')
    expected = datetime(2024, 1, 31, 14, 0, 0, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Singular vs Plural Units
# ============================================================================

def test_parse_datetime_singular_day():
    """Test parsing with singular 'day' unit."""
    result = parse_datetime_with_arithmetic('2024-01-31 + 1 day')
    expected = datetime(2024, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_singular_hour():
    """Test parsing with singular 'hour' unit."""
    result = parse_datetime_with_arithmetic('2024-01-31 15:30:00 + 1 hour')
    expected = datetime(2024, 1, 31, 16, 30, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_no_space_between_number_and_unit():
    """Test parsing with no space between number and unit."""
    result = parse_datetime_with_arithmetic('2024-01-31 + 7days')
    expected = datetime(2024, 2, 7, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Whitespace Handling
# ============================================================================

def test_parse_datetime_extra_whitespace():
    """Test parsing with extra whitespace."""
    result = parse_datetime_with_arithmetic('  2024-01-31   +   7 days  ')
    expected = datetime(2024, 2, 7, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_arithmetic_minimal_whitespace():
    """Test parsing with minimal whitespace around operators."""
    result = parse_datetime_with_arithmetic('2024-01-31+7 days')
    expected = datetime(2024, 2, 7, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Error Cases
# ============================================================================

def test_parse_datetime_empty_string():
    """Test that empty string raises error."""
    with pytest.raises(RemyError, match="Datetime value cannot be empty"):
        parse_datetime_with_arithmetic('')


def test_parse_datetime_whitespace_only():
    """Test that whitespace-only string raises error."""
    with pytest.raises(RemyError, match="Datetime value cannot be empty"):
        parse_datetime_with_arithmetic('   ')


def test_parse_datetime_invalid_format():
    """Test that invalid datetime format raises error."""
    with pytest.raises(RemyError, match="Invalid datetime format"):
        parse_datetime_with_arithmetic('not-a-date')


def test_parse_datetime_invalid_date():
    """Test that invalid date values raise error."""
    with pytest.raises(RemyError, match="Invalid datetime format"):
        parse_datetime_with_arithmetic('2024-02-30')  # February doesn't have 30 days


def test_parse_datetime_invalid_timedelta_unit():
    """Test that invalid timedelta unit raises error."""
    with pytest.raises(RemyError, match="Invalid arithmetic in temporal expression"):
        parse_datetime_with_arithmetic('2024-01-31 + 7 fortnights')


def test_parse_datetime_invalid_timedelta_format():
    """Test that invalid timedelta format raises error."""
    with pytest.raises(RemyError, match="Invalid arithmetic in temporal expression"):
        parse_datetime_with_arithmetic('2024-01-31 + seven days')


def test_parse_datetime_missing_timedelta():
    """Test that missing timedelta after operator raises error."""
    with pytest.raises(RemyError, match="Invalid arithmetic in temporal expression"):
        parse_datetime_with_arithmetic('2024-01-31 +')


def test_parse_datetime_non_string_input():
    """Test that non-string input raises error."""
    with pytest.raises(RemyError, match="Expected string value"):
        parse_datetime_with_arithmetic(12345)


# ============================================================================
# Rejection of 'now' and 'today' Keywords
# ============================================================================

def test_parse_datetime_rejects_now():
    """Test that 'now' keyword is rejected."""
    with pytest.raises(RemyError, match="'now' and 'today' keywords are not supported"):
        parse_datetime_with_arithmetic('now')


def test_parse_datetime_rejects_today():
    """Test that 'today' keyword is rejected."""
    with pytest.raises(RemyError, match="'now' and 'today' keywords are not supported"):
        parse_datetime_with_arithmetic('today')


def test_parse_datetime_rejects_now_with_arithmetic():
    """Test that 'now' keyword with arithmetic is rejected."""
    with pytest.raises(RemyError, match="'now' and 'today' keywords are not supported"):
        parse_datetime_with_arithmetic('now - 2 days')


def test_parse_datetime_rejects_today_with_arithmetic():
    """Test that 'today' keyword with arithmetic is rejected."""
    with pytest.raises(RemyError, match="'now' and 'today' keywords are not supported"):
        parse_datetime_with_arithmetic('today + 1 week')


def test_parse_datetime_rejects_now_case_insensitive():
    """Test that 'now' keyword is rejected case-insensitively."""
    with pytest.raises(RemyError, match="'now' and 'today' keywords are not supported"):
        parse_datetime_with_arithmetic('NOW')


def test_parse_datetime_rejects_today_case_insensitive():
    """Test that 'today' keyword is rejected case-insensitively."""
    with pytest.raises(RemyError, match="'now' and 'today' keywords are not supported"):
        parse_datetime_with_arithmetic('ToDay')


# ============================================================================
# Edge Cases
# ============================================================================

def test_parse_datetime_across_month_boundary():
    """Test arithmetic that crosses month boundaries."""
    result = parse_datetime_with_arithmetic('2024-01-29 + 5 days')
    expected = datetime(2024, 2, 3, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_across_year_boundary():
    """Test arithmetic that crosses year boundaries."""
    result = parse_datetime_with_arithmetic('2024-12-30 + 5 days')
    expected = datetime(2025, 1, 4, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_negative_result():
    """Test arithmetic that would go to an earlier date."""
    result = parse_datetime_with_arithmetic('2024-01-05 - 10 days')
    expected = datetime(2023, 12, 26, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_large_values():
    """Test arithmetic with large values."""
    result = parse_datetime_with_arithmetic('2024-01-31 + 365 days')
    expected = datetime(2025, 1, 30, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Timezone Awareness
# ============================================================================

def test_parse_datetime_always_returns_utc():
    """Test that all returned datetimes are in UTC."""
    test_cases = [
        '2024-01-31',
        '2024-01-31 15:30:00',
        '2024-01-31 + 7 days',
        '2024-01-31 15:30:00 - 2 hours',
    ]
    
    for test_case in test_cases:
        result = parse_datetime_with_arithmetic(test_case)
        assert result.tzinfo == timezone.utc, f"Failed for: {test_case}"


def test_parse_datetime_timezone_conversion():
    """Test that timezone is properly converted to UTC."""
    # 2024-01-31 20:00:00 in New York (EST, UTC-5) should be 2024-02-01 01:00:00 UTC
    result = parse_datetime_with_arithmetic('2024-01-31 20:00:00-05:00')
    expected = datetime(2024, 2, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_with_timezone_and_arithmetic():
    """Test parsing datetime with timezone and arithmetic operations."""
    # 2024-01-31 20:00:00-05:00 + 2 hours
    # First convert to UTC: 2024-02-01 01:00:00
    # Then add 2 hours: 2024-02-01 03:00:00
    result = parse_datetime_with_arithmetic('2024-01-31 20:00:00-05:00 + 2 hours')
    expected = datetime(2024, 2, 1, 3, 0, 0, tzinfo=timezone.utc)
    assert result == expected


# ============================================================================
# Import Test
# ============================================================================

def test_import_from_remy():
    """Test that the parser can be imported from remy package."""
    from remy import parse_datetime_with_arithmetic as parser
    
    result = parser('2024-01-31')
    expected = datetime(2024, 1, 31, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected


def test_import_from_remy_parsers():
    """Test that the parser can be imported from remy.parsers module."""
    from remy.parsers import parse_datetime_with_arithmetic as parser
    
    result = parser('2024-01-31 + 7 days')
    expected = datetime(2024, 2, 7, 0, 0, 0, tzinfo=timezone.utc)
    assert result == expected
