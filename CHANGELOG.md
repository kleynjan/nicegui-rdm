# Changelog

All notable changes to ng_rdm (`nicegui-rdm` on PyPI) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries for versions before 0.1.67 are reconstructed from git history and are
summaries only.

## [Unreleased]

Follow-ups from integrating 0.2.0 into the SMS-Alert app — three small gaps in the new
toolbar chrome, plus a primitive the counts+drilldown pattern kept working around.

### Added

- **Pager markers** — the pager buttons and label now carry `rdm-pager-prev`,
  `rdm-pager-next` and `rdm-pager-label` markers, matching `rdm-search` and
  `rdm-sort-{column}`. Without them the pager was the one piece of built-in chrome
  `user.find()` could not drive, so apps had to drop click-through paging tests.
- **`ReactiveCounts(with_total=True)`** — a grouped count-view also publishes the sum of
  its groups under `key` (default `"total"`). An "All" tile beside the per-group tiles no
  longer needs a second `ReactiveCounts` instance and a second `COUNT` per event.

### Changed

- **`pager_label` is no longer asked about the empty case.** At `total == 0` the label
  falls back to the built-in empty text, and that default now prefers
  `TableConfig.empty_message` over the generic "No data". A custom label that forgot the
  `total == 0` branch used to silently render "0–0 of 0 persons"; it now can't.

## [0.2.0] — unreleased

Structural follow-up to 0.1.67: the table toolbar moves **out** of the refreshable, so it
can host stateful widgets (search input, pager) that survive a refresh instead of losing
focus and value on the keystroke that triggered it. On that foundation, search and paging
ship in-library — tables stop being something apps have to wrap to make usable at scale.

### Added

- **`ObservableRdmTable.render()`** — new public entry point. Renders the toolbar slots
  once, around the refreshable `build()`. Toolbar content reacts by *binding* to
  `self.state` (the `ReactiveCounts` pattern) rather than being re-rendered.
- **Built-in pager** — `TableConfig(show_pager=True)` renders a bound label plus
  prev/next. Every read publishes the window's numbers into `self.state` as first-class
  keys — `total`, `shown`, `page_first`, `page_last`, `has_prev`, `has_next`, plus a
  formatted `page_label`. The raw keys are the point: an app can bind its own counter
  (`pager_label=lambda first, last, total: …`) with its own wording instead of taking the
  built-in chrome. A `COUNT` runs only when something displays a total, and never when the
  first page already came back short of its own `limit`.
- **Built-in search** — `TableConfig(show_search=True, search_fields=[…])`, with
  `search_placeholder` and `search_debounce` (300 ms). Safe now that the toolbar is
  outside the refresh scope. Wants `auto_observe=False`: `q` takes no part in topic
  routing, so a searched *and* observed table re-reads on every store event.
- **`Store.search_q(text, fields)` / `Store.and_q(a, b)`** — predicate building lives on
  the store, so tables stay free of ORM knowledge and search is testable on `DictStore`.
  `TortoiseStore` returns an OR of `icontains` `Q`s; `DictStore` a callable. `and_q`
  composes the table's own `q` with the search predicate so both apply instead of one
  clobbering the other. Both are part of `RdmDataSource`.
- **`set_derived_fields(..., query_map={…})`** — real fields standing in for a derived
  name: `order_by` uses the first, `search_q` ORs over all of them. This is what makes a
  derived column sortable *and* searchable. `Column.sort_key` now resolves lazily against
  the attached store, since a `Column` is constructed before any store exists.
- **`table.requery(q=…, filter_by=…, order_by=…, offset=0)`** — one call instead of the
  order-sensitive "assign, reset offset, refresh" sequence. A new `filter_by` also moves
  the observer subscription, so an observed table keeps reacting to its *new* scope; a
  table given explicit topics via `observe(topics=…)` keeps those untouched.
- **Selection/paging hazard is surfaced** — `SelectionTable` publishes `selected_count`
  and `selected_offscreen`; the pager label appends "N selected (M off page)" so a bulk
  action over invisible rows is at least visible. `clear_selection_on_page_change=True`
  opts into page-scoped selection instead.
- **CSS**: `.rdm-search`, `.rdm-pager`, `.rdm-pager-label`, `.rdm-pager-btn`. New i18n
  keys for the pager, search and selection strings.
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
- App-side search/paging wrappers collapse into config: a `ListTable` subclass that
  existed only to pass `q`, plus a hand-rolled search box, counter and prev/next, become
  `TableConfig(show_search=True, search_fields=[…], show_pager=True, pager_label=…)` on a
  table with `limit=` and `auto_observe=False`.
- A custom `RdmDataSource` (one not deriving from `Store`) needs `search_q()` and
  `and_q()` before it can use `show_search`; without them the table raises a `TypeError`
  naming the missing method. A custom **`Store` subclass** that inherits the base
  implementations raises `NotImplementedError` when searched — deliberately, so a missing
  override cannot present a search box that filters nothing.

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

[Unreleased]: https://github.com/kleynjan/nicegui-rdm/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.67...v0.2.0
[0.1.67]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.66...v0.1.67
[0.1.66]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.65...v0.1.66
[0.1.65]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.64...v0.1.65
[0.1.64]: https://github.com/kleynjan/nicegui-rdm/compare/v0.1.63...v0.1.64
[0.1.63]: https://github.com/kleynjan/nicegui-rdm/releases/tag/v0.1.63
