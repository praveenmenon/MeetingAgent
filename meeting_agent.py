#!/usr/bin/env python3
"""
Meeting Agent Launcher
This file provides backward compatibility and launches the main application.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from meeting_agent.main import main

if __name__ == "__main__":
    main()