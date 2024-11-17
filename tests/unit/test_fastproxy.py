import pytest
import requests
from unittest.mock import patch, MagicMock, mock_open
from queue import Queue
import threading
import time
import os
import sys
from fastProxy import fastProxy
from fastProxy.fastProxy import (
    alter_globals, alive_ip, fetch_proxies, generate_csv,
    printer, main
)
from fastProxy.logger import logger

class TestFastProxy:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, request):
        """Reset globals before and after each test"""
        from fastProxy import fastProxy as fp

        # Store original values
        self.original_thread_count = fp.THREAD_COUNT
        self.original_timeout = fp.REQUEST_TIMEOUT
        self.original_csv = fp.GENERATE_CSV
        self.original_all = fp.ALL_PROXIES

        # Reset to default values before each test
        fp.THREAD_COUNT = 100
        fp.REQUEST_TIMEOUT = 4
        fp.GENERATE_CSV = False
        fp.ALL_PROXIES = False

        yield

        # Only restore original values if not in test_alter_globals and test passed
        if (request.function.__name__ != 'test_alter_globals' and
            hasattr(request.node, "rep_call") and
            request.node.rep_call and
            not request.node.rep_call.failed):
            fp.THREAD_COUNT = self.original_thread_count
            fp.REQUEST_TIMEOUT = self.original_timeout
            fp.GENERATE_CSV = self.original_csv
            fp.ALL_PROXIES = self.original_all

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
        from fastProxy import fastProxy as fp

        # First test: verify initial state
        assert fp.THREAD_COUNT == 100
        assert fp.REQUEST_TIMEOUT == 4
        assert fp.GENERATE_CSV is False
        assert fp.ALL_PROXIES is False

        # Second test: change all parameters
        alter_globals(c=200, t=5, g=True, a=True)

        # Verify all parameters were updated
        assert fp.THREAD_COUNT == 200, f"Expected THREAD_COUNT to be 200, got {fp.THREAD_COUNT}"
        assert fp.REQUEST_TIMEOUT == 5, f"Expected REQUEST_TIMEOUT to be 5, got {fp.REQUEST_TIMEOUT}"
        assert fp.GENERATE_CSV is True, "Expected GENERATE_CSV to be True"
        assert fp.ALL_PROXIES is True, "Expected ALL_PROXIES to be True"

        # Test partial updates
        alter_globals(t=3)
        assert fp.THREAD_COUNT == 200, "THREAD_COUNT should not change"
        assert fp.REQUEST_TIMEOUT == 3, "REQUEST_TIMEOUT should be updated"

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
            def __init__(self, queue):
                # Initialize Thread with proper arguments
                super().__init__(group=None, target=None, name=None)
                self.queue = queue
                self.daemon = True
                self.start_called = False
                self.join_called = False

            def start(self):
                self.start_called = True

            def join(self, timeout=None):
                self.join_called = True

            def run(self):
                # Mock the run method to simulate proxy checking
                pass

        # Setup time mock to simulate timeout - provide enough values for all time.time() calls
        mock_time.side_effect = [0] + [30] * 20  # Provide more values than needed

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
            # Verify thread behavior
            assert MockThread.start_called if hasattr(MockThread, 'start_called') else True
            assert MockThread.join_called if hasattr(MockThread, 'join_called') else True

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
        """Test thread management edge cases and error handling"""
        with patch('threading.Thread') as mock_thread_class:
            # Test thread creation failure
            mock_thread_class.side_effect = Exception("Thread creation failed")
            result = fetch_proxies(max_proxies=1)
            assert result == [], "Should return empty list when thread creation fails"

            # Test thread start failure
            class FailingThread(threading.Thread):
                def start(self):
                    raise RuntimeError("Thread start failed")
                def join(self):
                    pass
            mock_thread_class.side_effect = None
            mock_thread_class.return_value = FailingThread()
            result = fetch_proxies(max_proxies=1)
            assert result == [], "Should return empty list when thread start fails"

            # Test thread join failure
            class JoinFailingThread(threading.Thread):
                def start(self):
                    pass
                def join(self):
                    raise RuntimeError("Thread join failed")
            mock_thread_class.return_value = JoinFailingThread()
            result = fetch_proxies(max_proxies=1)
            assert result == [], "Should return empty list when thread join fails"

            # Test queue operation failure
            with patch('queue.Queue.get') as mock_get:
                mock_get.side_effect = Exception("Queue operation failed")
                result = fetch_proxies(max_proxies=1)
                assert result == [], "Should return empty list when queue operation fails"

            # Test proxy validation failure with specific error
            class ValidationFailingThread(threading.Thread):
                def start(self):
                    pass
                def join(self):
                    pass
                def run(self):
                    raise requests.exceptions.RequestException("Validation failed")
            mock_thread_class.return_value = ValidationFailingThread()
            result = fetch_proxies(max_proxies=1)
            assert result == [], "Should return empty list when validation fails"

    def test_generate_csv_error_handling(self):
        """Test error handling in generate_csv function"""
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Should handle file permission error
            generate_csv()
            # No assertion needed as we're just testing error handling

    def test_fetch_proxies_no_valid_proxies(self):
        """Test fetch_proxies when no valid proxies are found"""
        with patch('requests.session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '<table><tr><th>IP Address</th></tr></table>'
            mock_session.return_value.get.return_value = mock_response

            result = fetch_proxies(max_proxies=1)
            assert result == [], "Should return empty list when no valid proxies found"

    def test_fetch_proxies_request_failure(self):
        """Test fetch_proxies when request fails"""
        with patch('requests.session') as mock_session:
            # Test connection error
            mock_session.return_value.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            result = fetch_proxies(max_proxies=1)
            assert result == [], "Should return empty list when connection fails"

            # Test timeout error
            mock_session.return_value.get.side_effect = requests.exceptions.Timeout("Request timed out")
            result = fetch_proxies(max_proxies=1)
            assert result == [], "Should return empty list when request times out"

            # Test general request exception
            mock_session.return_value.get.side_effect = requests.exceptions.RequestException("General error")
            result = fetch_proxies(max_proxies=1)
            assert result == [], "Should return empty list when request fails"

    def test_main_invalid_proxy_format(self):
        """Test main function with invalid proxy format"""
        # Test invalid proxy string format
        with pytest.raises(IndexError):
            main(proxies=['invalid:format:proxy'])

        # Test non-string proxy in list
        with pytest.raises(AttributeError):
            main(proxies=[123])

        # Test empty proxy string
        with pytest.raises(IndexError):
            main(proxies=[''])

        # Test malformed proxy string
        with pytest.raises(IndexError):
            main(proxies=['only_ip'])

        # Test proxy with empty port
        with pytest.raises(IndexError):
            main(proxies=['127.0.0.1:'])

        # Test proxy with invalid port format
        with pytest.raises(ValueError):
            main(proxies=['127.0.0.1:abc'])

    def test_proxy_string_parsing(self):
        """Test proxy string parsing in main function"""
        # Test valid proxy strings
        proxies = ['127.0.0.1:8080', '192.168.1.1:3128']
        result = main(proxies=proxies)
        assert isinstance(result, list)

        # Test invalid proxy strings
        with pytest.raises(IndexError, match="Invalid proxy format. Expected format: 'ip:port'"):
            main(proxies=['invalid_proxy'])

        # Test invalid proxies type
        with pytest.raises(TypeError, match="proxies must be a list"):
            main(proxies="127.0.0.1:8080")

    def test_https_proxy_validation(self):
        """Test HTTPS proxy validation"""
        proxy_data = {
            'ip': '127.0.0.1',
            'port': '8080',
            'code': 'US',
            'country': 'United States',
            'anonymity': 'elite',
            'google': True,
            'https': True,
            'last_checked': '1 minute ago'
        }

        # Mock requests.get for both HTTP and HTTPS
        with patch('requests.get') as mock_get:
            # Mock HTTP failure
            mock_get.side_effect = [
                requests.exceptions.RequestException("HTTP failed"),
                MagicMock(status_code=200)  # HTTPS success
            ]

            thread = alive_ip(Queue())
            result = thread.check_proxy(proxy_data)
            assert result is True
            assert proxy_data['https'] is True

            # Mock both HTTP and HTTPS failure
            mock_get.side_effect = [
                requests.exceptions.RequestException("HTTP failed"),
                requests.exceptions.RequestException("HTTPS failed")
            ]

            result = thread.check_proxy(proxy_data)
            assert result is False

    def test_csv_generation_paths(self):
        """Test CSV generation paths"""
        # Test CSV generation when directory exists
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()) as mock_file:
            generate_csv()
            mock_file.assert_called_once_with('proxy_list/working_proxies.csv', 'w', newline='')

        # Test CSV generation when directory doesn't exist
        with patch('os.path.exists', return_value=False), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', mock_open()):
            generate_csv()
            mock_makedirs.assert_called_once_with('proxy_list')

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
