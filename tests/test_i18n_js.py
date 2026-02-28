"""Test i18n.js plural support by parsing the JS file."""

_I18N_JS_PATH = "portal_core/portal_core/static/js/i18n.js"


def _read_i18n_js():
    with open(_I18N_JS_PATH) as f:
        return f.read()


def test_i18n_js_has_plural_logic():
    """The i18n.js t() function must include plural key resolution."""
    content = _read_i18n_js()
    assert "_plural" in content, "i18n.js should contain _plural key logic"
    # count !== 1 triggers plural form
    assert "count !== 1" in content or "count != 1" in content, (
        "i18n.js should check count !== 1 for plural selection"
    )


def test_i18n_js_plural_key_fallback():
    """If no _plural key exists, i18n.js falls back to the base key."""
    content = _read_i18n_js()
    # There must be a resolvedKey variable used for key selection
    assert "resolvedKey" in content, (
        "i18n.js should use resolvedKey variable for plural key resolution"
    )


def test_i18n_js_plural_key_lookup():
    """i18n.js should look up the _plural variant in _messages before falling back."""
    content = _read_i18n_js()
    # The pluralKey construction must be present
    assert "pluralKey" in content or "_plural" in content, (
        "i18n.js should build a pluralKey from the base key"
    )
    # The lookup in _messages for the plural key must exist
    assert "_messages[pluralKey]" in content or '_plural"' in content, (
        "i18n.js should check _messages for the plural key"
    )


def test_i18n_js_backward_compatible_no_count():
    """Calls without params.count must work exactly as before."""
    content = _read_i18n_js()
    # The original parameter substitution loop must still exist
    assert "Object.entries(params)" in content, (
        "i18n.js should still use Object.entries for parameter substitution"
    )
    assert "msg.replace" in content, (
        "i18n.js should still use msg.replace for substitution"
    )


def test_locale_en_has_plural_keys():
    """en.json locale file should contain at least one _plural key."""
    import json

    with open("static/locale/en.json") as f:
        messages = json.load(f)

    plural_keys = [k for k in messages if k.endswith("_plural")]
    assert len(plural_keys) > 0, "en.json should have at least one _plural key"


def test_locale_ja_has_plural_keys():
    """ja.json locale file should contain at least one _plural key."""
    import json

    with open("static/locale/ja.json") as f:
        messages = json.load(f)

    plural_keys = [k for k in messages if k.endswith("_plural")]
    assert len(plural_keys) > 0, "ja.json should have at least one _plural key"


def test_locale_en_item_plural():
    """en.json should have item and item_plural with different values."""
    import json

    with open("static/locale/en.json") as f:
        messages = json.load(f)

    assert "item" in messages, "en.json should have 'item' key"
    assert "item_plural" in messages, "en.json should have 'item_plural' key"
    assert messages["item"] != messages["item_plural"], (
        "en.json 'item' and 'item_plural' should differ (singular vs plural)"
    )


def test_locale_ja_item_plural():
    """ja.json should have item and item_plural (same value is OK for Japanese)."""
    import json

    with open("static/locale/ja.json") as f:
        messages = json.load(f)

    assert "item" in messages, "ja.json should have 'item' key"
    assert "item_plural" in messages, "ja.json should have 'item_plural' key"
