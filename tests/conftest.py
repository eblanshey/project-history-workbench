# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pytest configuration and shared fixtures for Diff Workbench tests."""

import pytest


@pytest.fixture
def mock_freecad_app():
    """Create a mock FreeCAD application object for testing."""

    class MockConsole:
        def PrintMessage(self, text):
            pass

        def PrintError(self, text):
            pass

        def PrintWarning(self, text):
            pass

    class MockDocument:
        Objects = []

        def getObject(self, name):
            return None

        def recompute(self):
            pass

    class MockApp:
        ActiveDocument = None
        Console = MockConsole()

        def translate(self, context, text):
            return text

        def ParamGet(self, path):
            return MockParamGet()

    class MockParamGet:
        def GetString(self, key, default=""):
            return default

        def SetString(self, key, value):
            pass

    return MockApp()


@pytest.fixture
def mock_freecad_gui():
    """Create a mock FreeCAD GUI object for testing."""

    class MockMainWindow:
        def workspace(self):
            return None

    class MockGui:
        @staticmethod
        def getMainWindow():
            return MockMainWindow()

    return MockGui()


@pytest.fixture
def freecad_context(mock_freecad_app, mock_freecad_gui):
    """Create a FreeCAD context with mocked app and gui."""
    from freecad.diff_wb.ports.freecad_context import FreeCadContext

    return FreeCadContext(app=mock_freecad_app, gui=mock_freecad_gui)