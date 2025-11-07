## Extracción y unión de tablas continuas (tablasContinuas.py)

Este pequeño servicio extrae tablas de archivos PDF usando Camelot, detecta tablas que están continuadas en páginas consecutivas y las une en DataFrames únicos. Finalmente convierte cada tabla a formato Markdown y genera un JSON con metadatos listo para consumir.

### Características principales
- Extrae tablas usando Camelot (`lattice` o `stream`).
- Detecta tablas que continúan en páginas consecutivas mediante comparación de encabezados y número de columnas.
- Une automáticamente grupos de tablas continuadas y normaliza columnas.
- Convierte cada tabla final a Markdown seguro (escapa `|`, trunca textos largos) y genera `output/tablas_pdf.json`.
- Expone un endpoint HTTP para procesar PDFs de forma sencilla.

---

### Requisitos
- Python 3.8+
- Paquetes Python (recomendado instalar en un venv):
  - camelot-py[cv]
  - pandas
  - numpy
  - flask
  - fuzzywuzzy
  - python-Levenshtein

- Ghostscript (en Windows instalar y añadir al PATH) — Camelot usa Ghostscript como backend para algunas operaciones.

Ejemplo de `pip` (ejecutar desde el entorno virtual):

```powershell
py -3 -m pip install "camelot-py[cv]" pandas numpy flask fuzzywuzzy python-Levenshtein
```

Si estás en Windows, instala Ghostscript desde:
https://www.ghostscript.com/ y reinicia la terminal. Asegúrate de que el ejecutable `gswin64c.exe` (o similar) esté en el PATH.

---

### ¿Qué hace `tablasContinuas.py`?

- `extract_tables_with_meta(pdf_path, pages, flavor)`: extrae tablas y devuelve metadatos por tabla (DataFrame en memoria, página, bbox, método de extracción).
- `should_merge(...)` y `header_similarity(...)`: deciden si dos tablas en páginas consecutivas son la misma tabla continuada, comparando encabezados normalizados y número de columnas.
- `merge_multiple_tables(...)`: une varias tablas continuadas en un único DataFrame, alineando columnas y deduplicando nombres.
- `df_to_markdown(df)`: convierte un DataFrame en una tabla Markdown segura.
- Endpoint `/procesar_pdf` (POST): recibe JSON con `pdf_path`, procesa el PDF y escribe `output/tablas_pdf.json`.

---

### Ejecución (modo desarrollo)

1. Activar un entorno virtual (opcional pero recomendado):

```powershell
# crear y activar venv (Windows PowerShell)
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instalar dependencias (ver sección Requisitos).

3. Ejecutar el servidor Flask:

```powershell
py .\tablasContinuas.py
# o
python .\tablasContinuas.py
```

El servidor levantará en http://127.0.0.1:5000 por defecto.

---

### Ejemplo de petición (PowerShell)

```powershell
# Usando Invoke-RestMethod para procesar un PDF local
Invoke-RestMethod -Uri http://127.0.0.1:5000/procesar_pdf -Method Post -ContentType 'application/json' -Body (@{pdf_path='C:\ruta\a\tu.pdf'} | ConvertTo-Json)
```

Respuesta esperada (JSON):

```
{
  "success": true,
  "message": "Extracción y unión completada.",
  "output_file": "output/tablas_pdf.json",
  "total_tables": 3
}
```

---

### Formato de salida (`output/tablas_pdf.json`)

Cada elemento del JSON tiene la estructura:

```json
{
  "id": "<uuid>",
  "type": "table",
  "shape": [[rows1, cols1], [rows2, cols2], ...],
  "document_id": "tu.pdf",
  "pages": [1,2],
  "bbox": [ [x1,y1,x2,y2], ... ],
  "extract_method": "lattice",
  "table_markdown": "| **col1** | **col2** |\n| --- | --- |\n| valor1 | valor2 |"
}
```

`table_markdown` contiene la tabla final en formato Markdown (encabezados en negrita y filas separadas con `|`).

---

### Buenas prácticas y recomendaciones
- Si tienes tablas sin bordes, prueba `flavor='stream'`; para tablas con líneas, `lattice` suele ser mejor.
- Revisa `output/tablas_pdf.json` y las tablas Markdown para validar que la unión fue correcta.
- Si observas columnas desalineadas tras la unión, considera inspeccionar manualmente los `dataframe` originales guardando también la versión raw para auditoría.

---

### Troubleshooting rápido
- Error al importar Camelot o al ejecutar: revisa que Ghostscript esté instalado y que tengas las dependencias de OpenCV si usas `camelot-py[cv]`.
- Camelot no detecta tablas: prueba cambiar `flavor`, ajustar `line_scale` o preprocesar el PDF (convertir a imágenes con mayor DPI).

---

### Próximos pasos sugeridos
- Añadir un `requirements.txt` y un script `make` o `scripts` para instalación rápida.
- Guardar también las tablas originales (raw) en el JSON para trazabilidad.
- Implementar tests unitarios para `header_similarity` y `merge_multiple_tables`.

----

Si quieres, puedo:
- Crear `requirements.txt` y un pequeño `scripts/install.ps1` para automatizar la instalación en Windows.
- Agregar logging y manejo de errores más detallado en `tablasContinuas.py`.

Dime cuál de estas mejoras prefieres y la implemento.
