# -*- coding:utf-8 -*-

import threading
import queue
from lxml.html import fromstring
import requests
from itertools import cycle
import traceback

def get_proxies():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies = set()
    for i in parser.xpath('//tbody/tr')[:10]:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    return proxies


#If you are copy pasting proxy ips, put in the list below
#proxies = ['121.129.127.209:80', '124.41.215.238:45169', '185.93.3.123:8080', '194.182.64.67:3128', '106.0.38.174:8080', '163.172.175.210:3128', '13.92.196.150:8080']
proxies = get_proxies()
proxy_pool = cycle(proxies)

q = queue.Queue()

def add_queue(q, proxy):
    try:
        response = requests.get(url,proxies={"http": proxy, "https": proxy})
        print(response.json())
        print(response.status_code)
        q.put(proxy)
    except:
        #Most free proxies will often get connection errors. You will have retry the entire request using another proxy to work. 
        #We will just skip retries as its beyond the scope of this tutorial and we are only downloading a single url 
        print("Skipping. Connnection error")

url = 'https://httpbin.org/ip'
for i in range(len(proxies)):
    #Get a proxy from the pool
    proxy = next(proxy_pool)
    print("Request #%d"%i)
    t= threading.Thread(target=add_queue, args=(q, proxy))
    t.daemon = True
    t.start()
    #t.join()

from time import sleep

sleep(10)
print(list(q.queue))