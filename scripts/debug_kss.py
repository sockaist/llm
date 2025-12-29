
import logging
import sys
import os

# Setup basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_logger")

print("--- Importing kss ---")
try:
    import kss
    print("--- kss imported ---")
except ImportError:
    print("kss not found")

# Check root logger handlers
print(f"Root handlers: {logging.root.handlers}")
# Check kss logger
kss_logger = logging.getLogger("kss")
print(f"KSS logger level: {kss_logger.level}")
print(f"KSS logger handlers: {kss_logger.handlers}")
print(f"KSS logger propagate: {kss_logger.propagate}")

# Emit a log
logger.info("This is a test log message")
