#!/usr/bin/env python3
"""
ERCOT Analytics Dashboard - Main Application Launcher
"""
import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

# Import and run the main application
if __name__ == "__main__":
    from src.app import app
    import uvicorn
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=80,
        reload=True
    )