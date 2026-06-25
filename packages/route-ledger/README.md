# route-ledger

Future home for append-only route and event ledger helpers.

Candidate responsibilities:

- atomic JSON writes
- JSONL append helpers
- route status transitions
- artifact metadata indexing
- state rebuild

No runtime data should be committed here.
