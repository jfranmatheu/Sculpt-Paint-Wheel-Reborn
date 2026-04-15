- Cargaremos las brush libraries de los asset libraries del usuario.
- En vez de brush sets en el primer nivel, tendremos brush libraries y luego algo llamado 'wheel page'.
- Como recordatorio, cada brush library corresponde a un asset library del usuario.
- Al cargar los brush libraries, si se encuentra un nuevo brush library o se detecta que el user actualizó un brush library del que tenemos constancia (ejemplo se borraron y/o agregaron brushes nuevas), entonces se irá cacheando el data de estas brushes y brush lib, y se iran asignando un wheel page válido, sabiendo que solo se podrán tener una máximo de 20 brushes por página (pensando en que el widget wheel tiene paginación, con el scroll se puede controla el número de página y el número de página activo para cada set se estará trackeando y guardando en una propiedad).
  - Deteccion de cambios en Python, de fecha y de tamaño para evitar falsos positivos:
    ```py
    stat = blend_file.stat()
    mtime = stat.st_mtime
    size = stat.st_size
    ```
- Con un load_post handler (no persistente), haremos un check de las librerias del usuario para ver si alguna de ellas se ha modificado (checkeamos los timestamps de modificacion y tamaño de archivo guardados con los actuales de estos archivos de libreria con formato .blend). En caso de que hayan sido modificados, procederemos a actualizar nuestra base de datos y JSON para incluir las modificaciones realizadas por el usuario en las librerias afectadas.
- Las brushes de la libreria por defecto de Blender (essentials) la tendremos pre-procesada con su metadata por separado dentro del source del addon, para evitar procesar algo que es estable e inmutable al ser una libreria de brushes interna e incluida por el propio Blender. Esta libreria por defecto será agregada junto a todas las demás de la misma manera, para su acceso y visualizacion de la UI y en la wheel, eso sí, si capacidad de edición, ya que vendrá pre-configurada y lock.
- El proceso de cargar las brush libraries será conocido como proceso de "Sincronización", o para el usuario "Sync with Asset Library". El proceso se realizará llamando un script de Python ejecutado en una instancia de Blender en background, allí se procederá a:
  1. Iterar sobre `bpy.context.preferences.filepaths.asset_libraries`.
  2. Buscar los .blend files en cada asset library, con `[fp for fp in library_path.rglob("*.blend") if fp.is_file()]`.
  3. Iterar los blend files y cargar cada uno como libreria `with bpy.data.libraries.load(str(blend_file), link=False, assets_only=True) as (data_from, data_to):`, luego importar todas las brushes que sean assets `data_to.brushes = data_from.brushes`.
  4.. Iterar sobre las brushes importadas `data_to.brushes`, para cada brush guardaremos en un dict:
    - El nombre: `brush.name`.
    - El tipo: ejemplo 'SCULPT' si `brush.use_paint_sculpt`, 'IMAGE_PAINT' si `brush.use_paint_image`, etc.
    - El wheel page (indice empieza en 0, max 20 brushes por page).
    - Icon/preview `hash_id` + `width` + `height`: aquí tiene algo de complejidad:
      1. Obtener la preview de la brush con `preview = brush.preview_ensure()`.
      2. obtener las dimensiones de la brush icon image `w, h = preview.image_size` y asegurar de que sean > 0 `w > 0 and h > 0`.
      3. Obtener los pixels de la imagen con `list(preview.image_pixels_float[:])` y asegurar de que haya match entre el tamaño de pixels y el tamaño de la imagen y los canales de imagen `len(pixels) == w * h * 4`.
      4. Guardar esos pixels de forma comprimida:
        ```py
        import zlib

        preview = some_id.preview
        w, h = preview.image_size

        # float → uint8
        pixels_f = preview.image_pixels_float

        data = bytes(
            int(max(0.0, min(1.0, p)) * 255)
            for p in pixels_f
        )

        compressed = zlib.compress(data, 6)

        import hashlib

        key = f"{library.name}|{blend_file.stem}|{brush.name}"
        hash_id = hashlib.sha1(key.encode()).hexdigest()

        with open(f"{hash_id}.bin", "wb") as f:
            # header simple: ancho + alto (4 bytes cada uno)
            f.write(w.to_bytes(4, 'little'))
            f.write(h.to_bytes(4, 'little'))
            f.write(compressed)
        ```
        Para su carga + reconstruccion sería:
        ```py
        import zlib

        with open(f"{hash_id}.bin", "rb") as f:
            w = int.from_bytes(f.read(4), 'little')
            h = int.from_bytes(f.read(4), 'little')
            compressed = f.read()

        data = zlib.decompress(compressed)  # bytes RGBA uint8
        ```
        Y para su uso en GPU:
        ```py
        import gpu
        from gpu.types import GPUTexture

        texture = GPUTexture((w, h), format='RGBA8', data=data)
        ```
    5. Se guardará un libraries.json global a modo de indice global:
        ```json
        {
        "version": 1,
        "generated_at": 1710000000,

        "libraries": {
            "<library_id>": {
            "name": "User Visible Name",
            "path": "/absolute/path/to/library",
            "last_scan": 1710000000,

            "blends": {
                "<blend_id>": {
                "file_name": "file.blend",
                "path": "/absolute/path/to/file.blend",

                "mtime": 1710000000,
                "size": 12345678,

                "brush_count": 42,

                "brushes": {
                    "<brush_id>": {
                    "name": "Draw",
                    "type": "SCULPT",

                    "wheel": {
                        "page": 0,
                        "index": 3
                    },

                    "preview": {
                        "path": "previews/ab/cd/abcdef123456.bin",
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
    6. Ejemplo de estructura en disco, almacenado en `cache_dir = Path(bpy.utils.resource_path("USER")) / f"{addon_module_name}_data" / "cache"`
        ```
        cache/
        │
        ├── libraries.json
        ├── previews/
        │   ├── libA/
        │   │   ├── blend1/
        │   │   │   ├── brush1.bin
        │   │   │   ├── brush2.bin
        │   │   │   └── ...
        │   │   └── ...
        │   └── libB/
        ```
    7. Al dibujar las previas de las brushes via modulo gpu para los graficos de la wheel (brush ring widget), Lazy loading de previews, no cargar todos los .bin al iniciar; solo cuando la brush se muestra en la wheel.
Importante, - Las ÚNICAs SITUACIÓNES en la que sincronizaremos y regeneraremos el libraries.json y los .bin será cuando veamos que alguna librería ha cambiado respecto a nuestro metadata en funcion de fechas de modificacion y tamaño, y la unica situacion en la que estas comprobaciones se darán será con el handler de load_post o con acción explicita del usuario mediante un botón operator en la UI panel del addon. Sólo se actualizará el data de las librerias que hayan sido modificadas, manteniendo el data del resto de librerias no afectadas. Si regeneramos .bin de una libreria modificada, primero limpiaremos las previews previamente generadas (si hay alguna).