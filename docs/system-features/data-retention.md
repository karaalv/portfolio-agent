# Data retention

To prevent storage bloat and minimise retained user data as a compliance
consideration, anonymous user records and their chat history are deleted after
seven days of inactivity.

Inactivity is measured from `last_active_at` in `application.users`. The user
data pruner runs when maintenance starts and every 24 hours thereafter. It
deletes eligible records from `application.users` and matching records from
`application.memories` by `user_id`. Deletion therefore occurs on the next
pruner run after the seven-day threshold, rather than at the exact moment the
threshold is reached.

This policy currently covers `application.users` and `application.memories`.
Retention for `application.corpus` and `analytics.monitoring` has yet to be
defined. See the [MongoDB data model](../architecture/mongodb-data-model.md).
