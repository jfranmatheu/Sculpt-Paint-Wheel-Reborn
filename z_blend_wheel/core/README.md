# `core` — Blender Addon Framework

The `core` package is an internal framework that accelerates Blender addon development. It handles the full lifecycle of a Blender addon — registration, type discovery, property injection, GPU drawing, tool/gizmo creation, and mesh utilities — with an opinionated, class-inheritance-driven API. Addon authors subclass provided base types, decorate them with presets, and the framework handles the rest.

---

## Table of Contents

- [Package Overview](#package-overview)
- [Root Modules](#root-modules)
  - [`__init__.py`](#__init__py)
  - [`_loader.py`](#_loaderpy)
  - [`globals.py`](#globalspy)
  - [`bl_types.py`](#bl_typespy)
  - [`types.py`](#typespy)
  - [`debug.py`](#debugpy)
- [`_auto_code/`](#_auto_code)
- [`_btypes/`](#_btypes)
  - [`_base.py` — BType](#_basepy--btype)
  - [`_register.py` — Registration Engine](#_registerpy--registration-engine)
  - [`data/` — Property Groups & Preferences](#data--property-groups--preferences)
  - [`ops/` — Operators](#ops--operators)
  - [`ui/` — Panels & Menus](#ui--panels--menus)
  - [`gz/` — Gizmos](#gz--gizmos)
  - [`ne/` — Node Editor](#ne--node-editor)
  - [`tool/` — WorkSpace Tools](#tool--workspace-tools)
- [`gpu/`](#gpu)
  - [`imm_2d.py` / `imm_3d.py`](#imm_2dpy--imm_3dpy)
  - [`_draw/` — Shader Builder](#_draw--shader-builder)
- [`utils/`](#utils)
  - [Core Utilities](#core-utilities)
  - [`bm/` — BMesh Operations](#bm--bmesh-operations)
  - [`geometry/` — Geometry Algorithms](#geometry--geometry-algorithms)

---

## Package Overview

```
core/
├── __init__.py          # Public entry point
├── _loader.py           # Addon registration lifecycle
├── globals.py           # Addon-wide constants and paths
├── bl_types.py          # Public type aliases for addon authors
├── types.py             # Public spec/data-type re-exports
├── debug.py             # Debug/profiling helpers
├── _auto_code/          # Code generation (icons)
├── _btypes/             # Blender RNA type base classes + registration
│   ├── _base.py
│   ├── _register.py
│   ├── data/            # PropertyGroup, AddonPreferences
│   ├── ops/             # Operators (action, modal, macro, multi-tool)
│   ├── ui/              # Panels, menus, pie menus
│   ├── gz/              # Gizmos and gizmo groups
│   ├── ne/              # Node editor types
│   └── tool/            # WorkSpace tools (standard, multi, all-in-one)
├── gpu/                 # GPU drawing utilities
│   ├── imm_2d.py
│   ├── imm_3d.py
│   ├── geom_specs.py
│   ├── globals.py
│   ├── state_control.py
│   └── _draw/           # Declarative shader builder
└── utils/               # General-purpose runtime helpers
    ├── bm/              # BMesh topology operations
    └── geometry/        # Computational geometry
```

---

## Root Modules

### `__init__.py`

The public entry point of the framework. Re-exports the core building blocks that addon authors use:

- `AddonLoader` — the registration lifecycle manager
- `AutoCode` — code generation utilities
- `GLOBALS`, `PATHS` — addon-wide state and file paths
- Subpackages: `bl_types`, `types`, `utils`, `debug`, `gpu`

---

### `_loader.py`

**`AddonLoader`** — the central orchestrator of addon registration.

Discovers all Python submodules under the addon root, calls lifecycle hooks on each, and manages dependency ordering. Supports two-phase initialization (`init` → `late_init`) and two-phase registration (`register` → `late_register`), allowing types that depend on others to be set up after their dependencies.

Key responsibilities:
- `init()` — import and initialize all submodules; run `AutoCode.ICONS()` if configured.
- `register()` / `unregister()` — delegate to `_btypes._register` to register/unregister all discovered Blender types.
- `cleanse_modules()` — remove all addon modules from `sys.modules` for clean reloads.

Helper functions: `get_all_submodules`, `iter_submodules`, `iter_submodule_names`.

---

### `globals.py`

Reads `blender_manifest.toml` at import time and exposes two singletons used throughout the framework:

**`PATHS`** — filesystem paths:
- `ROOT` — addon root directory
- `ASSETS`, `ICONS`, `IMAGES` — asset subdirectory paths

**`GLOBALS`** — addon identity and runtime state:
- `ADDON_ID`, `ADDON_NAME` — from the manifest
- `PACKAGE`, `PACKAGE_PARENT` — Python package names
- `DEBUG`, `BACKGROUND` — runtime flags
- Nested `ADDON` — user-facing addon metadata

Helper functions:
- `set_global_value(key, value)` — persist a value on `bpy.<addon_id>` for cross-module state.
- `get_global_value(key, default)` — retrieve it.

---

### `bl_types.py`

The **primary authoring surface** for addon developers. Provides clean, friendly aliases for all the `BType_*` concrete bases defined in `_btypes`, so addon code never imports from deep internal paths.

Exposed names include:

| Alias | Maps to |
|---|---|
| `AddonPreferences` | `BType_AddonPreferences` |
| `PropertyGroup`, `PropertyGroupRoot` | `BType_PGChild`, `BType_PGRoot` |
| `Operator` | `BType_Operator` (preset) |
| `OperatorAction` | `BType_OpAction` |
| `OperatorModal` | `BType_OpModal` |
| `MacroCreator` | `MacroCreator` |
| `Panel` | `BType_Panel` (preset) |
| `Menu`, `MenuPie` | `BType_Menu`, `BType_MenuPie` |
| `Tool` | `BType_WorkSpaceTool` (preset) |
| `MultiTool`, `MultiToolGroup` | `BType_WorkSpaceToolMulti`, `ToolGroup` |
| `AllInOneTool` | `BType_WorkSpaceTool_AllInOne` |
| `ToolWidget` | `BType_ToolWidget` |
| `Gizmo`, `GizmoGroup` | `BType_GZ`, `BType_GZG` |

---

### `types.py`

Re-exports spec and data types that are used as annotations and return values in addon code:

- `ToolGroup`, `ToolPreselectionSpecs`, `ToolRaycastSpecs`
- `PreselectionInfo`, `PRESELECTION_HIGHLIGHT_VALUES`
- `OpReturn`, `ModalMouse`, `RaycastInfo`, `BVHTreeRaycastInfo`
- `ModalRaycastSpecs` (alias for `ToolRaycastSpecs`)

These are the vocabulary types for building tool logic — passed to specs, returned from callbacks, read in modal operators.

---

### `debug.py`

Utilities for development-time debugging and profiling. Not meant for shipping code.

| Symbol | Description |
|---|---|
| `enable_debug_buffer()` / `disable_debug_buffer()` | Redirect print output to an in-memory buffer. |
| `print_debug_buffer()` | Flush the buffer to stdout. |
| `CM_PrintDebug` / `CM_PrintDebugDeferred` | Context managers that print a label on entry (or exit). |
| `PrintDebug` | Decorator that logs function calls. |
| `time_it(label)` / `CM_TimeIt` | Measure execution time of a block or function. |

---

## `_auto_code/`

Generates Python source files at addon load time to avoid hand-maintaining boilerplate.

### `icons.py` — Icon code generation

**`generate_icons_py(icons_dir, output_path)`** — scans the icons asset directory and writes a self-contained `icons.py` file to the addon root. The generated file defines:
- `IconsEnum` — an enum class listing all icon names.
- `IconData` — a dataclass holding per-icon metadata.
- A `previews` collection backed by Blender's `bpy.utils.previews`.

**`AutoCode.ICONS()`** — the callable that triggers generation; invoked by `AddonLoader` when the manifest declares `auto_code_options.icons = true`.

---

## `_btypes/`

The core registration layer. Every Blender type (operator, panel, property group, tool, gizmo, …) is represented as a subclass of `BType`. The registration engine discovers all leaf subclasses at addon load time, sorts them by dependency, and calls `bpy.utils.register_class` / `unregister_class` for each.

### `_base.py` — BType

**`BType`** is the metaclass-driven base for every Blender-registered class in the framework.

Key behaviours:
- **Automatic `bl_idname`**: derives a correct, Blender-compatible `bl_idname` from the class name using patterns defined per `bpy.types.*` base class.
- **Automatic `bl_label`**: `label_from_class_name()` converts `CamelCase` to `"Title Case"` if no label is set.
- **`tag_register()`**: an overridable class method called after the class is defined (before registration); subclasses use it to declare properties, keymaps, sockets, etc.
- **`decorator(*args, **kwargs)`**: a class factory that creates a mixin type pre-configured with specific `bl_options`, region/space types, or other properties — used by `bl_types.py` to create the preset aliases.
- **`on_register()` / `on_unregister()`**: optional hooks for per-type side effects.

### `_register.py` — Registration Engine

Manages the full lifecycle of Blender type registration for an addon.

- **`init(package_root)`** — walks all subclasses of `BType` (excluding framework-internal ones), groups them by Blender type category, resolves `PropertyGroup` dependency order via topological sort.
- **`register()`** — calls `bpy.utils.register_class` for all discovered types in correct order. For `PropertyGroup` roots, synthesises a **MASTER** `PropertyGroup` type with `PointerProperty` entries (one per root PG, per attachment target like `Scene`, `Object`, `WindowManager`). Handles special cases: `WorkSpaceTool.register()`, macro chain setup.
- **`unregister()`** — reverses registration in dependency-safe order.
- **`sort_property_group_classes()`** — topological sort so a PG that references another PG as a `PointerProperty` is registered after its dependency.

---

### `data/` — Property Groups & Preferences

#### `btype_pg.py`

Base classes for attaching structured data to Blender data-blocks.

**`BType_PGChild`** — a plain `PropertyGroup` with no special attachment; used for nested/child groups referenced by `PointerProperty`.

**`BType_PGRoot`** — a "root" property group that gets automatically attached to a Blender data-block type. Its `pg_root_type` class attribute selects the attachment target:

| Preset | Attachment target |
|---|---|
| `BType_PGRootTypes.WINDOW_MANAGER` | `bpy.types.WindowManager` |
| `BType_PGRootTypes.SCENE` | `bpy.types.Scene` |
| `BType_PGRootTypes.OBJECT` | `bpy.types.Object` |
| `BType_PGRootTypes.MESH` | `bpy.types.Mesh` |
| `BType_PGRootTypes.BRUSH` | `bpy.types.Brush` |
| … | … |

At registration time, a dynamic MASTER `PropertyGroup` is created and the root PGs are injected into the target type as `PointerProperty` entries.

#### `btype_prefs.py`

**`BType_AddonPreferences`** — extends `BType_PGChild` for `bpy.types.AddonPreferences`. Overrides `tag_register()` to set `bl_idname` to the addon's package name (required by Blender). Automatically discovered and registered by the engine.

---

### `ops/` — Operators

#### `btype_op_base.py` — `BType_Operator`

The base for all operators. Extends `bpy.types.Operator` with:
- `decorator(options, poll_mode, ...)` — creates preset subclasses with `bl_options` = `REGISTER`, `UNDO`, `REGISTER_UNDO`, etc.
- `run(context)` — the primary method addon authors override (replaces raw `execute`).
- `run_invoke(context, event)` — override for custom invoke behaviour.
- `poll(context)` / `poll_operator(context)` — composable poll; the base implementation uses `poll_mode` from the decorator to check context mode.
- Dialog helpers for property popups.

#### `btype_op_action.py` — `BType_OpAction`

A lightweight operator intended for simple one-shot actions. Implements `execute` by calling the subclass's `action(context)` method. `invoke` immediately calls `execute`.

#### `btype_op_modal.py` — `BType_OpModal`

A full-featured base for modal operators (interactive operators that run over multiple events).

Built-in features:
- **Raycast integration**: configures scene/object/BVHTree raycasting via `ToolRaycastSpecs`, updated every event and accessible as `self.raycast`.
- **`ModalMouse`**: tracks cursor position, delta, velocity, and path shape analysis; available as `self.mouse`.
- **Draw handlers**: registers 2D and 3D `SpaceView3D` draw callbacks automatically; the subclass implements `draw_2d(context)` / `draw_3d(context)`.
- **Timer**: optional `timer_interval` for time-driven modal steps.
- **Sub-modal**: nesting support — a modal can spawn a child modal and resume when it completes.
- **Lifecycle**: `modal_begin(context, event)`, `modal_step(context, event)`, `modal_end(context, event, cancelled)`.
- **Context mode guard**: the modal exits cleanly if the context mode changes unexpectedly.

#### `btype_op_macro.py` — `MacroCreator`

Utility for building Blender `Macro` operators (a sequence of operators executed in order).

`MacroCreator` holds a list of `(operator_idname, properties)` pairs and provides `register()` / `unregister()` to create and destroy the dynamic macro type.

#### `btype_op_tool_multi.py` — `BType_OpToolMulti`

A modal operator that acts as the execution entry point for a **multi-tool**. When invoked, it resolves the correct `Tool` subclass from `tool_cls_id`, instantiates it, and delegates `modal_begin/step/end` to it. This decouples the Blender operator registration from the per-tool logic.

---

### `ui/` — Panels & Menus

#### `btype_ui_base.py`

**`BType_UICommon`** — shared base for all UI types; holds common `bl_options` wiring.

**`BType_UIExtra`** — mixin that adds `draw_section(layout, label)`, a helper for drawing collapsible, labelled sections in a panel.

#### `btype_panel.py`

**`BType_Panel`** — base for `bpy.types.Panel`. The `decorator()` accepts a `panel_type` from `BType_PanelTypes` to pre-configure `bl_space_type` / `bl_region_type` / `bl_category`:

| Preset | Space / Region |
|---|---|
| `VIEW_3D_SIDEBAR` | 3D Viewport → Sidebar |
| `VIEW_3D_HEADER` | 3D Viewport → Header |
| `VIEW_3D_TOOLS` | 3D Viewport → Tools region |
| `POPOVER` | Generic popover |
| `PROPERTIES_EDITOR` | Properties editor |
| … | … |

`_new_panel_type(space, region, category)` — programmatic factory for panels without decorator.

#### `btype_menu.py`

**`BType_Menu`** — base for `bpy.types.Menu`; inherits `BType_UIExtra`.

**`BType_MenuPie`** — base for `bpy.types.Menu` rendered as a pie; provides directional slot helpers.

---

### `gz/` — Gizmos

#### `btype_gz.py` / `btype_gzg.py`

**`BType_GZ`** — base for individual `bpy.types.Gizmo` types.

**`BType_GZG`** — base for `bpy.types.GizmoGroup` types; manages a collection of gizmos and their keymaps.

#### `btype_gz_tool_widget.py`

**`BType_ToolWidget`** — a paired Gizmo + GizmoGroup combination for use as a visual widget attached to a `WorkSpaceTool`. Handles keymap registration (`WidgetKM`), `late_init` for deferred setup, and clean `register` / `unregister` lifecycle.

#### `btype_gz_tool_multi.py`

Provides the gizmo layer for **multi-tools** (`BType_WorkSpaceToolMulti`):

- **`BType_GZG_ToolMulti`** — a GizmoGroup that renders a custom toolbar with tool slot icons using `imm_2d`.
- **`BType_GZ_ToolMulti`** — a single gizmo slot; handles hit-testing mouse position against the toolbar slots.

---

### `ne/` — Node Editor

Helpers for building custom node trees.

#### `node.py` — `BType_Node`

Base for custom `bpy.types.Node` types. In `tag_register()` it introspects class-level `Prop` descriptors and dynamically creates `bpy.props.*` properties. `PropDef`, `_PropProxy`, and `Prop` form a lightweight property DSL for node inputs/outputs without boilerplate.

`_make_bpy_property(prop_def)` converts a `PropDef` into the appropriate `bpy.props.*` call.

#### `node_tree.py` — `BType_NodeTree`

Base for `bpy.types.NodeTree`. The `add_node` class decorator registers a node class into the tree and adds it to the node menu.

#### `node_socket.py` — `BType_NodeSocket`

Base for custom `bpy.types.NodeSocket`. Provides:
- `SocketSpec` — describes a socket (name, type, default value).
- `SocketRef` / `SocketDef` — reference and definition helpers for wiring nodes.
- `Socket` — high-level descriptor for declaring sockets on a node class.
- `SOCKET_TYPE_MAP`, `get_socket_bl_id()` — maps Python types to Blender socket class ids.
- Built-in types: `TM_NodeSocketFloat`, `TM_NodeSocketInt`, `TM_NodeSocketBool`.

#### `node_cat.py`

`NodeCategory` + `_categories` — integrates with Blender's `nodeitems_utils` to register node categories in the Add menu of a custom node editor.

---

### `tool/` — WorkSpace Tools

#### `btype_tool.py` — `BType_WorkSpaceTool`

Base for `bpy.types.WorkSpaceTool`. Handles `bl_idname` construction, icon lookup, and attaches the operator and keymap for the tool. `BType_WorkSpaceToolTypes` provides presets for the tool's context mode:

| Preset | Blender mode |
|---|---|
| `OBJECT` | Object Mode |
| `EDIT_MESH` | Edit Mesh |
| `SCULPT_MESH` | Sculpt Mode |
| `PAINT_WEIGHT` | Weight Paint |
| `PAINT_VERTEX` | Vertex Paint |
| `PAINT_TEXTURE` | Texture Paint |

`RegionView3DInfo` — a frozen helper holding viewport metadata available inside tool callbacks.

#### `tool_specs.py`

**`ToolRaycastSpecs`** — configures what to raycast against when the tool is active:
- `do_scene_raycast` — hit scene geometry.
- `do_object_raycast` — hit the active object.
- `do_bvh_raycast` — build/reuse a BVHTree and hit it.
- `depsgraph_mode` — evaluated or original mesh.

**`ToolPreselectionSpecs`** — configures hover highlighting:
- `highlight_verts`, `highlight_edges`, `highlight_faces` — what to highlight.
- `snap_to_*` — snap cursor to nearest element.
- `draw_*` — whether to draw the highlight overlay.

#### `tool_group.py` — `ToolGroup`

Manages a named group of tools that share a single toolbar slot (like Blender's built-in tool groups). Builds and owns the GizmoGroup toolbar widget that lets the user pick the active sub-tool. `ToolbarItem` wraps each tool entry in the group.

#### `tool_switch.py`

Hooks into Blender's internal tool activation by monkey-patching (`wrap_function`) the tool-activation call. When a tool from this addon becomes active or inactive, registered callbacks fire. Exposes:
- `add_tool_enter_callback(tool_id, fn)` — called when a tool becomes active.
- `add_tool_exit_callback(tool_id, fn)` — called when a tool is deactivated.

#### `tool_preselection.py`

Drives hover/preselection highlighting when the cursor moves over geometry. On each cursor move it runs a raycast against the mesh, identifies the nearest vertex/edge/face, stores the result in `PreselectionInfo`, and draws a highlight overlay via `imm_2d`. 

`MousePreselectionResult` — the data returned per-frame: hit element, distance, world position.

`preselect_editmesh_primitive_from_mouse(context, mouse_pos, specs)` — the main entry point, usable from any modal operator or tool.

#### `tool_statusbar.py`

Overrides Blender's status bar text while a tool is active, showing context-sensitive hints. Uses a `CallbackDict` keyed by context mode so different hint sets can be registered per mode. Restores the original draw function on tool exit.

#### `tool_draw.py`

A registry of 2D and 3D draw handler functions keyed by tool id. When a tool becomes active, its registered draw handlers are installed into `SpaceView3D`. When it exits, they are removed.

#### `multi/tool_multi.py` — `Tool`

The per-sub-tool logic class for a **multi-tool** setup. Addon authors subclass `Tool` and implement:
- `modal_begin(context, event, mouse, raycast)` — enter the interaction.
- `modal_step(context, event, mouse, raycast)` — per-event logic.
- `modal_end(context, event, cancelled)` — cleanup.

Static decorators `set_raycast_specs(specs)` and `set_preselection_specs(specs)` attach configuration to the class.

#### `multi/btype_tool_multi.py` — `BType_WorkSpaceToolMulti`

A `WorkSpaceTool` that hosts multiple `Tool` subclasses. Registers a single shared operator (`BType_OpToolMulti`) and a shared gizmo group toolbar (`BType_GZG_ToolMulti`). The `add_tool(tool_cls)` decorator registers a `Tool` subclass into this multi-tool.

#### `all_in_one/btype_tool_allinone.py` — `BType_WorkSpaceTool_AllInOne`

An alternative to multi-tools for simpler cases. The addon author defines a single class with class methods for each interaction phase and the framework synthesises both the `WorkSpaceTool` and its modal operator at registration time. Useful when the tool doesn't need a picker toolbar.

---

## `gpu/`

GPU drawing utilities for immediate-mode overlays, declarative shader rendering, and GPU state management.

### `globals.py`

**`RuntimeDrawGlobals`** — stores `context`, `region`, and `region_3d` so draw callbacks (which do not receive `context` in all Blender versions) can access them. Updated each frame by `track_context`.

**`ContextTracker`** / `track_context` — a lightweight handler registered in `SpaceView3D`'s draw callbacks that captures the live Blender context and stores it in `RuntimeDrawGlobals`.

### `geom_specs.py`

Simple geometry specification dataclasses used as input to the drawing functions:
- **`GeomSpec`** — base; position and color.
- **`RectSpec`** — axis-aligned rectangle with position, size, and color.
- **`TriaSpec`** — three-point triangle.
- **`CubeSpec`** — axis-aligned cube.

### `state_control.py`

**`CM_GPU_BLEND(mode)`** — a context manager that saves the current GPU blend state, sets the requested mode (`ALPHA`, `ADDITIVE`, `MULTIPLY`, …), and restores the original on exit. Prevents GPU state leaks between draw calls.

**`gpu_state_blend(mode)`** — decorator version of the same pattern.

### `imm_2d.py`

Immediate-mode 2D drawing primitives for overlay drawing in `SpaceView3D`. All functions accept colors as `(R, G, B, A)` tuples and coordinates in region pixel space.

Functions include:
- `draw_circle_2d(center, radius, color, segments)` — filled/outlined circle.
- `draw_rect_2d(x, y, w, h, color)` — filled rectangle.
- `draw_line_2d(start, end, color, width)` — anti-aliased line.
- `draw_points_2d(points, color, size)` — point cloud.
- `draw_texture_2d(texture, x, y, w, h)` — GPU texture blit.
- Text helpers wrapping `blf`.

### `imm_3d.py`

Immediate-mode 3D drawing for in-viewport overlays. Coordinates are in world space.

Functions include:
- `draw_circle_3d(center, normal, radius, color)` — circle facing a normal direction.
- `draw_line_3d(start, end, color)` — 3D line.
- `draw_points_3d(points, color, size)` — 3D point cloud.

### `_draw/` — Shader Builder

A declarative framework for writing custom GLSL shaders and using them in draw callbacks without boilerplate.

#### `types.py`

- **`GPU_TYPES`** — mapping of GLSL type strings to Python equivalents.
- **`PRIMITIVE_TYPES`** — `POINTS`, `LINES`, `TRIS`, `LINE_STRIP`, etc.
- **`UniformType`** — enum of supported uniform categories (float, vec2, vec3, mat4, sampler2D, …).

#### `shader_builder.py` — `ShaderBuilder`

The core class. Built with a vertex shader, a fragment shader, and a list of uniform/attribute declarations. Manages:
- Shader compilation and caching.
- Batch building (geometry upload to GPU).
- `draw(uniforms, geometry)` — one-shot draw call.
- Sampler binding for texture uniforms.

#### `draw_shader.py` — Shader Decorators

Decorators that connect a `ShaderBuilder` instance to a Python draw callback function:
- `@draw_shader_auto(shader)` — infers primitive type from the shader.
- `@draw_shader_points(shader)` — point primitives.
- `@draw_shader_tris(shader)` — triangle primitives.
- `@draw_shader_lines(shader)` — line primitives.

`DrawShaderCallable` — the wrapper class returned by the decorators; handles the batch rebuild and draw dispatch.

#### `draw_codegen.py`

**`generate_draw_py(shader_builder, output_path)`** — introspects a `ShaderBuilder` and writes a ready-to-use `draw_*.py` file with stubs pre-filled with the correct uniform names and types. Saves time when iterating on shader code.

#### `glsl_parser.py`

Parses GLSL source strings and extracts `in`/`out`/`uniform` declarations. Converts them to `GPUShaderCreateInfo` attribute entries. Used internally by `ShaderBuilder` to avoid duplicating GLSL declarations in Python.

---

## `utils/`

General-purpose Python/Blender helpers. None of these register Blender types; they are pure utility libraries.

### Core Utilities

#### `class_utils.py`

- `get_subclasses(cls)` — return direct subclasses.
- `get_subclasses_recursive(cls)` — return all transitive leaf subclasses.
- `is_method_overridden(cls, base, method_name)` — check if a subclass actually overrides a method.

#### `op_return.py` — `OpReturn`

Frozenset constants for operator return values: `FINISHED`, `CANCELLED`, `RUNNING_MODAL`, `PASS_THROUGH`. Avoids magic string literals in operator code.

#### `callback_utils.py`

- **`CallbackList`** — a list that can be called like a function; iterates and calls all registered callables.
- **`CallbackDict`** — a dict of callback lists keyed by an arbitrary key (e.g., context mode string). Used for status bar hints and tool draw handlers.

#### `wrap_fn.py`

**`wrap_function(target_object, method_name, pre_fn, post_fn)`** — monkey-patches a method on an arbitrary object; `pre_fn` is called before and `post_fn` after the original. Returns an `unregister` callable that restores the original method. Used by `tool_switch.py` to hook Blender's tool activation.

#### `mouse_utils.py` — `ModalMouse`

Tracks mouse state inside a modal operator across events:
- `position`, `delta`, `velocity` — current cursor state.
- `path` — list of positions recorded over the modal's lifetime.
- `analyze_path_shape()` — classifies the path as `LINE`, `CIRCLE`, `ZIGZAG`, etc.
- Uses RDP (Ramer–Douglas–Peucker) simplification and Savitzky–Golay smoothing internally.

#### `raycast_utils.py`

- **`RaycastInfo`** — result of a scene raycast: hit location, normal, face index, object.
- **`raycast_scene(context, mouse_pos)`** — wrapper around `context.scene.ray_cast`.
- **`raycast_object(context, obj, mouse_pos)`** — per-object raycast using the evaluated depsgraph mesh.
- **`BVHTreeRaycastInfo`** / **`BVHTreeRaycaster`** — caches a `mathutils.bvhtree.BVHTree` per object and performs fast repeated raycasts against it. The BVHTree is rebuilt only when the object's mesh changes.

#### `view_utils.py`

- `get_view_vector(context)` — camera/view forward direction.
- `get_ray_origin(context, mouse_pos)` — world-space ray origin from a 2D mouse position.
- `is_navigating(context)` — returns `True` while the user is orbiting/panning/zooming, useful for skipping expensive operations.

#### `math_utils.py`

Vector angle, dot product, normalization, and clamping helpers not covered by `mathutils` defaults.

#### `geom_utils.py`

3D geometry helpers:
- `is_face_facing_view(face_normal, view_vector)` — backface test.
- `CM_PlaneProject(plane_point, plane_normal)` — context manager that projects a 3D point onto a plane.
- `get_n_points_around(center, radius, n, plane_normal)` — evenly-spaced points around a circle in 3D.
- Segment-to-segment and point-to-segment distance functions.

#### `object.py`

- `is_visible(obj, context)` — checks all viewport visibility flags.
- `has_polygons(obj)` — quick check for mesh data.
- `get_bbox_min_max(obj)` — world-space bounding box extremes.
- `get_mesh_objects(context)` — all visible mesh objects in the scene.

#### `cursor.py`

**`Cursor`** — enum of Blender's `context.window.cursor_set` values (`DEFAULT`, `CROSSHAIR`, `MOVE_X`, `KNIFE`, …). Helpers for setting and restoring the cursor during modal operations.

#### `falloff.py`

**`FalloffType`** — enum of common falloff curves: `LINEAR`, `SMOOTH`, `SPHERE`, `ROOT`, `SHARP`, `CONSTANT`. Each variant implements `evaluate(t)` returning a `[0, 1]` value for a normalised input `t`. Used for brush-style influence falloff in sculpt/paint tools.

---

### `bm/` — BMesh Operations

Topology-level operations on `bmesh.BMesh` objects. All functions receive an open BMesh and return modified geometry.

| File | Key operations |
|---|---|
| `intersect.py` | Intersect edges/faces at a plane or curve; split geometry at intersection points. |
| `fill.py` | `grid_fill_between_equivalent_edge_loops` — fill the gap between two parallel edge loops with a quad grid. |
| `move.py` / `move_step.py` | Slide verts/edges along their topology; `QuadRetopoMove` for retopology-style sliding. |
| `smooth.py` | `QuadRetopoSmooth` — Laplacian-style smoothing constrained to quad topology. |
| `shortest_path.py` | `get_shortest_path_between_verts` — Dijkstra on the mesh graph; returns a list of edge indices. |
| `snap.py` | Snap BMesh vertices to a target surface via raycast or nearest-point projection. |
| `tweak.py` | Small positional adjustments of selected elements; handles vert/edge/face modes. |

---

### `geometry/` — Geometry Algorithms

Pure Python (and optionally `shapely`) geometry algorithms operating on 2D or 3D point sets.

| File | Key operations |
|---|---|
| `bbox.py` | Bounding box construction, containment tests, overlap checks for 2D/3D boxes. |
| `intersect.py` | Segment–segment, line–circle, and ray–AABB intersection tests. |
| `interpolate.py` | Catmull–Rom and linear interpolation along a polyline with arc-length parameterisation. |
| `savgol.py` | Savitzky–Golay filter for smoothing a sequence of 2D/3D points (noise reduction on mouse paths). |
| `rpd.py` | Ramer–Douglas–Peucker polyline simplification. |
| `shapely.py` | Optional wrappers around the `shapely` library for 2D polygon boolean operations (union, difference, intersection). Gracefully absent if `shapely` is not installed. |

---

## Cross-cutting Patterns

### 1. `BType` + `tag_register`

Every Blender class the framework manages subclasses `BType`. `tag_register()` is the designated place to declare properties, keymaps, sockets, or any setup that must happen after the class body is parsed but before Blender registration. Because Python class body execution happens at import time, `tag_register()` allows deferred, ordered setup.

### 2. `BType.decorator()`

`decorator(**kwargs)` returns a new class that can be used as a base class, pre-configured with a specific combination of `bl_space_type`, `bl_region_type`, `bl_options`, etc. This is how `bl_types.py` creates the named presets (`Panel.VIEW_3D_SIDEBAR`, `Operator.UNDO`, …) from a single generic base.

### 3. Dynamic type construction

Several places use `type(name, bases, namespace)` to synthesise Blender types at registration time:
- The MASTER `PropertyGroup` per data-block type.
- Multi-tool shared operator and gizmo group.
- Macro pre/post operator wrappers.
- `AllInOneTool` generated operator.

This keeps the number of hand-written Blender classes minimal while satisfying Blender's requirement for unique concrete types.

### 4. Callback infrastructure

`CallbackList` and `CallbackDict` (from `utils/callback_utils.py`) are used throughout:
- `tool_switch.py` — enter/exit callbacks per tool.
- `tool_statusbar.py` — hint strings per context mode.
- `tool_draw.py` — draw handlers per tool.

`wrap_function` provides the hook point into Blender internals without monkey-patching globally.

### 5. Raycast triad

Three complementary raycasting strategies share the same `RaycastInfo` result type:
- **Scene raycast** — general purpose; uses `bpy.context.scene.ray_cast`.
- **Object raycast** — per-object, respects modifiers via the depsgraph.
- **BVHTree raycast** — fastest for repeated queries on a single object; tree is cached and invalidated on mesh change.

Modal operators and tools receive all three results pre-computed each event via the shared specs system.

### 6. GPU drawing pipeline

The framework provides three levels of abstraction:
1. **`imm_2d` / `imm_3d`** — one-liner drawing functions for common primitives.
2. **`ShaderBuilder`** — reusable shader + batch management for custom GLSL.
3. **`@draw_shader_*` decorators** — bind a `ShaderBuilder` directly to a Python draw function with no boilerplate.
