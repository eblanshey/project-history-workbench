# SPDX-License-Identifier: LGPL-3.0-or-later
"""Configuration for the Diff Workbench.

This module contains hard-coded configuration defaults. In a future phase,
these will be moved to FreeCAD Preferences with runtime reload support.
"""

# Type IDs to exclude from diff computation by default
# Objects of these types and their children are removed from the diff view
EXCLUDED_TYPES = ["App::Origin"]

# Property names to exclude from diff comparison
# These properties often change without meaningful semantic differences
EXCLUDED_PROPERTIES = ["TimeStamp", "LastModified", "Label2"]
