from __future__ import annotations

import os
import tempfile

_db_file = os.path.join(tempfile.gettempdir(), "tunneling_test.db")
os.environ["TUNNEL_DB_URL"] = f"sqlite:///{_db_file}"
