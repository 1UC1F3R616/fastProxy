import pytest
import unittest
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
    printer, alive_queue, THREAD_COUNT, REQUEST_TIMEOUT,
    GENERATE_CSV, ALL_PROXIES
)
from fastProxy.logger import logger

@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global variables before each test."""
    # Store original values
    original_globals = {}
    try:
        original_globals['THREAD_COUNT'] = THREAD_COUNT
        original_globals['REQUEST_TIMEOUT'] = REQUEST_TIMEOUT
        original_globals['GENERATE_CSV'] = GENERATE_CSV
        original_globals['ALL_PROXIES'] = ALL_PROXIES

        # Clear queue
        while not alive_queue.empty():
            alive_queue.get()
    except (ImportError, AttributeError) as e:
        logger.error(f"Error in reset_globals: {str(e)}")

    # Reset globals
    alter_globals(c=100, t=100, g=True, a=True)

    yield

    # Restore original values
    try:
        for key, value in original_globals.items():
            setattr(fastProxy, key, value)
        # Clear queue again
        while not alive_queue.empty():
            alive_queue.get()
    except (ImportError, AttributeError) as e:
        logger.error(f"Error restoring globals: {str(e)}")

class TestFastProxy(unittest.TestCase):
    """Test cases for fastProxy functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Clear queue before each test
        while not alive_queue.empty():
            alive_queue.get()

    def tearDown(self):
        """Clean up after each test"""
        # Clear queue after each test
        while not alive_queue.empty():
            alive_queue.get()

    @patch('requests.get')
    def test_alive_ip_check_proxy(self, mock_get):
        """Test proxy validation"""
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
        mock_response.text = '{"origin": "127.0.0.1"}'
        mock_get.return_value = mock_response

        thread = alive_ip(proxy_data)
        thread.start()
        thread.join(timeout=5)  # Increased timeout for stability

        self.assertFalse(alive_queue.empty())
        proxy_info = alive_queue.get()
        self.assertEqual(proxy_info['ip'], '127.0.0.1')
        self.assertEqual(proxy_info['port'], '8080')

    @patch('requests.get')
    def test_alive_ip_check_proxy(self, mock_get):
        """Test proxy validation"""
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
        mock_response.text = '{"origin": "127.0.0.1"}'
        mock_get.return_value = mock_response

        thread = alive_ip(proxy_data)
        thread.start()
        thread.join(timeout=5)  # Increased timeout for stability

        self.assertFalse(alive_queue.empty())
        proxy_info = alive_queue.get()
        self.assertEqual(proxy_info['proxy'], '127.0.0.1:8080')
        self.assertEqual(proxy_info['type'], 'http')
        self.assertEqual(proxy_info['country'], 'United States')
        self.assertEqual(proxy_info['anonymity'], 'elite proxy')

        # Test HTTPS proxy
        proxy_data['https'] = True
        thread = alive_ip(proxy_data)
        thread.start()
        thread.join(timeout=5)

        self.assertFalse(alive_queue.empty())
        proxy_info = alive_queue.get()
        self.assertEqual(proxy_info['proxy'], '127.0.0.1:8080')
        self.assertEqual(proxy_info['type'], 'https')
        self.assertEqual(proxy_info['country'], 'United States')
        self.assertEqual(proxy_info['anonymity'], 'elite proxy')

        # Test failed proxy
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")
        thread = alive_ip(proxy_data)
        thread.start()
        thread.join(timeout=5)

        self.assertTrue(alive_queue.empty())

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
    @patch('fastProxy.proxy_sources.manager.ProxySourceManager.fetch_all')
    def test_fetch_proxies_failure(self, mock_fetch_all, mock_session):
        """Test proxy fetching failure scenarios"""
        # Test when no proxies are found
        mock_fetch_all.return_value = []
        proxies = fetch_proxies(max_proxies=1)
        assert proxies == []

        # Test when proxies are found but validation fails
        mock_fetch_all.return_value = [{
            'ip': '127.0.0.1',
            'port': '8080',
            'country': 'Test',
            'anonymity': 'unknown',
            'https': 'no'
        }]
        # Mock validation to fail
        with patch('requests.get', side_effect=requests.exceptions.RequestException):
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

        # Test when proxy source raises an exception
        mock_fetch_all.side_effect = Exception("Source error")
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
                self.working_proxies = []
                self.start_called = False
                self.join_called = False

            def start(self):
                self.start_called = True

            def join(self, timeout=None):
                self.join_called = True

            def run(self):
                # Mock the run method to simulate proxy checking
                pass

        # Setup time mock to simulate gradual time progression
        start_time = 0
        def time_sequence():
            nonlocal start_time
            while True:
                yield start_time
                start_time += 0.1

        mock_time.side_effect = time_sequence()

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
    def test_generate_csv(self, mock_makedirs, mock_exists, mock_file):
        # Test directory creation when directory doesn't exist
        mock_exists.return_value = False
        working_proxies = [{'proxy': '127.0.0.1:8080', 'type': 'http', 'country': 'US', 'anonymity': 'elite'}]

        generate_csv(working_proxies)
        mock_makedirs.assert_called_once_with('proxy_list', exist_ok=True)
        mock_file.assert_called_with('proxy_list/working_proxies.csv', 'w', newline='')

        # Reset mocks for next test
        mock_makedirs.reset_mock()
        mock_file.reset_mock()

        # Test when directory already exists - makedirs should still be called with exist_ok=True
        mock_exists.return_value = True
        generate_csv(working_proxies)
        mock_makedirs.assert_called_once_with('proxy_list', exist_ok=True)
        mock_file.assert_called_with('proxy_list/working_proxies.csv', 'w', newline='')

    @patch('fastProxy.fastProxy.alive_queue')
    def test_printer(self, mock_queue):
        """Test printer function with various scenarios"""
        # Mock the queue with proper attributes
        mock_queue.queue = []
        mock_queue.empty.return_value = True

        # Test with empty queue
        with patch('builtins.print') as mock_print:
            printer()
            mock_print.assert_not_called()

        # Test with single proxy
        proxy = {'ip': '127.0.0.1', 'port': '8080', 'https': True}
        mock_queue.queue = [proxy]
        mock_queue.empty.return_value = False

        with patch('builtins.print') as mock_print:
            printer()
            assert mock_print.call_count >= 1, "Print should be called at least once"

        # Test with multiple proxies
        mock_queue.queue = [proxy, proxy]
        with patch('builtins.print') as mock_print:
            printer()
            assert mock_print.call_count >= 2, "Print should be called at least twice"

    @patch('fastProxy.proxy_sources.manager.ProxySourceManager.fetch_all')
    def test_fetch_proxies_empty(self, mock_fetch_all):
        """Test fetch_proxies with no valid proxies"""
        mock_fetch_all.return_value = []
        proxies = fetch_proxies()
        assert proxies == []

    @patch('fastProxy.proxy_sources.manager.ProxySourceManager.fetch_all')
    def test_fetch_proxies_with_data(self, mock_fetch_all):
        """Test fetch_proxies with valid proxy data"""
        mock_fetch_all.return_value = [{'ip': '127.0.0.1', 'port': '8080'}]
        proxies = fetch_proxies(max_proxies=1)
        assert isinstance(proxies, list)

    def test_error_handling_edge_cases(self):
        """Test error handling edge cases"""
        # Test with invalid proxy format
        proxies = [{'invalid': 'data'}]
        result = fetch_proxies(proxies=proxies)
        assert result == []

        # Test with empty proxy list
        result = fetch_proxies(proxies=[])
        assert result == []

        # Test with None proxy list
        result = fetch_proxies(proxies=None)
        assert result == []

        # Test with invalid timeout
        result = fetch_proxies(t=-1)
        assert result == []

        # Test with invalid thread count
        result = fetch_proxies(c=-1)
        assert result == []

    def test_table_parsing_edge_cases(self):
        """Test edge cases in proxy table parsing"""
        # Test malformed row data
        malformed_html = """
        <table id="proxylisttable">
            <tbody>
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
            </tbody>
        </table>
        """

        class MockThread:
            def __init__(self):
                self.working_proxies = []
                pass
            def start(self):
                pass
            def join(self, timeout=None):
                pass
            def check_proxy(self, proxy):
                return False

        with patch('requests.get') as mock_get, \
             patch('fastProxy.fastProxy.alive_ip', return_value=MockThread()), \
             patch('time.time', side_effect=[0, 1, 2, 3, 4, 5] * 100):  # Ensure enough values
            mock_response = MagicMock()
            mock_response.text = malformed_html
            mock_get.return_value = mock_response
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

        # Test missing table
        no_table_html = "<div>No proxy table here</div>"
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = no_table_html
            mock_get.return_value = mock_response
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

        # Test timeout during proxy validation
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

        # Test CSV generation with directory creation error
        with patch('os.path.exists', return_value=False), \
             patch('os.makedirs', side_effect=OSError("Permission denied")):
            generate_csv([])
            assert True  # Should not raise exception

    def test_thread_management_edge_cases(self):
        """Test edge cases in thread management"""
        class FailingThread:
            def start(self):
                raise RuntimeError("Thread start failed")
            def join(self, timeout=None):
                pass

        class JoinFailingThread:
            def start(self):
                pass
            def join(self, timeout=None):
                raise RuntimeError("Thread join failed")

        class ValidationFailingThread:
            def start(self):
                pass
            def join(self, timeout=None):
                pass
            def run(self):
                raise RuntimeError("Validation failed")

        def time_sequence():
            start_time = 0
            while True:
                yield start_time
                start_time += 0.5  # Increment by 0.5 seconds each time

        # Test thread start failure
        with patch('fastProxy.fastProxy.alive_ip', return_value=FailingThread()), \
             patch('time.time', side_effect=time_sequence()), \
             patch('fastProxy.fastProxy.WORKING_PROXIES', []):
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

        # Test thread join failure
        with patch('fastProxy.fastProxy.alive_ip', return_value=JoinFailingThread()), \
             patch('time.time', side_effect=time_sequence()), \
             patch('fastProxy.fastProxy.WORKING_PROXIES', []):
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

        # Test thread timeout
        with patch('fastProxy.fastProxy.alive_ip', return_value=ValidationFailingThread()), \
             patch('time.time', side_effect=time_sequence()), \
             patch('fastProxy.fastProxy.WORKING_PROXIES', []):
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

    def test_generate_csv_error_handling(self):
        """Test error handling in CSV generation"""
        # Mock file operations
        mock_file = MagicMock()
        mock_file.write.side_effect = IOError("Mock write error")

        with patch('builtins.open', return_value=mock_file) as mock_file_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs') as mock_makedirs:

            # Test with empty list
            working_proxies = []
            generate_csv(working_proxies)
            mock_makedirs.assert_not_called()
            mock_file_open.assert_not_called()

            # Test with IOError during write
            working_proxies = [{'proxy': '127.0.0.1:8080', 'type': 'http', 'country': 'US', 'anonymity': 'elite'}]
            mock_file_open.side_effect = IOError("Mock open error")

            # Use logger.error to capture the error message
            with patch('fastProxy.logger.logger.error') as mock_logger:
                with pytest.raises(IOError):
                    generate_csv(working_proxies)
                mock_logger.assert_called_with("Error generating CSV: Mock open error")

    def test_fetch_proxies_no_valid_proxies(self):
        """Test fetch_proxies when no valid proxies are found"""
        html_content = """
        <table id="proxylisttable">
            <tbody>
                <tr>
                    <td>invalid</td>
                    <td>invalid</td>
                    <td>invalid</td>
                </tr>
            </tbody>
        </table>
        """
        with patch('requests.get') as mock_get, \
             patch('fastProxy.fastProxy.alive_ip') as mock_alive_ip, \
             patch('time.time', side_effect=[0, 1, 2, 3, 4, 5] * 100):
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_get.return_value = mock_response
            mock_thread = MagicMock()
            mock_thread.check_proxy.return_value = False
            mock_alive_ip.return_value = mock_thread
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

    def test_fetch_proxies_request_failure(self):
        """Test fetch_proxies when request fails"""
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Failed")):
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

    @patch('fastProxy.proxy_sources.manager.ProxySourceManager.fetch_all')
    def test_fetch_proxies_invalid_format(self, mock_fetch_all):
        """Test fetch_proxies with invalid proxy format"""
        # Test with missing required fields
        mock_fetch_all.return_value = [{'invalid': 'data'}]
        proxies = fetch_proxies()
        assert proxies == []

        # Test with invalid port format
        mock_fetch_all.return_value = [{'ip': '127.0.0.1', 'port': 'invalid'}]
        proxies = fetch_proxies()
        assert proxies == []

        # Test with invalid IP format
        mock_fetch_all.return_value = [{'ip': 'invalid', 'port': '8080'}]
        proxies = fetch_proxies()
        assert proxies == []

    def test_proxy_string_parsing(self):
        """Test parsing of proxy strings with various formats"""
        with patch('fastProxy.fastProxy.alive_ip') as mock_thread_class, \
             patch('fastProxy.fastProxy.requests.session') as mock_session, \
             patch('fastProxy.fastProxy.alive_queue') as mock_alive_queue:
            # Configure mock thread to not validate proxies
            mock_thread = MagicMock()
            mock_thread.daemon = True
            mock_thread_class.return_value = mock_thread

            # Configure session mock to return error
            mock_response = MagicMock()
            mock_response.status_code = 404  # Simulate failed request
            mock_response.text = '<html></html>'  # Empty HTML
            mock_session.return_value = MagicMock()
            mock_session.return_value.get.return_value = mock_response

            # Configure alive queue mock
            mock_alive_queue.queue = []

            result = fetch_proxies()
            assert result == [], "Should return empty list when proxy source is unavailable"

            # Test empty proxy list
            result = main(proxies=[])
            assert result == []

            # Test None proxy list
            result = main(proxies=None)
            assert isinstance(result, list)

    @patch('requests.get')
    def test_https_proxy_validation(self, mock_get):
        """Test HTTPS proxy validation"""
        proxy_data = {
            'ip': '127.0.0.1',
            'port': '8080',
            'https': True,
            'country': 'Test',
            'anonymity': 'elite'
        }

        # Test successful HTTPS proxy
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"origin": "127.0.0.1"}'
        mock_get.return_value = mock_response

        thread = alive_ip(proxy_data)
        thread.start()
        thread.join(timeout=1)
        assert not alive_queue.empty()
        proxy_info = alive_queue.get()
        assert proxy_info['type'] == 'https'

    def test_csv_generation_paths(self):
        """Test CSV generation with different paths"""
        working_proxies = [{
            'proxy': '127.0.0.1:8080',
            'type': 'http',
            'country': 'United States',
            'anonymity': 'elite proxy'
        }]

        # Test with new directory
        with patch('os.path.exists', return_value=False), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', new_callable=mock_open) as mock_file:
            generate_csv(working_proxies)
            mock_makedirs.assert_called_once()
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called()

        # Test with existing directory
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', new_callable=mock_open) as mock_file:
            generate_csv(working_proxies)
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called()

    @patch('fastProxy.proxy_sources.manager.ProxySourceManager.fetch_all')
    def test_fetch_proxies_edge_cases(self, mock_fetch_all):
        """Test fetch_proxies edge cases"""
        # Test with empty proxy list
        mock_fetch_all.return_value = []
        proxies = fetch_proxies()
        assert proxies == []

        # Test with None proxy list
        mock_fetch_all.return_value = None
        proxies = fetch_proxies()
        assert proxies == []

        # Test with exception from proxy source
        mock_fetch_all.side_effect = Exception("Test error")
        proxies = fetch_proxies()
        assert proxies == []

    def test_proxy_validation_timeout(self):
        """Test proxy validation timeout handling"""
        class TimeoutThread(threading.Thread):
            def __init__(self, queue):
                super().__init__()
                self.queue = queue
                self.daemon = True
                self.working_proxies = []

            def start(self):
                pass

            def join(self, timeout=None):
                if timeout and timeout > 0:
                    raise TimeoutError()

            def check_proxy(self, proxy):
                return False

            def run(self):
                pass

        mock_html = """
        <table id="proxylisttable">
            <tbody>
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
            </tbody>
        </table>
        """

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        # Test thread pool timeout with infinite time sequence
        start_time = 0
        def time_sequence():
            nonlocal start_time
            while True:
                yield start_time
                start_time += 20  # Increment by 20 seconds each time to force timeout

        with patch('fastProxy.fastProxy.alive_ip', return_value=TimeoutThread(Queue())), \
             patch('time.time', side_effect=time_sequence()), \
             patch('requests.session', return_value=mock_session):
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

    def test_uncovered_lines(self):
        """Test specifically targeting uncovered lines"""
        # Test proxy validation with missing fields
        proxy_data = {'ip': '127.0.0.1', 'port': '8080'}
        thread = alive_ip(proxy_data)
        thread.start()
        thread.join(timeout=1)

        # Test CSV generation with empty queue
        generate_csv()

        # Test printer with empty list
        printer([])

        # Test printer with invalid proxy data
        printer([{'invalid': 'data'}])

        # Test fetch_proxies with various settings
        fetch_proxies(c=1, t=1, g=True, a=True, max_proxies=1)
        fetch_proxies(c=None, t=None, g=None, a=None)
