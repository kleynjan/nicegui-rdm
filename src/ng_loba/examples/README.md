# CRUD Table Examples

This directory contains runnable examples demonstrating the three CRUD table modes available in `ng_loba.crud`.

## Running the Demo

From the examples directory:

```bash
python main
```

## CRUD Modes Comparison

The demo shows all three modes side-by-side with shared data. Changes made in one table are immediately reflected in the others, demonstrating the observer pattern in action.

### 1. Modal Mode
- **Use case**: Complex forms with many fields; when you need clean separation between view and edit
- **Behavior**: 
  - Table displays read-only data
  - Edit/Add opens modal dialog
  - Separate column configurations for table view vs dialog
- **Best for**: Production interfaces with detailed editing requirements

### 2. Direct Mode
- **Use case**: Quick inline editing; spreadsheet-like data entry
- **Behavior**:
  - All rows are editable at all times
  - Changes auto-save on blur
  - No explicit save/cancel buttons
- **Best for**: Simple data with few columns; rapid data entry

### 3. Explicit Mode
- **Use case**: Balance between modal complexity and direct simplicity
- **Behavior**:
  - Click to select row
  - Double-click or Edit button to enter edit mode
  - Save/Cancel buttons for explicit control
  - Arrow key navigation
- **Best for**: Medium complexity data; when users need visual feedback about edit state

## API Reference

See the main.py source code for examples of:
- Field validation with `Validator` and `FieldSpec`
- Column configuration with `Column` and `TableConfig`
- Creating tables with `create_crud_table()`
- Integrating with data stores (`DictStore`, `TortoiseStore`)
- Sharing a single store across multiple table instances

## Project Integration

This demo shows how to properly import and use CRUD components in your own NiceGUI applications.
