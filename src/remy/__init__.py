import warnings

# Convert dateutil's UnknownTimezoneWarning to an error so users can identify
# and fix malformed timezone values in their notecards
try:
    from dateutil.parser import UnknownTimezoneWarning
    warnings.filterwarnings("error", category=UnknownTimezoneWarning)
except ImportError:
    # dateutil may not be installed, that's OK
    pass

from .notecard import Notecard
from .notecard_cache import NotecardCache
from .parsers import parse_datetime_with_arithmetic
