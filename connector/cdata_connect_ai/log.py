import logging

# Library code must not call basicConfig — that belongs to the application.
# Adding NullHandler suppresses "No handler found" warnings when the
# embedding application has not configured logging.
logger = logging.getLogger("cdata_connect_ai")
logger.addHandler(logging.NullHandler())
