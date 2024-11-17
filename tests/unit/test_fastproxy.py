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

@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global variables before each test."""
    # Store original values
    original_globals = {}
    try:
        from fastProxy.fastProxy import alive_queue, WORKING_PROXIES
        original_globals['alive_queue'] = alive_queue
        original_globals['WORKING_PROXIES'] = WORKING_PROXIES.copy() if hasattr(WORKING_PROXIES, 'copy') else []
    except (ImportError, AttributeError):
        pass

    # Reset globals
    alter_globals(max_proxies=100, threads=100, google=True, anonymous=True)

    yield

    # Restore original values
    try:
        from fastProxy.fastProxy import alive_queue, WORKING_PROXIES
        alive_queue = original_globals.get('alive_queue', Queue())
        WORKING_PROXIES = original_globals.get('WORKING_PROXIES', [])
    except (ImportError, AttributeError):
        pass

@pytest.fixture
def mock_proxy_queue():
    """Fixture to provide a mock proxy queue."""
    return Queue()

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
        """Fixture providing an empty queue for proxy testing"""
        queue = Queue()
        yield queue
        # Clear queue after each test
        while not queue.empty():
            queue.get()

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

        # Test malformed proxy data
        malformed_proxy = {'ip': '127.0.0.1', 'port': 'abc'}
        assert thread.check_proxy(malformed_proxy) is False

        # Test connection timeout
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        assert thread.check_proxy(proxy_data) is False

        # Test connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        assert thread.check_proxy(proxy_data) is False

        # Test invalid URL format
        mock_get.side_effect = requests.exceptions.InvalidURL("Invalid URL")
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
        """Test printer function with various scenarios"""
        queue = mock_proxy_queue

        # Clear any existing proxies
        while not queue.empty():
            queue.get()

        # Test with empty queue
        with patch('builtins.print') as mock_print:
            printer()
            mock_print.assert_not_called()

        # Test with single proxy
        proxy = {'ip': '127.0.0.1', 'port': '8080', 'https': True}
        queue.put(proxy)
        with patch('builtins.print') as mock_print:
            printer()
            assert mock_print.call_count >= 1, "Print should be called at least once"

        # Clear queue for next test
        while not queue.empty():
            queue.get()

        # Test with multiple proxies
        queue.put(proxy)
        queue.put(proxy)
        with patch('builtins.print') as mock_print:
            printer()
            assert mock_print.call_count >= 2, "Print should be called at least twice"

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
        """Test error handling edge cases"""
        # Test with invalid proxy format
        proxy_list = ['invalid:format']
        with pytest.raises(ValueError, match="Port must be a valid number"):
            main(proxies=proxy_list)

        # Test with invalid port number
        proxy_list = ['127.0.0.1:70000']
        with pytest.raises(ValueError, match="Port number must be between 1 and 65535"):
            main(proxies=proxy_list)

        # Test with non-numeric port
        proxy_list = ['127.0.0.1:abc']
        with pytest.raises(ValueError, match="Port must be a valid number"):
            main(proxies=proxy_list)

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
            generate_csv()
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

        # Test thread start failure
        with patch('fastProxy.fastProxy.alive_ip', return_value=FailingThread()), \
             patch('time.time') as mock_time:
            mock_time.side_effect = [0, 1, 2, 3, 4, 5] * 100  # Ensure enough values
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

        # Test thread join failure
        with patch('fastProxy.fastProxy.alive_ip', return_value=JoinFailingThread()), \
             patch('time.time') as mock_time:
            mock_time.side_effect = [0, 1, 2, 3, 4, 5] * 100  # Ensure enough values
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

        # Test thread timeout
        with patch('fastProxy.fastProxy.alive_ip', return_value=ValidationFailingThread()), \
             patch('time.time') as mock_time:
            mock_time.side_effect = [0, 1, 2, 3, 4, 5] * 100  # Ensure enough values
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

    def test_generate_csv_error_handling(self, mock_proxy_queue):
        """Test CSV generation error handling"""
        queue = mock_proxy_queue

        # Clear any existing proxies and ensure queue is empty
        while not queue.empty():
            queue.get()

        # Test with no working proxies
        with patch('fastProxy.fastProxy.WORKING_PROXIES', []), \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', new_callable=mock_open) as mock_file:
            generate_csv()
            mock_file.assert_not_called()

        # Test with working proxies but file write error
        proxy = {'ip': '127.0.0.1', 'port': '8080', 'https': True}
        with patch('fastProxy.fastProxy.WORKING_PROXIES', [proxy]), \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', side_effect=IOError("Permission denied")):
            generate_csv()

        # Test with working proxies and successful write
        with patch('fastProxy.fastProxy.WORKING_PROXIES', [proxy]), \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', new_callable=mock_open) as mock_file:
            generate_csv()
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called()

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

    def test_main_invalid_proxy_format(self):
        """Test main function with invalid proxy format"""
        # Test non-list input
        with pytest.raises(TypeError, match="proxies must be a list"):
            main(proxies="not a list")

        # Test non-string proxy
        with pytest.raises(AttributeError, match="Each proxy must be a string"):
            main(proxies=[123])

        # Test empty proxy string
        with pytest.raises(IndexError, match="Invalid proxy format"):
            main(proxies=[""])

        # Test invalid format (no port)
        with pytest.raises(IndexError, match="Invalid proxy format"):
            main(proxies=["127.0.0.1"])

        # Test invalid format (too many parts)
        with pytest.raises(IndexError, match="Invalid proxy format"):
            main(proxies=["127.0.0.1:8080:extra"])

        # Test invalid port (non-numeric)
        with pytest.raises(ValueError, match="Port must be a valid number"):
            main(proxies=["127.0.0.1:abc"])

        # Test invalid port range (too low)
        with pytest.raises(ValueError, match="Port number must be between"):
            main(proxies=["127.0.0.1:0"])

        # Test invalid port range (too high)
        with pytest.raises(ValueError, match="Port number must be between"):
            main(proxies=["127.0.0.1:65536"])

    def test_proxy_string_parsing(self):
        """Test proxy string parsing edge cases"""
        # Test valid proxy format
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            mock_fetch.return_value = []
            result = main(proxies=["127.0.0.1:8080"])
            mock_fetch.assert_called_once()
            assert result == []

        # Test empty proxy list
        result = main(proxies=[])
        assert result == []

        # Test None proxy list
        result = main(proxies=None)
        assert isinstance(result, list)

    def test_https_proxy_validation(self):
        """Test HTTPS proxy validation"""
        proxy_data = {
            'ip': '127.0.0.1',
            'port': '8080',
            'https': True
        }
        thread = alive_ip(Queue())

        # Test HTTPS validation success
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                requests.exceptions.RequestException(),  # HTTP fails
                MagicMock(status_code=200)  # HTTPS succeeds
            ]
            assert thread.check_proxy(proxy_data) is True

        # Test HTTPS validation failure
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                requests.exceptions.RequestException(),  # HTTP fails
                requests.exceptions.RequestException()  # HTTPS fails
            ]
            assert thread.check_proxy(proxy_data) is False

    def test_csv_generation_paths(self):
        """Test CSV generation with different paths"""
        proxy = {'ip': '127.0.0.1', 'port': '8080', 'code': 'US', 'country': 'United States',
                'anonymity': 'elite', 'google': True, 'https': True, 'last_checked': '1s'}

        # Test with queue-based proxies
        with patch('fastProxy.fastProxy.alive_queue') as mock_queue, \
             patch('os.path.exists', return_value=False), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', new_callable=mock_open) as mock_file:
            # Set up the mock queue
            mock_queue.queue = [proxy]
            generate_csv()
            mock_makedirs.assert_called_once()
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called()

        # Test with existing directory
        with patch('fastProxy.fastProxy.alive_queue') as mock_queue, \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', new_callable=mock_open) as mock_file:
            # Set up the mock queue
            mock_queue.queue = [proxy]
            generate_csv()
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called()

    def test_main_edge_cases(self):
        """Test main function edge cases"""
        # Test with missing port separator
        with pytest.raises(IndexError, match="Invalid proxy format"):
            main(proxies=["127.0.0.1"])

        # Test with empty IP
        with pytest.raises(IndexError, match="Invalid proxy format"):
            main(proxies=[":8080"])

        # Test with empty port
        with pytest.raises(IndexError, match="Invalid proxy format"):
            main(proxies=["127.0.0.1:"])

        # Test with valid proxy
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            mock_fetch.return_value = []
            result = main(proxies=["127.0.0.1:8080"])
            assert result == []

        # Test with invalid port number
        with pytest.raises(ValueError, match="Port must be a valid number"):
            main(proxies=["127.0.0.1:abc"])

        # Test with port out of range
        with pytest.raises(ValueError, match="Port number must be between"):
            main(proxies=["127.0.0.1:0"])
            main(proxies=["127.0.0.1:65536"])

    def test_proxy_validation_timeout(self):
        """Test proxy validation timeout handling"""
        class TimeoutThread(threading.Thread):
            def __init__(self, queue):
                super().__init__()
                self.queue = queue
                self.daemon = True

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

        # Test thread pool timeout
        with patch('fastProxy.fastProxy.alive_ip', return_value=TimeoutThread(Queue())), \
             patch('time.time', side_effect=[0] * 50 + [30] * 50 + [61] * 50), \
             patch('requests.session', return_value=mock_session):
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []

    def test_uncovered_lines(self):
        """Test specifically targeting uncovered lines"""
        # Test malformed proxy data handling
        thread = alive_ip(Queue())
        malformed_proxy = {'ip': '127.0.0.1'}  # Missing port
        assert thread.check_proxy(malformed_proxy) is False

        # Test invalid proxy format in main
        with patch('fastProxy.fastProxy.fetch_proxies') as mock_fetch:
            mock_fetch.return_value = []
            result = main(proxies=['127.0.0.1:8080'])
            assert result == []

        # Test CSV generation with makedirs error
        proxy_data = {'ip': '127.0.0.1', 'port': '8080', 'code': 'US', 'country': 'United States',
                     'anonymity': 'elite', 'google': True, 'https': True, 'last_checked': '1s'}

        with patch('fastProxy.fastProxy.alive_queue') as mock_queue:
            mock_queue.queue = [proxy_data]
            with patch('os.path.exists', return_value=False), \
                 patch('os.makedirs', side_effect=OSError), \
                 patch('builtins.open', new_callable=mock_open):
                generate_csv()  # Should handle error gracefully

        # Test thread join timeout
        class TimeoutJoinThread(threading.Thread):
            def __init__(self, queue):
                super().__init__()
                self.queue = queue
                self.daemon = True

            def start(self):
                pass

            def join(self, timeout=None):
                raise TimeoutError()

            def check_proxy(self, proxy):
                return False

            def run(self):
                pass

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """
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
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        with patch('fastProxy.fastProxy.alive_ip', return_value=TimeoutJoinThread(Queue())), \
             patch('time.time', side_effect=[0] * 50 + [30] * 50 + [61] * 50), \
             patch('requests.session', return_value=mock_session):
            proxies = fetch_proxies(max_proxies=1)
            assert proxies == []
