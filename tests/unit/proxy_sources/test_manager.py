import pytest
from unittest.mock import Mock, patch
from fastProxy.proxy_sources.manager import ProxySourceManager
from fastProxy.proxy_sources.free_proxy_list import FreeProxyListSource
from fastProxy.proxy_sources.geonode import GeoNodeSource

@pytest.fixture
def mock_sources():
    """Fixture to create mock proxy sources"""
    free_proxy = Mock(spec=FreeProxyListSource)
    geonode = Mock(spec=GeoNodeSource)

    free_proxy.fetch.return_value = [
        {'ip': '1.2.3.4', 'port': '8080', 'country': 'US', 'anonymity': 'elite', 'https': 'yes'},
    ]
    geonode.fetch.return_value = [
        {'ip': '5.6.7.8', 'port': '3128', 'country': 'DE', 'anonymity': 'anonymous', 'https': 'no'},
    ]

    return free_proxy, geonode

def test_fetch_all_success(mock_sources):
    """Test successful fetching from all sources"""
    free_proxy, geonode = mock_sources

    with patch('fastProxy.proxy_sources.manager.FreeProxyListSource', return_value=free_proxy), \
         patch('fastProxy.proxy_sources.manager.GeoNodeSource', return_value=geonode):
        manager = ProxySourceManager()
        proxies = manager.fetch_all(max_proxies=10)

        assert len(proxies) == 2
        assert any(p['ip'] == '1.2.3.4' for p in proxies)
        assert any(p['ip'] == '5.6.7.8' for p in proxies)

def test_fetch_all_with_failed_source(mock_sources):
    """Test handling of failed source"""
    free_proxy, geonode = mock_sources
    free_proxy.fetch.side_effect = Exception("Source failed")

    with patch('fastProxy.proxy_sources.manager.FreeProxyListSource', return_value=free_proxy), \
         patch('fastProxy.proxy_sources.manager.GeoNodeSource', return_value=geonode):
        manager = ProxySourceManager()
        proxies = manager.fetch_all(max_proxies=10)

        assert len(proxies) == 1
        assert proxies[0]['ip'] == '5.6.7.8'

def test_fetch_all_max_proxies(mock_sources):
    """Test max_proxies limit"""
    free_proxy, geonode = mock_sources
    free_proxy.fetch.return_value = [
        {'ip': f'1.1.1.{i}', 'port': '8080', 'country': 'US', 'anonymity': 'elite', 'https': 'yes'}
        for i in range(5)
    ]

    with patch('fastProxy.proxy_sources.manager.FreeProxyListSource', return_value=free_proxy), \
         patch('fastProxy.proxy_sources.manager.GeoNodeSource', return_value=geonode):
        manager = ProxySourceManager()
        proxies = manager.fetch_all(max_proxies=3)

        assert len(proxies) == 3

def test_fetch_all_empty_sources(mock_sources):
    """Test handling of empty sources"""
    free_proxy, geonode = mock_sources
    free_proxy.fetch.return_value = []
    geonode.fetch.return_value = []

    with patch('fastProxy.proxy_sources.manager.FreeProxyListSource', return_value=free_proxy), \
         patch('fastProxy.proxy_sources.manager.GeoNodeSource', return_value=geonode):
        manager = ProxySourceManager()
        proxies = manager.fetch_all()

        assert len(proxies) == 0
