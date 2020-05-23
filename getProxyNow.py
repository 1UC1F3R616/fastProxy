""" Just Run Me and I will give u a list
    Change any params if you want
    Make sure complete repo is cloned :)
"""

import fastProxy as p


print(dir(p))
p.THREAD_COUNT = 100
p.REQUEST_TIMEOUT = 3
p.GENERATE_CSV = False
p.ALL_IPS = False
print(p.THREAD_COUNT)
print(p.fetch_proxies())
