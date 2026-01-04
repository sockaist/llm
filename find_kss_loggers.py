import logging
import sys

# Import everything that might initialize loggers
try:
    import llm_backend.utils.logger
    import vectordb.core.logger
except Exception as e:
    pass

loggers = [logging.root] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]

for logger in loggers:
    if logger.handlers:
        for h in logger.handlers:
            fmt = h.formatter._fmt if h.formatter and hasattr(h.formatter, '_fmt') else str(h.formatter)
            print(f"LOGGER: {logger.name} | FORMAT: {fmt}")
