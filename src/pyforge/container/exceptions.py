class ContainerError(Exception):
    """Base exception for all dependency-injection container errors."""


class BindingResolutionError(ContainerError):
    """Raised when the container cannot resolve a requested type."""
