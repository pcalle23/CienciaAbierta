import pandas as pd
import streamlit as st
from SPARQLWrapper import JSON, SPARQLWrapper

KG_PREFIX = "https://researchmap.es/ontology#"
DEFAULT_ENDPOINT = "http://127.0.0.1:3030/graph/query"

st.set_page_config(page_title="Global Research Mapping Explorer", layout="wide")

@st.cache_data(ttl=60)
def run_sparql(DEFAULT_ENDPOINT, query):
    sparql = SPARQLWrapper(DEFAULT_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    raw = sparql.query().convert()

    rows = []
    for row in raw.get("results", {}).get("bindings", []):
        parsed = {}
        for key, cell in row.items():
            parsed[key] = cell.get("value")
        rows.append(parsed)

    return pd.DataFrame(rows)


def get_topics(DEFAULT_ENDPOINT):
    query = f"""
    PREFIX kg: <{KG_PREFIX}>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?topic ?topicName (COUNT(DISTINCT ?paper) AS ?papers) (AVG(xsd:float(?prob)) AS ?avgProbability)
    WHERE {{
      ?paper a kg:Paper ;
             kg:hasTopicAssignment ?topicAssignment .
      ?topicAssignment kg:assignedTopic ?topic .
      OPTIONAL {{ ?topic kg:name ?topicName . }}
      OPTIONAL {{ ?topicAssignment kg:probability ?prob . }}
    }}
    GROUP BY ?topic ?topicName
    ORDER BY DESC(?papers)
    """
    df = run_sparql(DEFAULT_ENDPOINT, query)
    if df.empty:
        return df

    df["topicName"] = df["topicName"].fillna(df["topic"].str.split("/").str[-1].str.replace("_", " "))
    df["papers"] = pd.to_numeric(df["papers"], errors="coerce").fillna(0).astype(int)
    df["avgProbability"] = pd.to_numeric(df["avgProbability"], errors="coerce").fillna(0.0)
    return df


def get_country_leaders_for_topic(DEFAULT_ENDPOINT, topic_uri, limit_count):
    query = f"""
    PREFIX kg: <{KG_PREFIX}>

    SELECT ?country (COUNT(DISTINCT ?paper) AS ?papers) (COUNT(DISTINCT ?organization) AS ?organizations)
    WHERE {{
      ?paper a kg:Paper ;
             kg:hasTopicAssignment ?topicAssignment ;
             kg:hasAcknowledgement ?ack .
      ?topicAssignment kg:assignedTopic <{topic_uri}> .
      ?ack kg:acknowledgesOrganization ?organization .
      ?organization kg:country ?countryEntity .

      OPTIONAL {{ ?countryEntity kg:countryName ?countryName . }}
      OPTIONAL {{ ?countryEntity kg:countryCode ?countryCode . }}
      BIND(COALESCE(?countryName, ?countryCode) AS ?country)
    }}
    GROUP BY ?country
    ORDER BY DESC(?papers)
    LIMIT {int(limit_count)}
    """
    df = run_sparql(DEFAULT_ENDPOINT, query)
    if df.empty:
        return df

    df["papers"] = pd.to_numeric(df["papers"], errors="coerce").fillna(0).astype(int)
    df["organizations"] = pd.to_numeric(df["organizations"], errors="coerce").fillna(0).astype(int)
    return df


def get_collaboration_network_for_topic(DEFAULT_ENDPOINT, topic_uri, limit_count):
    query = f"""
    PREFIX kg: <{KG_PREFIX}>

    SELECT ?orgAName ?orgBName (COUNT(DISTINCT ?paper) AS ?sharedPapers)
    WHERE {{
      ?paper a kg:Paper ;
             kg:hasTopicAssignment ?topicAssignment ;
             kg:hasAuthor ?authorA, ?authorB .
      ?topicAssignment kg:assignedTopic <{topic_uri}> .

      ?authorA kg:affiliatedWith ?orgA .
      ?authorB kg:affiliatedWith ?orgB .
      ?orgA kg:officialName ?orgAName .
      ?orgB kg:officialName ?orgBName .

      FILTER(?orgA != ?orgB)
      FILTER(STR(?orgA) < STR(?orgB))
    }}
    GROUP BY ?orgAName ?orgBName
    ORDER BY DESC(?sharedPapers)
    LIMIT {int(limit_count)}
    """
    df = run_sparql(DEFAULT_ENDPOINT, query)
    if df.empty:
        return df

    df["sharedPapers"] = pd.to_numeric(df["sharedPapers"], errors="coerce").fillna(0).astype(int)
    return df


def get_similarity_for_topic(DEFAULT_ENDPOINT, topic_uri, limit_count):
    query = f"""
    PREFIX kg: <{KG_PREFIX}>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?source ?target ?sourceTitle ?targetTitle (MAX(xsd:float(?score)) AS ?similarity)
    WHERE {{
            ?sim a kg:SimilarityRelation ;
                     kg:sourcePaper ?source ;
           kg:targetPaper ?target ;
           kg:similarityScore ?score .

            {{
                ?source kg:hasTopicAssignment ?topicAssignmentSource .
                ?topicAssignmentSource kg:assignedTopic <{topic_uri}> .
            }}
            UNION
            {{
                ?target kg:hasTopicAssignment ?topicAssignmentTarget .
                ?topicAssignmentTarget kg:assignedTopic <{topic_uri}> .
            }}

      OPTIONAL {{ ?source kg:title ?sourceTitle . }}
      OPTIONAL {{ ?target kg:title ?targetTitle . }}
    }}
    GROUP BY ?source ?target ?sourceTitle ?targetTitle
    ORDER BY DESC(?similarity)
    LIMIT {int(limit_count)}
    """
    df = run_sparql(DEFAULT_ENDPOINT, query)
    if df.empty:
        return df

    df["similarity"] = pd.to_numeric(df["similarity"], errors="coerce").fillna(0.0)
    return df


def get_researchers_for_topic(DEFAULT_ENDPOINT, topic_uri, limit_count):
        query = f"""
        PREFIX kg: <{KG_PREFIX}>

        SELECT
            ?person
            (SAMPLE(?personNameValue) AS ?name)
            (SAMPLE(?orcidValue) AS ?orcid)
            (SAMPLE(?orgNameValue) AS ?affiliation)
            (GROUP_CONCAT(DISTINCT ?conceptValue; separator=", ") AS ?specialization)
            (COUNT(DISTINCT ?paper) AS ?papers)
            (AVG(?cites) AS ?avgCitations)
        WHERE {{
            ?paper a kg:Paper ;
                         kg:hasTopicAssignment ?topicAssignment ;
                         kg:hasAuthor ?person .
            ?topicAssignment kg:assignedTopic <{topic_uri}> .

            OPTIONAL {{ ?person kg:name ?personNameValue . }}
            OPTIONAL {{ ?person kg:orcid ?orcidValue . }}
            OPTIONAL {{
                ?person kg:affiliatedWith ?org .
                ?org kg:officialName ?orgNameValue .
            }}
            OPTIONAL {{ ?person kg:hasConcept ?conceptValue . }}
            OPTIONAL {{ ?paper kg:citedByCount ?cites . }}
        }}
        GROUP BY ?person
        ORDER BY DESC(?papers) DESC(?avgCitations)
        LIMIT {int(limit_count)}
        """
        df = run_sparql(DEFAULT_ENDPOINT, query)
        if df.empty:
                return df

        # Algunas variables OPTIONAL pueden no venir en los resultados.
        for col in ["person", "name", "orcid", "affiliation", "papers", "avgCitations"]:
            if col not in df.columns:
                df[col] = None
        if "specialization" not in df.columns:
            df["specialization"] = None

        df["name"] = df["name"].fillna(df["person"].str.split("/").str[-1].str.replace("_", " "))
        df["orcid"] = df["orcid"].fillna("N/A")
        df["affiliation"] = df["affiliation"].fillna("N/A")
        df["specialization"] = df["specialization"].fillna("N/A")
        df["papers"] = pd.to_numeric(df["papers"], errors="coerce").fillna(0).astype(int)
        df["avgCitations"] = pd.to_numeric(df["avgCitations"], errors="coerce").fillna(0.0)
        return df

def get_countries_overview(DEFAULT_ENDPOINT, limit_count=200):
        query = f"""
        PREFIX kg: <{KG_PREFIX}>

        SELECT ?country (COUNT(DISTINCT ?paper) AS ?papers) (COUNT(DISTINCT ?organization) AS ?organizations)
        WHERE {{
            ?paper a kg:Paper ;
                         kg:hasAcknowledgement ?ack .
            ?ack kg:acknowledgesOrganization ?organization .
            ?organization kg:country ?countryEntity .

            OPTIONAL {{ ?countryEntity kg:countryName ?countryName . }}
            OPTIONAL {{ ?countryEntity kg:countryCode ?countryCode . }}
            BIND(COALESCE(?countryName, ?countryCode) AS ?country)
        }}
        GROUP BY ?country
        ORDER BY DESC(?papers)
        LIMIT {int(limit_count)}
        """
        df = run_sparql(DEFAULT_ENDPOINT, query)
        if df.empty:
                return df

        df["papers"] = pd.to_numeric(df["papers"], errors="coerce").fillna(0).astype(int)
        df["organizations"] = pd.to_numeric(df["organizations"], errors="coerce").fillna(0).astype(int)
        return df


def get_entities_for_country(DEFAULT_ENDPOINT, country_value, limit_count=50):
        # Organizations
        org_q = f"""
        PREFIX kg: <{KG_PREFIX}>

        SELECT DISTINCT ?org ?orgName ?orgType WHERE {{
            ?org a kg:Organization .
            ?org kg:country ?countryEntity .
            OPTIONAL {{ ?countryEntity kg:countryName ?countryName . }}
            OPTIONAL {{ ?countryEntity kg:countryCode ?countryCode . }}
            BIND(COALESCE(?countryName, ?countryCode) AS ?countryVal)
            FILTER(str(?countryVal) = "{country_value}")
            OPTIONAL {{ ?org kg:officialName ?orgName . }}
            OPTIONAL {{ ?org kg:organizationType ?orgType . }}
        }}
        """
        orgs = run_sparql(DEFAULT_ENDPOINT, org_q)

        # Topics present in papers acknowledged by orgs in the country
        top_q = f"""
        PREFIX kg: <{KG_PREFIX}>

        SELECT ?topic ?topicName (COUNT(DISTINCT ?paper) AS ?papers) WHERE {{
            ?paper a kg:Paper ; kg:hasTopicAssignment ?ta ; kg:hasAcknowledgement ?ack .
            ?ta kg:assignedTopic ?topic .
            ?ack kg:acknowledgesOrganization ?org .
            ?org kg:country ?countryEntity .
            OPTIONAL {{ ?countryEntity kg:countryName ?countryName . }}
            OPTIONAL {{ ?countryEntity kg:countryCode ?countryCode . }}
            BIND(COALESCE(?countryName, ?countryCode) AS ?countryVal)
            FILTER(str(?countryVal) = "{country_value}")
            OPTIONAL {{ ?topic kg:name ?topicName . }}
        }}
        GROUP BY ?topic ?topicName
        ORDER BY DESC(?papers)
        LIMIT {int(limit_count)}
        """
        topics = run_sparql(DEFAULT_ENDPOINT, top_q)

        return {
                "organizations": orgs.fillna("") if (orgs is not None and not orgs.empty) else pd.DataFrame(),
                "topics": topics.fillna("") if (topics is not None and not topics.empty) else pd.DataFrame(),
        }


def clean_uri_label(value):
    if not isinstance(value, str):
        return value
    if value.startswith("http://") or value.startswith("https://"):
        tail = value.rstrip("/").split("/")[-1]
        return tail.replace("_", " ")
    return value


def sort_known_first(frame, columns):
    if frame.empty:
        return frame

    sorted_frame = frame.copy()
    for column in columns:
        if column not in sorted_frame.columns:
            sorted_frame[column] = ""

        normalized = sorted_frame[column].fillna("").astype(str).str.strip().str.lower()
        sorted_frame[f"_{column}_unknown"] = normalized.isin({"", "unknown", "desconocido", "n/a"})

    sort_columns = [f"_{column}_unknown" for column in columns] + columns
    sorted_frame = sorted_frame.sort_values(by=sort_columns, ascending=[True] * len(sort_columns), kind="mergesort")
    return sorted_frame.drop(columns=[f"_{column}_unknown" for column in columns], errors="ignore")


def join_unique(values):
    items = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        if text not in items:
            items.append(text)
    return "; ".join(items) if items else "N/A"


def first_non_empty(values, default="N/A"):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() not in {"unknown", "desconocido", "n/a"}:
            return text
    return default


def get_global_overview(DEFAULT_ENDPOINT):
    query = f"""
    PREFIX kg: <{KG_PREFIX}>

    SELECT
        (COUNT(DISTINCT ?paper) AS ?papers)
        (COUNT(DISTINCT ?person) AS ?researchers)
        (COUNT(DISTINCT ?organization) AS ?organizations)
        (COUNT(DISTINCT ?topic) AS ?topics)
        (COUNT(DISTINCT ?country) AS ?countries)
    WHERE {{
        ?paper a kg:Paper .
        OPTIONAL {{ ?paper kg:hasAuthor ?person . }}
        OPTIONAL {{ ?paper kg:hasTopicAssignment ?ta . ?ta kg:assignedTopic ?topic . }}
        OPTIONAL {{ ?paper kg:hasAcknowledgement ?ack . ?ack kg:acknowledgesOrganization ?organization . }}
        OPTIONAL {{ ?organization kg:country ?country . }}
    }}
    """
    df = run_sparql(DEFAULT_ENDPOINT, query)
    if df.empty:
        return {}

    row = df.iloc[0].to_dict()
    return {
        "papers": int(float(row.get("papers") or 0)),
        "researchers": int(float(row.get("researchers") or 0)),
        "organizations": int(float(row.get("organizations") or 0)),
        "topics": int(float(row.get("topics") or 0)),
        "countries": int(float(row.get("countries") or 0)),
    }

def get_paper_authors_details(DEFAULT_ENDPOINT, paper_uri):
    query = f"""
    PREFIX kg: <{KG_PREFIX}>

    SELECT DISTINCT
        ?author
        ?authorName
        ?orcid
        ?authorCountryValue
        ?org
        ?orgName
        ?organizationType
        ?orgCountryValue
        ?conceptValue
    WHERE {{
        VALUES ?paper {{ <{paper_uri}> }}
        ?paper kg:hasAuthor ?author .

        OPTIONAL {{ ?author kg:name ?authorName . }}
        OPTIONAL {{ ?author kg:orcid ?orcid . }}

        OPTIONAL {{
            ?author kg:addressCountry ?authorCountry .
            OPTIONAL {{ ?authorCountry kg:countryName ?authorCountryName . }}
            OPTIONAL {{ ?authorCountry kg:countryCode ?authorCountryCode . }}
            BIND(COALESCE(?authorCountryName, ?authorCountryCode) AS ?authorCountryValue)
        }}

        OPTIONAL {{
            ?author kg:affiliatedWith ?org .
            OPTIONAL {{ ?org kg:officialName ?orgName . }}
            OPTIONAL {{ ?org kg:organizationType ?organizationType . }}
            OPTIONAL {{
                ?org kg:country ?orgCountry .
                OPTIONAL {{ ?orgCountry kg:countryName ?orgCountryName . }}
                OPTIONAL {{ ?orgCountry kg:countryCode ?orgCountryCode . }}
                BIND(COALESCE(?orgCountryName, ?orgCountryCode) AS ?orgCountryValue)
            }}
        }}

        OPTIONAL {{ ?author kg:hasConcept ?conceptValue . }}
    }}
    ORDER BY ?authorName ?orgName
    """
    df = run_sparql(DEFAULT_ENDPOINT, query)
    if df.empty:
        return df

    for column in ["author", "authorName", "orcid", "authorCountryValue", "org", "orgName", "organizationType", "orgCountryValue", "conceptValue"]:
        if column not in df.columns:
            df[column] = None

    grouped_rows = []
    for author_uri, group in df.groupby("author", dropna=False):
        author_name = first_non_empty(group["authorName"], default=clean_uri_label(str(author_uri).split("/")[-1]))
        grouped_rows.append(
            {
                "author": author_uri,
                "Nombre completo": author_name,
                "ORCID": first_non_empty(group["orcid"]),
                "País del investigador": first_non_empty(group["authorCountryValue"]),
                "Afiliación(es)": join_unique(group["orgName"]),
                "Tipo de organización": join_unique(group["organizationType"]),
                "País(es) de afiliación": join_unique(group["orgCountryValue"]),
                "Área de especialización": join_unique(group["conceptValue"]),
            }
        )

    authors_df = pd.DataFrame(grouped_rows)
    return sort_known_first(authors_df, ["Nombre completo", "País del investigador", "Afiliación(es)"])


st.title("Explorador de conocimiento global")

try:
    topics_df = get_topics(DEFAULT_ENDPOINT)
except Exception as e:
    st.error(f"No se pudo consultar Fuseki en {DEFAULT_ENDPOINT}: {e}")
    st.stop()

if topics_df.empty:
    st.warning("No hay tópicos en el grafo. Verifica que los datos de topic assignment estén cargados en Fuseki.")
    st.stop()

try:
    global_overview = get_global_overview(DEFAULT_ENDPOINT)
    countries_overview_global = get_countries_overview(DEFAULT_ENDPOINT, 200)
except Exception as e:
    st.warning(f"No se pudieron calcular algunos resúmenes globales: {e}")
    global_overview = {}
    countries_overview_global = pd.DataFrame()

st.subheader("Resumen general")
summary_cols = st.columns(5)
summary_values = {
    "Papers": global_overview.get("papers", int(topics_df["papers"].sum())),
    "Investigadores": global_overview.get("researchers", 0),
    "Organizaciones": global_overview.get("organizations", 0),
    "Tópicos": global_overview.get("topics", int(topics_df["topic"].nunique())),
    "Países": global_overview.get("countries", 0),
}
for column, (label, value) in zip(summary_cols, summary_values.items()):
    column.metric(label, int(value) if isinstance(value, (int, float)) else value)

st.markdown("### Tópicos")
st.write(f"**Probabilidad media de tópicos:** {round(float(topics_df['avgProbability'].mean()), 3)}")
st.bar_chart(topics_df.set_index("topicName")["papers"].head(10))
if not countries_overview_global.empty:
    st.write("**Países más activos:**")
    st.dataframe(
        countries_overview_global.sort_values(by="papers", ascending=False).head(10).rename(
            columns={"country": "País", "papers": "Papers", "organizations": "Organizaciones"}
        ),
        width="stretch",
    )

st.divider()
st.subheader("Explorador por temática")

options = {
    f"{row['topicName']} ({row['papers']} papers)": row["topic"]
    for _, row in topics_df.sort_values(by="papers", ascending=False).iterrows()
}
selected_label = st.selectbox("Selecciona una temática", options=list(options.keys()))
selected_topic_uri = options[selected_label]

try:
    countries_df = get_country_leaders_for_topic(DEFAULT_ENDPOINT, selected_topic_uri, 10)
    collaboration_df = get_collaboration_network_for_topic(DEFAULT_ENDPOINT, selected_topic_uri, 10)
    similarity_df = get_similarity_for_topic(DEFAULT_ENDPOINT, selected_topic_uri, 10)
    researchers_df = get_researchers_for_topic(DEFAULT_ENDPOINT, selected_topic_uri, 10)
except Exception as e:
    st.error(f"Error al consultar paneles del tópico seleccionado: {e}")
    st.stop()


st.markdown("### Países")
if countries_df.empty:
    st.info("No hay países asociados a organizaciones para este tópico.")
else:
    st.bar_chart(countries_df.set_index("country")[["papers", "organizations"]])

st.markdown("### Investigadores")
if researchers_df.empty:
    st.info("No se encontraron investigadores vinculados a este tópico.")
else:
    researchers_df = researchers_df.copy()
    researchers_df["affiliation"] = researchers_df["affiliation"].apply(clean_uri_label)
    researchers_df["specialization"] = researchers_df["specialization"].fillna("N/A")

    researchers_chart = researchers_df[["name", "papers"]].drop_duplicates().set_index("name")
    st.dataframe(
        researchers_df.rename(
            columns={
                "name": "Investigador",
                "orcid": "ORCID",
                "affiliation": "Afiliación",
                "specialization": "Área de especialización",
                "papers": "Papers",
                "avgCitations": "Citas medias",
            }
        )[["Investigador", "ORCID", "Afiliación", "Área de especialización", "Papers", "Citas medias"]],
        width="stretch",
    )

# Vista por país
st.divider()
st.subheader("Explora por país")
countries_overview = get_countries_overview(DEFAULT_ENDPOINT, 200)
if countries_overview.empty:
    st.info("No se encontraron países en el grafo.")
else:
    countries_overview = countries_overview.copy()
    country_options = list(countries_overview["country"])
    chosen_country = st.selectbox("Selecciona país", options=country_options, index=0)

    ents = get_entities_for_country(DEFAULT_ENDPOINT, chosen_country, 200)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Compañías / organizaciones en el país**")
        if ents["organizations"].empty:
            st.write("(No se encontraron organizaciones)")
        else:
            df_orgs = ents["organizations"].copy()
            df_orgs["orgName"] = df_orgs["orgName"].fillna(df_orgs["org"].str.split("/").str[-1])
            if "orgType" not in df_orgs.columns:
                df_orgs["orgType"] = "N/A"
            df_orgs["orgType"] = df_orgs["orgType"].fillna("N/A")
            df_orgs = sort_known_first(df_orgs, ["orgName", "orgType"])
            df_orgs["Nombre completo"] = df_orgs["orgName"].apply(clean_uri_label)
            st.dataframe(df_orgs[["Nombre completo", "orgType"]].rename(columns={"orgType": "Tipo"}), width="stretch")

    with col2:
        st.markdown("**Tópicos asociados**")
        if ents["topics"].empty:
            st.write("(No se encontraron tópicos)")
        else:
            df_top = ents["topics"].copy()
            df_top["topicName"] = df_top["topicName"].fillna(df_top["topic"].str.split("/").str[-1])
            df_top["papers"] = pd.to_numeric(df_top["papers"], errors="coerce").fillna(0).astype(int)
            st.dataframe(df_top.rename(columns={"topicName": "Tópico", "papers": "Papers"})[["Tópico", "Papers"]], width="stretch")

st.divider()

st.markdown("### Red de colaboración institucional")
if collaboration_df.empty:
    st.info("No se detectaron colaboraciones institucionales para este tópico.")
else:
    collaboration_df["edge"] = collaboration_df["orgAName"] + "  <>  " + collaboration_df["orgBName"]
    st.dataframe(
        collaboration_df.rename(
            columns={
                "orgAName": "Organización A",
                "orgBName": "Organización B",
                "sharedPapers": "Papers compartidos",
            }
        )[["Organización A", "Organización B", "Papers compartidos"]],
        width="stretch",
    )

def get_papers_list(DEFAULT_ENDPOINT, limit_count=50):
    query = f"""
    PREFIX kg: <{KG_PREFIX}>

        SELECT ?paper ?title ?date WHERE {{
            ?paper a kg:Paper .
            OPTIONAL {{ ?paper kg:title ?title . }}
            OPTIONAL {{ ?paper kg:publicationDate ?date . }}
        }}
    ORDER BY DESC(?date)
    LIMIT {int(limit_count)}
    """
    df = run_sparql(DEFAULT_ENDPOINT, query)
    if df.empty:
        return df

    df["title"] = df["title"].fillna(df["paper"].str.split("/").str[-1].str.replace("_", " "))
    return df


def get_paper_details(DEFAULT_ENDPOINT, paper_uri):
    query = f"""
    PREFIX kg: <{KG_PREFIX}>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?paper ?title ?abstract ?publicationDate ?citedByCount
                     (GROUP_CONCAT(DISTINCT CONCAT(str(?author),"^^",COALESCE(?authorName,''),"^^",COALESCE(?orcid,''),"^^",COALESCE(?orgName,'')); separator='||') AS ?authorsList)
                     (GROUP_CONCAT(DISTINCT CONCAT(str(?topic),"^^",COALESCE(?topicName,''),"^^",COALESCE(str(?prob),'')); separator='||') AS ?topicsList)
                     (GROUP_CONCAT(DISTINCT CONCAT(str(?ackOrg),"^^",COALESCE(?ackOrgName,'')); separator='||') AS ?ackOrgsList)
                     (GROUP_CONCAT(DISTINCT CONCAT(str(?ackPerson),"^^",COALESCE(?ackPersonName,'')); separator='||') AS ?ackPersonsList)
        WHERE {{
            VALUES ?paper {{ <{paper_uri}> }}
            OPTIONAL {{ ?paper kg:title ?title . }}
            OPTIONAL {{ ?paper kg:abstract ?abstract . }}
            OPTIONAL {{ ?paper kg:publicationDate ?publicationDate . }}
            OPTIONAL {{ ?paper kg:citedByCount ?citedByCount . }}

            OPTIONAL {{
                ?paper kg:hasAuthor ?author .
                OPTIONAL {{ ?author kg:name ?authorName . }}
                OPTIONAL {{ ?author kg:orcid ?orcid . }}
                OPTIONAL {{ ?author kg:affiliatedWith ?org . ?org kg:officialName ?orgName . }}
            }}

            OPTIONAL {{
                ?paper kg:hasTopicAssignment ?ta .
                ?ta kg:assignedTopic ?topic .
                OPTIONAL {{ ?topic kg:name ?topicName . }}
                OPTIONAL {{ ?ta kg:probability ?prob . }}
            }}

            OPTIONAL {{
                ?paper kg:hasAcknowledgement ?ack .
                OPTIONAL {{ ?ack kg:acknowledgesOrganization ?ackOrg . ?ackOrg kg:officialName ?ackOrgName . }}
                OPTIONAL {{ ?ack kg:acknowledgesPerson ?ackPerson . ?ackPerson kg:name ?ackPersonName . }}
            }}
        }}
    GROUP BY ?paper ?title ?abstract ?doi ?publicationDate ?citedByCount
    """
    df = run_sparql(DEFAULT_ENDPOINT, query)
    if df.empty:
        return None

    row = df.iloc[0].to_dict()

    def split_list_field(val):
        if not isinstance(val, str) or val.strip() == "":
            return []
        parts = [p for p in val.split("||") if p]
        items = []
        for p in parts:
            items.append(p.split("^^"))
        return items

    details = {
        "paper": row.get("paper"),
        "title": row.get("title"),
        "abstract": row.get("abstract"),
        "doi": row.get("doi"),
        "publicationDate": row.get("publicationDate"),
        "citedByCount": row.get("citedByCount"),
        "authors": split_list_field(row.get("authorsList")),
        "topics": split_list_field(row.get("topicsList")),
        "ackOrgs": split_list_field(row.get("ackOrgsList")),
        "ackPersons": split_list_field(row.get("ackPersonsList")),
    }

    # Fetch similar papers (separate query)
    sim_q = f"""
        PREFIX kg: <{KG_PREFIX}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?peer ?peerTitle ?score WHERE {{
      ?sim a kg:SimilarityRelation ; kg:similarityScore ?score .
      {{ ?sim kg:sourcePaper <{paper_uri}> ; kg:targetPaper ?peer . }}
      UNION
      {{ ?sim kg:targetPaper <{paper_uri}> ; kg:sourcePaper ?peer . }}
      OPTIONAL {{ ?peer kg:title ?peerTitle . }}
    }}
    ORDER BY DESC(xsd:float(?score))
    LIMIT 50
    """
    sim_df = run_sparql(DEFAULT_ENDPOINT, sim_q)
    if sim_df is None or sim_df.empty:
        details["similar"] = []
    else:
        details["similar"] = sim_df.fillna("").to_dict(orient="records")

    return details


# --- Visor de papers: selección y navegación uno a uno ---
st.divider()
st.subheader("Visor de papers")

papers_df = get_papers_list(DEFAULT_ENDPOINT, 500)
if papers_df.empty:
    st.info("No hay papers en el grafo para mostrar.")
else:
    papers_df = papers_df.copy()
    papers_df["label"] = papers_df["title"].fillna(papers_df["paper"].str.split("/").str[-1])

    if "paper_index" not in st.session_state:
        st.session_state.paper_index = 0

    col_left, col_right = st.columns([1, 3])
    with col_left:
        sel = st.selectbox("Selecciona paper", options=list(papers_df["label"]))
        idx = int(papers_df[papers_df["label"] == sel].index[0])
        st.session_state.paper_index = idx

    current_paper_uri = papers_df.iloc[st.session_state.paper_index]["paper"]
    details = get_paper_details(DEFAULT_ENDPOINT, current_paper_uri)
    authors_df = get_paper_authors_details(DEFAULT_ENDPOINT, current_paper_uri)

    with col_right:
        if details is None:
            st.info("No se encontraron detalles para el paper seleccionado.")
        else:
            st.markdown(f"### {clean_uri_label(details.get('title') or details.get('paper'))}")
            st.write(f"**ID:** {details.get('paper').replace('http://example.org/paper/', '') or 'N/A'}")
            st.write(f"**Fecha:** {details.get('publicationDate') or 'N/A'}")
            st.write(f"**Citas:** {details.get('citedByCount') or '0'}")

            st.markdown("**Autores**")
            if authors_df.empty:
                st.info("No se encontró información de autores para este paper.")
            else:
                st.dataframe(
                    authors_df[[
                        "Nombre completo",
                        "ORCID",
                        "País del investigador",
                        "Afiliación(es)",
                        "Tipo de organización",
                        "País(es) de afiliación",
                        "Área de especialización",
                    ]],
                    width="stretch",
                )

            # Topics
            st.markdown("**Tópicos**")
            if details.get("topics"):
                topic_rows = []
                for t in details["topics"]:
                    tid = t[0] if len(t) > 0 else ""
                    tname = t[1] if len(t) > 1 else ""
                    prob = t[2] if len(t) > 2 else ""
                    topic_rows.append({"Tópico": clean_uri_label(tname) or clean_uri_label(tid), "Probabilidad": prob})
                topic_rows = sorted(topic_rows, key=lambda x: (x["Probabilidad"] if isinstance(x["Probabilidad"], (int, float)) else 0), reverse=True)
                st.table(pd.DataFrame(topic_rows))

            # Acknowledgements
            if details.get("ackOrgs") or details.get("ackPersons"):
                st.markdown("**Agradecimientos / Acknowledgements**")
                if details.get("ackOrgs"):
                    st.write("Organizaciones:")
                    for o in details["ackOrgs"]:
                        st.write(f"- {clean_uri_label(o[1] if len(o) > 1 else o[0])}")
                if details.get("ackPersons"):
                    st.write("Personas:")
                    for p in details["ackPersons"]:
                        st.write(f"- {clean_uri_label(p[1] if len(p) > 1 else p[0])}")

            # Similar papers
            if details.get("similar"):
                st.markdown("**Papers similares**")
                sim_df = pd.DataFrame(list(filter(lambda x: float(x["score"]) > 0.5, details["similar"]))).fillna("")
                if not sim_df.empty:
                    sim_df["peerTitle"] = sim_df["peerTitle"].fillna(sim_df["peer"].str.split("/").str[-1])
                    st.dataframe(sim_df.rename(columns={"peerTitle": "Título", "score": "Similitud"})[["Título", "Similitud"]], width="stretch")
