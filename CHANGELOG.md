# Changelog

All notable changes to ng_rdm (`nicegui-rdm` on PyPI) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries for versions before 0.1.67 are reconstructed from git history and are
summaries only.

## [Unreleased]

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
