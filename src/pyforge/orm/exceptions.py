class ModelNotFoundError(Exception):
    """Raised by ``Model.find_or_fail`` when no matching row exists."""
