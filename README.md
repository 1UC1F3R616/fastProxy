<p align="center">
  <img width="600" height="200" src="https://user-images.githubusercontent.com/41824020/80387953-e7147080-88c6-11ea-9c35-4fd083f47ec4.jpg">
</p>
<p align="center">
  MultiThreaded Application to Scrape Working Web Proxies
<p>
  
<p align="center">
	<a align="center" href="https://pypi.org/project/fastProxy"><img src="https://badge.fury.io/py/fastProxy.svg" alt="PyPI version"></a>
</p>

---
[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

[![Open Source Love png3](https://badges.frapsoft.com/os/v3/open-source.png?v=103)](https://github.com/ellerbrock/open-source-badges/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/1UC1F3R616/fastProxy)

## Functionalites
- [x] More than 300 Live Proxy Fetch
- [x] CLI Support
- [x] Selection of Proxy based on Speed
- [x] Proxy Export
- [ ] Country Filteration

## Installation
### pip install
```bash
pip install fastProxy==0.1.3
```
### git clone
```text
git clone https://github.com/1UC1F3R616/fastProxy.git
cd fastProxy/
pip install -r requirements.txt
```

## Run using CLI
#### Default run
- Threads: 100
- Request Timeout: 4sec
```bash
python fastProxy.py 
```
#### Aletered Parameters

| Flag        | Usage           | Purpose  |  Default  |  Usage  |
| ------------- |:-------------:|:-----:|:-----:|:-----:|
| c     | Thread Count | Increase Testing Speed |   100 | `--c=16`  |
| t      | Request Timeout in sec    |   Give Faster Proxy when set to lower Values | 4 | `--t=20`  |
| g | Generate CSV      |  Generate CSV of Working proxy only with user flags| False | `--g` |
| a | All Scraped Proxy     |  Generate CSV of All Scrapped Proxies with more Detail  | False | `--a` |

```bash
python fastProxy.py --c=256 --t=2 --g --a 
```

## Run by import
- Set Flags or Default Values are Taken

| Flag        | Usage           | Purpose  |  Default  | Usage|
| ------------- |:-------------:|:-----:|:-----:|:-----:|
| c     | Thread Count | Increase Testing Speed |   100 | `c=256`|
| t      | Request Timeout in sec    |   Give Faster Proxy when set to lower Values| 4 | `t=2` |
| g | Generate CSV      |  Generate CSV of Working proxy only with user flags| False | `g=True`|
| a | All Scraped Proxy     |  Generate CSV of All Scrapped Proxies with more Detail  | False | `a=True`|

```py
import fastProxy

myProxyList = fastProxy.fetch_proxies(c=128, t=2, g=True, a=True)

print(myProxyList)
```

#### Sample [CSV File](https://github.com/1UC1F3R616/fastProxy/blob/master/Sample/all_proxies.csv)

</br>

[![LinkedIn](https://img.shields.io/static/v1.svg?label=Connect&message=@Kush&color=grey&logo=linkedin&labelColor=blue&style=social)](https://www.linkedin.com/in/kush-choudhary-567b38169?lipi=urn%3Ali%3Apage%3Ad_flagship3_profile_view_base_contact_details%3BDYkgbUGhTniMSRqOUkdN3A%3D%3D)
[![LinkedIn](https://img.shields.io/static/v1.svg?label=Connect&message=@Dhruv&color=grey&logo=linkedin&labelColor=blue&style=social)](https://www.linkedin.com/in/dhruv-agarwal-043ab3179/?lipi=urn%3Ali%3Apage%3Ad_flagship3_profile_view_base_contact_details%3BDYkgbUGhTniMSRqOUkdN3A%3D%3D)
