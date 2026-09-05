# Organize & archive features

Branch: `feature/organize-and-archive`. Builds on the existing FastAPI + vanilla-JS app,
following the async background-task + polling pattern already used by scan/delete/export.

## Scope (this pass)

1. **Label rename / move / cascade-delete** — port from `label_manager.py` (currently a
   standalone, unwired CLI script) into `app/services/gmail/labels.py` and expose via new
   API endpoints. Gmail nests labels via `/` in the name; rename/move need to cascade to
   children by name-prefix match.
2. **Filter-based archive** — extend `ArchiveRequest`/`archive_emails_background` to accept
   `filters` (reusing `build_gmail_query`) so archiving isn't limited to a manually-selected
   sender list.
3. **Unified date picker** — replace the plain `<input type=date>` in Search & Export with
   the same Litepicker component already used in the main filter bar, plus relative-date
   shortcuts inside it. Frontend-only; run through the design skill before implementing.

Explicitly out of scope: persistent auto-label rules (needs a new persistence layer — parked
per [[project_gmail_tools_consolidation]] memory, separate decision later).

## Backend changes

### `app/services/gmail/labels.py`
- `_get_user_labels(service)` — small helper, list + filter to `type == "user"` (dedupe logic
  already spread across `get_labels`/CLI; centralize it).
- `rename_label(label_id, new_name)` — renames target label; finds children by
  `name.startswith(old_name + "/")` and cascades the rename, preserving the suffix after the
  old prefix. Returns `{success, label, cascaded: [...], error}`.
- `move_label(label_id, new_parent)` — computes `new_name` from the label's current leaf name
  + `new_parent` (empty string = move to root), delegates to `rename_label`.
- `delete_label(label_id, cascade=False)` — unchanged behavior when no children exist. If
  children exist and `cascade=False`, return `{success: False, error, children: [names]}`
  instead of deleting (so the UI can ask for confirmation). If `cascade=True`, delete children
  first, then the target.

### `app/services/gmail/archive.py`
- `archive_emails_background(senders=None, filters=None)` — `filters` builds a query suffix via
  `build_gmail_query`. Two paths:
  - senders given: existing per-sender loop, each query becomes
    `from:{sender} in:inbox {filter_query}`.
  - no senders, filters given: single `in:inbox {filter_query}` pass over all matching mail.
  Factor the fetch-all-message-ids-then-batch-archive logic out of the sender loop so both
  paths share it.

### `app/models/schemas.py`
- `RenameLabelRequest(label_id, new_name)`, `MoveLabelRequest(label_id, new_parent="")`.
- `ArchiveRequest`: `senders` becomes optional (default `[]`), add
  `filters: Optional[FiltersModel]`, `model_validator` requiring at least one of
  senders/filters (mirrors `SearchThreadsRequest`'s existing validator).

### `app/api/actions.py`
- `POST /api/labels/rename` → `rename_label`.
- `POST /api/labels/move` → `move_label`.
- `DELETE /api/labels/{label_id}` gains `cascade: bool = False` query param.
- `/api/archive` validation relaxes to "senders or filters required"; passes both through to
  the background task.

## Frontend changes (after design review)

- `static/js/labels.js`: build a `/`-delimited tree from the existing flat `user_labels` list
  (indent + expand/collapse, matching the collapsible-tree UX already shipped for the flat
  list per `CHANGELOG.md`), add rename (inline edit) and move (drag or a "move to..." picker)
  actions, and a cascade-confirm dialog for delete-with-children (reusing `preview.js`'s modal
  pattern).
- `static/js/filters.js` / `export.js`: replace the native `<input type=date>` pair in
  Search & Export with the same Litepicker instance pattern from `filters.js`, plus relative
  shortcuts (7/30/90/180/365d) inside the picker.
- Archive button (`labels.js` `archiveSelected`) gains a "use current filters" mode when no
  senders are selected but filters are active.

## Testing

- `tests/unit/services/gmail/` — new test files for `labels.py` (rename cascade, move,
  cascade-delete-blocked/allowed) and `archive.py` (filter-only path), mocking
  `get_gmail_service` the way existing service tests do.
- `tests/unit/api/test_api_actions.py` — new endpoint tests following the existing
  `@patch("app.api.actions.<fn>")` + `client.post(...)` pattern.
- `uv run pytest` must pass before moving to frontend; `uv run pytest` again before calling
  the feature done.

## Not doing

- No changes to `label_manager.py`/`label_manager_ui.py` themselves (they stay as standalone
  tools) — this ports their *logic* into the main app, doesn't touch the originals.
- No new persistence layer, no rules engine.
