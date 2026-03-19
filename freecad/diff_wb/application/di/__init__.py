"""Module responsibility: Dependency injection container for application and UI layers.

This module wires actions, presenters, and views together.
It's the composition root for the application layer.
"""

from .container import ApplicationContainer, create_application_container


__all__ = ["ApplicationContainer", "create_application_container"]
