# ng_rdm Examples

Runnable examples demonstrating ng_rdm components and store usage.

## Examples

```
examples/
├── catalog.py           # Component catalog — showcases all widgets
├── custom_datasource.py # Custom RdmDataSource implementation
├── master_detail.py     # ViewStack master-detail navigation
├── in_row_editing.py    # Custom RdmTable with inline rendering & editing
├── multitenant.py       # MultitenantTortoiseStore, models subclass MultitenantRdmModel
├── vanilla_store.py     # Basic store usage without UI components
├── topic_filtering.py   # Topic-based observer filtering
└── chips.py             # Custom cell rendering via Column.render (colored status chips)
```

## Running

All examples start a NiceGUI web server at http://localhost:8080:

```bash
pip install nicegui-rdm

python -m ng_rdm.examples.catalog
python -m ng_rdm.examples.master_detail
python -m ng_rdm.examples.in_row_editing
python -m ng_rdm.examples.custom_datasource
python -m ng_rdm.examples.vanilla_store
python -m ng_rdm.examples.topic_filtering
python -m ng_rdm.examples.chips
```

## What Each Example Demonstrates

- **catalog** — All component types: ActionButtonTable, ListTable, SelectionTable, EditDialog, DetailCard, Dialog, Tabs, ViewStack, StepWizard, buttons, layout primitives
- **master_detail** — ViewStack pattern: list -> detail -> edit navigation with DetailCard and EditCard
- **in_row_editing** - Subclassing ObservableRdmTable and customizing the rendering and on_add / on_edit handling to create a table with 'in-row' editing
- **multitenant** — MultitenantTortoiseStore with two tenant-scoped stores; models subclass MultitenantRdmModel
- **custom_datasource** — Implementing the RdmDataSource protocol for a non-Store data source
- **vanilla_store** — DictStore/TortoiseStore CRUD, observers, validation without UI components
- **topic_filtering** — Observer topic subscriptions for selective UI refresh
- **chips** — Custom cell rendering via Column.render: a dict-based table with colored status chips and a button that mutates the store out-of-band
