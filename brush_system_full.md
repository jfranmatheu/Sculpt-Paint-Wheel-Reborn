# 🧠 Sistema Completo de Brush Libraries + Cache + GPU Previews

## 🎯 Objetivo

Diseñar un sistema robusto, escalable y eficiente para:

-   Gestionar Brush Libraries desde Asset Libraries del usuario
-   Cachear metadata y previews
-   Renderizar previews eficientemente en GPU
-   Detectar cambios automáticamente
-   Minimizar uso de memoria y tiempo de carga

------------------------------------------------------------------------

# 🧱 Arquitectura General

El sistema se compone de:

1.  **Asset Libraries (fuente de verdad)**
2.  **Proceso de sincronización (background)**
3.  **Cache en disco**
4.  **Índice global (`libraries.json`)**
5.  **Carga lazy en runtime (GPU)**

------------------------------------------------------------------------

# 📚 Conceptos clave

## Brush Library

-   Representa un Asset Library del usuario

## Wheel Page

-   Página de UI con máximo **20 brushes**
-   Cada brush tiene:
    -   `page`
    -   `index`

## Cache

-   Persistente en disco
-   Contiene:
    -   metadata
    -   previews comprimidas

------------------------------------------------------------------------

# 🔄 Sincronización

## Descripción

Proceso que:

-   Detecta nuevas librerías
-   Detecta cambios en `.blend`
-   Regenera metadata
-   Regenera previews
-   Actualiza `libraries.json`

## Ejecución

-   Blender en background
-   Script Python dedicado

------------------------------------------------------------------------

# 🔍 Detección de cambios

``` python
stat = blend_file.stat()
mtime = stat.st_mtime
size = stat.st_size
```

Se considera modificado si cambia: - `mtime` - `size`

------------------------------------------------------------------------

# ⚙️ Flujo de sincronización

1.  Obtener asset libraries:

``` python
bpy.context.preferences.filepaths.asset_libraries
```

2.  Buscar `.blend`:

``` python
[fp for fp in library_path.rglob("*.blend") if fp.is_file()]
```

3.  Cargar librería:

``` python
with bpy.data.libraries.load(str(blend_file), link=False, assets_only=True) as (data_from, data_to):
    data_to.brushes = data_from.brushes
```

4.  Iterar brushes y extraer:

-   `name`
-   `type`
-   `wheel.page`
-   `wheel.index`
-   preview

------------------------------------------------------------------------

# 🆔 Sistema de IDs (hashing)

## library_id

``` python
hash(library_path)
```

## blend_id

``` python
hash(blend_path + str(mtime) + str(size))
```

## brush_id

``` python
hash(blend_path + brush.name)
```

Ventajas: - Independiente de nombres - Permite invalidación automática -
Evita colisiones lógicas

------------------------------------------------------------------------

# 🖼️ Procesamiento de previews

## Validación

``` python
preview = brush.preview_ensure()
w, h = preview.image_size

assert w > 0 and h > 0
assert len(pixels) == w * h * 4
```

------------------------------------------------------------------------

## Conversión (float → uint8)

``` python
data = bytes(
    int(max(0.0, min(1.0, p)) * 255)
    for p in pixels_f
)
```

------------------------------------------------------------------------

## Compresión

``` python
compressed = zlib.compress(data, 6)
```

------------------------------------------------------------------------

## Hash del preview

``` python
import hashlib
key = f"{library.name}|{blend_file}|{brush.name}"
hash_id = hashlib.sha1(key.encode()).hexdigest()
```

------------------------------------------------------------------------

## Guardado

``` python
with open(f"{hash_id}.bin", "wb") as f:
    f.write(w.to_bytes(4, 'little'))
    f.write(h.to_bytes(4, 'little'))
    f.write(compressed)
```

------------------------------------------------------------------------

## Carga

``` python
with open(f"{hash_id}.bin", "rb") as f:
    w = int.from_bytes(f.read(4), 'little')
    h = int.from_bytes(f.read(4), 'little')
    compressed = f.read()

data = zlib.decompress(compressed)
```

------------------------------------------------------------------------

# 🎮 Uso en GPU

``` python
from gpu.types import GPUTexture

texture = GPUTexture((w, h), format='RGBA8', data=data)
```

-   No requiere reconversión a float
-   Valores automáticamente normalizados

------------------------------------------------------------------------

# 📄 JSON Global (`libraries.json`)

## Propósito

-   Índice central de todo el sistema
-   Fuente de verdad para metadata

## Schema completo

``` json
{
  "version": 1,
  "generated_at": 1710000000,
  "libraries": {
    "<library_id>": {
      "name": "Library Name",
      "path": "/abs/path",
      "last_scan": 1710000000,
      "builtin": false,
      "blends": {
        "<blend_id>": {
          "file_name": "file.blend",
          "path": "/abs/path/file.blend",
          "mtime": 1710000000,
          "size": 123456,
          "brush_count": 10,
          "brushes": {
            "<brush_id>": {
              "name": "Draw",
              "type": "SCULPT",
              "wheel": {
                "page": 0,
                "index": 0
              },
              "preview": {
                "path": "previews/ab/cd/hash.bin",
                "width": 128,
                "height": 128,
                "format": "RGBA8",
                "compression": "zlib"
              }
            }
          }
        }
      }
    }
  }
}
```

------------------------------------------------------------------------

# ⭐ Librerías builtin (Essentials)

``` json
"builtin": true
```

Características: - Preprocesadas - Inmutables - No requieren sync - Solo
lectura

------------------------------------------------------------------------

# 📂 Estructura en disco

    cache/
    ├── libraries.json
    ├── previews/
    │   ├── ab/
    │   │   ├── cd/
    │   │   │   ├── hash.bin

## Generación de paths

``` python
h = sha1(...)
path = f"previews/{h[:2]}/{h[2:4]}/{h}.bin"
```

------------------------------------------------------------------------

# ⚡ Runtime

## Lazy Loading (CRÍTICO)

-   No cargar todas las previews al inicio
-   Cargar solo cuando:
    -   la brush es visible
    -   se necesita en UI

Beneficios: - menor uso de RAM - menor tiempo de arranque - mejor
rendimiento GPU

------------------------------------------------------------------------

# 🔄 Integración con Blender

## Handler `load_post`

-   Se ejecuta al abrir archivo
-   No persistente

### Responsabilidades:

1.  Revisar asset libraries
2.  Comparar estado
3.  Detectar cambios
4.  Lanzar sync si necesario

------------------------------------------------------------------------

# 🚀 Posibles mejoras futuras

-   Texture Atlas (optimización GPU)
-   Compresión alternativa (LZ4)
-   Sync incremental (diff por brush)
-   Cache en memoria con LRU

------------------------------------------------------------------------

# ✅ Decisiones clave

  Área           Decisión
  -------------- ----------------------
  Metadata       JSON global
  Imágenes       Binarios comprimidos
  IDs            Hashing
  Invalidación   mtime + size
  Essentials     builtin
  GPU            RGBA8
  Carga          Lazy

------------------------------------------------------------------------

# 🧭 Resultado

Sistema: - Escalable (+100 previews) - Robusto - Eficiente en GPU -
Independiente de nombres - Preparado para producción
