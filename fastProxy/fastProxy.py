import fire
import requests
from bs4 import BeautifulSoup as soup
import threading
from queue import Queue, Empty
import csv
import os
from .logger import logger
from datetime import datetime
import time
import pycountry
from .proxy_sources.manager import ProxySourceManager

# Constants
HTTP_URL = 'http://httpbin.org/ip'
HTTPS_URL = 'https://httpbin.org/ip'

# Global variables for configuration
THREAD_COUNT = 10  # Reduced for testing
REQUEST_TIMEOUT = 15  # Increased for testing
GENERATE_CSV = True
ALL_PROXIES = False
WORKING_PROXIES = []

# Global queue for storing working proxies with metadata
alive_queue = Queue()

def alter_globals(c=None, t=None, g=None, a=None):
    """Alter global variables based on parameters"""
    # Get module reference
    import sys
    module = sys.modules['fastProxy.fastProxy']

    # Store current values for debugging
    old_timeout = module.REQUEST_TIMEOUT
    old_thread_count = module.THREAD_COUNT

    # Update values if provided
    if c is not None:
        setattr(module, 'THREAD_COUNT', c)
        logger.debug(f"Updated THREAD_COUNT from {old_thread_count} to {c}")
    if t is not None:
        setattr(module, 'REQUEST_TIMEOUT', t)
        logger.debug(f"Updated REQUEST_TIMEOUT from {old_timeout} to {t}")
    if g is not None:
        setattr(module, 'GENERATE_CSV', g)
        logger.debug(f"Updated GENERATE_CSV to {g}")
    if a is not None:
        setattr(module, 'ALL_PROXIES', a)
        logger.debug(f"Updated ALL_PROXIES to {a}")

class alive_ip(threading.Thread):
    """Thread class for validating proxies"""

    def __init__(self, proxy_data):
        super().__init__(daemon=True)
        self.proxy_data = proxy_data

    def check_proxy(self):
        """Check if a proxy is working"""
        try:
            proxy = self.proxy_data.get('proxy', f"{self.proxy_data['ip']}:{self.proxy_data['port']}")
            is_https = self.proxy_data.get('is_https', self.proxy_data.get('https', False))
            country = self.proxy_data.get('country', '')
            anonymity = self.proxy_data.get('anonymity', 'unknown')
            if not anonymity.endswith(' proxy'):
                anonymity += ' proxy'

            # Test HTTPS proxy first if supported
            if is_https:
                try:
                    proxies = {
                        'https': f'https://{proxy}'
                    }
                    response = requests.get(
                        HTTPS_URL,
                        proxies=proxies,
                        timeout=REQUEST_TIMEOUT,
                        verify=False  # Allow self-signed certificates
                    )
                    if response.status_code == 200:
                        logger.debug(f"Working HTTPS proxy found: {proxy}")
                        proxy_info = {
                            'proxy': proxy,
                            'type': 'https',
                            'country': country,
                            'anonymity': anonymity
                        }
                        alive_queue.put(proxy_info)
                        return True
                except requests.exceptions.RequestException as e:
                    logger.debug(f"HTTPS proxy failed: {proxy} - {e.__class__.__name__}: {str(e)}")

            # Test HTTP proxy if HTTPS failed or not supported
            try:
                proxies = {
                    'http': f'http://{proxy}',
                    'https': None  # Don't use HTTPS for HTTP test
                }
                response = requests.get(
                    HTTP_URL,
                    proxies=proxies,
                    timeout=REQUEST_TIMEOUT,
                    verify=False  # Allow self-signed certificates
                )
                if response.status_code == 200:
                    logger.debug(f"Working HTTP proxy found: {proxy}")
                    proxy_info = {
                        'proxy': proxy,
                        'type': 'http',
                        'country': country,
                        'anonymity': anonymity
                    }
                    alive_queue.put(proxy_info)
                    return True
            except requests.exceptions.RequestException as e:
                logger.debug(f"HTTP proxy failed: {proxy} - {e.__class__.__name__}: {str(e)}")

            return False

        except Exception as e:
            logger.error(f"Error validating proxy: {str(e)}")
            return False

    def run(self):
        self.check_proxy()

def fetch_proxies(c=None, t=None, g=None, a=None, proxies=None, max_proxies=None):
    """Fetch and validate proxies"""
    # Update global settings if provided
    alter_globals(c=c, t=t, g=g, a=a)

    logger.info("Starting proxy fetching process...")

    # Get proxies from sources if not provided
    if proxies is None:
        manager = ProxySourceManager()
        proxies = manager.fetch_all(max_proxies=max_proxies if max_proxies else 10)

    # Validate input parameters
    if not isinstance(max_proxies, (type(None), int)) or (isinstance(max_proxies, int) and max_proxies <= 0):
        logger.error("Invalid max_proxies parameter")
        return []

    # Process proxies in small batches
    batch_size = 1  # Process one at a time for testing
    working_proxies = []
    total_timeout = REQUEST_TIMEOUT  # Use global timeout setting

    try:
        # Process only up to max_proxies if specified
        proxy_list = proxies[:max_proxies] if max_proxies else proxies
        logger.info(f"Successfully parsed {len(proxy_list)} valid proxies")

        for i in range(0, len(proxy_list), batch_size):
            batch = proxy_list[i:i+batch_size]
            thread = None
            logger.info(f"Processing proxy {i+1}/{len(proxy_list)}")

            try:
                # Start single thread
                proxy = batch[0]
                thread = alive_ip(proxy)
                thread.daemon = True
                thread.start()

                # Wait for thread with timeout
                thread.join(timeout=total_timeout)

                # Get results from queue
                while not alive_queue.empty():
                    working_proxies.append(alive_queue.get_nowait())

                if thread.is_alive():
                    logger.warning(f"Proxy {i+1} timed out")
                else:
                    logger.info(f"Proxy {i+1} completed")

            except Exception as e:
                logger.error(f"Error processing proxy {i+1}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error in fetch_proxies: {str(e)}")

    # Generate CSV if enabled
    if GENERATE_CSV and working_proxies:
        generate_csv(working_proxies)

    return working_proxies

def generate_csv(working_proxies=None):
    """Generate CSV file with working proxies"""
    if working_proxies is None:
        working_proxies = []
        while not alive_queue.empty():
            working_proxies.append(alive_queue.get())

    if not working_proxies:
        logger.warning("No working proxies to write to CSV")
        return

    # Create proxy_list directory if it doesn't exist
    os.makedirs('proxy_list', exist_ok=True)
    csv_file = os.path.join('proxy_list', 'working_proxies.csv')

    # Write to CSV file
    try:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['IP Address', 'Port', 'Code', 'Country', 'Anonymity', 'Google', 'Https', 'Last Checked'])

            for proxy in working_proxies:
                ip, port = proxy['proxy'].split(':')
                writer.writerow([
                    ip,
                    port,
                    '',  # Code (not available)
                    proxy.get('country', ''),
                    proxy.get('anonymity', 'unknown'),
                    'False',  # Google (not tested)
                    'True' if proxy.get('type') == 'https' else 'False',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])
        logger.info(f"Successfully wrote {len(working_proxies)} proxies to {csv_file}")
    except Exception as e:
        logger.error(f"Error writing CSV file: {str(e)}")

def printer(proxies):
    """Print working proxies"""
    print(f"\nFound {len(proxies)} working proxies:")
    for proxy in proxies:
        try:
            proxy_str = proxy.get('proxy', f"{proxy.get('ip', 'unknown')}:{proxy.get('port', 'unknown')}")
            country = proxy.get('country', 'Unknown')
            anonymity = proxy.get('anonymity', 'unknown')
            print(f"{proxy_str} ({country}, {anonymity})")
        except Exception as e:
            logger.error(f"Error printing proxy data: {str(e)}")
            continue

if __name__ == '__main__':
    fire.Fire({
        'fetch': fetch_proxies,
        'alter': alter_globals
    })
