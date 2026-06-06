import subprocess
import sys
import os
import runpy

# Set working directory to zeravaneai for proper imports
os.chdir(os.path.join(os.path.dirname(__file__), "zeravaneai"))
sys.path.insert(0, os.getcwd())

# Use runpy.run_path() instead of exec() for safer code execution
runpy.run_path("frontend/app.py", run_name="__main__")
