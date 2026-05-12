# TODO

- [ ] Migration `downgrade()` for `70345c3ebb63` doesn't drop the `source_type` ENUM — add `op.execute("DROP TYPE source_type")` so downgrade→upgrade cycles don't fail with "type already exists".
- [ ] `Source.updated_at` uses SQLAlchemy `onupdate=func.now()` which only fires on ORM updates; replace with a Postgres trigger if raw SQL `UPDATE`s need to bump it too.
- [ ] `~/.openclaw/openclaw.json` fails `openclaw config validate` because `channels.telegram.dmPolicy` and `channels.telegram.groupPolicy` are required by the current schema but absent — blocks `openclaw config patch`; use `config set` until fixed.
- [ ] Migrate synthesis skill from `google-generativeai` (end-of-life per Google) to the new `google-genai` SDK. Currently a `FutureWarning` is suppressed in `synthesize.py`.
- [ ] Synthesis v4 still produces *within-company* multi-event themes (e.g. Circle Arc presale + Circle AI agent launch under one theme). The primary_signal_id schema defeated *cross-entity* bucketing but not *same-entity* bucketing. v5 candidate fix: tighten "source_signal_ids must all be about the same event" — possibly via an LLM self-check pass that re-reads each theme's sources and drops ones not about the primary event.
