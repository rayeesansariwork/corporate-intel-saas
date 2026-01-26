import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging():
    """
    Configures application-wide logging with both console and file outputs.
    Creates detailed logs for debugging with timestamps, log levels, and module names.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with date
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | Line:%(lineno)-4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler (DEBUG level - captures everything)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler (INFO level - less verbose)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set levels for noisy third-party libraries
    # logging.getLogger("httpx").setLevel(logging.WARNING)
    # logging.getLogger("httpcore").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # logging.info("=" * 80)
    # logging.info("🚀 Logging system initialized")
    # logging.info(f"📁 Log file: {log_file}")
    # logging.info("=" * 80)
