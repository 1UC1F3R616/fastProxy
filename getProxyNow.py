""" Just Run Me and I will give u a list
    Change any params if you want
    Make sure complete repo is cloned :)
"""

from fastProxy import (
    fetch_proxies,
    alter_globals,
    printer,
    THREAD_COUNT,
    REQUEST_TIMEOUT,
    GENERATE_CSV,
    ALL_PROXIES
)

# Configure settings
alter_globals(
    c=3,    # Thread count (extremely conservative)
    t=10,   # Request timeout (very short for testing)
    g=True, # Generate CSV
    a=True  # All proxies
)

# Fetch and validate proxies
proxies = fetch_proxies(max_proxies=10)  # Very small batch for testing
printer(proxies)
