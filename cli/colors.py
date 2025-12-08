"""ANSI color utilities for Codey CLI - Termux compatible"""
import sys
import os

# Check if terminal supports colors
def supports_color():
    """Check if the terminal supports ANSI colors"""
    # Check if stdout is a terminal
    if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
        return False

    # Check TERM environment variable
    term = os.environ.get('TERM', '')
    if term in ('dumb', 'unknown'):
        return False

    return True

# ANSI color codes
class Colors:
    """ANSI color codes"""
    # Basic colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # Bright foreground colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

# Disable colors if not supported
COLORS_ENABLED = supports_color()

def colorize(text: str, color: str) -> str:
    """Apply color to text if colors are enabled"""
    if not COLORS_ENABLED:
        return text
    return f"{color}{text}{Colors.RESET}"

# Semantic color functions
def success(text: str) -> str:
    """Format text as success (green)"""
    return colorize(text, Colors.GREEN)

def error(text: str) -> str:
    """Format text as error (red)"""
    return colorize(text, Colors.RED)

def warning(text: str) -> str:
    """Format text as warning (yellow)"""
    return colorize(text, Colors.YELLOW)

def info(text: str) -> str:
    """Format text as info (cyan)"""
    return colorize(text, Colors.CYAN)

def permission(text: str) -> str:
    """Format text as permission request (magenta)"""
    return colorize(text, Colors.MAGENTA)

def bold(text: str) -> str:
    """Make text bold"""
    if not COLORS_ENABLED:
        return text
    return f"{Colors.BOLD}{text}{Colors.RESET}"

def dim(text: str) -> str:
    """Make text dim"""
    if not COLORS_ENABLED:
        return text
    return f"{Colors.DIM}{text}{Colors.RESET}"

# Icons (using Unicode, works in Termux)
class Icons:
    """Unicode icons for CLI"""
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    INFO = "ℹ"
    LOCK = "🔒"
    ROCKET = "🚀"
    WRENCH = "🔧"
    FILE = "📄"
    FOLDER = "📁"
    GIT = "🔀"
    SHELL = "💻"
    PACKAGE = "📦"
    ROBOT = "🤖"
    HOURGLASS = "⏳"
    CHECK = "✅"
    CROSS = "❌"
    CIRCLE = "○"

# Formatted status messages
def success_msg(msg: str) -> str:
    """Format a success message"""
    return success(f"{Icons.SUCCESS} {msg}")

def error_msg(msg: str) -> str:
    """Format an error message"""
    return error(f"{Icons.ERROR} {msg}")

def warning_msg(msg: str) -> str:
    """Format a warning message"""
    return warning(f"{Icons.WARNING} {msg}")

def info_msg(msg: str) -> str:
    """Format an info message"""
    return info(f"{Icons.INFO} {msg}")

def permission_msg(msg: str) -> str:
    """Format a permission request message"""
    return permission(f"{Icons.LOCK} {msg}")
