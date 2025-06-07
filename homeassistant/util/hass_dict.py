"""Implementation for menuaiDict and custom menuaiKey types.

Custom for type checking. See stub file.
"""

from __future__ import annotations


class menuaiKey[_T](str):
    """Generic menuai key type.

    At runtime this is a generic subclass of str.
    """

    __slots__ = ()


class menuaiEntryKey[_T](str):
    """Key type for integrations with config entries.

    At runtime this is a generic subclass of str.
    """

    __slots__ = ()


menuaiDict = dict
