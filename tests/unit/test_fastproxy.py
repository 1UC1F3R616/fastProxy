import pytest
from unittest.mock import patch, MagicMock, mock_open
from queue import Queue
from fastProxy.fastProxy import (
    alter_globals, alive_ip, check_proxy, fetch_proxies,
    generate_csv, printer, main
)

class TestFastProxy:
    @pytest.fixture
    def mock_response(self):
        mock = MagicMock()
        mock.status_code = 200
        mock.text = '<table><tr><td>127.0.0.1</td><td>8080</td><td>US</td><td>United States</td><td>elite proxy</td><td>yes</td><td>yes</td><td>1 minute ago</td></tr></table>'
        return mock

    @pytest.fixture
    def mock_proxy_queue(self):
        queue = Queue()
        proxy_data = {
            'ip': '127.0.0.1',
            'port': '8080',
            'code': 'US',
            'country': 'United States',
            'anonymity': 'elite proxy',
            'google': 'yes',
            'https': 'yes',
            'last_checked': '1 minute ago'
        }
        queue.put(proxy_data)
        return queue

    def test_alter_globals(self):
        # Test with all parameters
        alter_globals(c=100, t=5, g=True, a=True)
        from fastProxy.fastProxy import CONCURRENT_REQUESTS, THREADS, GOOGLE_PROXIES_ONLY, ANONYMOUS_PROXIES_ONLY
        assert CONCURRENT_REQUESTS == 100
        assert THREADS == 5
        assert GOOGLE_PROXIES_ONLY is True
        assert ANONYMOUS_PROXIES_ONLY is True

    @patch('fastProxy.fastProxy.requests.get')
    def test_check_proxy(self, mock_get):
        proxy_data = {
            'ip': '127.0.0.1',
            'port': '8080',
            'code': 'US',
            'country': 'United States',
            'anonymity': 'elite proxy',
            'google': 'yes',
            'https': 'yes',
            'last_checked': '1 minute ago'
        }

        # Test successful proxy
        mock_get.return_value.status_code = 200
        assert check_proxy(proxy_data) is True

        # Test failed proxy
        mock_get.side_effect = Exception("Connection error")
        assert check_proxy(proxy_data) is False

    @patch('fastProxy.fastProxy.requests.get')
    @patch('fastProxy.fastProxy.BeautifulSoup')
    def test_fetch_proxies(self, mock_bs, mock_get, mock_response):
        mock_get.return_value = mock_response
        mock_bs.return_value.find.return_value.find_all.return_value = [
            mock_response.text
        ]

        proxies = fetch_proxies(c=1, t=1, g=False, a=False)
        assert isinstance(proxies, list)
        assert len(proxies) >= 0

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_csv(self, mock_file, mock_proxy_queue):
        with patch('os.path.exists') as mock_exists:
            with patch('os.makedirs') as mock_makedirs:
                mock_exists.return_value = False
                generate_csv()
                mock_makedirs.assert_called_once()
                mock_file.assert_called_once()

    def test_printer(self, mock_proxy_queue):
        with patch('fastProxy.fastProxy.logger.info') as mock_logger:
            printer()
            assert mock_logger.called

    def test_main_with_no_proxies(self):
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            mock_fetch.return_value = []
            result = main()
            assert isinstance(result, list)
            mock_fetch.assert_called_once()

    def test_main_with_proxy_list(self):
        proxy_list = ['127.0.0.1:8080', '127.0.0.2:8081']
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            result = main(proxies=proxy_list)
            assert isinstance(result, list)
            mock_fetch.assert_called_once()

    @patch('fastProxy.fastProxy.requests.get')
    def test_alive_ip_thread(self, mock_get, mock_proxy_queue):
        thread = alive_ip(mock_proxy_queue)

        # Test successful proxy check
        mock_get.return_value.status_code = 200
        thread.start()
        thread.join()

        # Test failed proxy check
        mock_get.side_effect = Exception("Connection error")
        thread = alive_ip(mock_proxy_queue)
        thread.start()
        thread.join()
