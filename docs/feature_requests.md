# Feature requests — from the SMS-Alert app (ng_rdm 0.1.66)

Filed from `~/Code/nicegui/alert`, an admin app built on ng_rdm with a few
large entities (~40k users, ~19k memberships, ~1.7k messages). Adding 0.1.66's
header-click sorting to its tables surfaced a cluster of gaps at the **component**
layer: the stores already do the heavy lifting (`q`, `limit`/`offset`, `order_by`,
`read_counts`), but the table widgets expose only part of it, so the app grew a
~280-line `routes/m/_scale.py` of workarounds. Most of that could live upstream.

Ordered by value. §1–§3 are the ones that would let the app delete code.

---

## 1. Pass `q` through the component layer

**Problem.** `Store.read_items()` accepts a `q` predicate (`src/ng_rdm/store/base.py`,
`read_items`), but no component can reach it: both
`ObservableRdmComponent.load_data` (`src/ng_rdm/components/base.py:259`) and
`ObservableRdmTable.load_data` (`base.py:365`) omit the argument entirely. Equality
filtering via `filter_by` is all a table can do, so **any table with a search box has
to subclass**.

The alert app carries this verbatim, purely to reintroduce one keyword
(`routes/m/_scale.py:39`):

```python
class _QueryListTable(ListTable):
    """ListTable that also honours a Tortoise `Q` predicate on load — the one thing
    the stock ListTable can't do (it filters by equality dict only). Search lives here."""

    def __init__(self, *args, q: Q | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.q = q

    async def load_data(self, join_fields=None, filter_by=None, transform=None,
                        limit=None, offset=0, order_by=None) -> None:
        all_joins = list(set(self.config.join_fields + self._extra_join_fields))
        self.data = await self.data_source.read_items(
            join_fields=join_fields or all_joins,
            filter_by=filter_by if filter_by is not None else self.filter_by,
            q=self.q,                                    # ← the entire reason this class exists
            limit=limit if limit is not None else self.state.get("limit"),
            offset=offset or self.state.get("offset", 0),
            order_by=order_by if order_by is not None else self.order_by,
        )
        tf = transform if transform is not None else self.transform
        if tf:
            self.data = tf(self.data)
```

Note it must duplicate the whole body, including the join-field merge — so it silently
goes stale whenever `load_data` changes upstream (it already misses nothing today, but
that is luck, not design).

**Proposal.** Mirror how `filter_by` is handled: a constructor kwarg + instance
attribute + a `load_data` parameter, on `ObservableRdmTable` (and ideally
`ObservableRdmComponent`):

```python
def __init__(self, ..., filter_by=None, q=None, ...):
    self.q = q

async def load_data(self, ..., q: Any | None = None):
    ...
    q=q if q is not None else self.q,
```

Setting `table.q = <Q>` then `await table.build.refresh()` becomes the supported way to
drive a search box — which is what every consumer with >1 screen of rows needs.

**Back-compat caveat.** `DictStore._read_items` **raises** on a non-None `q`
(`src/ng_rdm/store/dict_store.py:36`: `NotImplementedError("ORM arguments q and
join_fields not supported")`). So the pass-through must keep the current call shape when
`q` is None (it will — `q=None` is already the implicit default today), and it would be
worth deciding whether `DictStore` should learn a callable-predicate form of `q` rather
than raising. Not required for this request.

**Test sketch.** `ListTable(data_source=tortoise_store, q=Q(name__icontains='ali'))`
renders only matching rows; reassigning `table.q` + `build.refresh()` swaps the result
set; `q=None` still works against `DictStore`.

---

## 2. A built-in bounded-window pager

**Problem.** `ObservableRdmTable` already holds the window (`state["limit"]`,
`state["offset"]`) and its docstring points at the intent —

> *"For large entities, pass limit=/order_by= and auto_observe=False to make this a
> bounded 'query-view'; the offset in state supports paging on the render_toolbar hook."*

— and `Store.read_counts()` can supply the total. But there is no pager widget, so every
consumer hand-rolls prev/next buttons and an "N of M" label, and each one re-derives the
same edge cases (disable prev at 0, disable next at the last page, reset to page 1 when
the query changes). The alert app's `SearchFirstList` (`routes/m/_scale.py:70`) is ~90
lines of which maybe 15 are app-specific.

**This is also where 0.1.66's sorting bites.** `_toggle_sort` (`base.py:397`) correctly
resets the window — `self.state["offset"] = 0` — and refreshes the table itself. Any
*externally* rendered pager is bypassed by that, so the counter and prev/next go stale on
a header click (table shows page 1, label still reads "26–50 of 400"). An app can fix
this on its own side (bind the chrome to `table.state` instead of mirroring the offset —
that is what alert will do), but every consumer will hit it independently, and it is
really a symptom of the pager living outside the component that owns the window.

**Proposal.** Something like:

```python
@dataclass
class TableConfig:
    ...
    show_pager: bool = False          # render prev/next + "lo–hi of N" for the bounded window
    pager_position: Literal["top", "bottom"] = "bottom"
```

rendered by `ObservableRdmTable` itself, driven by `state["offset"]`/`state["limit"]`
and a `read_counts(filter_by=self.filter_by, q=self.q)` total. Then:

- the pager is always consistent with `_toggle_sort`'s offset reset, for free;
- the total is trivially available for the count label (and is the same query the
  table already needs);
- consumers get search-first/paged lists without a subclass.

Composes with §1: with `q` and a pager upstream, `SearchFirstList` reduces to "a debounced
input that assigns `table.q`".

**Test sketch.** 3 rows, `limit=2`, `show_pager=True`: label reads `1–2 of 3`; click next
→ `3–3 of 3`, next disabled; click a sortable header → back to `1–2 of 3`, prev disabled.

---

## 3. `ListTable` / `SelectionTable` never render their toolbar, and hide it when empty

Two related bugs, both of which block using `render_toolbar` as the documented paging seam.

**3a — the toolbar is dead on two of the three tables.** `ActionButtonTable.build()`
calls `self._build_toolbar("top")` / `("bottom")`
(`src/ng_rdm/components/widgets/action_button_table.py:66,93`). `ListTable.build()` and
`SelectionTable.build()` call neither — only the opt-in `build_with_toolbars()` wrapper
(`base.py:450`) does, and it is not what consumers reach for. So on `ListTable` and
`SelectionTable`, both `config.show_add_button` and the `render_toolbar=` constructor
argument silently do nothing when you call `build()`. That is a surprising asymmetry
between three widgets that share a config object.

*Proposal:* have all three `build()` implementations call `_build_toolbar` at both slots,
and drop `build_with_toolbars()` (or keep it as a deprecated alias). If the current split
is deliberate, the three docstrings and `TableConfig.show_add_button` should say so.

**3b — an empty result set hides the toolbar.** `ListTable.build()` (`list_table.py:73`)
and `SelectionTable.build()` (`selection_table.py:119`) `return` early when `self.data`
is empty, after rendering only `empty_message`. So on a paged view, landing on an empty
page removes the very controls you need to get back — you are stranded with "No results"
and no *previous* button. (`ActionButtonTable` gets this right: it renders the empty
message as a row *inside* the table, so its toolbar survives — `action_button_table.py:80`.)

*Proposal:* render the toolbar (and, arguably, the column headers — you lose the sort
affordance too) around the empty message rather than returning before it. Adopting
`ActionButtonTable`'s "empty row inside the table" shape in all three would fix 3b and
make the widgets consistent in one move.

**Test sketch.** `ListTable(render_toolbar=lambda: ui.label('TOOLBAR'))` shows `TOOLBAR`
after a plain `build()`; and still shows it when `filter_by` matches zero rows.

---

## 4. Allow an async `render_toolbar`

`render_toolbar` is typed `Callable[[], None]` and invoked synchronously
(`base.py:_build_toolbar`). Anything a real toolbar wants to show — a total from
`await store.read_counts()`, a filter's option list from the DB — cannot be awaited
there, which is the second reason alert renders its pager outside the table.

*Proposal:* widen to `Callable[[], None | Awaitable[None]]` and await the result if
awaitable, the same way `RowAction._invoke` (`base.py:53`) already handles
sync-or-async callbacks. `_build_toolbar` would become async, which is fine — all three
call sites are inside an async `build()`.

Largely moot if §2 lands, but cheap and useful on its own.

---

## 5. `Column.sort_desc_first` for dates and counts

0.1.66's `_toggle_sort` always opens ascending on the first click. For the columns people
actually sort by in this app — *Sent*, *Delivered*, *Recipients*, *Expires* — the useful
first click is descending (newest / largest first); ascending-first costs an extra click
every time and, on nullable date columns in MySQL, opens on a block of NULLs.

*Proposal:* `Column(sortable=True, sort_desc_first=True)` — used only to pick the initial
direction; toggling behaviour is unchanged.

Related, smaller: consider a `nulls_last` option (or documenting the DB-dependent
behaviour), since `DictStore` explicitly sorts `None` first
(`dict_store.py:45`, *"None sorts first"*) while MySQL/Postgres differ from each other —
a `DictStore`-backed test can pass while the ORM-backed screen looks wrong.

---

## 6. Make derived fields queryable / sortable (`set_derived_fields` mapping)

**Problem.** `set_derived_fields` computes values **after** the DB read
(`store/base.py:192` — `_apply_derived_fields` runs on the returned rows), so a derived
column is invisible to both `order_by` and `q`, which go into `Model.filter(...)` /
`.order_by(...)` (`store/orm.py:138-141`). Passing a derived name to either raises
Tortoise `FieldError`.

This is easy to get wrong because the column *looks* like a field everywhere else. The
alert app has exactly this bug in production code — a search box configured over a
derived `member_name` column that throws the moment anyone types in it — and 0.1.66's
`sort_key` escape hatch is the same problem's other half (it exists precisely so a
derived column can name a real one).

**Proposal.** Let `set_derived_fields` carry the mapping it already almost has:

```python
store.set_derived_fields(
    {"member_name": lambda r: ...},
    dependencies=["member__first_name", "member__last_name"],
    query_map={"member_name": ["member__first_name", "member__last_name"]},  # new
)
```

with the store expanding a derived name in `order_by` (first entry) and in `q`
(OR across the listed fields) — or, minimally, **raising a clear ng_rdm-level error**
("`member_name` is a derived field; pass `sort_key=`/query a real field") instead of
letting a raw Tortoise `FieldError` surface. `Column.sort_key` could then default to the
mapping, so `sortable=True` just works on FK-name columns.

Given `dependencies` already lists the underlying join fields, `query_map` is often the
same list — deriving it by default may be enough.

---

## 7. Minor / documentation

- **`ObservableRdmComponent.build` type-ignore churn.** Every widget carries
  `async def build(self):  # type: ignore[override]` against the base's stub
  (`base.py:456`, and the comment at `base.py:294-310`). If the base declared `build` via
  a `Protocol` or annotated it as `Any`, three ignores disappear. Cosmetic, but it is the
  first thing a new consumer copies.
- **Document that `_toggle_sort` writes `state["offset"]`** in `docs/facts.md` — it is
  correct behaviour, but any consumer with an external pager needs to know the component
  can move the window out from under it (see §2).
- **`SelectionTable` + sorting:** worth documenting that selection survives a re-sort
  because `state['selected_ids']` is keyed on `row_key`, not on position. It does; it
  just isn't stated, and it is the first thing you'd worry about.
