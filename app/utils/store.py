"""
/Users/georgecorthine/Documents/Projects/forex-service/utils/store.py
"""
from collections import deque, defaultdict
import asyncio

# Global state to track the service status
state = {
    "running": False,
    "latest_signal": {},
    "errors": deque(maxlen=100),  # Keep only last 100 errors to prevent memory leak
    "error_counts": defaultdict(int),  # Track error counts by type
}

# Lock for thread-safe state updates
state_lock = asyncio.Lock()
