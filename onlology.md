# Aplicación

Buscar información sobre los autores y otras publicaciones de los mismos autores.
# Knowledge Graphs

**Wikidata (RDF)** para las publicaciones
- Q5246046 (academic publishing) para obtener información del paper
- P921 (main subject) para obtener el topic del paper
- P463 (member of) para obtener proyectos al que pertenece una persona

**ORCID (API)** para los autores
- credit-name (para obtener nombre del autor) ?
- works (para obtener lista de papers del autor)
- employment (para obtener la organización para la que trabaja) ?
# Diagrama

```mermaid
erDiagram
	PAPER {
		string title
		string doi
		date publication_date
	}
	PERSON {
		string name
		string orcid_id
	}
	ORGANIZATION {
		string name
	}
	PROJECT {
		string name
	}
	TOPIC {
		string name
	}
	
	PAPER ||--o{ TOPIC : belongs_to_topic
	PAPER ||--o{ PAPER : similar_to
	PAPER }|--o{ PERSON : has_author
	PAPER }|--o{ ORGANIZATION : acknowledges
	PERSON ||--o{ ORGANIZATION : employed_by
	PROJECT }|--o{ PERSON : involves
```
