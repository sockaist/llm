import logging
import sys

def inspect():
    loggers = [logging.root] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for logger in loggers:
        if logger.handlers:
            print(f"LOGGER: {logger.name} (Propagate: {logger.propagate})")
            for h in logger.handlers:
                fmt = h.formatter._fmt if h.formatter and hasattr(h.formatter, '_fmt') else str(h.formatter)
                print(f"  HANDLER: {h}")
                print(f"    FORMAT: {fmt}")

if __name__ == "__main__":
    # Import relevant modules to initialize their loggers
    try:
        import llm_backend.utils.logger
        import vectordb.core.logger
        import llm_backend.server.vector_server.main
    except Exception as e:
        print(f"Import error: {e}")
    inspect()
