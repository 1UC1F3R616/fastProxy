# FastProxy Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Project Structure](#project-structure)
5. [Code Documentation](#code-documentation)
6. [Testing](#testing)
7. [Usage Examples](#usage-examples)
8. [Configuration](#configuration)
9. [Flow Diagrams](#flow-diagrams)
10. [Troubleshooting](#troubleshooting)

## Project Overview

FastProxy is a Python package designed to fetch and validate working web proxies from multiple sources. It uses multithreading for efficient proxy validation and provides both CLI and Python API interfaces.

### Key Features
- Multi-source proxy fetching (free-proxy-list.net and geonode.com)
- Concurrent proxy validation
- CSV export functionality
- Comprehensive logging system
- Both CLI and Python API interfaces
- Configurable timeout and thread settings

## Architecture

The project follows a modular architecture with the following key components:

```
fastProxy/
├── fastProxy/                 # Main package directory
│   ├── __init__.py           # Package initialization and version
│   ├── fastProxy.py          # Core proxy validation logic
│   ├── logger.py             # Logging configuration
│   └── proxy_sources/        # Proxy source implementations
│       ├── __init__.py       # Source interface definitions
│       ├── manager.py        # Proxy source management
│       ├── free_proxy_list.py# Free-proxy-list.net implementation
│       └── geonode.py        # Geonode.com API implementation
├── tests/                    # Test directory
│   └── unit/                # Unit tests
├── cli.py                   # CLI interface
└── getProxyNow.py          # Python API example script
```

### Component Interactions
1. **Proxy Sources**: Each source (free-proxy-list.net, geonode.com) implements a common interface for fetching proxies
2. **Source Manager**: Coordinates proxy fetching from multiple sources
3. **Validator**: Validates proxies using multithreading
4. **Logger**: Provides detailed logging for debugging and monitoring
5. **Output Manager**: Handles CSV generation and console output

## Installation

### From PyPI
```bash
pip install fastProxy==1.0.0
```

### From Source
```bash
git clone https://github.com/1UC1F3R616/fastProxy.git
cd fastProxy
pip install -r requirements.txt
```

### Dependencies
- Python 3.8+
- requests
- beautifulsoup4
- fire
- pytest (for testing)
- pytest-cov (for coverage)
- requests-mock (for testing)

## Project Structure

### Core Components

#### 1. Proxy Sources (`fastProxy/proxy_sources/`)
- **manager.py**: Manages multiple proxy sources
  - `ProxySourceManager`: Coordinates proxy fetching
  - `fetch_all()`: Fetches proxies from all sources

- **free_proxy_list.py**: Free-proxy-list.net implementation
  - `FreeProxyListSource`: Scrapes and parses proxy data
  - `fetch()`: Retrieves proxies using BeautifulSoup

- **geonode.py**: Geonode.com API implementation
  - `GeoNodeSource`: Fetches proxies from API
  - `fetch()`: Retrieves and formats proxy data

#### 2. Core Logic (`fastProxy/fastProxy.py`)
- `alive_ip`: Thread class for proxy validation
- `check_proxy()`: Validates individual proxies
- `fetch_proxies()`: Main entry point for proxy fetching
- `generate_csv()`: Exports results to CSV

#### 3. Logger (`fastProxy/logger.py`)
- Configurable logging levels
- File and console output
- Rotation handling
- Detailed error tracking

### Testing Structure

#### Unit Tests (`tests/unit/`)
- **test_fastproxy.py**: Core functionality tests
- **test_logger.py**: Logging system tests
- **proxy_sources/**: Source-specific tests
  - `test_manager.py`: Source manager tests
  - `test_free_proxy_list.py`: Free-proxy-list source tests
  - `test_geonode.py`: Geonode API source tests

## Code Documentation

### Core Classes and Methods

#### ProxySourceManager
```python
class ProxySourceManager:
    """Manages multiple proxy sources and aggregates results"""

    def fetch_all(self, max_proxies=None):
        """
        Fetches proxies from all registered sources
        Args:
            max_proxies (int, optional): Maximum proxies to fetch
        Returns:
            list: Combined proxy list from all sources
        """
```

#### alive_ip (Thread Class)
```python
class alive_ip(Thread):
    """
    Thread class for proxy validation

    Attributes:
        proxy_data (dict): Proxy information
        timeout (int): Request timeout
    """
```

### Key Functions

#### fetch_proxies
```python
def fetch_proxies(c=None, t=None, g=None, a=None):
    """
    Main function to fetch and validate proxies

    Args:
        c (int): Thread count
        t (int): Timeout in seconds
        g (bool): Generate CSV
        a (bool): Include all proxies

    Returns:
        list: Valid proxies
    """
```


## Testing

### Test Coverage
Current test coverage: 86%
- fastProxy/fastProxy.py: 88%
- fastProxy/logger.py: 97%
- fastProxy/proxy_sources/__init__.py: 95%
- fastProxy/proxy_sources/free_proxy_list.py: 86%
- fastProxy/proxy_sources/geonode.py: 71%
- fastProxy/proxy_sources/manager.py: 100%

### Running Tests
```bash
# Run all tests
python -m pytest tests/unit/ -v

# Run with coverage
python -m pytest tests/unit/ -v --cov=fastProxy --cov-report=term-missing
```

### Test Categories
1. **Core Functionality Tests**
   - Proxy validation
   - Thread management
   - CSV generation

2. **Source Tests**
   - API responses
   - Error handling
   - Data parsing

3. **Integration Tests**
   - Multi-source fetching
   - End-to-end validation

## Usage Examples

### CLI Usage
```bash
# Basic usage
python cli.py

# With options
python cli.py --c=10 --t=5 --g --a
```

### Python API Usage
```python
from fastProxy import fetch_proxies

# Basic usage
proxies = fetch_proxies()

# With options
proxies = fetch_proxies(c=10, t=5, g=True, a=True)
```

### Configuration Options
- `c`: Thread count (default: 256)
- `t`: Request timeout in seconds (default: 2)
- `g`: Generate CSV output (default: False)
- `a`: Include all proxies (default: False)

## Flow Diagrams

### Proxy Fetching and Validation Flow
```
[Start] -> [Initialize Sources]
           -> [Fetch from Sources (Parallel)]
              -> [Free-proxy-list.net] -> [Parse HTML] -> [Extract Proxies]
              -> [Geonode API] -> [Parse JSON] -> [Extract Proxies]
           -> [Combine Results]
           -> [Initialize Thread Pool]
              -> [Validate Proxies (Parallel)]
                 -> [HTTP Check] -> [HTTPS Check]
           -> [Collect Results]
           -> [Generate CSV (if enabled)]
[End]
```

### Logging Flow
```
[Log Event] -> [Format Message]
            -> [Check Log Level]
               -> [Console Output]
               -> [File Output]
                  -> [Rotation Check]
```

## Troubleshooting

### Common Issues

1. **Timeout Errors**
   - Increase timeout value with `--t` option
   - Reduce thread count with `--c` option

2. **No Proxies Found**
   - Check internet connection
   - Verify source websites are accessible
   - Review logs in `logs/fastproxy.log`

3. **CSV Generation Issues**
   - Ensure write permissions in `proxy_list` directory
   - Check disk space

4. **High Memory Usage**
   - Reduce thread count
   - Set maximum proxy limit

### Debug Mode
Enable detailed logging:
```python
import logging
logging.getLogger('fastProxy').setLevel(logging.DEBUG)
```

### Log Analysis
Log files location: `logs/fastproxy.log`
Format: `[TIMESTAMP] [LEVEL] [MODULE] Message`

Example:
```
[2024-11-17 11:04:10] [INFO] [manager] Found 300 proxies from free-proxy-list.net
[2024-11-17 11:04:10] [INFO] [manager] Found 74 proxies from geonode.com
```
