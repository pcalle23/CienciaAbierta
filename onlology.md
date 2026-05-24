# Aplicación y Grafo de Conocimiento

## Casos de Uso

El objetivo de este Knowledge Graph es descubrir los flujos de financiación y las redes de colaboración en la investigación.
**Caso de uso principal:** Permitir a un investigador o institución identificar rápidamente qué agencias (gubernamentales o privadas) están financiando los proyectos más relevantes de una temática concreta (topics), y visualizar mediante un mapa qué países y organizaciones lideran dichas temáticas. Esto facilita la búsqueda de futuros socios estratégicos o fuentes de financiación.

## Reutilización de Vocabularios Estándar (Extensión de clases)

Para el modelado de los datos, hemos extendido vocabularios estándar de la Web Semántica:

- **Paper:** `schema:ScholarlyArticle` / `fabio:ResearchPaper`
- **Person (Author):** `foaf:Person` / `schema:Person`
- **Organization:** `org:Organization` / `schema:Organization`
- **Project:** `foaf:Project` / `schema:ResearchProject`
- **Topic:** `skos:Concept`

## Flujo de trabajo

1. El sistema recibe un identificador de publicación inicial (arxivID) para obtener el DOI del artículo.
2. Utilizando el DOI, se consulta la API de OpenAlex para extraer citas, conceptos y el listado de autores con ORCID.
3. Se itera sobre los ORCID para extraer el país del investigador y su área de trabajo.
4. **Hugging Face (IA):** Se procesan los _Abstracts_ para generar Tópicos (con probabilidad) y Similitud entre papers (con threshold) usando Modelos de Lenguaje.
5. **Hugging Face (NER):** Se procesa la sección _Acknowledgements_ con Grobid para extraer Organizaciones, Personas y Proyectos involucrados en la financiación.
6. Se enriquece la información de organizaciones con Wikidata.
7. Los datos se integran en un grafo RDF (Apache Jena Fuseki) utilizando clases n-arias para relaciones complejas.

## Diagrama

```mermaid
erDiagram
	%% Clases principales mapeadas a vocabularios estándar
	SCHOLARLY_ARTICLE {
		string title
		string doi
		date publication_date
		int cited_by_count
	}

	PERSON {
		string name
		string orcid
		string keywords
		string country
	}

	ORGANIZATION {
		string official_name
		string org_type
		string country
	}

	PROJECT {
		string project_name
	}

	TOPIC {
		string topic_name
	}

	%% Clases N-Arias para manejar probabilidades y thresholds
	TOPIC_ASSIGNMENT {
		float probability_score
	}

	SIMILARITY_LINK {
		float similarity_score
	}

	%% Relaciones de cardinalidad corregidas (muchos a muchos / uno a muchos)
	SCHOLARLY_ARTICLE ||--o{ PERSON : "has_author"
	SCHOLARLY_ARTICLE ||--o{ ORGANIZATION : "affiliated_with"

	%% Relaciones extraidas de los Acknowledgements (NER)
	SCHOLARLY_ARTICLE }o--o{ PROJECT : "acknowledges_project"
	SCHOLARLY_ARTICLE }o--o{ ORGANIZATION : "acknowledges_funding_from"
	SCHOLARLY_ARTICLE }o--o{ PERSON : "acknowledges_person"

	%% Conexiones con N-Arias
	SCHOLARLY_ARTICLE ||--o{ TOPIC_ASSIGNMENT : "has_topic_assignment"
	TOPIC_ASSIGNMENT }o--|| TOPIC : "assigns_topic"

	SCHOLARLY_ARTICLE ||--o{ SIMILARITY_LINK : "source_paper"
	SIMILARITY_LINK }o--|| SCHOLARLY_ARTICLE : "target_paper"
```
