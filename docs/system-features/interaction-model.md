# Interaction model

The portfolio agent is designed for visitors to use without creating an account
or logging in. Each visitor is treated as an anonymous user and assigned a
`user_id`.

The `user_id` is the sole persistent identifier used to associate a visitor
with their user record, activity, and chat history across interactions. The
anonymous user record is stored in `application.users`, and chat history is
stored in `application.messages` using the same `user_id`.

A `user_id` links records, but it is not proof of identity or authorisation on
its own. See the [anonymous user schema](../schemas/users/anonymous.md) and
[MongoDB data model](../architecture/mongodb-data-model.md).
