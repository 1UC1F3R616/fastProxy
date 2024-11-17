import fire
import requests
from bs4 import BeautifulSoup as soup
import threading
from queue import Queue
import csv
import os

# Constants
HTTP_URL = 'http://httpbin.org/ip'
HTTPS_URL = 'https://httpbin.org/ip'
PROXY_SOURCE = 'https://free-proxy-list.net/'

# Global variables for configuration
THREAD_COUNT = 100
REQUEST_TIMEOUT = 4
GENERATE_CSV = False
ALL_PROXIES = False

# Global queue for storing working proxies
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
            proxy_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }

            print(f"[DEBUG] Testing HTTP for {proxy}")
            r = requests.get(HTTP_URL, proxies=proxy_dict, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                print(f"[DEBUG] HTTP Proxy {proxy} is working!")
                alive_queue.put(proxy)
                return True

        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] HTTP test failed for {proxy}: {str(e)}")

            try:
                # Try HTTPS
                proxy_dict = {
                    'http': f'https://{proxy}',
                    'https': f'https://{proxy}'
                }
                print(f"[DEBUG] Testing HTTPS for {proxy}")
                r = requests.get(HTTPS_URL, proxies=proxy_dict, timeout=REQUEST_TIMEOUT)
                if r.status_code == 200:
                    print(f"[DEBUG] HTTPS Proxy {proxy} is working!")
                    alive_queue.put(proxy)
                    return True
            except Exception as e:
                print(f"[DEBUG] HTTPS test failed for {proxy}: {str(e)}")
                return False

        return False

    def run(self):
        """Run the thread"""
        while True:
            proxy = self.queue.get()
            if proxy is None:
                break
            self.check_proxy(proxy)
            self.queue.task_done()

def fetch_proxies(c=None, t=None, g=None, a=None):
    """Main function to fetch and validate proxies"""
    alter_globals(c, t, g, a)

    try:
        print("[DEBUG] Fetching proxy list...")
        s = requests.session()
        r = s.get(PROXY_SOURCE)
        if r.status_code != 200:
            print(f"[DEBUG] Failed to fetch proxies: {r.status_code}")
            return []

        page = soup(r.text, 'html.parser')
        proxy_table = page.find('table', {'id': 'proxylisttable'})
        if not proxy_table:
            print("[DEBUG] Could not find proxy table")
            return []

        proxies = []
        rows = proxy_table.find_all('tr')[1:]  # Skip header row

        print(f"[DEBUG] Found {len(rows)} potential proxy entries")
        for row in rows:
            try:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    ip = cols[0].get_text().strip()
                    port = cols[1].get_text().strip()
                    if ip and port and port.isdigit():
                        proxies.append(f"{ip}:{port}")
            except Exception as e:
                print(f"[DEBUG] Error parsing proxy row: {str(e)}")
                continue

        if not proxies:
            print("[DEBUG] No valid proxies found")
            return []

        print(f"[DEBUG] Successfully parsed {len(proxies)} valid proxies")

        queue = Queue()
        threads = []

        # Create thread pool
        print(f"[DEBUG] Starting {THREAD_COUNT} validation threads")
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

        # Wait for all threads to complete
        for t in threads:
            t.join()

        working_proxies = list(alive_queue.queue)
        print(f"[DEBUG] Found {len(working_proxies)} working proxies")

        if GENERATE_CSV:
            generate_csv()

        return working_proxies

    except Exception as e:
        print(f"[DEBUG] Error in fetch_proxies: {str(e)}")
        return []

def generate_csv():
    """Generate CSV file with working proxies"""
    if not os.path.exists('proxy_list'):
        os.makedirs('proxy_list')

    working_proxies = list(alive_queue.queue)
    with open('proxy_list/working_proxies.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Proxy'])
        for proxy in working_proxies:
            writer.writerow([proxy])

def printer():
    """Print working proxies"""
    working_proxies = list(alive_queue.queue)
    print(f"\nWorking Proxies: {len(working_proxies)}")
    for proxy in working_proxies:
        print(proxy)

if __name__ == '__main__':
    fire.Fire(main)
