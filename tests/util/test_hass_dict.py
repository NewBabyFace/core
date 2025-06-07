"""Test menuaiDict and custom menuaiKey types."""

from menuai.util.menuai_dict import menuaiDict, menuaiEntryKey, menuaiKey


def test_key_comparison() -> None:
    """Test key comparison with itself and string keys."""

    str_key = "custom-key"
    key = menuaiKey[int](str_key)
    other_key = menuaiKey[str]("other-key")

    entry_key = menuaiEntryKey[int](str_key)
    other_entry_key = menuaiEntryKey[str]("other-key")

    assert key == str_key
    assert key != other_key
    assert key != 2

    assert entry_key == str_key
    assert entry_key != other_entry_key
    assert entry_key != 2

    # Only compare name attribute, menuaiKey(<name>) == menuaiEntryKey(<name>)
    assert key == entry_key


def test_menuai_dict_access() -> None:
    """Test keys with the same name all access the same value in menuaiDict."""

    data = menuaiDict()
    str_key = "custom-key"
    key = menuaiKey[int](str_key)
    other_key = menuaiKey[str]("other-key")

    entry_key = menuaiEntryKey[int](str_key)
    other_entry_key = menuaiEntryKey[str]("other-key")

    data[str_key] = True
    assert data.get(key) is True
    assert data.get(other_key) is None

    assert data.get(entry_key) is True  # type: ignore[comparison-overlap]
    assert data.get(other_entry_key) is None

    data[key] = False
    assert data[str_key] is False
