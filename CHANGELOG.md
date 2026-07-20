# Changelog

All notable changes to ng_rdm (`nicegui-rdm` on PyPI) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries for versions before 0.1.67 are reconstructed from git history and are
summaries only.

## [Unreleased]

## [0.2.0] — unreleased

Structural follow-up to 0.1.67: the table toolbar moves **out** of the refreshable, so it
can host stateful widgets (search input, pager) that survive a refresh instead of losing
focus and value on the keystroke that triggered it.

### Added

- **`ObservableRdmTable.render()`** — new public entry point. Renders the toolbar slots
  once, around the refreshable `build()`. Toolbar content reacts by *binding* to
  `self.state` (the `ReactiveCounts` pattern) rather than being re-rendered.
- **`render_toolbar` may be async** — rendered once, so it can `await read_counts()` for
  the cost of a single query.
- **Per-element toolbar slots** — `TableConfig.search_position` (default `"top"`) and
  `pager_position` (default `"bottom"`) alongside `toolbar_position`, so search-top /
  pager-bottom is expressible. Both slots are now visited; each renders what is assigned
  to it.
- **`SelectionTable(on_add=...)`** — previously only `ListTable` and `ActionButtonTable`
  accepted it, which made `show_add_button` unsatisfiable there.

### Changed

- **BREAKING: `ActionButtonTable.build()` no longer renders its own toolbar.** Callers
  that relied on it move to `await table.render()`. `build()` stays
  `@ui.refreshable_method`, so `build.refresh()` and the `prune()`/`targets` lifecycle are
  unchanged.
- **BREAKING: the Add button requires a handler.** It renders only when
  `config.show_add_button` **and** `on_add is not None` — `add_button` is only the label,
  so it could not imply a handler. The no-op `_default_on_add` is gone.
- **Empty results keep their chrome.** `ListTable` and `SelectionTable` now render the
  empty message as a row *inside* the table, so column headers and the sort affordance
  survive a filter that matches nothing (`ActionButtonTable` already did).
- **A derived field reaching the DB inside `q=` now raises a clear `ValueError`.**
  `_reject_derived` can only inspect `filter_by`/`order_by`/`group_by`; a derived name
  inside a `Q` only fails when the query runs. `TortoiseStore` now catches that
  `FieldError` and re-raises it annotated with the store's derived field names. Stores
  with no derived fields keep the raw `FieldError` (most likely a typo).

### Deprecated

- **`build_with_toolbars()`** — alias for `render()`; logs a warning.

### Migration

- `await table.build_with_toolbars()` → `await table.render()`.
- `ActionButtonTable`: `await table.build()` → `await table.render()` wherever the add
  button or a `render_toolbar` is used.
- Tables that set `show_add_button=False` purely to suppress an unwired button can drop
  the setting.

## [0.1.67] — 2026-07-20

Component-layer follow-up to 0.1.66's header-click sorting: the store layer already
supported non-equality filtering and DB-side ordering, but tables could not reach it.
All changes are additive — no visual change to existing screens.

### Added

- **`q` reaches the component layer.** `ObservableRdmTable` (and its three widgets,
  `ListTable` / `SelectionTable` / `ActionButtonTable`) accept a `q=` constructor
  keyword and honour it in `load_data()`, mirroring how `filter_by` works. Assign
  `table.q` and `await table.build.refresh()` to drive a search box — tables no longer
  need to be subclassed for this. `ObservableRdmComponent.load_data()` gained the same
  parameter. Note `q` takes no part in topic routing; `observe()` still subscribes on
  `filter_by`.
- **`DictStore` accepts `q` as a callable predicate** — `q=lambda item: ...` — so
  component-level filtering can be tested without a database. Tortoise `Q` objects (and
  any other non-callable) still raise `NotImplementedError` on the in-memory path.
- **`Column.sort_desc_first`** opens a sortable column descending on the first click,
  for date and count columns where newest/largest first is the useful default.
  Toggling behaviour is unchanged.

### Changed

- **Derived fields used in a query now raise a clear error.** `set_derived_fields()`
  computes values *after* the read, so a derived name is invisible to the database.
  Passing one to `read_items(filter_by=/order_by=)` or `read_counts(filter_by=/group_by=)`
  now raises a `ValueError` naming the field and pointing at `Column.sort_key`. Previously
  this surfaced as a raw Tortoise `FieldError` on the ORM path and — worse — sorted by
  nothing at all on `DictStore`.
- `load_data()` gained a `q` parameter positioned after `filter_by` on both
  `ObservableRdmComponent` and `ObservableRdmTable`. Callers passing `transform`,
  `limit`, `offset` or `order_by` *positionally* to `load_data()` must switch to
  keywords; keyword callers (the documented usage) are unaffected.

### Added — documentation

- `CHANGELOG.md` (this file).
- `docs/facts.md`: `_toggle_sort` resets `state["offset"]`, so external paging chrome
  must bind to `table.state` rather than mirror the offset; `SelectionTable` selection
  survives a re-sort because `state['selected_ids']` is keyed on `row_key`, not
  position; the state-ownership convention (a state dict passed to a component belongs
  to that component); and the DB-dependent NULL ordering caveat.

## [0.1.66] — 2026-07-13

### Added

- Header-click sorting on all three table widgets: `Column.sortable`, `Column.sort_key`,
  `ObservableRdmTable._toggle_sort()` with a stable `row_key` tie-break, and sort
  indicator styling in `ng_rdm.css`. Sort state is per-instance, so components sharing a
  store sort independently.

## [0.1.65] — 2026-07-08

### Fixed

- Timezone handling in `now_utc()`.

## [0.1.64] — 2026-07-07

### Added

- Bounded views for large datasets: notifier throttling, `Store.read_counts()`
  (total and grouped), and the `ReactiveCounts` binding-driven count view.
- `limit` / `offset` / `order_by` on `read_items()` and on the table widgets.

## [0.1.63] — 2026-06-02

### Changed

- Tortoise `index` → `db_index` for current Tortoise versions.

[Unreleased]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.67...HEAD
[0.1.67]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.66...v0.1.67
[0.1.66]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.65...v0.1.66
[0.1.65]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.64...v0.1.65
[0.1.64]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.63...v0.1.64
[0.1.63]: https://github.com/kleynjan/nicegui-rdm/releases/tag/v0.1.63
