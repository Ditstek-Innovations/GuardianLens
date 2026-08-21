from __future__ import annotations

from uuid import uuid4

from guardian_lens.services.ptz_commands import PtzCommandStore


def test_ptz_commands_are_delivered_once_to_the_correct_site() -> None:
    store = PtzCommandStore()
    site_a, site_b, camera = uuid4(), uuid4(), uuid4()
    queued = store.enqueue("pilot", site_a, camera, "up")

    assert store.take("pilot", site_b) == []
    assert store.take("another-tenant", site_a) == []
    assert store.take("pilot", site_a) == [queued]
    assert store.take("pilot", site_a) == []
