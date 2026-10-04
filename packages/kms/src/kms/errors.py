"""Typed error so call sites never inspect HTTP internals."""


class KmsError(Exception):
    """A KMS API call failed on the backend side."""
