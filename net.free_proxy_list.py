import requests
from bs4 import BeautifulSoup as soup
import threading
from queue import Queue

s = requests.session()
r1 = s.get('https://free-proxy-list.net/')

page = soup(r1.text, 'html.parser')

f = open('lin.txt', 'w')

for line in page.find_all('tr'):
    content = str(line)#.getText(separator = ' '))
    if 'Date' in content:
        break
    f.write(content + '\n')
f.close()


url = 'https://httpbin.org/ip'
ips = page.find_all('tr')[1:]
#for line in ips:
#    content = line.find_all('td')
#    ip, port = content[0].get_text(), content[1].get_text()
#    proxy = '{}:{}'.format(ip, port)
#    # print(str(ip) + ':' +str(port))
#    try:
#        r2 = requests.get(url, timeout=2, proxies={'http':proxy, 'https':proxy})
#        if r2.status_code == 200:
#            print(proxy)
#    except:
#        pass

class alive_ip(threading.Thread):


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
        
        # print(str(ip) + ':' +str(port))
        try:
            r2 = requests.get(url, proxies={'http':proxy, 'https':proxy}, timeout=4)
            if r2.status_code == 200:
                print(proxy)
                alive_queue.put(proxy)
                
        except:
            pass

def main(proxies = ips):
    """
    Run the program
    """
    queue = Queue()

    # create a thread pool and give them a queue
    for i in range(100):
        t = alive_ip(queue)
        t.setDaemon(True)
        t.start()

    # give the queue some data
    for proxy in proxies:
        try:
            content = proxy.find_all('td')
            ip, port = content[0].get_text(), content[1].get_text()
            proxy_ = '{}:{}'.format(ip, port)
            queue.put(proxy_)
        except Exception as e:
            print(e)

    # wait for queue to finish
    queue.join()

alive_queue = Queue()

if __name__ == "__main__":
    main(proxies = ips)
    print(list(alive_queue.queue))



            
# Number of Threads by choice
# Speed of Proxy by Choice 'super', 'good', 'normal', 'every', 'custom' where self timeout can be used
# number of proxies | 'max', 'count'
# proxy export feature in csv
# proxy filteration by 'country'
# proxy return in list
# deafult settings which gives max number of proxies at normal (timeout=4)
# code to refresh proxy list in every x minutes
