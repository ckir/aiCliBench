from ai_service_api import ServiceConfig, create_composition, health_check


def test_api_imports():
    import ai_service_api

    assert ai_service_api is not None


def test_api_health():
    assert health_check() == {"status": "ok", "service": "ai-service-api"}


def test_api_composition_lists_echo():
    composition = create_composition(ServiceConfig())
    names = [t.name for t in composition["server"].list_tools()]
    assert "echo" in names
