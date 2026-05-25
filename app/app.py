import streamlit as st
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

st.set_page_config(page_title="Knowledge Graph Explorer", layout="wide")
st.title("🔬 Explorador de Ciencia Abierta")
st.write("Consulta en tiempo real al Grafo de Conocimiento alojado en Fuseki.")

# Conectar a Fuseki
sparql = SPARQLWrapper("http://localhost:3030/ds/query")

# Consulta SPARQL Genérica: Top 10 elementos más conectados en tu grafo
query = """
SELECT ?objeto (COUNT(?sujeto) as ?conexiones)
WHERE {
  ?sujeto ?predicado ?objeto .
  FILTER(isIRI(?objeto)) # Solo cogemos entidades, no textos largos
}
GROUP BY ?objeto
ORDER BY DESC(?conexiones)
LIMIT 10
"""

try:
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    # Procesar datos y limpiar un poco los enlaces (URIs) para que quede bonito
    data = []
    for r in results["results"]["bindings"]:
        nombre_bruto = r["objeto"]["value"]
        # Quedarnos solo con la parte final del enlace para que sea legible
        nombre_limpio = nombre_bruto.split("/")[-1].split("#")[-1]
        data.append({"Entidad": nombre_limpio, "Conexiones": int(r["conexiones"]["value"])})
    
    df = pd.DataFrame(data)
    
    if not df.empty:
        st.subheader("📊 Top 10 Entidades Principales del Grafo")
        st.bar_chart(df.set_index("Entidad"))
        st.dataframe(df)
    else:
        st.warning("El grafo parece estar completamente vacío. Comprueba si el archivo .ttl pesa más de 0 KB.")
except Exception as e:
    st.error(f"Error conectando a Fuseki: {e}")