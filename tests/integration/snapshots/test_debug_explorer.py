# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Debug helper for exploring snapshot extractor hierarchy with real FreeCAD documents.

This is NOT a test file - it contains no assertions. It's a debug helper that replicates
the explore_paths.py script functionality but runs in the pytest/PyCharm debugging environment.

Usage in PyCharm:
    1. Set breakpoint anywhere in this file
    2. Run/Debug this file as a Python script
    3. Inspect variables in debugger

Run with:
    ./run_integration_tests.sh tests/integration/snapshots/test_debug_explorer.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from freecad.diff_wb.domain.ports import AppLike, FreeCadContext


class TestDebugExplorer:
    """Debug helper for exploring document structure - NO ASSERTIONS."""

    def test_explore_basic_file(
        self, freecad_app: AppLike, project_root: object, freecad_context: FreeCadContext
    ) -> None:
        """Explore BasicFile.FCStd document structure for debugging purposes.

        This method replicates the explore_paths.py script but runs in pytest environment.
        Set breakpoints and inspect variables to understand the document structure.

        Key things to inspect:
        - doc.Objects: All objects in document
        - obj.InList: Objects that reference this object
        - obj.OutList: Objects referenced by this object
        - obj._Body: Body property for PartDesign features
        - obj.Group: Group contents for containers
        - obj.OriginFeatures: Origin geometry list
        - children_map: Built parent-child relationships
        """
        from pathlib import Path

        # Open the BasicFile test document
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            print("=" * 80)
            print(f"Document: {doc.Name}")
            print(f"Total objects: {len(doc.Objects)}")
            print("=" * 80)
            print()

            # Build dictionary of all objects
            all_objects = {}
            for obj in doc.Objects:
                if hasattr(obj, "Name"):
                    all_objects[obj.Name] = obj

            # Print comprehensive information for each object
            for name, obj in all_objects.items():
                print(f"\n{'=' * 40}")
                print(f"{name} ({obj.TypeId})")
                print(f"{'=' * 40}")

                # Hierarchy relationships
                in_list = [o.Name for o in getattr(obj, "InList", []) if hasattr(o, "Name")]
                out_list = [o.Name for o in getattr(obj, "OutList", []) if hasattr(o, "Name")]
                sub_objects = [s.split(".")[0] for s in getattr(obj, "getSubObjects", lambda: ())() if s]

                print(f"  InList:          {in_list}")
                print(f"  OutList:         {out_list}")
                print(f"  getSubObjects(): {sub_objects}")

                # Container-specific properties
                body_prop = getattr(obj, "_Body", None)
                body_name = body_prop.Name if body_prop and hasattr(body_prop, "Name") else None

                group = getattr(obj, "Group", [])
                group_names = [g.Name for g in group if hasattr(g, "Name")]

                origin_features = getattr(obj, "OriginFeatures", [])
                origin_feature_names = [o.Name for o in origin_features if hasattr(o, "Name")]

                tip = getattr(obj, "Tip", None)
                tip_name = tip.Name if tip and hasattr(tip, "Name") else None

                base_feature = getattr(obj, "BaseFeature", None)
                base_feature_name = base_feature.Name if base_feature and hasattr(base_feature, "Name") else None

                if body_name:
                    print(f"  _Body:           {body_name}")
                if base_feature_name:
                    print(f"  BaseFeature:     {base_feature_name}")
                if group_names:
                    print(f"  Group:           {group_names}")
                if origin_feature_names:
                    print(f"  OriginFeatures:  {origin_feature_names}")
                if tip_name:
                    print(f"  Tip:             {tip_name}")

                # Sketch-specific properties
                profile = getattr(obj, "Profile", None)
                if profile:
                    profile_names = []
                    if isinstance(profile, (list, tuple)):
                        for item in profile:
                            if hasattr(item, "Name"):
                                profile_names.append(item.Name)
                    if profile_names:
                        print(f"  Profile:         {profile_names}")

                attachment_support = getattr(obj, "AttachmentSupport", None)
                if attachment_support:
                    support_names = []
                    if isinstance(attachment_support, list):
                        for item in attachment_support:
                            if isinstance(item, (list, tuple)) and len(item) > 0:
                                obj_ref = item[0]
                                if hasattr(obj_ref, "Name"):
                                    support_names.append(obj_ref.Name)
                    if support_names:
                        print(f"  AttachmentSupport: {support_names}")

            print("\n" + "=" * 80)
            print("SIMPLE HIERARCHY (using Group + OriginFeatures + InList):")
            print("=" * 80)

            # First pass: determine parent for each object
            parent_map = {}

            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name

                if name in parent_map:
                    continue

                # Check Group of all containers
                for container_obj in doc.Objects:
                    if not hasattr(container_obj, "Name"):
                        continue
                    container_name = container_obj.Name

                    group = getattr(container_obj, "Group", [])
                    group_names = [g.Name for g in group if hasattr(g, "Name")]
                    if name in group_names:
                        parent_map[name] = container_name
                        break

                    origin_features = getattr(container_obj, "OriginFeatures", [])
                    origin_feature_names = [f.Name for f in origin_features if hasattr(f, "Name")]
                    if name in origin_feature_names:
                        parent_map[name] = container_name
                        break

            # Second pass: check InList for objects still without parent
            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name

                if name in parent_map:
                    continue

                in_list = getattr(obj, "InList", [])
                for parent_obj in in_list:
                    if hasattr(parent_obj, "Name"):
                        parent_name = parent_obj.Name
                        parent_type = getattr(parent_obj, "TypeId", "")
                        # Fix Origins not having parents
                        if parent_type in ("App::Part", "PartDesign::Body"):
                            parent_map[name] = parent_name
                            break

            # Build children map preserving doc.Objects order
            children_map = {}

            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name
                parent_name = parent_map.get(name)

                if parent_name:
                    if parent_name not in children_map:
                        children_map[parent_name] = []
                    children_map[parent_name].append(name)

            def print_tree(parent_name, indent=0):
                prefix = "    " * indent
                children = children_map.get(parent_name, [])
                for i, child_name in enumerate(children):
                    if child_name not in all_objects:
                        continue
                    child_obj = all_objects[child_name]
                    is_last = i == len(children) - 1
                    connector = "└── " if is_last else "├── "
                    print(f"{prefix}{connector}{child_name} ({child_obj.TypeId}) [{child_obj.Label}]")
                    print_tree(child_name, indent + 1)

            roots = []
            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name
                if name not in parent_map:
                    roots.append(name)

            print("\nComputed tree hierarchy:")
            for i, root_name in enumerate(roots):
                root_obj = all_objects[root_name]
                is_last = i == len(roots) - 1
                connector = "└── " if is_last else "├── "
                print(f"{connector}{root_name} ({root_obj.TypeId}) [{root_obj.Label}]")
                print_tree(root_name, 1)

            print("\n" + "=" * 80)
            print("EXPECTED FREECAD GUI TREE VIEW:")
            print("=" * 80)
            print("""
Part_MyPart (App::Part)
├── Origin (App::Origin) [Origin]
│   ├── X_Axis (App::Line) [X_Axis]
│   ├── Y_Axis (App::Line) [Y_Axis]
│   ├── Z_Axis (App::Line) [Z_Axis]
│   ├── XY_Plane (App::Plane) [XY_Plane]
│   ├── XZ_Plane (App::Plane) [XZ_Plane]
│   ├── YZ_Plane (App::Plane) [YZ_Plane]
│   └── Origin001 (App::Point) [Origin001]
├── Body_MyBody (PartDesign::Body) [Body_MyBody]
│   ├── Origin004 (App::Origin) [Origin004]
│   │   ├── X_Axis001 (App::Line) [X_Axis001]
│   │   ├── Y_Axis001 (App::Line) [Y_Axis001]
│   │   ├── Z_Axis001 (App::Line) [Z_Axis001]
│   │   ├── XY_Plane001 (App::Plane) [XY_Plane001]
│   │   ├── XZ_Plane001 (App::Plane) [XZ_Plane001]
│   │   ├── YZ_Plane001 (App::Plane) [YZ_Plane001]
│   │   └── Origin003 (App::Point) [Origin003]
│   ├── Pad_Main (PartDesign::Pad) [Pad_Main]
│   │   └── Sketch_Pad (Sketcher::SketchObject) [Sketch_Pad]
│   └── Pocket_Main (PartDesign::Pocket) [Pocket_Main]
│       └── Sketch_Pocket (Sketcher::SketchObject) [Sketch_Pocket]
└── MyVarSet (App::VarSet) [MyVarSet]
""")

            # Also run the actual extractor to compare
        finally:
            freecad_app.closeDocument(doc.Name)

        print("\nDone! Set breakpoints above to inspect variables.")
