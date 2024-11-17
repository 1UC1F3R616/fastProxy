from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from ..logger import logger

class ProxySource(ABC):
    """Abstract base class for proxy sources"""

    @abstractmethod
    def fetch(self) -> List[Dict[str, str]]:
        """Fetch proxies from the source

        Returns:
            List[Dict[str, str]]: List of proxy dictionaries with keys:
                - ip: IP address
                - port: Port number
                - country: Country code
                - anonymity: Anonymity level
                - https: Whether HTTPS is supported
        """
        pass

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Error fetching from {url}: {str(e)}")
            return None
