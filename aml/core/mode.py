"""Data mode: real extract (local) or synthetic only (CI, fresh clones).

The real workbook and the rule catalogue derived from the vendor guide are not
in version control. Set AML_SYNTHETIC_ONLY=1 to run without them.
"""

import os

SYNTHETIC_ONLY = os.environ.get("AML_SYNTHETIC_ONLY") == "1"
