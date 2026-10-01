"""Focused tests for inactive user data pruning."""

import asyncio
from datetime import datetime, timedelta, timezone

from api.maintenance import user_data_pruner
from database.mongodb.collections import MongoDBCollection


class _Cursor:
    def __init__(self, documents: list[dict[str, str]]) -> None:
        self._documents = iter(documents)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._documents)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


async def test_prunes_only_still_inactive_users(monkeypatch) -> None:
    """Delete messages before user records and skip reactivated users."""
    operations: list[tuple[str, str]] = []

    class Users:
        def find(self, query, projection):
            assert isinstance(query['last_active_at']['$lt'], datetime)
            assert projection == {'_id': 0, 'user_id': 1}
            return _Cursor([
                {'user_id': 'inactive'},
                {'user_id': 'reactivated'},
            ])

        async def find_one(self, query, projection):
            assert projection == {'_id': 1}
            return {'_id': 1} if query['user_id'] == 'inactive' else None

        async def delete_one(self, query):
            operations.append(('users', query['user_id']))

    class Messages:
        async def delete_many(self, query):
            operations.append(('messages', query['user_id']))

    users = Users()
    messages = Messages()
    collections = {
        MongoDBCollection.USERS: users,
        MongoDBCollection.MESSAGES: messages,
    }
    monkeypatch.setattr(
        user_data_pruner,
        'get_collection',
        collections.__getitem__,
    )

    pruner = user_data_pruner.UserDataPruner()
    await pruner.prune_once()

    assert operations == [('messages', 'inactive'), ('users', 'inactive')]
    assert pruner._inactive_user_ids == set()


async def test_cutoff_is_seven_days(monkeypatch) -> None:
    """Query the documented activity field with a seven-day UTC cutoff."""
    before = datetime.now(timezone.utc) - timedelta(days=7)
    cutoffs: list[datetime] = []

    class Users:
        def find(self, query, projection):
            cutoffs.append(query['last_active_at']['$lt'])
            return _Cursor([])

    collections = {
        MongoDBCollection.USERS: Users(),
        MongoDBCollection.MESSAGES: object(),
    }
    monkeypatch.setattr(
        user_data_pruner,
        'get_collection',
        collections.__getitem__,
    )

    await user_data_pruner.UserDataPruner().prune_once()

    after = datetime.now(timezone.utc) - timedelta(days=7)
    assert before <= cutoffs[0] <= after


async def test_failed_message_deletion_keeps_user_for_retry(monkeypatch) -> None:
    """Leave the user record in place when message deletion fails."""
    user_deleted = False

    class Users:
        def find(self, query, projection):
            return _Cursor([{'user_id': 'inactive'}])

        async def find_one(self, query, projection):
            return {'_id': 1}

        async def delete_one(self, query):
            nonlocal user_deleted
            user_deleted = True

    class Messages:
        async def delete_many(self, query):
            raise RuntimeError('database unavailable')

    collections = {
        MongoDBCollection.USERS: Users(),
        MongoDBCollection.MESSAGES: Messages(),
    }
    monkeypatch.setattr(
        user_data_pruner,
        'get_collection',
        collections.__getitem__,
    )

    pruner = user_data_pruner.UserDataPruner()
    try:
        await pruner.prune_once()
    except RuntimeError as exc:
        assert str(exc) == 'database unavailable'
    else:
        raise AssertionError('Expected message deletion to fail.')

    assert not user_deleted
    assert pruner._inactive_user_ids == {'inactive'}


async def test_prunes_in_batches_of_thirty(monkeypatch) -> None:
    """Run at most 30 deletions concurrently per batch."""
    active = 0
    peak_active = 0
    deleted_users: set[str] = set()

    class Users:
        def find(self, query, projection):
            return _Cursor(
                [{'user_id': f'user-{index}'} for index in range(31)]
            )

        async def find_one(self, query, projection):
            nonlocal active, peak_active
            if len(deleted_users) == 30:
                assert active == 0
            active += 1
            peak_active = max(peak_active, active)
            await asyncio.sleep(0)
            active -= 1
            return {'_id': 1}

        async def delete_one(self, query):
            deleted_users.add(query['user_id'])

    class Messages:
        async def delete_many(self, query):
            return None

    collections = {
        MongoDBCollection.USERS: Users(),
        MongoDBCollection.MESSAGES: Messages(),
    }
    monkeypatch.setattr(
        user_data_pruner,
        'get_collection',
        collections.__getitem__,
    )

    pruner = user_data_pruner.UserDataPruner()
    await pruner.prune_once()

    assert peak_active == pruner._batch_size == 30
    assert len(deleted_users) == 31
    assert pruner._inactive_user_ids == set()
