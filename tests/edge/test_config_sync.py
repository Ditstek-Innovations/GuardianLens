"""Config sync — ADR-008: conditional pull, atomic apply, last-known-good."""

from __future__ import annotations

import httpx

from guardian_lens_edge.auth import AgentAuthenticator
from guardian_lens_edge.config_sync import ConfigSync
from guardian_lens_edge.store import EdgeStore

from tests.edge.conftest import AGENT_ID, FakeControlPlane, at, make_config

API = "http://control-plane.test"
NOW = at(0)


def make_sync(store: EdgeStore, plane: FakeControlPlane) -> ConfigSync:
    client = plane.client()
    auth = AgentAuthenticator(client, API, "site:agent:secret")
    return ConfigSync(store, client, API, AGENT_ID, auth)


def document(config_version: int = 1) -> dict:
    return make_config(config_version=config_version).model_dump()


def test_200_validates_applies_and_persists(store: EdgeStore) -> None:
    plane = FakeControlPlane(config_document=document(config_version=3))
    sync = make_sync(store, plane)
    applied = sync.tick(NOW)
    assert applied is not None
    assert applied.config_version == 3
    assert sync.applied_version == 3
    assert sync.last_fetch_error is None
    persisted = store.load_config()
    assert persisted is not None
    assert persisted.config_version == 3


def test_304_changes_nothing(store: EdgeStore) -> None:
    plane = FakeControlPlane(config_document=document(config_version=3))
    sync = make_sync(store, plane)
    sync.tick(NOW)
    # Same document version: the conditional GET returns 304.
    applied = sync.tick(NOW)
    assert applied is not None
    assert applied.config_version == 3
    config_requests = [
        entry for entry in plane.request_log if entry[1].endswith("/config")
    ]
    assert len(config_requests) == 2


def test_if_none_match_header_is_sent_after_first_apply(
    store: EdgeStore,
) -> None:
    plane = FakeControlPlane(config_document=document(config_version=3))
    sync = make_sync(store, plane)
    sync.tick(NOW)
    seen: list[str | None] = []
    original = plane.handler

    def spying_handler(request):
        if request.url.path.endswith("/config"):
            seen.append(request.headers.get("if-none-match"))
        return original(request)

    client = httpx.Client(transport=httpx.MockTransport(spying_handler))
    auth = AgentAuthenticator(client, API, "site:agent:secret")
    resumed = ConfigSync(store, client, API, AGENT_ID, auth)
    resumed.load_last_known_good()
    resumed.tick(NOW)
    assert seen == ['"3"']


def test_invalid_document_retains_last_known_good(store: EdgeStore) -> None:
    plane = FakeControlPlane(config_document=document(config_version=1))
    sync = make_sync(store, plane)
    sync.tick(NOW)
    # Next fetch returns garbage that fails validation.
    plane.config_responses = [{"config_version": "not-an-int"}]
    applied = sync.tick(NOW)
    assert applied is not None
    assert applied.config_version == 1  # last-known-good retained
    assert sync.last_fetch_error is not None
    assert "invalid config document" in sync.last_fetch_error
    persisted = store.load_config()
    assert persisted is not None
    assert persisted.config_version == 1
    assert persisted.last_fetch_error is not None


def test_5xx_retains_last_known_good(store: EdgeStore) -> None:
    plane = FakeControlPlane(config_document=document(config_version=1))
    sync = make_sync(store, plane)
    sync.tick(NOW)
    plane.config_responses = [503]
    applied = sync.tick(NOW)
    assert applied is not None
    assert applied.config_version == 1
    assert sync.last_fetch_error == "HTTP 503"


def test_network_error_retains_last_known_good(store: EdgeStore) -> None:
    plane = FakeControlPlane(config_document=document(config_version=1))
    sync = make_sync(store, plane)
    sync.tick(NOW)
    plane.config_responses = [httpx.ConnectError("down")]
    applied = sync.tick(NOW)
    assert applied is not None
    assert applied.config_version == 1
    assert "ConnectError" in (sync.last_fetch_error or "")


def test_no_config_ever_means_none_never_a_default(store: EdgeStore) -> None:
    plane = FakeControlPlane(config_document=None)  # control plane has none
    sync = make_sync(store, plane)
    assert sync.tick(NOW) is None
    assert sync.applied is None
    assert store.load_config() is None  # nothing invented, nothing persisted


def test_restart_restores_last_known_good_without_network(
    store: EdgeStore,
) -> None:
    plane = FakeControlPlane(config_document=document(config_version=5))
    sync = make_sync(store, plane)
    sync.tick(NOW)
    # Simulated restart with the control plane unreachable.
    down = FakeControlPlane()
    down.config_responses = [httpx.ConnectError("down")] * 10
    resumed = make_sync(store, down)
    restored = resumed.load_last_known_good()
    assert restored is not None
    assert restored.config_version == 5
    assert resumed.tick(NOW) is not None  # still the restored document


def test_401_reauthenticates_then_applies(store: EdgeStore) -> None:
    plane = FakeControlPlane(config_document=document(config_version=2))
    plane.config_responses = [401]
    sync = make_sync(store, plane)
    applied = sync.tick(NOW)
    assert applied is not None
    assert applied.config_version == 2
    assert plane.auth_calls == 2
