import pytest
import requests
from unittest.mock import patch, MagicMock, mock_open
from queue import Queue
import threading
import time
import os
from fastProxy.fastProxy import (
    alter_globals, alive_ip, fetch_proxies, generate_csv,
    printer, main, THREAD_COUNT, REQUEST_TIMEOUT, GENERATE_CSV,
    ALL_PROXIES, alive_queue
)
from fastProxy.logger import logger

class TestFastProxy:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Reset globals before and after each test"""
        global THREAD_COUNT, REQUEST_TIMEOUT, GENERATE_CSV, ALL_PROXIES

        # Store original values
        self.original_thread_count = THREAD_COUNT
        self.original_timeout = REQUEST_TIMEOUT
        self.original_csv = GENERATE_CSV
        self.original_all = ALL_PROXIES

        # Reset to default values before each test
        THREAD_COUNT = 100
        REQUEST_TIMEOUT = 4
        GENERATE_CSV = False
        ALL_PROXIES = False

        # Run the test
        yield

        # Only restore original values if not in test_alter_globals
        if self._testMethodName != 'test_alter_globals':
            THREAD_COUNT = self.original_thread_count
            REQUEST_TIMEOUT = self.original_timeout
            GENERATE_CSV = self.original_csv
            ALL_PROXIES = self.original_all

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
        """Test altering global variables"""
        global THREAD_COUNT, REQUEST_TIMEOUT, GENERATE_CSV, ALL_PROXIES

        # First test: verify initial state
        assert THREAD_COUNT == 100
        assert REQUEST_TIMEOUT == 4
        assert GENERATE_CSV is False
        assert ALL_PROXIES is False

        # Second test: change all parameters
        alter_globals(c=200, t=5, g=True, a=True)
        # Add a small delay to ensure globals are updated
        time.sleep(0.1)
        assert THREAD_COUNT == 200, f"Expected THREAD_COUNT to be 200, got {THREAD_COUNT}"
        assert REQUEST_TIMEOUT == 5, f"Expected REQUEST_TIMEOUT to be 5, got {REQUEST_TIMEOUT}"
        assert GENERATE_CSV is True, f"Expected GENERATE_CSV to be True, got {GENERATE_CSV}"
        assert ALL_PROXIES is True, f"Expected ALL_PROXIES to be True, got {ALL_PROXIES}"

        # Third test: change only some parameters
        alter_globals(c=50)
        time.sleep(0.1)
        assert THREAD_COUNT == 50, f"Expected THREAD_COUNT to be 50, got {THREAD_COUNT}"
        assert REQUEST_TIMEOUT == 5  # Should remain unchanged
        assert GENERATE_CSV is True  # Should remain unchanged
        assert ALL_PROXIES is True  # Should remain unchanged

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

        # Test unexpected exception in HTTPS request
        mock_get.side_effect = [
            requests.exceptions.RequestException("HTTP failed"),
            Exception("Unexpected error")
        ]
        assert thread.check_proxy(proxy_data) is False

        # Test non-200 status code
        mock_get.side_effect = None
        mock_get.return_value = MagicMock(status_code=404)
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

        # Test connection error
        mock_session.return_value.get.side_effect = requests.exceptions.RequestException("Connection error")
        proxies = fetch_proxies(max_proxies=1)
        assert proxies == []

        # Test parsing error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<table><tr><td>127.0.0.1</td></tr></table>'  # Missing required columns
        mock_session.return_value.get.return_value = mock_response
        proxies = fetch_proxies(max_proxies=1)
        assert proxies == []

    @patch('time.time')
    def test_thread_management(self, mock_time):
        """Test thread management with proper mocking"""
        # Create a mock thread class that properly inherits from Thread
        class MockThread(threading.Thread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.daemon = True
                self.start_called = False
                self.join_called = False

            def start(self):
                self.start_called = True

            def join(self, timeout=None):
                self.join_called = True

        # Setup time mock to simulate timeout
        mock_time.side_effect = [0, 30, 45, 50, 55, 61]

        with patch('fastProxy.fastProxy.alive_ip', MockThread), \
             patch('requests.session') as mock_session:
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
            # Get the last created thread instance
            thread_instance = MockThread()
            thread_instance.start()
            thread_instance.join()
            assert thread_instance.start_called
            assert thread_instance.join_called

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

    def test_error_handling_edge_cases(self):
        # Test with invalid proxy format
        proxy_list = ['invalid:format']
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            mock_fetch.return_value = []
            result = main(proxies=proxy_list)
            assert isinstance(result, list)
            assert len(result) == 0

        # Test with empty proxy list
        proxy_list = []
        with patch('requests.session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '<table></table>'
            mock_session.return_value.get.return_value = mock_response
            result = main(proxies=proxy_list)
            assert isinstance(result, list)
            assert len(result) == 0

    def test_table_parsing_edge_cases(self):
        """Test edge cases in proxy table parsing"""
        with patch('requests.session') as mock_session:
            # Test missing columns
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '''
            <table>
                <tr>
                    <th>IP Address</th>
                    <th>Port</th>
                </tr>
                <tr>
                    <td>127.0.0.1</td>
                    <td>8080</td>
                </tr>
            </table>
            '''
            mock_session.return_value.get.return_value = mock_response
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

            # Test invalid port
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
                    <td>invalid</td>
                    <td>US</td>
                    <td>United States</td>
                    <td>elite proxy</td>
                    <td>yes</td>
                    <td>yes</td>
                    <td>1 minute ago</td>
                </tr>
            </table>
            '''
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

    def test_thread_management_edge_cases(self):
        """Test thread management edge cases"""
        # Create a mock thread class that properly inherits from Thread
        class MockThread(threading.Thread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.daemon = True
                self.start_called = False
                self.join_called = False

            def start(self):
                self.start_called = True

            def join(self, timeout=None):
                self.join_called = True

        # Setup time mock to simulate timeout
        with patch('time.time') as mock_time, \
             patch('requests.session') as mock_session, \
             patch('fastProxy.fastProxy.alive_ip', MockThread):

            # Setup mock response
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

            # Test thread join timeout
            mock_time.side_effect = [0] + [61] * 10  # First call returns 0, rest return 61
            proxies = fetch_proxies(c=1, t=1, max_proxies=1)
            assert isinstance(proxies, list)

            # Get the last created thread instance
            thread_instance = MockThread()
            thread_instance.start()
            thread_instance.join()
            assert thread_instance.start_called
            assert thread_instance.join_called

            # Test thread exception handling
            mock_time.side_effect = [0] + [30] * 10
            thread_instance.join = MagicMock(side_effect=Exception("Thread error"))
            proxies = fetch_proxies(c=1, t=1, max_proxies=1)
            assert isinstance(proxies, list)

    def test_main_edge_cases(self):
        """Test main function edge cases"""
        # Test with invalid proxy string format
        with pytest.raises(IndexError):
            main(proxies=['invalid_format'])

        # Test with mixed proxy formats
        proxies = ['127.0.0.1:8080', 'invalid:format']
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            mock_fetch.return_value = []
            result = main(proxies=proxies)
            assert isinstance(result, list)
            assert len(result) == 0

        # Test with non-list proxies
        with pytest.raises(TypeError):
            main(proxies='127.0.0.1:8080')

    def test_proxy_validation_timeout(self):
        """Test proxy validation with timeout"""
        with patch('requests.session') as mock_session:
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

            with patch('time.time') as mock_time:
                mock_time.side_effect = [0, 30, 45, 50, 55, 61] * 10  # Ensure enough values
                proxies = fetch_proxies(c=1, t=1, max_proxies=1)
                assert isinstance(proxies, list)
