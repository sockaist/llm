import logging
import sys

# Standardize existing 'kss' logger
kss_logger = logging.getLogger("kss")
kss_logger.propagate = False

# Remove any root handlers that might be printing [Kss]
root = logging.getLogger()
for h in root.handlers[:]:
    root.removeHandler(h)

print("KSS Log Fix script executed.")
