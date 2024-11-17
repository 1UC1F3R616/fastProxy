from typing import List, Dict
import json
from . import ProxySource
from ..logger import logger

class GeoNodeSource(ProxySource):
    """Proxy source for geonode.com API"""

    API_URL = ('https://proxylist.geonode.com/api/proxy-list'
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
        try:
            response = self._make_request(self.API_URL)
            if not response:
                logger.error("No response received from geonode.com API")
                return proxies

            try:
                data = response.json()
                logger.debug(f"Received response from geonode.com: {data.keys()}")

                if 'data' not in data:
                    logger.error("Invalid response format from geonode.com API")
                    return proxies

                for proxy in data['data']:
                    try:
                        protocols = proxy.get('protocols', [])
                        if isinstance(protocols, str):
                            protocols = protocols.lower().split(',')
                        elif isinstance(protocols, list):
                            protocols = [p.lower() for p in protocols]
                        else:
                            logger.warning(f"Unexpected protocols format: {protocols}")
                            protocols = []

                        anonymity = proxy.get('anonymityLevel', 'unknown').lower()
                        anonymity = anonymity.replace('_', ' ')
                        if not anonymity.endswith(' proxy'):
                            anonymity += ' proxy'

                        proxy_entry = {
                            'ip': proxy.get('ip', ''),
                            'port': str(proxy.get('port', '')),
                            'country': proxy.get('country', ''),
                            'anonymity': anonymity,
                            'https': 'yes' if 'https' in protocols else 'no'
                        }

                        # Validate required fields
                        if not proxy_entry['ip'] or not proxy_entry['port']:
                            logger.warning(f"Skipping proxy with missing required fields: {proxy_entry}")
                            continue

                        proxies.append(proxy_entry)
                    except Exception as e:
                        logger.debug(f"Error processing proxy entry: {str(e)}", exc_info=True)
                        continue

                logger.info(f"Found {len(proxies)} proxies from geonode.com")

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing geonode.com API response: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing geonode.com API response: {str(e)}")
                logger.debug(f"Error details: {str(e)}", exc_info=True)

        except Exception as e:
            logger.error(f"Error fetching from geonode.com: {str(e)}")
            logger.debug(f"Error details: {str(e)}", exc_info=True)

        return proxies
