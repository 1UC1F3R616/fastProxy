import fire
import requests
from bs4 import BeautifulSoup as soup
import threading
from queue import Queue


# Defined | Not Supposed to be Altered
s = requests.session()
r1 = s.get('https://free-proxy-list.net/')
page = soup(r1.text, 'html.parser')
tr_container = page.find_all('tr')

url = 'https://httpbin.org/ip' # End-Point to Test the response speed of ip address
ips = page.find_all('tr')[1:100] # This is to skip the 1st header and take the leftout content. but it does contain some garbage

alive_queue = Queue() # It will collect the working ips


# Global Variables
THREAD_COUNT = 100
REQUEST_TIMEOUT = 4
GENERATE_CSV = False
ALL_IPS = False


def alter_globals(c=100, t=4, g=False, a=False):
    global THREAD_COUNT
    global REQUEST_TIMEOUT
    global GENERATE_CSV
    global ALL_IPS

    try:
        c = int(c)
        t = int(t)
    except Exception as e:
        print(e)
        return

    if c < 0:
        THREAD_COUNT = 1
        print("[!] Negative Values are not Entertained")
        print("[*] Thread Count Set to 100")
    elif c==0:
        THREAD_COUNT = 1

    if t < 0:
        print("[!] Negative Values are not Entertained")
        print("[*] Request Timeout Set to 4 sec")
    
    THREAD_COUNT = c
    REQUEST_TIMEOUT = t

    print("[-] Threads: {}\tRequest Timeout:{}".format(THREAD_COUNT, REQUEST_TIMEOUT))

    if g in ['True', 'true', True, 1, 'yes']:
        GENERATE_CSV = True
    if a in ['True', 'true', True, 1, 'yes']:
        ALL_IPS = True


class alive_ip(threading.Thread):
    """
    Take ip address and put in alive_queue if it is working
    """

    def __init__(self, queue):

        """Initialize the thread"""
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        """Run the thread"""

        while True:
            # gets the proxy from the queue
            proxy = self.queue.get()

            # checks the proxy
            self.check_proxy(proxy)

            # send a signal to the queue that the job is done
            self.queue.task_done()

    def check_proxy(self, proxy):
        """Checks if Proxy is Alive"""
        
        try:
            r2 = requests.get(url, proxies={'http':proxy, 'https':proxy}, timeout=REQUEST_TIMEOUT)
            if r2.status_code == 200:
                alive_queue.put(proxy)
                
        except:
            pass


def main(proxies = ips):
    """
    Run the program
    """
    queue = Queue()

    # create a thread pool and give them a queue
    for i in range(THREAD_COUNT):
        t = alive_ip(queue)
        t.setDaemon(True)
        t.start()

    # give the queue some data
    for proxy in proxies:
        try:
            content = proxy.find_all('td')
            if len(content) != None:
                ip, port = content[0].get_text(), content[1].get_text()
                proxy_ = '{}:{}'.format(ip, port)
                queue.put(proxy_)
        except Exception as e:
            print(e)

    # wait for queue to finish
    queue.join()

    return list(alive_queue.queue)


def generate_csv():
    """Generate a CSV File with all Proxies"""

    if ALL_IPS:
        f = open('all_proxies.csv', 'w')
        for line in tr_container:
            content = str(line.getText(separator = ';')) # delimeter is ;
            if 'Date' in content:
                break
            f.write(content + '\n')
        f.close()
    else:
        f = open('working_ips.csv', 'w')
        for ip in list(alive_queue.queue):
            f.write(ip + '\n')
        f.close()


def printer(ip_list = list(alive_queue.queue)):
    """
    Prints the IP Address of working IPs
    """
    for ip in ip_list:
        print(ip)


def fetch_proxies():

    working_ips = main(proxies = ips)

    if GENERATE_CSV == True:
        generate_csv()

    return working_ips


if __name__ == "__main__":

    fire.Fire(alter_globals)
    
    main(proxies = ips)
    printer()

    if GENERATE_CSV == True:
        generate_csv()


# proxy filteration by 'country'
# code to refresh proxy list in every x minutes
# 1 way is as import (importing)
# 2nd way is as a command line tool (cli)