from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from . import ProxySource
from ..logger import logger

class FreeProxyListSource(ProxySource):
    """Proxy source for free-proxy-list.net"""

    URL = 'https://free-proxy-list.net/'

    def fetch(self) -> List[Dict[str, str]]:
        """Fetch proxies from free-proxy-list.net"""
        proxies = []
        response = self._make_request(self.URL)

        if not response:
            return proxies

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Try different table selectors
            proxy_table = (
                soup.find('table', {'id': 'proxylisttable'}) or
                soup.find('table', {'class': 'table table-striped table-bordered'}) or
                soup.find('table')  # Fallback to first table
            )

            if not proxy_table:
                logger.error("Could not find proxy table on free-proxy-list.net")
                return proxies

            # Debug table structure
            logger.debug(f"Table found with {len(proxy_table.find_all('tr'))} rows")

            rows = proxy_table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 8:  # Changed from 7 to 8 since we need all 8 columns
                    proxy = {
                        'ip': cols[0].text.strip(),
                        'port': cols[1].text.strip(),
                        'code': cols[2].text.strip(),
                        'country': cols[3].text.strip(),
                        'anonymity': cols[4].text.strip(),
                        'google': cols[5].text.strip().lower(),
                        'https': cols[6].text.strip().lower(),
                        'last_checked': cols[7].text.strip()
                    }
                    # Debug log to see what's being filtered
                    logger.debug(f"Processing proxy: {proxy}")
                    proxies.append(proxy)  # Remove validation for now to see what's happening

            logger.info(f"Found {len(proxies)} proxies from free-proxy-list.net")

        except Exception as e:
            logger.error(f"Error parsing free-proxy-list.net: {str(e)}")

        return proxies
