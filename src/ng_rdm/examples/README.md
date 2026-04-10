# ng_rdm Examples

Runnable examples demonstrating ng_rdm components and store usage.

## Examples

```
examples/
├── catalog.py           # Component catalog — showcases all widgets
├── custom_datasource.py # Custom RdmDataSource implementation
├── master_detail.py     # ViewStack master-detail navigation
├── multitenant.py       # MultitenantTortoiseStore, models subclass MultitenantRdmModel
├── vanilla_store.py     # Basic store usage without UI components
└── topic_filtering.py   # Topic-based observer filtering
```

## Running

All examples start a NiceGUI web server at http://localhost:8080:

```bash
python -m ng_rdm.examples.catalog
python -m ng_rdm.examples.master_detail
python -m ng_rdm.examples.custom_datasource
python -m ng_rdm.examples.vanilla_store
python -m ng_rdm.examples.topic_filtering
```

## What Each Example Demonstrates

- **catalog** — All component types: ActionButtonTable, ListTable, SelectionTable, EditDialog, DetailCard, Dialog, Tabs, ViewStack, StepWizard, buttons, layout primitives
- **master_detail** — ViewStack pattern: list -> detail -> edit navigation with DetailCard and EditCard
- **multitenant** — MultitenantTortoiseStore with two tenant-scoped stores; models subclass `MultitenantRdmModel`
- **custom_datasource** — Implementing the `RdmDataSource` protocol for a non-Store data source
- **vanilla_store** — DictStore/TortoiseStore CRUD, observers, validation without UI components
- **topic_filtering** — Observer topic subscriptions for selective UI refresh
