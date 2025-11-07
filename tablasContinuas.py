import camelot
from flask import Flask, jsonify, request
import pandas as pd
import numpy as np
import json
# import uuid
from fuzzywuzzy import fuzz
import os
import re

app = Flask(__name__)

# --- EXTRACCIÓN CON METADATOS ---
def extract_tables_with_meta(pdf_path, pages="all", flavor="stream"):
    tables = camelot.read_pdf(pdf_path, pages=pages, flavor=flavor, line_scale=40)
    print(tables.n)
    extracted = []
    for i, t in enumerate(tables):
        df = t.df.copy()
        # Detectar header
        if all(isinstance(x, str) for x in df.iloc[0]):
            df.columns = df.iloc[0]
            df = df[1:]

        meta = {
            "page": int(t.page),
            "shape": df.shape,
            "bbox": getattr(t, "_bbox", None),
            "extract_method": flavor,
            "dataframe": df
        }
        extracted.append(meta)
    return extracted
# # --- LIMPIAR Y NORMALIZAR ENCABEZADOS ---
# def normalize_header(col):
#     """Normaliza texto de encabezado para comparación más estable."""
#     col = str(col).lower().strip()
#     col = re.sub(r'[^a-z0-9áéíóúüñ ]', '', col)
#     col = re.sub(r'\s+', ' ', col)
#     return col

# # --- FUNCIONES DE SIMILITUD ---
# def header_similarity(df1, df2):
#     """Devuelve similitud de encabezados entre 0 y 1 (más tolerante)."""
#     cols1 = [normalize_header(c) for c in df1.columns]
#     cols2 = [normalize_header(c) for c in df2.columns]
    
#     if not cols1 or not cols2:
#         return 0.0

#     # Calcula similitud columna a columna (más robusto que una sola cadena)
#     scores = []
#     for c1 in cols1:
#         best = max(fuzz.partial_ratio(c1, c2) for c2 in cols2)
#         scores.append(best)

#     # Promedio normalizado entre 0 y 1
#     return sum(scores) / (len(scores) * 100)

# def should_merge(table_a, table_b, sim_threshold=0.7):
#     """Decide si dos tablas son continuas (páginas consecutivas + encabezados similares)."""
#     # Verificar páginas consecutivas
#     if int(table_b["page"]) != int(table_a["page"]) + 1:
#         return False

#     # Verificar número de columnas similar (tolerancia de ±1)
#     cols_a = table_a["dataframe"].shape[1]
#     cols_b = table_b["dataframe"].shape[1]
#     if abs(cols_a - cols_b) > 1:
#         return False

#     # Calcular similitud
#     sim = header_similarity(table_a["dataframe"], table_b["dataframe"])
#     return sim >= sim_threshold

# # --- FUNCIÓN PARA UNIR VARIAS TABLAS CONTINUADAS ---
# def merge_multiple_tables(tables):
#     """Une una lista de tablas continuadas en un único DataFrame ."""
#     dfs = []

#     for t in tables:
#         df = t["dataframe"].copy()

#         # --- 1. Deduplicar nombres de columnas manualmente ---
#         seen = {}
#         new_cols = []
#         for col in df.columns:
#             col_str = str(col).strip()
#             if col_str in seen:
#                 seen[col_str] += 1
#                 new_cols.append(f"{col_str}_{seen[col_str]}")
#             else:
#                 seen[col_str] = 0
#                 new_cols.append(col_str)
#         df.columns = new_cols
#         if df.columns.isnull().any():
#             df.columns = [f"col_{i}" for i in range(df.shape[1])]


#         dfs.append(df)

#     # --- 2. Alinear columnas entre todas las tablas ---
#     all_cols = sorted(set().union(*[df.columns for df in dfs]))
#     dfs = [df.reindex(columns=all_cols) for df in dfs]

#     # --- 3. Concatenar sin errores ---
#     merged_df = pd.concat(dfs, ignore_index=True, sort=False)

#     return {
#         "shape": [t["shape"] for t in tables],
#         "pages": [t["page"] for t in tables],
#         "bbox": [t["bbox"] for t in tables],
#         "extract_method": tables[0]["extract_method"],
#         "dataframe": merged_df
#     }



# # --- DETECTAR SECUENCIAS Y UNIR ---
# def merge_tables_across_pages(tables_meta, sim_threshold=0.7):
#     """Detecta grupos de tablas continuadas y las une en una sola."""
#     if not tables_meta:
#         return []
    
#     tables_sorted = sorted(tables_meta, key=lambda x: x["page"])
#     merged_results = []
#     current_group = [tables_sorted[0]]

#     for i in range(1, len(tables_sorted)):
#         prev = tables_sorted[i - 1]
#         curr = tables_sorted[i]

#         if should_merge(prev, curr, sim_threshold):
#             current_group.append(curr)
#         else:
#             # cerrar grupo actual
#             if len(current_group) > 1:
#                 merged_results.append(merge_multiple_tables(current_group))
#             else:
#                 merged_results.append(current_group[0])
#             current_group = [curr]

#     # último grupo
#     if current_group:
#         if len(current_group) > 1:
#             merged_results.append(merge_multiple_tables(current_group))
#         else:
#             merged_results.append(current_group[0])

#     return merged_results

# --- FUNCIONES DE SIMILITUD ---
def header_similarity(df1, df2):
    """Devuelve similitud de encabezados entre 0 y 1."""
    h1 = " | ".join(map(str, df1.columns))
    h2 = " | ".join(map(str, df2.columns))
    return fuzz.partial_ratio(h1.lower(), h2.lower()) / 100.0

def should_merge(table_a, table_b, sim_threshold=0.7):
    """Decide si dos tablas son continuas."""
    if int(table_b["page"]) != int(table_a["page"]) + 1:
        return False
    same_cols = table_a["dataframe"].shape[1] == table_b["dataframe"].shape[1]
    sim = header_similarity(table_a["dataframe"], table_b["dataframe"])
    return same_cols and sim >= sim_threshold

# --- FUNCIÓN PARA UNIR VARIAS TABLAS CONTINUADAS ---
def merge_multiple_tables(tables):
    """Une una lista de tablas continuadas en un único DataFrame (robusta y compatible)."""
    dfs = []

    for t in tables:
        df = t["dataframe"].copy()

        # --- 1. Deduplicar nombres de columnas manualmente ---
        seen = {}
        new_cols = []
        for col in df.columns:
            col_str = str(col).strip()
            if col_str in seen:
                seen[col_str] += 1
                new_cols.append(f"{col_str}_{seen[col_str]}")
            else:
                seen[col_str] = 0
                new_cols.append(col_str)
        df.columns = new_cols

        dfs.append(df)

    # --- 2. Alinear columnas entre todas las tablas ---
    all_cols = sorted(set().union(*[df.columns for df in dfs]))
    dfs = [df.reindex(columns=all_cols) for df in dfs]

    # --- 3. Concatenar sin errores ---
    merged_df = pd.concat(dfs, ignore_index=True, sort=False)

    return {
        "shape": [t["shape"] for t in tables],
        "pages": [t["page"] for t in tables],
        "bbox": [t["bbox"] for t in tables],
        "extract_method": tables[0]["extract_method"],
        "dataframe": merged_df
    }

# --- DETECTAR SECUENCIAS Y UNIR ---
def merge_tables_across_pages(tables_meta, sim_threshold=0.7):
    """Detecta grupos de tablas continuadas y las une en una sola."""
    tables_sorted = sorted(tables_meta, key=lambda x: x["page"])
    merged_results = []
    current_group = [tables_sorted[0]]

    for i in range(1, len(tables_sorted)):
        prev = tables_sorted[i - 1]
        curr = tables_sorted[i]

        if should_merge(prev, curr, sim_threshold):
            current_group.append(curr)
        else:
            # cerrar grupo actual
            if len(current_group) > 1:
                merged_results.append(merge_multiple_tables(current_group))
            else:
                merged_results.append(current_group[0])
            current_group = [curr]

    # último grupo
    if current_group:
        if len(current_group) > 1:
            merged_results.append(merge_multiple_tables(current_group))
        else:
            merged_results.append(current_group[0])

    return merged_results

# --- CONVERTIR A MARKDOWN + JSON FINAL ---
def df_to_markdown(df: pd.DataFrame, max_rows: int = None) -> str:
    """
    Convierte un DataFrame a una tabla Markdown bien formateada.
    - Escapa caracteres especiales.
    - Muestra encabezados en negrita.
    - Maneja NaN y valores largos.
    - Permite limitar el número de filas mostradas.
    """

    # --- Copia segura ---
    df = df.copy()

    # --- Limitar filas si se solicita ---
    if max_rows is not None and len(df) > max_rows:
        df = df.head(max_rows)
        df.loc["..."] = ["..." for _ in df.columns]

    # --- Reemplazar NaN o None ---
    df = df.replace({np.nan: "", None: ""})

    # --- Función para limpiar texto ---
    def clean_text(value):
        text = str(value).replace("\n", " ").replace("|", "\\|").strip()
        if len(text) > 100:
            text = text[:97] + "..."
        return text

    # --- Encabezados en negrita ---
    header = "| " + " | ".join(f"**{clean_text(col)}**" for col in df.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(df.columns)) + " |"

    # --- Filas ---
    rows = []
    for _, row in df.iterrows():
        cells = [clean_text(v) for v in row]
        rows.append("| " + " | ".join(cells) + " |")

    # --- Unir todo ---
    markdown_table = f"{header}\n{separator}\n" + "\n".join(rows)
    return markdown_table

# --- CONVERTIR A JSON
def build_final_json(tables_merged, pdf_path):
    result = []
    id = 0
    for t in tables_merged:
        df = t["dataframe"]
        markdown_table = df_to_markdown(df)
        id += 1
        result.append({
            "id": f"{id}",
            "type": "table",
            "shape": t["shape"],
            "document_id": pdf_path.split("/")[-1],
            "pages": t["pages"] if "pages" in t else [t["page"]],
            "bbox": t.get("bbox", None),
            "extract_method": t["extract_method"],
            "table_markdown": markdown_table
        })
    return result

# pdf_path = "data/Benchmark.pdf"

# --- RUTA PRINCIPAL
@app.route("/procesar_pdf", methods=['POST'])
def existencia_tablas():

    try:

        data = request.get_json()
        if not data: 
            return jsonify({'success': False, 'message': 'No se recibió JSON en la petición'}), 400

        pdf_path = data.get('pdf_path')

        if not pdf_path:
            return jsonify({'success': False, 'message' : "Falta el campo 'pdf_path' en el JSON."}), 400

        if not os.path.exists(pdf_path):
            return jsonify({"success": False, "message": f"el archivo '{pdf_path}' no existe"}), 404
        # 1 Extraer todas las tablas
        tables_meta = extract_tables_with_meta(pdf_path, pages="all", flavor="lattice")

        # 2️ Detectar y unir secuencias continuadas
        merged_tables = merge_tables_across_pages(tables_meta)

        # 3️ Convertir a JSON + Markdown
        final_json = build_final_json(merged_tables, pdf_path)

        # 4️ Guardar resultado
        output_path = 'output/tablas_pdf.json'
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_json, f, ensure_ascii=False, indent=2)

        return jsonify({
            "success": True,
            "message": "Extracción y unión completada.",
            "output_file": output_path,
            "total_tables": len(final_json)
        }), 200
    except Exception as e:
        # capturar cualquier error
        return jsonify({
            "success": False,
            "message": f"Ocurrio un error inesperado: {str(e)}"
        }), 400

if __name__ == "__main__":
    app.run(debug=True)
