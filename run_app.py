import sys
from unittest.mock import MagicMock

# Mock the platform module to avoid WMI hangs on Windows
mock_platform = MagicMock()
mock_platform.system.return_value = 'Windows'
mock_platform.release.return_value = '10'
mock_platform.version.return_value = '10.0'
mock_platform.machine.return_value = 'x86_64'
mock_platform.platform.return_value = 'Windows-10'
mock_platform.uname.return_value = MagicMock(
    system='Windows', node='localhost', release='10', version='10.0', machine='x86_64', processor='Intel'
)
sys.modules['platform'] = mock_platform

# Now we can safely import and run streamlit
from streamlit.web.cli import main

if __name__ == "__main__":
    # Simulate: streamlit run app.py
    sys.argv = ["streamlit", "run", "app.py"]
    main()
