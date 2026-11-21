"""Runtime registry for independently replaceable provider and transport adapters."""

from __future__ import annotations

from pathlib import Path

from clouddeck.contracts import SessionProvider, StreamTransport
from clouddeck.providers.codespaces import CodespacesProvider
from clouddeck.transports.novnc import NoVNCTransport


class AdapterRegistry:
    def __init__(self, state_dir: Path, display: str = ":1") -> None:
        self.providers: dict[str, SessionProvider] = {"codespaces": CodespacesProvider(state_dir, display=display)}
        self.transports: dict[str, StreamTransport] = {"novnc": NoVNCTransport()}

    def provider(self, provider_id: str = "codespaces") -> SessionProvider:
        try:
            return self.providers[provider_id]
        except KeyError as error:
            raise ValueError(f"Unknown session provider: {provider_id}") from error

    def transport(self, transport_id: str = "novnc") -> StreamTransport:
        try:
            return self.transports[transport_id]
        except KeyError as error:
            raise ValueError(f"Unknown stream transport: {transport_id}") from error

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.providers))

    def transport_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.transports))
