import pytest
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call
    setattr(item, f"rep_{call.when}", rep)

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
