from clouddeck.registry import AdapterRegistry
from clouddeck.transports.novnc import NoVNCTransport


def test_registry_exposes_only_installed_adapters(tmp_path):
    registry = AdapterRegistry(tmp_path)
    assert registry.provider_ids() == ("codespaces",)
    assert registry.transport_ids() == ("novnc",)
    assert registry.provider().provider_id == "codespaces"
    assert registry.transport().transport_id == "novnc"


def test_unknown_adapters_fail_closed(tmp_path):
    registry = AdapterRegistry(tmp_path)
    try:
        registry.provider("gpu-pc")
    except ValueError as error:
        assert "Unknown session provider" in str(error)
    else:
        raise AssertionError("Unknown provider was unexpectedly resolved")
    try:
        registry.transport("moonlight")
    except ValueError as error:
        assert "Unknown stream transport" in str(error)
    else:
        raise AssertionError("Unknown transport was unexpectedly resolved")


def test_novnc_transport_declares_exact_current_capabilities():
    transport = NoVNCTransport()
    assert transport.viewer_path().startswith("/vnc.html?")
    capabilities = transport.capabilities()
    assert capabilities["websocket"] is True
    assert capabilities["webrtc"] is False
    assert capabilities["native_gamepad"] is False
