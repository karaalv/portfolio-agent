# Data retention

To prevent storage bloat and minimise retained user data as a
compliance consideration, anonymous user records and their chat
history are deleted after seven days of inactivity.

Inactivity is measured from `last_active_at` in
`application.users`. The user data pruner runs when maintenance
starts and every 24 hours thereafter. It deletes eligible records
from `application.users` and matching records from
`application.memories` by `user_id`. Deletion therefore occurs on
the next pruner run after the seven-day threshold, rather than at
the exact moment the threshold is reached.

This policy currently covers `application.users` and
`application.memories`. `analytics.usage` records are pruned
after ten days without a counted request, using
`last_request_at`. The usage observer runs at startup and UTC
midnight, so deletion follows the next pass.

`analytics.blocked` records have a minimum blocking period of 24
hours. The block observer deletes expired records at startup and
every six hours. Existing records deny access until deleted.

Retention for `application.corpus` has yet to be defined. See the
[MongoDB data model](../architecture/mongodb-data-model.md).
