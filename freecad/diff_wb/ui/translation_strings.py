"""Module responsibility: Centralized translation strings for the UI layer.

This module contains all translation templates used across the UI layer.
All user-facing strings should be defined here to provide a single source
of truth for translators and prevent duplication.

Translation Strategy:
- Templates use Qt-style placeholders: %1, %2, %3, etc.
- Views handle both translation AND parameter substitution
- Presenters pass raw data only (no message formatting)
- Translation happens at view creation time for performance

Usage Example:
    # In a view implementation:
    from freecad.diff_wb.ui.translation_strings import SNAPSHOT_SUCCESS_TEMPLATE

    template = QCoreApplication.translate("SnapshotView", SNAPSHOT_SUCCESS_TEMPLATE)
    translated = template % snapshot_name  # %1 is replaced with snapshot_name
    self._label.setText(translated)
"""

# ============================================================================
# SNAPSHOT VIEW STRINGS
# ============================================================================
# Context: "SnapshotView"
# These strings are used by the snapshot view component for success/error/loading states.

SNAPSHOT_SUCCESS_TEMPLATE = "Snapshot '%1' created successfully"
"""Success message after creating a snapshot.

Placeholder:
    %1 - The snapshot name (str)

Example:
    "Snapshot 'my_snapshot' created successfully"
"""

SNAPSHOT_LOADING_DEFAULT = "Creating snapshot..."
"""Default loading message shown while snapshot is being created.

No placeholders. This is a static message.
"""

# ============================================================================
# DIFF VIEW STRINGS
# ============================================================================
# Context: "DiffView"
# These strings are used by the diff view component for displaying results.

DIFF_SUMMARY_ADDED_LABEL = "Added:"
"""Label for the added nodes count in the diff summary.

No placeholders. The view appends the count after this label.

Example:
    "Added: 5"
"""

DIFF_SUMMARY_DELETED_LABEL = "Deleted:"
"""Label for the deleted nodes count in the diff summary.

No placeholders. The view appends the count after this label.

Example:
    "Deleted: 3"
"""

DIFF_SUMMARY_MODIFIED_LABEL = "Modified:"
"""Label for the modified nodes count in the diff summary.

No placeholders. The view appends the count after this label.

Example:
    "Modified: 2"
"""

DIFF_LOADING_MESSAGE = "Computing diff..."
"""Loading message shown while diff is being computed.

No placeholders. This is a static message.
"""

# ============================================================================
# COMMON STRINGS
# ============================================================================
# Context: "Common"
# These strings are shared across multiple views for common error/loading states.

ERROR_UNKNOWN = "Unknown error occurred"
"""Generic error message when no specific error information is available.

No placeholders. This is a static message.
"""

ERROR_NO_DOCUMENT = "No active document available"
"""Error message when no document is open in FreeCAD.

No placeholders. This is a static message.
"""

# ============================================================================
# GIT REPOSITORY STRINGS
# ============================================================================
# Context: "Common"
# These strings are used for displaying git repository information in the UI.

REPOSITORY_INFO_TEMPLATE = "Repository: %1"
"""Template for displaying git repository info.

Placeholders:
    %1 - Repository name (str)

The absolute path is stored separately for use as a tooltip.

Example:
    "Repository: my_project"
"""

REPOSITORY_NO_REPO_MESSAGE = "No git repository detected"
"""Message shown when no git repository is detected for the active document.

No placeholders. This is a static message.
"""

HISTORY_LABEL = "History"
"""Label for the history/commit list widget.

No placeholders. This is a static label.
"""

# ============================================================================
# COMMIT STRINGS
# ============================================================================
# Context: "Commit"
# These strings are used for commit-related UI messages in entry points.

COMMIT_NO_REPOSITORY_TITLE = "No Repository"
"""Title for the warning when no git repository is detected.

No placeholders. This is a static message.
"""

COMMIT_NO_REPOSITORY_MESSAGE = "No git repository detected. Please open a document from a git repository."
"""Message shown when no git repository is detected for the active document.

No placeholders. This is a static message.
"""

COMMIT_NO_STAGED_FILES_TITLE = "No Staged Files"
"""Title for the info message when there are no staged files to commit.

No placeholders. This is a static message.
"""

COMMIT_NO_STAGED_FILES_MESSAGE = "There are no staged files to commit."
"""Message shown when there are no staged files to commit.

No placeholders. This is a static message.
"""

COMMIT_DIALOG_TITLE = "Git Commit"
"""Title for the commit message input dialog.

No placeholders. This is a static message.
"""

COMMIT_DIALOG_PROMPT = "Enter commit message:"
"""Prompt text for the commit message input dialog.

No placeholders. This is a static message.
"""

COMMIT_EMPTY_MESSAGE_TITLE = "Empty Message"
"""Title for the warning when commit message is empty.

No placeholders. This is a static message.
"""

COMMIT_EMPTY_MESSAGE = "Commit message cannot be empty"
"""Message shown when the user provides an empty commit message.

No placeholders. This is a static message.
"""

COMMIT_FAILED_TITLE = "Commit Failed"
"""Title for the error dialog when commit fails.

No placeholders. This is a static message.
"""

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Snapshot View
    "SNAPSHOT_SUCCESS_TEMPLATE",
    "SNAPSHOT_LOADING_DEFAULT",
    # Diff View
    "DIFF_SUMMARY_ADDED_LABEL",
    "DIFF_SUMMARY_DELETED_LABEL",
    "DIFF_SUMMARY_MODIFIED_LABEL",
    "DIFF_LOADING_MESSAGE",
    # Common
    "ERROR_UNKNOWN",
    "ERROR_NO_DOCUMENT",
    # Git Repository
    "REPOSITORY_INFO_TEMPLATE",
    "REPOSITORY_NO_REPO_MESSAGE",
    "HISTORY_LABEL",
    # Commit
    "COMMIT_NO_REPOSITORY_TITLE",
    "COMMIT_NO_REPOSITORY_MESSAGE",
    "COMMIT_NO_STAGED_FILES_TITLE",
    "COMMIT_NO_STAGED_FILES_MESSAGE",
    "COMMIT_DIALOG_TITLE",
    "COMMIT_DIALOG_PROMPT",
    "COMMIT_EMPTY_MESSAGE_TITLE",
    "COMMIT_EMPTY_MESSAGE",
    "COMMIT_FAILED_TITLE",
]
