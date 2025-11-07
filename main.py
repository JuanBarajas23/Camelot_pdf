# import camelot

# tablas_detectadas = camelot.read_pdf('data/Figuras_Tablas.pdf', flavor='lattice', )

# print(tablas_detectadas)


# Requiere: camelot-py, pandas, fuzzywuzzy (pip install camelot-py[cv] pandas fuzzywuzzy python-Levenshtein)

import camelot
import pandas as pd
from fuzzywuzzy import fuzz
import uuid
import json

def df_to_markdown(df: pd.DataFrame) -> str:
    #Convierte un DataFrame en formato tabla Markdown
    header = "| " + " | ".join(df.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(df.columns)) + " |"
    rows = "\n".join("| " + " | ".join(map(str, row)) + " |" for row in df.values)
    return f"{header}\n{separator}\n{rows}"

def extract_tables_as_json(pdf_path: str, pages="all", flavor="stream"):
    tables = camelot.read_pdf(pdf_path, pages=pages, flavor=flavor, process_background=True, line_scale=40)
    results = []

    for i, table in enumerate(tables):
        df = table.df.copy()

        # Usa primera fila como encabezado si parece serlo
        if all(isinstance(x, str) for x in df.iloc[0]):
            df.columns = df.iloc[0]
            df = df[1:]

        markdown_table = df_to_markdown(df)

        results.append({
            "type": "table",
            "document_id": pdf_path.split("/")[-1],
            "pages": [table.page],
            "shape": df.shape,
            "bbox": getattr(table, "_bbox", None),
            "extract_method": flavor,
            # "columns": list(df.columns),
            # "rows": df.values.tolist(),
            "table_markdown": markdown_table
        })

    return results

def header_from_df(df):
    # heurística simple: asume primera fila como header si tiene strings no-nulos
    header = list(df.iloc[0].astype(str).str.strip())
    # si detectas que primera fila parecen datos numéricos, busca fila con más strings
    return header

def header_similarity(h1, h2):
    # compara concatenación o por columnas
    s1 = " | ".join([str(x) for x in h1])
    s2 = " | ".join([str(x) for x in h2])
    return fuzz.partial_ratio(s1.lower(), s2.lower()) / 100.0  # 0..1

def should_merge(table_meta_a, table_meta_b, thresh=0.7):
    # 1) páginas contiguas?
    pa = int(table_meta_a['page'])
    pb = int(table_meta_b['page'])
    if pb != pa + 1:
        return False
    # 2) header similarity
    hA = header_from_df(table_meta_a['dataframe'])
    hB = header_from_df(table_meta_b['dataframe'])
    sim = header_similarity(hA, hB)
    # 3) column count or geometry check
    colsA = table_meta_a['shape'][1]
    colsB = table_meta_b['shape'][1]
    cols_ok = (colsA == colsB)
    return (sim >= thresh) or cols_ok

def merge_tables(table_meta_a, table_meta_b):
    # Preserva header de a, concatena filas de b (quitando header repetida)
    df_a = table_meta_a['dataframe']
    df_b = table_meta_b['dataframe']
    # Asume primera fila como header, concatena de la fila 1 en adelante
    merged_df = pd.concat([df_a, df_b.iloc[1:]], ignore_index=True)
    merged_meta = {
        "table_id": f"{uuid.uuid4().hex}",
        "pages": [table_meta_a['page'], table_meta_b['page']],
        "bbox": [table_meta_a.get('bbox'), table_meta_b.get('bbox')],
        "dataframe": merged_df
    }
    return merged_meta

# ejemplo de uso:
metas = extract_tables_as_json("data/sample-tables.pdf", pages="1", flavor='lattice')
print(metas)
# luego recorrer y aplicar should_merge en orden de páginas

# Guarda resultado como JSON
with open("tablas_extraidas.json", "w", encoding="utf-8") as f:
    json.dump(metas, f, ensure_ascii=False, indent=2)