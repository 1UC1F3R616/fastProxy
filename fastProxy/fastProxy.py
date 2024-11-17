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
THREAD_COUNT = 20  # Reduced from 100 to avoid overwhelming
REQUEST_TIMEOUT = 10  # Increased from 4 to allow slower proxies
GENERATE_CSV = False
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

    def __init__(self, q, working_proxies):
        threading.Thread.__init__(self)
        self.q = q
        self.working_proxies = working_proxies

    def check_proxy(self, proxy_data):
        """Check if a proxy is working"""
        try:
            proxy = proxy_data.get('proxy', f"{proxy_data['ip']}:{proxy_data['port']}")
            is_https = proxy_data.get('is_https', proxy_data.get('https', False))
            country = proxy_data.get('country', '')
            anonymity = proxy_data.get('anonymity', 'unknown')
            if not anonymity.endswith(' proxy'):
                anonymity += ' proxy'

            # Test HTTP proxy first
            http_works = False
            try:
                proxies = {
                    'http': f'http://{proxy}',
                    'https': None  # Don't use HTTPS for HTTP test
                }
                response = requests.get(
                    HTTP_URL,
                    proxies=proxies,
                    timeout=REQUEST_TIMEOUT
                )
                if response.status_code == 200:
                    logger.debug(f"Working HTTP proxy found: {proxy}")
                    with threading.Lock():
                        self.working_proxies.append({
                            'proxy': proxy,
                            'type': 'http',
                            'country': country,
                            'anonymity': anonymity
                        })
                    http_works = True
            except Exception as e:
                logger.debug(f"HTTP proxy failed: {proxy} - {str(e)}")

            # Test HTTPS proxy if supported
            if is_https:
                try:
                    proxies = {
                        'https': f'https://{proxy}'
                    }
                    response = requests.get(
                        HTTPS_URL,
                        proxies=proxies,
                        timeout=REQUEST_TIMEOUT,
                        verify=True  # Enforce SSL verification
                    )
                    if response.status_code == 200:
                        logger.debug(f"Working HTTPS proxy found: {proxy}")
                        with threading.Lock():
                            self.working_proxies.append({
                                'proxy': proxy,
                                'type': 'https',
                                'country': country,
                                'anonymity': anonymity
                            })
                        return True
                except Exception as e:
                    logger.debug(f"HTTPS proxy failed: {proxy} - {str(e)}")

            return http_works

        except Exception as e:
            logger.error(f"Error validating proxy: {str(e)}")
            return False

    def run(self):
        while True:
            proxy_data = None
            try:
                # Get proxy from queue with timeout
                proxy_data = self.q.get(timeout=1)
                self.check_proxy(proxy_data)
            except Empty:
                break
            except Exception as e:
                logger.error(f"Error validating proxy: {str(e)}")
            finally:
                if proxy_data is not None:
                    self.q.task_done()

def fetch_proxies(c=None, t=None, g=None, a=None, max_proxies=50, proxies=None):
    """Main function to fetch and validate proxies"""
    alter_globals(c, t, g, a)

    try:
        logger.info("Starting proxy fetching process...")

        if proxies:
            # If proxies are provided, use them directly
            proxy_list = proxies
        else:
            # Fetch proxies from all sources
            source_manager = ProxySourceManager()
            proxy_list = source_manager.fetch_all(max_proxies)

        if not proxy_list:
            logger.warning("No valid proxies found")
            return []

        logger.info(f"Successfully parsed {len(proxy_list)} valid proxies")

        # Create queue and threads for validation
        proxy_queue = Queue()
        threads = []
        working_proxies = []

        # Add proxies to queue
        for proxy in proxy_list:
            proxy_str = f"{proxy['ip']}:{proxy['port']}"
            proxy_queue.put({
                'proxy': proxy_str,
                'is_https': proxy['https'] == 'yes',
                'country': proxy['country'],
                'anonymity': proxy['anonymity']
            })

        logger.info(f"Starting {len(proxy_list)} validation threads")

        # Create and start validation threads
        for _ in range(min(len(proxy_list), THREAD_COUNT)):
            thread = alive_ip(proxy_queue, working_proxies)
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        logger.info(f"Found {len(working_proxies)} working proxies")

        if working_proxies and GENERATE_CSV:
            logger.info("Generating CSV file...")
            generate_csv(working_proxies)
            logger.info("CSV file generated successfully")

        return working_proxies

    except Exception as e:
        logger.error(f"Error in fetch_proxies: {str(e)}")
        return []

def generate_csv(working_proxies):
    """Generate CSV file with working proxies"""
    try:
        if not working_proxies:
            logger.debug("No proxies to write to CSV file")
            return

        os.makedirs('proxy_list', exist_ok=True)
        with open('proxy_list/working_proxies.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['IP Address', 'Port', 'Code', 'Country', 'Anonymity', 'Google', 'Https', 'Last Checked'])
            for proxy in working_proxies:
                proxy_parts = proxy['proxy'].split(':')
                anonymity = proxy.get('anonymity', 'unknown')
                if not anonymity.endswith(' proxy'):
                    anonymity += ' proxy'
                writer.writerow([
                    proxy_parts[0],  # IP
                    proxy_parts[1],  # Port
                    '',  # Code
                    proxy.get('country', ''),  # Country
                    anonymity.replace(' proxy', ''),  # Normalize anonymity format
                    False,  # Google
                    proxy.get('type', '') == 'https',  # Https
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Last Checked
                ])
            logger.debug(f"Wrote {len(working_proxies)} proxies to CSV file")
    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}")
        raise  # Re-raise the exception for proper error handling in tests

def printer():
    """Print working proxies"""
    working_proxies = list(alive_queue.queue)
    if working_proxies:
        print(f"\nWorking Proxies: {len(working_proxies)}")
        for proxy in working_proxies:
            print(f"{proxy['ip']}:{proxy['port']} ({proxy.get('country', 'Unknown')}, {proxy.get('anonymity', 'unknown')})")

def main(proxies=None):
    """Main function to handle proxy operations"""
    if proxies is not None:
        if not isinstance(proxies, list):
            raise TypeError("proxies must be a list")

        valid_proxies = []
        for proxy in proxies:
            if not isinstance(proxy, str):
                raise AttributeError("Each proxy must be a string")
            if not proxy or ':' not in proxy:
                raise IndexError("Invalid proxy format. Expected format: 'ip:port'")
            try:
                parts = proxy.split(':')
                if len(parts) != 2:
                    raise IndexError("Invalid proxy format. Expected format: 'ip:port'")
                ip, port = parts
                if not ip or not port:
                    raise IndexError("Invalid proxy format. Expected format: 'ip:port'")
                # Validate port number
                try:
                    port_num = int(port)
                    if port_num < 1 or port_num > 65535:
                        raise ValueError("Port number must be between 1 and 65535")
                except ValueError as e:
                    if "Port number must be between" in str(e):
                        raise
                    raise ValueError("Port must be a valid number")
                valid_proxies.append({'ip': ip, 'port': port})
            except (ValueError, IndexError) as e:
                if isinstance(e, ValueError):
                    raise
                raise IndexError("Invalid proxy format. Expected format: 'ip:port'")

        return fetch_proxies(proxies=valid_proxies)
    return fetch_proxies()

if __name__ == '__main__':
    fire.Fire(main)
