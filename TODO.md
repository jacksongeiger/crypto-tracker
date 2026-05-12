# TODO

- [ ] Migration `downgrade()` for `70345c3ebb63` doesn't drop the `source_type` ENUM — add `op.execute("DROP TYPE source_type")` so downgrade→upgrade cycles don't fail with "type already exists".
- [ ] `Source.updated_at` uses SQLAlchemy `onupdate=func.now()` which only fires on ORM updates; replace with a Postgres trigger if raw SQL `UPDATE`s need to bump it too.
