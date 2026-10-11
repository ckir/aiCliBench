from plugin_loader import PluginRegistry


def test_registry_empty():
    reg = PluginRegistry()
    assert reg.get_plugins() == []
