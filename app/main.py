import os
from rdflib import Graph, Namespace, URIRef, Literal, RDF, BNode
from rdflib.namespace import FOAF, SKOS, XSD

from grobid import process_dataset
from openalex import get_paper_info_from_arxiv
from wikidata import get_wikidata_id, get_organization_info
from orcid import get_author_info
from ai_models import AIProcessor

SCHEMA = Namespace("http://schema.org/")
ORG = Namespace("http://www.w3.org/ns/org#")
EX = Namespace("http://example.org/ontology/")

def build_knowledge_graph():
    print("=== INICIANDO EL SISTEMA COMPLETO DE CIENCIA ABIERTA ===")
    
    ai = AIProcessor()
    g = Graph()
    g.bind("schema", SCHEMA)
    g.bind("foaf", FOAF)
    g.bind("org", ORG)
    g.bind("skos", SKOS)
    g.bind("ex", EX)
    
    dataset_path = "dataset"
    grobid_url = "http://127.0.0.1:8070"
    
    print("\n[Paso 1] Extrayendo datos de los PDFs con Grobid...")
    papers_data = process_dataset(dataset_path, grobid_url)
    
    print("\n[Paso 2] Enriqueciendo datos y construyendo el Grafo Semántico...")
    for i, paper in enumerate(papers_data):
        arxiv_id = paper.get('paper_id')
        print(f"\n--> Procesando Artículo {i+1}/{len(papers_data)} (arXiv ID: {arxiv_id})")
        
        openalex_data = {}
        if arxiv_id:
            try:
                openalex_data = get_paper_info_from_arxiv(arxiv_id)
                print(f"    ✓ Datos de OpenAlex recuperados con éxito.")
            except Exception as e:
                print(f"    ✗ No se pudieron obtener datos de OpenAlex para {arxiv_id}: {e}")

        paper_uri = URIRef(f"http://example.org/paper/{arxiv_id if arxiv_id else i}")
        g.add((paper_uri, RDF.type, SCHEMA.ScholarlyArticle))
        
        title = openalex_data.get('title') or paper.get('title')
        if title:
            g.add((paper_uri, SCHEMA.name, Literal(title, datatype=XSD.string)))
            
        if openalex_data.get('doi'):
            g.add((paper_uri, SCHEMA.identifier, Literal(openalex_data['doi'], datatype=XSD.string)))
            
        if openalex_data.get('cited_by_count') is not None:
            g.add((paper_uri, EX.cited_by_count, Literal(openalex_data['cited_by_count'], datatype=XSD.integer)))

        authors = openalex_data.get('authors', [])
        for author in authors:
            orcid_url = author.get('orcid')
            if orcid_url:
                orcid_data = get_author_info(orcid_url)
                
                author_uri = URIRef(f"http://example.org/person/{orcid_data['orcid']}")
                g.add((author_uri, RDF.type, FOAF.Person))
                g.add((author_uri, FOAF.name, Literal(author.get('name', 'Autor Desconocido'))))
                g.add((author_uri, EX.orcid, Literal(orcid_url)))
                
                if orcid_data.get('country') and orcid_data['country'] != 'Unknown':
                    g.add((author_uri, SCHEMA.addressCountry, Literal(orcid_data['country'])))
                
                g.add((paper_uri, SCHEMA.author, author_uri))

        abstract = openalex_data.get('abstract') or paper.get('abstract', '')
        ack_text = paper.get('acknowledgement', '')
        
        if abstract:
            topics = ai.assign_topics(abstract)
            for t in topics:
                topic_uri = URIRef(f"http://example.org/topic/{t['topic'].replace(' ', '_')}")
                g.add((topic_uri, RDF.type, SKOS.Concept))
                g.add((topic_uri, SKOS.prefLabel, Literal(t['topic'])))
                
                assignment_node = BNode()
                g.add((assignment_node, RDF.type, EX.TopicAssignment))
                g.add((assignment_node, EX.assigns_topic, topic_uri))
                g.add((assignment_node, EX.probability_score, Literal(t['probability'], datatype=XSD.float)))
                g.add((paper_uri, EX.has_topic_assignment, assignment_node))

        if ack_text:
            entities = ai.extract_entities(ack_text)
            
            for org_name in entities.get("organizations", []):
                org_uri = URIRef(f"http://example.org/organization/{org_name.replace(' ', '_')}")
                g.add((org_uri, RDF.type, ORG.Organization))
                g.add((org_uri, SCHEMA.legalName, Literal(org_name)))
                g.add((paper_uri, EX.acknowledges_funding_from, org_uri))
                
                try:
                    wd_id = get_wikidata_id(org_name)
                    if wd_id:
                        wd_info = get_organization_info(wd_id)
                        if wd_info.get('country'):
                            g.add((org_uri, SCHEMA.addressCountry, Literal(wd_info['country'])))
                except:
                    pass
                    
            for p_name in entities.get("persons", []):
                p_uri = URIRef(f"http://example.org/acknowledged_person/{p_name.replace(' ', '_')}")
                g.add((p_uri, RDF.type, FOAF.Person))
                g.add((p_uri, FOAF.name, Literal(p_name)))
                g.add((paper_uri, EX.acknowledges_person, p_uri))

    print("\n[Paso 2.5] Calculando similitud semántica entre artículos...")
    for x in range(len(papers_data)):
        for y in range(x + 1, len(papers_data)):
            abs1 = papers_data[x].get('abstract', '')
            abs2 = papers_data[y].get('abstract', '')
            
            if abs1 and abs2:
                sim_score = ai.compute_similarity(abs1, abs2)
                
                if sim_score > 0.65:
                    id_x = papers_data[x].get('paper_id', str(x))
                    id_y = papers_data[y].get('paper_id', str(y))
                    
                    uri_x = URIRef(f"http://example.org/paper/{id_x}")
                    uri_y = URIRef(f"http://example.org/paper/{id_y}")
                    
                    sim_node = BNode()
                    g.add((sim_node, RDF.type, EX.SimilarityLink))
                    g.add((sim_node, EX.source_paper, uri_x))
                    g.add((sim_node, EX.target_paper, uri_y))
                    g.add((sim_node, EX.similarity_score, Literal(sim_score, datatype=XSD.float)))
                    
                    g.add((uri_x, EX.is_similar_to, sim_node))
                    print(f"    ✓ Conectados Paper {id_x} y Paper {id_y} (Similitud: {sim_score})")

    output_file = "knowledge_graph.ttl"
    g.serialize(destination=output_file, format="turtle")
    print(f"\n[Paso 3] ¡ÉXITO TOTAL! Grafo completo guardado en: {output_file}")
    print(f"Se han generado un total de {len(g)} triples semánticas.")

if __name__ == "__main__":
    build_knowledge_graph()