from backend.services import connector_catalog


def test_catalog_defaults_structure():
    defaults = connector_catalog.get_default_connector_settings()
    assert isinstance(defaults, dict)
    assert "catalog" in defaults
    assert isinstance(defaults["catalog"], list)
