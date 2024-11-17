import pytest
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def sample_proxy_data():
    return {
        'ip': '127.0.0.1',
        'port': '8080',
        'code': 'US',
        'country': 'United States',
        'anonymity': 'elite proxy',
        'google': 'yes',
        'https': 'yes',
        'last_checked': '1 minute ago'
    }
