# User management

The package manages anonymous records in `application.users`.
Visitors are identified by `user_id` without requiring login.

## Modules

- `creation.py`: `create_user()` generates a UUID and stores a
  record. `push_user(user)` persists a supplied `AnonymousUser`.
- `retrieval.py`: `get_user(user_id)` returns a record or raises
  when missing. `does_user_exist(user_id)` checks existence.
- `update.py`: `update_last_active(user_id)` records UTC activity
  and returns whether the stored record changed.
- `deletion.py`: `delete_user(user_id)` removes the user record
  and returns whether a record was deleted.

Operations use the MongoDB collection resolver. The MongoDB
client must be started before these functions are called.
Creation and updates use the shared ID and UTC time helpers.
Deleting a user here does not delete their conversation memories.
