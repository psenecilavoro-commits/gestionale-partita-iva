# JWT startup recovery — 2026-10-07

Operational branch: main. Previous checkpoint: 0ca5d0d7e6e9757d8745c4d1b108068b436d52f2.

The user supplied a first-start screenshot containing `JWT issued at future`.
`readTable` previously threw every Data API error immediately, leaving the initial
screen empty. Session handling does not mint or alter tokens. This error is
consistent with issuance/validation clock skew on the service, but the project's
log query did not return matching entries and a fresh Chrome tab loaded normally.
The project-specific infrastructure cause was therefore not conclusively reproduced.

Completed: bounded retry of read-only requests for exactly PGRST303 / JWT issued
at future, after 1, 2 and 4 seconds. Other errors pass through immediately.
Persistent rejection remains an error with a useful manual retry message.
Writes are never retried. No token refresh is forced and validation is unchanged.
An old in-flight load cannot populate table state after a session change.

Validation: 27 JavaScript tests passed, including transient/persistent failures,
pagination, expired tokens, permission errors and no replay of writes; build passed.
The real intermittent service failure cannot safely be forced in production.

Next step if recurring after bounded recovery: collect failure timestamps and
request service-side diagnosis; do not weaken JWT validation or reset production.
