#!/usr/bin/env python3
"""CLI entry point for fastProxy"""

import fire
import signal
from fastProxy import (
    fetch_proxies,
    alter_globals,
    printer,
    THREAD_COUNT,
    REQUEST_TIMEOUT,
    GENERATE_CSV,
    ALL_PROXIES
)

def timeout_handler(signum, frame):
    """Handle timeout signal"""
    raise TimeoutError("CLI operation timed out")

def main(c=None, t=None, g=None, a=None, max_proxies=5):
    """Main CLI function to handle proxy operations

    Args:
        c (int, optional): Thread count. Defaults to None.
        t (int, optional): Request timeout. Defaults to None.
        g (bool, optional): Generate CSV. Defaults to None.
        a (bool, optional): All proxies. Defaults to None.
        max_proxies (int, optional): Maximum number of proxies to fetch. Defaults to 5.
    """
    # Set global timeout for CLI operation
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(45)  # 45 second timeout for entire CLI operation

    try:
        # Configure settings with very conservative defaults
        alter_globals(
            c=c or 2,     # Default to 2 threads
            t=t or 15,    # Default to 15 second timeout
            g=g or True,  # Default to generating CSV
            a=a or True   # Default to all proxies
        )

        # Fetch and validate proxies with minimal settings
        proxies = fetch_proxies(max_proxies=max_proxies)
        if proxies:
            print(f"\nFound {len(proxies)} working proxies:")
            printer(proxies)
        else:
            print("\nNo working proxies found. Try increasing timeout or thread count.")
    except TimeoutError:
        print("\nOperation timed out. Try with more conservative settings (--c=2 --t=15)")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        signal.alarm(0)  # Disable alarm

if __name__ == '__main__':
    fire.Fire(main)
