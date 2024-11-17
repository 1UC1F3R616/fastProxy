import pytest
import requests
from unittest.mock import patch, MagicMock, mock_open
from queue import Queue
import threading
import time
from fastProxy.fastProxy import (
    alter_globals, alive_ip, fetch_proxies,
    generate_csv, printer, main,
    THREAD_COUNT, REQUEST_TIMEOUT, GENERATE_CSV, ALL_PROXIES
)

class TestFastProxy:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Reset globals before and after each test"""
        yield
        alter_globals(c=100, t=4, g=False, a=False)

    @pytest.fixture
    def mock_proxy_data(self):
        return {
            'ip': '127.0.0.1',
            'port': '8080',
            'code': 'US',
            'country': 'United States',
            'anonymity': 'elite proxy',
            'google': True,
            'https': True,
            'last_checked': '1 minute ago'
        }

    @pytest.fixture
    def mock_proxy_queue(self):
        queue = Queue()
        proxy_data = {
            'ip': '127.0.0.1',
            'port': '8080',
            'code': 'US',
            'country': 'United States',
            'anonymity': 'elite proxy',
            'google': True,
            'https': True,
            'last_checked': '1 minute ago'
        }
        queue.put(proxy_data)
        return queue

    def test_alter_globals(self):
        # Test with all parameters
        alter_globals(c=100, t=5, g=True, a=True)
        assert THREAD_COUNT == 100
        assert REQUEST_TIMEOUT == 5
        assert GENERATE_CSV is True
        assert ALL_PROXIES is True

        # Test with partial parameters
        alter_globals(c=50)
        assert THREAD_COUNT == 50
        assert REQUEST_TIMEOUT == 5  # Unchanged
        assert GENERATE_CSV is True  # Unchanged
        assert ALL_PROXIES is True  # Unchanged

    @patch('requests.get')
    def test_alive_ip_check_proxy(self, mock_get):
        queue = Queue()
        thread = alive_ip(queue)
        proxy_data = {
            'ip': '127.0.0.1',
            'port': '8080',
            'code': 'US',
            'country': 'United States',
            'anonymity': 'elite proxy',
            'google': True,
            'https': False,
            'last_checked': '1 minute ago'
        }

        # Test successful HTTP proxy
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        assert thread.check_proxy(proxy_data) is True

        # Test failed HTTP but successful HTTPS proxy
        mock_get.side_effect = [
            requests.exceptions.RequestException("HTTP failed"),
            MagicMock(status_code=200)
        ]
        proxy_data['https'] = True
        assert thread.check_proxy(proxy_data) is True

        # Test both HTTP and HTTPS failure
        mock_get.side_effect = requests.exceptions.RequestException("Both failed")
        assert thread.check_proxy(proxy_data) is False

    @patch('requests.session')
    def test_fetch_proxies_success(self, mock_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''
        <table>
            <tr>
                <th>IP Address</th>
                <th>Port</th>
                <th>Code</th>
                <th>Country</th>
                <th>Anonymity</th>
                <th>Google</th>
                <th>Https</th>
                <th>Last Checked</th>
            </tr>
            <tr>
                <td>127.0.0.1</td>
                <td>8080</td>
                <td>US</td>
                <td>United States</td>
                <td>elite proxy</td>
                <td>yes</td>
                <td>yes</td>
                <td>1 minute ago</td>
            </tr>
        </table>
        '''
        mock_session.return_value.get.return_value = mock_response
        proxies = fetch_proxies(c=1, t=1, max_proxies=1)
        assert isinstance(proxies, list)

    @patch('requests.session')
    def test_fetch_proxies_failure(self, mock_session):
        # Test HTTP error
        mock_session.return_value.get.return_value = MagicMock(status_code=404)
        proxies = fetch_proxies(max_proxies=1)
        assert proxies == []

        # Test invalid table structure
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<table><tr><td>Invalid</td></tr></table>'
        mock_session.return_value.get.return_value = mock_response
        proxies = fetch_proxies(max_proxies=1)
        assert proxies == []

        # Test exception handling
        mock_session.return_value.get.side_effect = Exception("Connection error")
        proxies = fetch_proxies(max_proxies=1)
        assert proxies == []

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_generate_csv(self, mock_makedirs, mock_exists, mock_file, mock_proxy_queue):
        # Test directory creation
        mock_exists.return_value = False
        generate_csv()
        mock_makedirs.assert_called_once()
        mock_file.assert_called_once()

        # Test existing directory
        mock_exists.return_value = True
        generate_csv()
        assert mock_makedirs.call_count == 1  # Should not be called again

    def test_printer(self, mock_proxy_queue):
        with patch('fastProxy.fastProxy.logger.info') as mock_logger:
            printer()
            assert mock_logger.call_count >= 2  # Header + at least one proxy

    def test_main_with_no_proxies(self):
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            mock_fetch.return_value = []
            result = main()
            assert isinstance(result, list)
            mock_fetch.assert_called_once_with()

    def test_main_with_proxy_list(self):
        proxy_list = ['127.0.0.1:8080']
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            mock_fetch.return_value = [{'ip': '127.0.0.1', 'port': '8080'}]
            result = main(proxies=proxy_list)
            assert isinstance(result, list)
            assert len(result) == 1
            mock_fetch.assert_called_once()
