"""Logging-related models for ADW.

- Verbosity: the CLI's -q / -v / --trace setting
"""

from enum import Enum


class Verbosity(str, Enum):
    """CLI verbosity levels for controlling console output.

    Verbosity controls what level of detail is shown on the console:
    - QUIET: Only errors and fatal messages (-q, --quiet)
    - NORMAL: Info and above (default)
    - VERBOSE: Debug and above (-v, --verbose)
    - TRACE: Same as VERBOSE; stdlib logging has no TRACE level (--trace)

    Note: Verbosity sets the console level. A run's live.log records INFO,
    or DEBUG at VERBOSE/TRACE; QUIET quiets the console only.
    """

    QUIET = "quiet"
    NORMAL = "normal"
    VERBOSE = "verbose"
    TRACE = "trace"
