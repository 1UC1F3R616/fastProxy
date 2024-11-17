import os
import pytest
from unittest.mock import patch, MagicMock
from fastProxy.logger import ProxyLogger

class TestProxyLogger:
    @pytest.fixture
    def logger_instance(self):
        with patch('fastProxy.logger.os.makedirs') as mock_makedirs:
            with patch('fastProxy.logger.RotatingFileHandler') as mock_file_handler:
                with patch('fastProxy.logger.logging.StreamHandler') as mock_stream_handler:
                    logger = ProxyLogger()
                    yield logger, mock_makedirs, mock_file_handler, mock_stream_handler

    def test_logger_initialization(self, logger_instance):
        logger, mock_makedirs, mock_file_handler, mock_stream_handler = logger_instance

        # Verify log directory creation
        mock_makedirs.assert_called_once()
        assert 'logs' in mock_makedirs.call_args[0][0]

        # Verify handlers setup
        mock_file_handler.assert_called_once()
        mock_stream_handler.assert_called_once()

        # Verify logger configuration
        assert logger.logger.level == 10  # DEBUG level

    @pytest.mark.parametrize("log_method,log_level", [
        ("debug", "DEBUG"),
        ("info", "INFO"),
        ("warning", "WARNING"),
        ("error", "ERROR"),
        ("critical", "CRITICAL")
    ])
    def test_logging_methods(self, logger_instance, log_method, log_level):
        logger, _, _, _ = logger_instance
        test_message = f"Test {log_level} message"

        with patch.object(logger.logger, log_method.lower()) as mock_log:
            # Call the logging method
            getattr(logger, log_method)(test_message)

            # Verify the log was called with correct message
            mock_log.assert_called_once_with(test_message)

    def test_file_handler_rotation(self, logger_instance):
        _, _, mock_file_handler, _ = logger_instance

        # Verify rotation settings
        handler_call_kwargs = mock_file_handler.call_args[1]
        assert handler_call_kwargs['maxBytes'] == 5*1024*1024  # 5MB
        assert handler_call_kwargs['backupCount'] == 3

    def test_formatter_configuration(self, logger_instance):
        logger, _, mock_file_handler, mock_stream_handler = logger_instance

        # Verify both handlers have formatters
        assert mock_file_handler.return_value.setFormatter.called
        assert mock_stream_handler.return_value.setFormatter.called

        # Verify different formatter patterns
        file_formatter = mock_file_handler.return_value.setFormatter.call_args[0][0]
        console_formatter = mock_stream_handler.return_value.setFormatter.call_args[0][0]
        assert file_formatter._fmt != console_formatter._fmt
