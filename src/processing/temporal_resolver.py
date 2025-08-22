"""
Temporal resolution system for converting relative and absolute time references.
"""
import re
import pytz
from datetime import datetime, timedelta, date, time
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from core.config import get_config
from core.logging import get_logger

logger = get_logger(__name__)


class TemporalType(Enum):
    """Types of temporal expressions."""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    RECURRING = "recurring"
    DURATION = "duration"
    RANGE = "range"


@dataclass
class TemporalInfo:
    """Information about a temporal expression."""
    original_text: str
    temporal_type: TemporalType
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    duration: Optional[timedelta] = None
    timezone: Optional[str] = None
    confidence: float = 0.0
    recurrence_pattern: Optional[str] = None
    is_recurring: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TemporalResolver:
    """Resolves temporal expressions in text to absolute datetime objects."""
    
    def __init__(self, reference_time: Optional[datetime] = None, timezone: Optional[str] = None):
        """
        Initialize temporal resolver.
        
        Args:
            reference_time: Reference time for relative calculations (defaults to now)
            timezone: Default timezone (defaults to config or UTC)
        """
        self.config = get_config()
        self.logger = logger
        
        # Set reference time (current time if not provided)
        self.reference_time = reference_time or datetime.now()
        
        # Set timezone
        if timezone:
            self.timezone = timezone
        else:
            self.timezone = getattr(self.config.memory, 'default_timezone', 'UTC')
        
        try:
            self.tz = pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            self.logger.warning(f"Unknown timezone: {self.timezone}, using UTC")
            self.timezone = 'UTC'
            self.tz = pytz.UTC
        
        # Ensure reference_time is timezone-aware
        if self.reference_time.tzinfo is None:
            self.reference_time = self.tz.localize(self.reference_time)
        
        self.logger.info(f"TemporalResolver initialized with timezone: {self.timezone}")
    
    def parse_temporal_expressions(self, text: str) -> List[TemporalInfo]:
        """
        Parse all temporal expressions in text.
        
        Args:
            text: Input text to parse
            
        Returns:
            List of TemporalInfo objects
        """
        temporal_expressions = []
        
        # Find all potential temporal expressions
        expressions = self._extract_temporal_candidates(text)
        
        for expr_text, start_pos, end_pos in expressions:
            temporal_info = self.parse_temporal_expression(expr_text)
            if temporal_info:
                temporal_info.metadata['position'] = (start_pos, end_pos)
                temporal_expressions.append(temporal_info)
        
        self.logger.debug(f"Found {len(temporal_expressions)} temporal expressions in text")
        return temporal_expressions
    
    def parse_temporal_expression(self, expr: str) -> Optional[TemporalInfo]:
        """
        Parse a single temporal expression.
        
        Args:
            expr: Temporal expression text
            
        Returns:
            TemporalInfo object or None if not parseable
        """
        expr = expr.strip().lower()
        
        # Try different parsing strategies
        parsers = [
            self._parse_relative_expression,
            self._parse_absolute_expression,
            self._parse_recurring_expression,
            self._parse_duration_expression,
            self._parse_range_expression
        ]
        
        for parser in parsers:
            try:
                result = parser(expr)
                if result:
                    self.logger.debug(f"Parsed '{expr}' as {result.temporal_type.value}")
                    return result
            except Exception as e:
                self.logger.debug(f"Parser {parser.__name__} failed for '{expr}': {e}")
                continue
        
        self.logger.debug(f"Could not parse temporal expression: '{expr}'")
        return None
    
    def _extract_temporal_candidates(self, text: str) -> List[Tuple[str, int, int]]:
        """Extract potential temporal expressions from text."""
        candidates = []
        
        # Patterns for temporal expressions
        patterns = [
            # Relative time
            r'\b(tomorrow|yesterday|today|tonight)\b',
            r'\b(next|last|this)\s+(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(in|after)\s+(\d+)\s+(minutes?|hours?|days?|weeks?|months?|years?)\b',
            r'\b(\d+)\s+(minutes?|hours?|days?|weeks?|months?|years?)\s+(ago|from now)\b',
            
            # Absolute time
            r'\b\d{1,2}:\d{2}\s*(am|pm)?\b',
            r'\b\d{1,2}:\d{2}:\d{2}\s*(am|pm)?\b',
            r'\b\d{1,2}\s*(am|pm)\b',  # Just "3 pm"
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(,\s*\d{4})?\b',
            
            # Days of week
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            
            # Recurring patterns
            r'\bevery\s+(day|week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\bdaily|weekly|monthly|yearly|annually\b',
            
            # Duration
            r'\bfor\s+(\d+)\s+(minutes?|hours?|days?|weeks?|months?|years?)\b',
            
            # Time ranges
            r'\bfrom\s+\d{1,2}:\d{2}\s*(am|pm)?\s+to\s+\d{1,2}:\d{2}\s*(am|pm)?\b',
            r'\bbetween\s+\d{1,2}:\d{2}\s*(am|pm)?\s+and\s+\d{1,2}:\d{2}\s*(am|pm)?\b',
            r'\bfrom\s+\d{1,2}\s*(am|pm)?\s+to\s+\d{1,2}\s*(am|pm)?\b',
            r'\bbetween\s+\d{1,2}\s*(am|pm)?\s+and\s+\d{1,2}\s*(am|pm)?\b'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                candidates.append((match.group(), match.start(), match.end()))
        
        # Remove duplicates and overlaps
        candidates = self._remove_overlapping_candidates(candidates)
        
        return candidates
    
    def _remove_overlapping_candidates(self, candidates: List[Tuple[str, int, int]]) -> List[Tuple[str, int, int]]:
        """Remove overlapping candidate expressions, keeping the longest ones."""
        if not candidates:
            return []
        
        # Sort by start position
        candidates.sort(key=lambda x: x[1])
        
        non_overlapping = []
        for text, start, end in candidates:
            # Check if this candidate overlaps with any already selected
            overlaps = False
            for _, prev_start, prev_end in non_overlapping:
                if start < prev_end and end > prev_start:  # Overlap detected
                    # Keep the longer expression
                    if end - start > prev_end - prev_start:
                        # Remove the previous shorter one
                        non_overlapping = [(t, s, e) for t, s, e in non_overlapping 
                                          if not (s == prev_start and e == prev_end)]
                    else:
                        overlaps = True
                    break
            
            if not overlaps:
                non_overlapping.append((text, start, end))
        
        return non_overlapping
    
    def _parse_relative_expression(self, expr: str) -> Optional[TemporalInfo]:
        """Parse relative temporal expressions."""
        patterns = {
            # Simple relative terms
            r'^tomorrow$': lambda: self.reference_time + timedelta(days=1),
            r'^yesterday$': lambda: self.reference_time - timedelta(days=1),
            r'^today$': lambda: self.reference_time,
            r'^tonight$': lambda: self.reference_time.replace(hour=20, minute=0, second=0, microsecond=0),
            
            # Next/last/this + unit
            r'^next\s+week$': lambda: self.reference_time + timedelta(weeks=1),
            r'^last\s+week$': lambda: self.reference_time - timedelta(weeks=1),
            r'^this\s+week$': lambda: self.reference_time,
            r'^next\s+month$': lambda: self._add_months(self.reference_time, 1),
            r'^last\s+month$': lambda: self._add_months(self.reference_time, -1),
            r'^this\s+month$': lambda: self.reference_time,
            r'^next\s+year$': lambda: self.reference_time.replace(year=self.reference_time.year + 1),
            r'^last\s+year$': lambda: self.reference_time.replace(year=self.reference_time.year - 1),
            r'^this\s+year$': lambda: self.reference_time,
        }
        
        for pattern, calc_func in patterns.items():
            if re.match(pattern, expr):
                try:
                    dt = calc_func()
                    return TemporalInfo(
                        original_text=expr,
                        temporal_type=TemporalType.RELATIVE,
                        start_datetime=dt,
                        timezone=self.timezone,
                        confidence=0.9
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to calculate relative time for '{expr}': {e}")
                    continue
        
        # Pattern: in/after X units
        match = re.match(r'^(?:in|after)\s+(\d+)\s+(minutes?|hours?|days?|weeks?|months?|years?)$', expr)
        if match:
            amount = int(match.group(1))
            unit = match.group(2).rstrip('s')  # Remove plural 's'
            
            try:
                dt = self._add_time_unit(self.reference_time, amount, unit)
                return TemporalInfo(
                    original_text=expr,
                    temporal_type=TemporalType.RELATIVE,
                    start_datetime=dt,
                    timezone=self.timezone,
                    confidence=0.85
                )
            except Exception as e:
                self.logger.debug(f"Failed to add time unit for '{expr}': {e}")
        
        # Pattern: X units ago
        match = re.match(r'^(\d+)\s+(minutes?|hours?|days?|weeks?|months?|years?)\s+ago$', expr)
        if match:
            amount = int(match.group(1))
            unit = match.group(2).rstrip('s')  # Remove plural 's'
            
            try:
                dt = self._add_time_unit(self.reference_time, -amount, unit)
                return TemporalInfo(
                    original_text=expr,
                    temporal_type=TemporalType.RELATIVE,
                    start_datetime=dt,
                    timezone=self.timezone,
                    confidence=0.85
                )
            except Exception as e:
                self.logger.debug(f"Failed to subtract time unit for '{expr}': {e}")
        
        # Pattern: X units from now
        match = re.match(r'^(\d+)\s+(minutes?|hours?|days?|weeks?|months?|years?)\s+from\s+now$', expr)
        if match:
            amount = int(match.group(1))
            unit = match.group(2).rstrip('s')  # Remove plural 's'
            
            try:
                dt = self._add_time_unit(self.reference_time, amount, unit)
                return TemporalInfo(
                    original_text=expr,
                    temporal_type=TemporalType.RELATIVE,
                    start_datetime=dt,
                    timezone=self.timezone,
                    confidence=0.85
                )
            except Exception as e:
                self.logger.debug(f"Failed to add time unit for '{expr}': {e}")
        
        # Next/last/this + weekday
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        match = re.match(r'^(next|last|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$', expr)
        if match:
            modifier = match.group(1).lower()
            weekday_name = match.group(2).lower()
            target_weekday = weekdays[weekday_name]
            current_weekday = self.reference_time.weekday()
            
            if modifier == 'next':
                days_ahead = target_weekday - current_weekday
                if days_ahead <= 0:  # Target day already passed this week
                    days_ahead += 7
            elif modifier == 'last':
                days_ahead = target_weekday - current_weekday
                if days_ahead >= 0:  # Target day hasn't come this week
                    days_ahead -= 7
            else:  # this
                days_ahead = target_weekday - current_weekday
                # If it's the same day, use today; otherwise use this week's occurrence
            
            dt = self.reference_time + timedelta(days=days_ahead)
            return TemporalInfo(
                original_text=expr,
                temporal_type=TemporalType.RELATIVE,
                start_datetime=dt,
                timezone=self.timezone,
                confidence=0.85
            )
        
        # Days of the week (next occurrence)
        if expr in weekdays:
            target_weekday = weekdays[expr]
            current_weekday = self.reference_time.weekday()
            
            # Find next occurrence of this weekday
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            
            dt = self.reference_time + timedelta(days=days_ahead)
            return TemporalInfo(
                original_text=expr,
                temporal_type=TemporalType.RELATIVE,
                start_datetime=dt,
                timezone=self.timezone,
                confidence=0.8
            )
        
        return None
    
    def _parse_absolute_expression(self, expr: str) -> Optional[TemporalInfo]:
        """Parse absolute temporal expressions."""
        # Time patterns (e.g., "3:30 pm", "15:30", "3 pm")
        time_patterns = [
            r'^(\d{1,2}):(\d{2})\s*(am|pm)?$',
            r'^(\d{1,2}):(\d{2}):(\d{2})\s*(am|pm)?$',
            r'^(\d{1,2})\s*(am|pm)$'  # Just hour with am/pm
        ]
        
        for pattern in time_patterns:
            match = re.match(pattern, expr)
            if match:
                groups = match.groups()
                hour = int(groups[0])
                minute = int(groups[1]) if len(groups) >= 2 and groups[1] and groups[1].isdigit() else 0
                second = int(groups[2]) if len(groups) >= 3 and groups[2] and groups[2].isdigit() else 0
                ampm = groups[-1] if len(groups) >= 2 and groups[-1] else None
                
                # Convert to 24-hour format
                if ampm:
                    if ampm.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif ampm.lower() == 'am' and hour == 12:
                        hour = 0
                
                # Validate time
                if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                    # Create datetime in the resolver's timezone
                    base_date = self.reference_time.date()
                    dt = datetime.combine(base_date, time(hour, minute, second))
                    dt = self.tz.localize(dt)
                    
                    # If time has passed today, assume tomorrow
                    if dt <= self.reference_time:
                        dt += timedelta(days=1)
                    
                    return TemporalInfo(
                        original_text=expr,
                        temporal_type=TemporalType.ABSOLUTE,
                        start_datetime=dt,
                        timezone=self.timezone,
                        confidence=0.9
                    )
        
        # Date patterns
        date_patterns = [
            # MM/DD/YYYY or MM/DD/YY
            (r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', lambda m: (int(m.group(2)), int(m.group(1)), int(m.group(3)))),
            # YYYY-MM-DD
            (r'^(\d{4})-(\d{2})-(\d{2})$', lambda m: (int(m.group(3)), int(m.group(2)), int(m.group(1)))),
            # Month DD, YYYY
            (r'^(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:,\s*(\d{4}))?$', 
             lambda m: self._parse_month_day_year(m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None))
        ]
        
        for pattern, parser in date_patterns:
            match = re.match(pattern, expr, re.IGNORECASE)
            if match:
                try:
                    if callable(parser):
                        day, month, year = parser(match)
                    else:
                        day, month, year = parser
                    
                    # Handle 2-digit years
                    if year and year < 100:
                        if year < 50:
                            year += 2000
                        else:
                            year += 1900
                    elif not year:
                        year = self.reference_time.year
                    
                    # Validate date components
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        dt = datetime(year, month, day, tzinfo=self.tz)
                        return TemporalInfo(
                            original_text=expr,
                            temporal_type=TemporalType.ABSOLUTE,
                            start_datetime=dt,
                            timezone=self.timezone,
                            confidence=0.95
                        )
                except (ValueError, TypeError) as e:
                    self.logger.debug(f"Invalid date components for '{expr}': {e}")
                    continue
        
        return None
    
    def _parse_recurring_expression(self, expr: str) -> Optional[TemporalInfo]:
        """Parse recurring temporal expressions."""
        recurring_patterns = {
            r'^every\s+day$': 'daily',
            r'^daily$': 'daily',
            r'^every\s+week$': 'weekly',
            r'^weekly$': 'weekly',
            r'^every\s+month$': 'monthly',
            r'^monthly$': 'monthly',
            r'^every\s+year$': 'yearly',
            r'^yearly$': 'yearly',
            r'^annually$': 'yearly',
        }
        
        for pattern, recurrence_type in recurring_patterns.items():
            if re.match(pattern, expr):
                return TemporalInfo(
                    original_text=expr,
                    temporal_type=TemporalType.RECURRING,
                    start_datetime=self.reference_time,
                    timezone=self.timezone,
                    confidence=0.85,
                    is_recurring=True,
                    recurrence_pattern=recurrence_type
                )
        
        # Every specific weekday
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        match = re.match(r'^every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$', expr)
        if match:
            weekday = match.group(1)
            return TemporalInfo(
                original_text=expr,
                temporal_type=TemporalType.RECURRING,
                start_datetime=self.reference_time,
                timezone=self.timezone,
                confidence=0.85,
                is_recurring=True,
                recurrence_pattern=f'weekly_{weekday}'
            )
        
        return None
    
    def _parse_duration_expression(self, expr: str) -> Optional[TemporalInfo]:
        """Parse duration expressions."""
        match = re.match(r'^for\s+(\d+)\s+(minutes?|hours?|days?|weeks?|months?|years?)$', expr)
        if match:
            amount = int(match.group(1))
            unit = match.group(2).rstrip('s')  # Remove plural 's'
            
            try:
                duration = self._get_timedelta(amount, unit)
                return TemporalInfo(
                    original_text=expr,
                    temporal_type=TemporalType.DURATION,
                    start_datetime=self.reference_time,
                    end_datetime=self.reference_time + duration,
                    duration=duration,
                    timezone=self.timezone,
                    confidence=0.8
                )
            except Exception as e:
                self.logger.debug(f"Failed to parse duration for '{expr}': {e}")
        
        return None
    
    def _parse_range_expression(self, expr: str) -> Optional[TemporalInfo]:
        """Parse time range expressions."""
        # Try different range patterns
        patterns = [
            # From X:YY to Z:WW
            r'^from\s+(\d{1,2}):(\d{2})\s*(am|pm)?\s+to\s+(\d{1,2}):(\d{2})\s*(am|pm)?$',
            # Between X:YY and Z:WW
            r'^between\s+(\d{1,2}):(\d{2})\s*(am|pm)?\s+and\s+(\d{1,2}):(\d{2})\s*(am|pm)?$',
            # From X am/pm to Y am/pm (no minutes)
            r'^from\s+(\d{1,2})\s*(am|pm)?\s+to\s+(\d{1,2})\s*(am|pm)?$',
            # Between X am/pm and Y am/pm (no minutes)
            r'^between\s+(\d{1,2})\s*(am|pm)?\s+and\s+(\d{1,2})\s*(am|pm)?$'
        ]
        
        match = None
        for pattern in patterns:
            match = re.match(pattern, expr)
            if match:
                break
        
        if match:
            groups = match.groups()
            
            # Determine if this is a pattern with minutes or without
            if len(groups) >= 6 and groups[1] and groups[1].isdigit():
                # Pattern with minutes: X:YY
                start_hour = int(groups[0])
                start_minute = int(groups[1])
                start_ampm = groups[2]
                end_hour = int(groups[3])
                end_minute = int(groups[4])
                end_ampm = groups[5]
            else:
                # Pattern without minutes: X am/pm
                start_hour = int(groups[0])
                start_minute = 0
                start_ampm = groups[1]
                end_hour = int(groups[2])
                end_minute = 0
                end_ampm = groups[3]
            
            # Convert to 24-hour format
            if start_ampm:
                if start_ampm.lower() == 'pm' and start_hour != 12:
                    start_hour += 12
                elif start_ampm.lower() == 'am' and start_hour == 12:
                    start_hour = 0
            
            if end_ampm:
                if end_ampm.lower() == 'pm' and end_hour != 12:
                    end_hour += 12
                elif end_ampm.lower() == 'am' and end_hour == 12:
                    end_hour = 0
            
            # Validate times
            if (0 <= start_hour <= 23 and 0 <= start_minute <= 59 and 
                0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                
                base_date = self.reference_time.date()
                start_dt = datetime.combine(base_date, time(start_hour, start_minute))
                end_dt = datetime.combine(base_date, time(end_hour, end_minute))
                
                # Handle case where end time is next day
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)
                
                # Make timezone-aware
                start_dt = self.tz.localize(start_dt)
                end_dt = self.tz.localize(end_dt)
                
                return TemporalInfo(
                    original_text=expr,
                    temporal_type=TemporalType.RANGE,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    timezone=self.timezone,
                    confidence=0.9
                )
        
        return None
    
    def _add_months(self, dt: datetime, months: int) -> datetime:
        """Add months to a datetime, handling edge cases."""
        month = dt.month - 1 + months
        year = dt.year + month // 12
        month = month % 12 + 1
        day = min(dt.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return dt.replace(year=year, month=month, day=day)
    
    def _add_time_unit(self, dt: datetime, amount: int, unit: str) -> datetime:
        """Add time unit to datetime."""
        if unit == 'minute':
            return dt + timedelta(minutes=amount)
        elif unit == 'hour':
            return dt + timedelta(hours=amount)
        elif unit == 'day':
            return dt + timedelta(days=amount)
        elif unit == 'week':
            return dt + timedelta(weeks=amount)
        elif unit == 'month':
            return self._add_months(dt, amount)
        elif unit == 'year':
            return dt.replace(year=dt.year + amount)
        else:
            raise ValueError(f"Unknown time unit: {unit}")
    
    def _get_timedelta(self, amount: int, unit: str) -> timedelta:
        """Get timedelta for amount and unit."""
        if unit == 'minute':
            return timedelta(minutes=amount)
        elif unit == 'hour':
            return timedelta(hours=amount)
        elif unit == 'day':
            return timedelta(days=amount)
        elif unit == 'week':
            return timedelta(weeks=amount)
        elif unit == 'month':
            return timedelta(days=amount * 30)  # Approximate
        elif unit == 'year':
            return timedelta(days=amount * 365)  # Approximate
        else:
            raise ValueError(f"Unknown time unit: {unit}")
    
    def _parse_month_day_year(self, month_name: str, day: int, year: Optional[int]) -> Tuple[int, int, int]:
        """Parse month name, day, and optional year."""
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        month = months.get(month_name.lower())
        if not month:
            raise ValueError(f"Unknown month: {month_name}")
        
        if not year:
            year = self.reference_time.year
        
        return day, month, year
    
    def convert_to_timezone(self, dt: datetime, target_timezone: str) -> datetime:
        """Convert datetime to different timezone."""
        if dt.tzinfo is None:
            dt = self.tz.localize(dt)
        
        target_tz = pytz.timezone(target_timezone)
        return dt.astimezone(target_tz)
    
    def validate_datetime(self, dt: datetime) -> bool:
        """Validate that datetime is reasonable."""
        # Check if date is not too far in past or future
        min_date = datetime(1900, 1, 1, tzinfo=self.tz)
        max_date = datetime(2100, 12, 31, tzinfo=self.tz)
        
        if dt.tzinfo is None:
            dt = self.tz.localize(dt)
        
        return min_date <= dt <= max_date
    
    def get_next_occurrence(self, temporal_info: TemporalInfo) -> Optional[datetime]:
        """Get next occurrence of a recurring temporal expression."""
        if not temporal_info.is_recurring or not temporal_info.recurrence_pattern:
            return None
        
        pattern = temporal_info.recurrence_pattern
        base_time = temporal_info.start_datetime or self.reference_time
        
        if pattern == 'daily':
            return base_time + timedelta(days=1)
        elif pattern == 'weekly':
            return base_time + timedelta(weeks=1)
        elif pattern == 'monthly':
            return self._add_months(base_time, 1)
        elif pattern == 'yearly':
            return base_time.replace(year=base_time.year + 1)
        elif pattern.startswith('weekly_'):
            # Weekly on specific day
            weekday_name = pattern.split('_')[1]
            weekdays = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            if weekday_name in weekdays:
                target_weekday = weekdays[weekday_name]
                current_weekday = base_time.weekday()
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7  # Next week
                return base_time + timedelta(days=days_ahead)
        
        return None