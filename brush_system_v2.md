# 🧠 Sistema Completo de Brush Libraries + Cache + GPU Previews (v2)

## 🎯 Objetivo

Sistema robusto para: - Gestionar brush libraries - Cachear previews -
Soportar preferencias de usuario persistentes - Sincronización
incremental segura

------------------------------------------------------------------------

# 🧱 Arquitectura

    Asset Libraries
          ↓
     Sync (background)
          ↓
     Cache (JSON + BIN)
          ↓
     Runtime (Lazy GPU)

------------------------------------------------------------------------

# 🔄 Sincronización

## ⚠️ Reglas CRÍTICAS

Las ÚNICAS situaciones donde ocurre sync:

1.  Handler `load_post`
2.  Acción explícita del usuario (botón UI)

------------------------------------------------------------------------

## 🔍 Detección de cambios

``` python
stat = blend_file.stat()
mtime = stat.st_mtime
size = stat.st_size
```

👉 Si cambian → se regenera SOLO esa librería

------------------------------------------------------------------------

## 🧹 Limpieza previa

Si una librería cambia:

-   ❗ Se eliminan previews `.bin` antiguos de ESA librería
-   ❗ Se regeneran nuevos

------------------------------------------------------------------------

## ♻️ Sync incremental

-   Solo se actualizan librerías modificadas
-   El resto permanece intacto

------------------------------------------------------------------------

# 🆔 IDs

``` python
library_id = hash(library_path)
blend_id = hash(blend_path + str(mtime) + str(size))
brush_id = hash(blend_path + brush.name)
```

------------------------------------------------------------------------

# 🖼️ Previews

-   float → uint8
-   zlib
-   GPU RGBA8

------------------------------------------------------------------------

# 📄 JSON Global

## 🔥 NUEVO: user_prefs persistente

Cada blend incluye:

``` json
"user_prefs": {}
```

### 📌 Propósito

Guardar preferencias específicas del usuario para ese brush set: -
página activa - orden personalizado - favoritos - flags UI

------------------------------------------------------------------------

## ⚠️ REGLA CRÍTICA

👉 `user_prefs` **NO se debe sobrescribir en sync**

------------------------------------------------------------------------

## 🔁 Estrategia de preservación

Durante sync:

1.  Cargar JSON existente
2.  Antes de sobrescribir un blend:
    -   copiar `user_prefs`
3.  Reinyectarlo en el nuevo data

------------------------------------------------------------------------

## 🧩 Schema completo

``` json
{
  "version": 1,
  "libraries": {
    "<library_id>": {
      "builtin": false,
      "blends": {
        "<blend_id>": {
          "mtime": 0,
          "size": 0,

          "user_prefs": {
            "active_page": 0,
            "custom_order": [],
            "favorites": []
          },

          "brushes": {}
        }
      }
    }
  }
}
```

------------------------------------------------------------------------

# 📂 Estructura

    cache/
    ├── libraries.json
    ├── previews/

------------------------------------------------------------------------

# ⚡ Runtime

## Lazy Loading

-   Cargar previews solo cuando visibles

------------------------------------------------------------------------

# 🔄 Handler

    load_post
       ↓
    check changes
       ↓
    if changed → sync

------------------------------------------------------------------------

# 📊 Diagrama Sync

    [Start]
       ↓
    Check Libraries
       ↓
    Compare mtime+size
       ↓
    Changed?
      /   \
    No     Yes
     |       ↓
     |   Clean previews
     |       ↓
     |   Rebuild data
     |       ↓
     | Preserve user_prefs
     |       ↓
     |   Update JSON
     ↓
    [End]

------------------------------------------------------------------------

# 📊 Diagrama user_prefs

    Old JSON
       ↓
    Extract user_prefs
       ↓
    Rebuild blend data
       ↓
    Inject user_prefs
       ↓
    Save JSON

------------------------------------------------------------------------

# ⭐ Builtin

``` json
"builtin": true
```

-   No sync
-   No cambios
-   Solo lectura

------------------------------------------------------------------------

# 🚀 Decisiones

  Área    Decisión
  ------- --------------
  Sync    Incremental
  Prefs   Persistentes
  JSON    Global
  GPU     RGBA8
  Cache   Binarios

------------------------------------------------------------------------

# 🧭 Resultado

Sistema: - Escalable - Determinista - Seguro ante sync - Persistente
para usuario
