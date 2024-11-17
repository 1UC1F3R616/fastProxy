import pytest
import requests
import requests_mock
from bs4 import BeautifulSoup
from fastProxy.proxy_sources.free_proxy_list import FreeProxyListSource

SAMPLE_HTML = """
<table id="proxylisttable">
    <tbody>
        <tr>
            <td>1.2.3.4</td>
            <td>8080</td>
            <td>US</td>
            <td>United States</td>
            <td>elite proxy</td>
            <td>yes</td>
            <td>yes</td>
            <td>1 minute ago</td>
        </tr>
        <tr>
            <td>5.6.7.8</td>
            <td>3128</td>
            <td>DE</td>
            <td>Germany</td>
            <td>anonymous</td>
            <td>no</td>
            <td>no</td>
            <td>5 minutes ago</td>
        </tr>
    </tbody>
</table>
"""

def test_fetch_success(requests_mock):
    """Test successful proxy fetching from free-proxy-list.net"""
    source = FreeProxyListSource()
    requests_mock.get(source.URL, text=SAMPLE_HTML)

    proxies = source.fetch()

    assert len(proxies) == 2
    assert proxies[0] == {
        'ip': '1.2.3.4',
        'port': '8080',
        'code': 'US',
        'country': 'United States',
        'anonymity': 'elite proxy',
        'google': 'yes',
        'https': 'yes',
        'last_checked': '1 minute ago'
    }
    assert proxies[1] == {
        'ip': '5.6.7.8',
        'port': '3128',
        'code': 'DE',
        'country': 'Germany',
        'anonymity': 'anonymous',
        'google': 'no',
        'https': 'no',
        'last_checked': '5 minutes ago'
    }

def test_fetch_no_table(requests_mock):
    """Test handling of HTML without proxy table"""
    source = FreeProxyListSource()
    requests_mock.get(source.URL, text="<html><body>No table here</body></html>")

    proxies = source.fetch()
    assert len(proxies) == 0

def test_fetch_error_response(requests_mock):
    """Test handling of HTTP error response"""
    source = FreeProxyListSource()
    requests_mock.get(source.URL, status_code=500)

    proxies = source.fetch()
    assert len(proxies) == 0

def test_fetch_connection_error(requests_mock):
    """Test handling of connection error"""
    source = FreeProxyListSource()
    requests_mock.get(source.URL, exc=requests.exceptions.ConnectionError)

    proxies = source.fetch()
    assert len(proxies) == 0

def test_fetch_invalid_html(requests_mock):
    """Test handling of invalid HTML response"""
    source = FreeProxyListSource()
    requests_mock.get(source.URL, text="<not>valid</html>")

    proxies = source.fetch()
    assert len(proxies) == 0
