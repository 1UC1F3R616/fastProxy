from .fastProxy import (printer,
                       fetch_proxies,
                       main)
from .logger import logger
from .proxy_sources.manager import ProxySourceManager

__version__ = '1.0.0'
__all__ = ['fetch_proxies', 'printer', 'main', 'logger', 'ProxySourceManager']
