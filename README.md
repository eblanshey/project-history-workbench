# FreeCAD Diff Workbench

This workbench provides the ability to view changes between the current document and an older "snapshot" of the same document. The diff view is rendered in two columns, each containing a feature and property tree that is colored to highlight differences.

This functionality is especially powerful when combined with git to version control your FreeCAD files. Git functionality is not integrated here.

Note that the diff view is only intended to verify that your changes didn't cause unintentional parametric downstream mistakes. Just because a diff doesn't show any changes doesn't mean the FreeCAD file itself is unchanged. FreeCAD updates metadata such as timestamps, "touched" attributes, and view orientation every time a file is saved, which may not be displayed in the diff view. The intention with this workbench is more to answer questions like "Did changing this variable from 2mm to 3mm cause any unintended features/properties to change?"

## Suggested Workflow

1. Start with a clean git working tree (everything is committed)
2. Start FreeCAD and open your part files
3. Open the Diff Workbench. The Diff window is opened.
4. Click the "Take Snapshot" command in the toolbar. The list of snapshots on the left side of the window is updated to include the new snapshot, which is named "Snapshot YYYY-MM-DD HH:MM:SS".
5. Start working on your part files.
6. When you are done with your changes, switch back to Diff workbench.
7. Click the "Take Snapshot and Compare" button.
8. Compare changes. If everything looks good, go to File → Save All.
9. Commit all changes to git.
10. Return to step 5 to keep working.

## Diff View

The Diff Window features columns on the left and right. The earlier snapshot is rendered as a tree view on the left, and current snapshot on the right. Scrolling is synchronized within both windows.

Most objects have two expansion icons: one displays children objects, the other displays the properties.

- New objects are colored in green on the right side, and crossed out on the left
- Deleted objects are crossed out on the right side, and green on the left
- Modified objects are blue on both sides

When an object's properties are expanded, both their current values and their expressions, if available, are displayed. A change in either will be highlighted in the diff.

The name of each snapshot is displayed above both columns in a dropdown box. Click the dropdown box to select another snapshot to compare against. A button in between them on the top allows you to switch columns.

For now snapshots are stored in memory and are lost when FreeCAD is closed, but in the future they can be saved to files.

## Configuration

The FreeCAD Preferences dialog has a Diff Workbench panel with the following options:

### Exclusion Lists

Each exclusion list (Types, Properties, Type-specific Properties) supports two modes:

- **Use default exclusion list**: Uses the built-in defaults from the workbench configuration
- **Use custom exclusion list**: Allows you to specify your own exclusions

When switching from default to custom mode for the first time, the custom list is pre-filled with the default values. After you edit or save once, the custom list preserves your changes (including empty lists) and will not be auto-repopulated.

#### Excluded Object Types
One TypeId per line (e.g., `App::Origin`). Objects of these types and their children are removed from the diff view. Default: `App::Origin`.

#### Excluded Properties
One property name per line (e.g., `TimeStamp`, `Label2`). These properties are excluded from all objects. Default: timestamp and UI-only properties.

#### Type-specific Excluded Properties
One mapping per line in the format `TypeId -> PropertyName`. This allows excluding a property for a specific type while keeping it visible for other types. Example:
```
TechDraw::DrawSVGTemplate -> PageResult
```

### Numeric Comparison

#### Float Precision
Number of decimal places for float comparison and display (0-12). Default: 2. This setting affects both the diff computation and how float values are formatted in the diff view.