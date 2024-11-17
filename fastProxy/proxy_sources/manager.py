from typing import List, Dict
from .free_proxy_list import FreeProxyListSource
from .geonode import GeoNodeSource
from ..logger import logger

class ProxySourceManager:
    """Manages multiple proxy sources"""

    def __init__(self):
        self.sources = [
            FreeProxyListSource(),
            GeoNodeSource()
        ]

    def fetch_all(self, max_proxies: int = 50) -> List[Dict[str, str]]:
        """Fetch proxies from all sources

        Args:
            max_proxies: Maximum number of total proxies to return

        Returns:
            List of proxy dictionaries
        """
        all_proxies = []

        for source in self.sources:
            try:
                proxies = source.fetch()
                all_proxies.extend(proxies)
                logger.debug(f"Fetched {len(proxies)} proxies from {source.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error fetching from {source.__class__.__name__}: {str(e)}")

        # Apply max_proxies limit to total proxies
        if max_proxies > 0 and len(all_proxies) > max_proxies:
            all_proxies = all_proxies[:max_proxies]
            logger.debug(f"Limited total proxies to {max_proxies}")

        return all_proxies
