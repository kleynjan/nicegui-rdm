"""Tests for ReactiveCounts."""
import pytest
from nicegui import ui
from nicegui.testing import User

from ng_rdm.store import DictStore
from ng_rdm.components import ReactiveCounts

pytestmark = pytest.mark.components


async def _seed(store: DictStore):
    for status in ['sent', 'sent', 'pending']:
        await store.create_item({'status': status})


async def test_grouped_counts_track_the_store(user: User):
    store = DictStore()
    counts = []

    @ui.page('/')
    async def page():
        await _seed(store)
        counts.append(await ReactiveCounts(store, group_by='status',
                                           keys=['sent', 'pending', 'failed']).start())

    await user.open('/')
    assert counts[0].values == {'sent': 2, 'pending': 1, 'failed': 0}


async def test_with_total_publishes_the_sum_beside_the_groups(user: User):
    """An 'All' tile without a second instance and a second COUNT query."""
    store = DictStore()
    counts = []

    @ui.page('/')
    async def page():
        await _seed(store)
        counts.append(await ReactiveCounts(store, group_by='status', keys=['sent', 'pending'],
                                           with_total=True).start())

    await user.open('/')
    c = counts[0]
    assert c.values['total'] == 3
    await store.create_item({'status': 'failed'})   # a group nobody pre-seeded still counts
    await c._recompute()
    assert c.values['total'] == 4 and c.values['sent'] == 2
