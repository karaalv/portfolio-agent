# MongoDB data model

Each environment, `testing`, `development`, and `production`,
uses a separate MongoDB Atlas project. The projects have the same
database and collection layout, so data from one environment is
isolated from the others.

## Databases and collections

| Database | Collection | Purpose |
| --- | --- | --- |
| `application` | `users` | Anonymous user records. |
| `application` | `memories` | Agent and visible chat history. |
| `application` | `corpus` | Personal information vector store. |
| `analytics` | `usage` | Daily allowances and connection IDs. |
| `analytics` | `blocked` | IP and user access blocks. |

The `application` database holds data used by core application
features. The `analytics` database holds monitoring data, logs,
and other data outside core application features. The collection
mapping is defined in `database/mongodb/collections.py` and
resolved by `get_collection`.

## Anonymous users

Documents in `application.users` follow the [anonymous user
schema](../schemas/users/anonymous.md). The `last_active_at` and
`created_at` fields are UTC datetimes stored as MongoDB dates.

The user data pruner runs when maintenance starts and every 24
hours after that. It identifies users whose `last_active_at` is
more than seven days old, then deletes their records from
`application.users` and matching chat history from
`application.memories` by `user_id`. It does not modify
`application.corpus` or the `analytics.usage` and
`analytics.blocked` collections.

Memory and corpus schemas are documented under `docs/schemas`.
