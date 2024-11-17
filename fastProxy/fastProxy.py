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

# Global queue for storing working proxies with metadata
alive_queue = Queue()

def alter_globals(c=None, t=None, g=None, a=None):
    """Alter global variables based on parameters"""
    global THREAD_COUNT, REQUEST_TIMEOUT, GENERATE_CSV, ALL_PROXIES
    if c is not None:
        THREAD_COUNT = c
    if t is not None:
        REQUEST_TIMEOUT = t
    if g is not None:
        GENERATE_CSV = g
    if a is not None:
        ALL_PROXIES = a

class alive_ip(threading.Thread):
    """Thread class for checking proxy status"""

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def check_proxy(self, proxy):
        """Checks if Proxy is Alive with proper protocol detection"""
        try:
            # First try HTTP
            proxy_str = f"{proxy['ip']}:{proxy['port']}"
            proxy_dict = {
                'http': f'http://{proxy_str}',
                'https': f'http://{proxy_str}'
            }

            logger.debug(f"Testing HTTP for {proxy_str}")
            start_time = time.time()
            r = requests.get(HTTP_URL, proxies=proxy_dict, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                proxy['last_checked'] = f"{int(time.time() - start_time)} seconds ago"
                logger.info(f"HTTP Proxy {proxy_str} is working!")
                alive_queue.put(proxy)
                return True

        except requests.exceptions.RequestException as e:
            logger.debug(f"HTTP test failed for {proxy_str}: {str(e)}")

            try:
                # Try HTTPS
                proxy_dict = {
                    'http': f'https://{proxy_str}',
                    'https': f'https://{proxy_str}'
                }
                logger.debug(f"Testing HTTPS for {proxy_str}")
                start_time = time.time()
                r = requests.get(HTTPS_URL, proxies=proxy_dict, timeout=REQUEST_TIMEOUT)
                if r.status_code == 200:
                    proxy['last_checked'] = f"{int(time.time() - start_time)} seconds ago"
                    proxy['https'] = True
                    logger.info(f"HTTPS Proxy {proxy_str} is working!")
                    alive_queue.put(proxy)
                    return True
            except Exception as e:
                logger.debug(f"HTTPS test failed for {proxy_str}: {str(e)}")
                return False

        return False

    def run(self):
        """Run the thread"""
        while True:
            proxy_data = self.queue.get()
            if proxy_data is None:
                break
            self.check_proxy(proxy_data)
            self.queue.task_done()

def fetch_proxies(c=None, t=None, g=None, a=None, max_proxies=50):
    """Main function to fetch and validate proxies"""
    alter_globals(c, t, g, a)

    try:
        logger.info("Starting proxy fetching process...")
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

        proxies = []
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
                        proxies.append(proxy_data)
            except Exception as e:
                logger.error(f"Error parsing proxy row: {str(e)}")
                continue

        if not proxies:
            logger.warning("No valid proxies found in source")
            return []

        logger.info(f"Successfully parsed {len(proxies)} valid proxies")

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
        for proxy in proxies:
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
        if not os.path.exists('proxy_list'):
            os.makedirs('proxy_list')
            logger.debug("Created proxy_list directory")

        working_proxies = list(alive_queue.queue)
        with open('proxy_list/working_proxies.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['IP Address', 'Port', 'Code', 'Country', 'Anonymity', 'Google', 'Https', 'Last Checked'])
            for proxy_data in working_proxies:
                writer.writerow([
                    proxy_data['ip'],
                    proxy_data['port'],
                    proxy_data['code'],
                    proxy_data['country'],
                    proxy_data['anonymity'],
                    'yes' if proxy_data['google'] else 'no',
                    'yes' if proxy_data['https'] else 'no',
                    proxy_data['last_checked']
                ])
        logger.debug(f"Wrote {len(working_proxies)} proxies to CSV file")
    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}", exc_info=True)

def printer():
    """Print working proxies"""
    working_proxies = list(alive_queue.queue)
    logger.info(f"\nWorking Proxies: {len(working_proxies)}")
    for proxy in working_proxies:
        proxy_str = f"{proxy['ip']}:{proxy['port']} ({proxy['country']}, {proxy['anonymity']})"
        logger.info(proxy_str)

def main(proxies=None):
    """CLI entry point"""
    if proxies is None:
        return fetch_proxies()
    # Convert string proxies to dictionary format if needed
    if isinstance(proxies, list) and all(isinstance(p, str) for p in proxies):
        proxies = [{'ip': p.split(':')[0], 'port': p.split(':')[1]} for p in proxies]
    return fetch_proxies(proxies=proxies)

if __name__ == '__main__':
    fire.Fire(fetch_proxies)
