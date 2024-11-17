from .fastProxy import (
    fetch_proxies,
    alter_globals,
    THREAD_COUNT,
    REQUEST_TIMEOUT,
    GENERATE_CSV,
    ALL_PROXIES,
    printer
)
from .logger import logger
from .proxy_sources.manager import ProxySourceManager

__version__ = '1.0.0'
__all__ = [
    'fetch_proxies',
    'printer',
    'logger',
    'ProxySourceManager',
    'alter_globals',
    'THREAD_COUNT',
    'REQUEST_TIMEOUT',
    'GENERATE_CSV',
    'ALL_PROXIES'
]
