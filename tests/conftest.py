import sys
from pathlib import Path
from unittest.mock import MagicMock

# Stub hoymiles_wifi before any project module imports it
_dtu_stub = MagicMock()
sys.modules.setdefault("hoymiles_wifi", MagicMock())
sys.modules.setdefault("hoymiles_wifi.dtu", _dtu_stub)

sys.path.insert(0, str(Path(__file__).parent.parent / "hoymetrics"))
