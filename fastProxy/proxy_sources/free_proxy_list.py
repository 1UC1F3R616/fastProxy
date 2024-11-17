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
            proxy_table = soup.find('table', {'id': 'proxylisttable'})

            if not proxy_table:
                logger.error("Could not find proxy table on free-proxy-list.net")
                return proxies

            rows = proxy_table.find_all('tr')[1:]  # Skip header row

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 7:
                    proxy = {
                        'ip': cols[0].text.strip(),
                        'port': cols[1].text.strip(),
                        'country': cols[3].text.strip(),
                        'anonymity': cols[4].text.strip(),
                        'https': 'yes' if cols[6].text.strip() == 'yes' else 'no'
                    }
                    proxies.append(proxy)

            logger.info(f"Found {len(proxies)} proxies from free-proxy-list.net")

        except Exception as e:
            logger.error(f"Error parsing free-proxy-list.net: {str(e)}")

        return proxies
