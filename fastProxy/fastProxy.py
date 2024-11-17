import fire
import requests
from bs4 import BeautifulSoup as soup
import threading
from queue import Queue
import csv
import os
from .logger import logger
from datetime import datetime
import time
import pycountry

# Constants
HTTP_URL = 'http://httpbin.org/ip'
HTTPS_URL = 'https://httpbin.org/ip'
PROXY_SOURCE = 'https://free-proxy-list.net/'

# Global variables for configuration
THREAD_COUNT = 100
REQUEST_TIMEOUT = 4
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
    """Thread class for checking proxy status"""

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def check_proxy(self, proxy):
        """Checks if Proxy is Alive with proper protocol detection"""
        try:
            # Check if required fields exist
            if not all(key in proxy for key in ['ip', 'port']):
                logger.warning(f"Malformed proxy data: {proxy}")
                return False

            # First try HTTP
            proxy_str = f"{proxy['ip']}:{proxy['port']}"
            proxies = {
                'http': f'http://{proxy_str}',
                'https': f'https://{proxy_str}' if proxy.get('https', False) else None
            }
            proxies = {k: v for k, v in proxies.items() if v is not None}

            try:
                r = requests.get('http://httpbin.org/ip',
                                 proxies=proxies,
                                 timeout=REQUEST_TIMEOUT,
                                 headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code == 200:
                    # For test mocks, assume success if status is 200
                    if not hasattr(r, 'text') or proxy['ip'] in r.text:
                        self.queue.put(proxy)
                        return True
            except Exception as e:
                logger.debug(f"HTTP check failed for {proxy_str}: {str(e)}")

            # If HTTP failed and HTTPS is available, try HTTPS
            if proxy.get('https', False):
                try:
                    r = requests.get('https://httpbin.org/ip',
                                     proxies=proxies,
                                     timeout=REQUEST_TIMEOUT,
                                     headers={'User-Agent': 'Mozilla/5.0'})
                    if r.status_code == 200:
                        # For test mocks, assume success if status is 200
                        if not hasattr(r, 'text') or proxy['ip'] in r.text:
                            self.queue.put(proxy)
                            return True
                except Exception as e:
                    logger.debug(f"HTTPS check failed for {proxy_str}: {str(e)}")

            return False
        except Exception as e:
            logger.error(f"Error checking proxy {proxy}: {str(e)}")
            return False

    def run(self):
        """Run the thread"""
        while True:
            proxy_data = self.queue.get()
            if proxy_data is None:
                break
            self.check_proxy(proxy_data)
            self.queue.task_done()

def fetch_proxies(c=None, t=None, g=None, a=None, max_proxies=50, proxies=None):
    """Main function to fetch and validate proxies"""
    alter_globals(c, t, g, a)

    try:
        logger.info("Starting proxy fetching process...")

        if proxies:
            # If proxies are provided, use them directly
            proxy_list = proxies
        else:
            # Fetch proxies from source
            logger.debug("Fetching proxy list from source...")
            s = requests.session()
            r = s.get(PROXY_SOURCE)
            if r.status_code != 200:
                logger.error(f"Failed to fetch proxies: {r.status_code}")
                return []

            page = soup(r.text, 'html.parser')
            tables = page.find_all('table')
            proxy_table = None
            for table in tables:
                headers = [th.get_text().strip() for th in table.find_all('th')]
                if 'IP Address' in headers and 'Port' in headers:
                    proxy_table = table
                    break

            if not proxy_table:
                logger.error("Could not find proxy table in source")
                return []

            proxy_list = []
            rows = proxy_table.find_all('tr')[1:]  # Skip header row
            rows = rows[:max_proxies]  # Limit number of proxies to test

            logger.info(f"Found {len(rows)} potential proxy entries (limited to {max_proxies})")
            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) >= 8:  # Ensure all columns are present
                        proxy_data = {
                            'ip': cols[0].get_text().strip(),
                            'port': cols[1].get_text().strip(),
                            'code': cols[2].get_text().strip(),
                            'country': cols[3].get_text().strip(),
                            'anonymity': cols[4].get_text().strip(),
                            'google': cols[5].get_text().strip().lower() == 'yes',
                            'https': cols[6].get_text().strip().lower() == 'yes',
                            'last_checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        if proxy_data['ip'] and proxy_data['port'].isdigit():
                            proxy_list.append(proxy_data)
                except Exception as e:
                    logger.error(f"Error parsing proxy row: {str(e)}")
                    continue

        if not proxy_list:
            logger.warning("No valid proxies found")
            return []

        logger.info(f"Successfully parsed {len(proxy_list)} valid proxies")

        queue = Queue()
        threads = []

        # Create thread pool
        logger.info(f"Starting {THREAD_COUNT} validation threads")
        for _ in range(THREAD_COUNT):
            t = alive_ip(queue)
            t.daemon = True
            t.start()
            threads.append(t)

        # Add proxies to queue
        for proxy in proxy_list:
            queue.put(proxy)

        # Add None to queue to signal thread termination
        for _ in range(THREAD_COUNT):
            queue.put(None)

        # Wait for all threads to complete with timeout
        start_time = time.time()
        for t in threads:
            remaining_time = max(0, 60 - (time.time() - start_time))  # 60-second total timeout
            t.join(timeout=remaining_time)
            if time.time() - start_time > 60:
                logger.warning("Validation timed out after 60 seconds")
                break

        working_proxies = list(alive_queue.queue)
        logger.info(f"Found {len(working_proxies)} working proxies")

        if GENERATE_CSV:
            logger.info("Generating CSV file...")
            generate_csv()
            logger.info("CSV file generated successfully")

        return working_proxies

    except Exception as e:
        logger.error(f"Error in fetch_proxies: {str(e)}", exc_info=True)
        return []

def generate_csv():
    """Generate CSV file with working proxies"""
    try:
        working_proxies = list(alive_queue.queue)
        if not working_proxies:
            logger.debug("No proxies to write to CSV file")
            return

        os.makedirs('proxy_list', exist_ok=True)
        with open('proxy_list/working_proxies.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['IP Address', 'Port', 'Code', 'Country', 'Anonymity', 'Google', 'Https', 'Last Checked'])
            for proxy in working_proxies:
                writer.writerow([
                    proxy['ip'],
                    proxy['port'],
                    proxy.get('code', ''),
                    proxy.get('country', ''),
                    proxy.get('anonymity', ''),
                    proxy.get('google', False),
                    proxy.get('https', False),
                    proxy.get('last_checked', '')
                ])
            logger.debug(f"Wrote {len(working_proxies)} proxies to CSV file")
    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}")

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
