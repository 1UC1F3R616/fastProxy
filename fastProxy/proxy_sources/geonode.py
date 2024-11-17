from typing import List, Dict
import json
from . import ProxySource
from ..logger import logger

class GeoNodeSource(ProxySource):
    """Proxy source for geonode.com API"""

    URL = ('https://proxylist.geonode.com/api/proxy-list'
           '?protocols=http%2Chttps%2Csocks4%2Csocks5'
           '&filterUpTime=90'
           '&filterLastChecked=5'
           '&speed=fast'
           '&limit=500'
           '&page=1'
           '&sort_by=lastChecked'
           '&sort_type=desc')

    def fetch(self) -> List[Dict[str, str]]:
        """Fetch proxies from geonode.com API"""
        proxies = []
        response = self._make_request(self.URL)

        if not response:
            return proxies

        try:
            data = response.json()

            if 'data' not in data:
                logger.error("Invalid response format from geonode.com API")
                return proxies

            for proxy in data['data']:
                proxy_entry = {
                    'ip': proxy.get('ip', ''),
                    'port': str(proxy.get('port', '')),
                    'country': proxy.get('country', ''),
                    'anonymity': proxy.get('anonymity', ''),
                    'https': 'yes' if 'https' in proxy.get('protocols', '').lower() else 'no'
                }
                proxies.append(proxy_entry)

            logger.info(f"Found {len(proxies)} proxies from geonode.com")

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing geonode.com API response: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing geonode.com API response: {str(e)}")

        return proxies
