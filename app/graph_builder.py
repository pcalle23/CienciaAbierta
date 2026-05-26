from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

KG = Namespace("https://researchmap.es/ontology#")


def build_knowledge_graph(papers_data, similarity_links=None, output_file="knowledge_graph.ttl"):
    g = Graph()
    g.bind("kg", KG)

    print("\n[Construcción] Generando el grafo RDF a partir de los resultados preparados...")
    for i, paper in enumerate(papers_data):
        paper_id = paper.get("paper_id", i)
        paper_uri = URIRef(f"http://example.org/paper/{paper_id}")
        g.add((paper_uri, RDF.type, KG.Paper))

        title = paper.get("title")
        if title:
            g.add((paper_uri, KG.title, Literal(title, datatype=XSD.string)))

        cited_by_count = paper.get("cited_by_count")
        if cited_by_count is not None:
            g.add((paper_uri, KG.citedByCount, Literal(cited_by_count, datatype=XSD.integer)))

        publication_date = paper.get("publication_date")
        if publication_date:
            g.add((paper_uri, KG.publicationDate, Literal(publication_date, datatype=XSD.date)))

        for author in paper.get("authors", []):
            author_id = author.get("orcid") or author.get("name", "autor")
            author_id = author_id.replace("https://orcid.org/", "").replace(" ", "_")
            author_uri = URIRef(f"http://example.org/person/{author_id}")
            g.add((author_uri, RDF.type, KG.Person))
            g.add((author_uri, KG.name, Literal(author.get("name", "Autor Desconocido"))))

            if author.get("orcid"):
                g.add((author_uri, KG.orcid, Literal(author["orcid"])))

            author_country = author.get("country")
            if author_country and author_country != "Unknown":
                country_value = author_country.replace("https://orcid.org/", "").strip()
                country_uri = URIRef(f"http://example.org/country/{country_value.replace(' ', '_')}")
                g.add((country_uri, RDF.type, KG.Country))
                if len(country_value) == 2 and country_value.isalpha():
                    g.add((country_uri, KG.countryCode, Literal(country_value.upper())))
                else:
                    g.add((country_uri, KG.countryName, Literal(country_value)))
                g.add((author_uri, KG.addressCountry, country_uri))

            for keyword in author.get("keywords", []):
                if keyword:
                    g.add((author_uri, KG.hasConcept, Literal(keyword)))

            g.add((paper_uri, KG.hasAuthor, author_uri))

            for institution in author.get("institutions", []):
                institution_name = institution.get("name")
                if not institution_name:
                    continue

                organization_uri = URIRef(f"http://example.org/organization/{institution_name.replace(' ', '_')}")
                g.add((organization_uri, RDF.type, KG.Organization))
                g.add((organization_uri, KG.officialName, Literal(institution_name)))
                g.add((author_uri, KG.affiliatedWith, organization_uri))

                organization_type = institution.get("organization_type")
                if organization_type:
                    g.add((organization_uri, KG.organizationType, Literal(organization_type)))

                country_code = institution.get("country_code")
                if country_code:
                    country_uri = URIRef(f"http://example.org/country/{country_code}")
                    g.add((country_uri, RDF.type, KG.Country))
                    g.add((country_uri, KG.countryCode, Literal(country_code)))
                    g.add((organization_uri, KG.country, country_uri))

        for topic in paper.get("topics", []):
            topic_name = topic.get("topic")
            if not topic_name:
                continue

            topic_uri = URIRef(f"http://example.org/topic/{topic_name.replace(' ', '_')}")
            g.add((topic_uri, RDF.type, KG.Topic))
            g.add((topic_uri, KG.name, Literal(topic_name)))
            g.add((topic_uri, KG.topicModel, Literal("AI topic assignment")))

            assignment_node = BNode()
            g.add((assignment_node, RDF.type, KG.BelongsToTopicRelation))
            g.add((assignment_node, KG.assignedTopic, topic_uri))
            g.add((assignment_node, KG.assignedPaper, paper_uri))
            probability = topic.get("probability")
            if probability is not None:
                g.add((assignment_node, KG.probability, Literal(probability, datatype=XSD.float)))
            g.add((paper_uri, KG.hasTopicAssignment, assignment_node))

        for org_name in paper.get("organizations", []):
            org_uri = URIRef(f"http://example.org/organization/{org_name.replace(' ', '_')}")
            g.add((org_uri, RDF.type, KG.Organization))
            g.add((org_uri, KG.officialName, Literal(org_name)))

            organization_type = paper.get("organization_info", {}).get(org_name, {}).get("organization_type")
            if organization_type:
                g.add((org_uri, KG.organizationType, Literal(organization_type)))

            acknowledgement_node = BNode()
            g.add((acknowledgement_node, RDF.type, KG.AcknowledgementRelation))
            g.add((acknowledgement_node, KG.acknowledgementPaper, paper_uri))
            g.add((acknowledgement_node, KG.acknowledgesOrganization, org_uri))
            g.add((paper_uri, KG.hasAcknowledgement, acknowledgement_node))

            org_info = paper.get("organization_info", {}).get(org_name, {})
            if org_info.get("country"):
                country_uri = URIRef(f"http://example.org/country/{org_info['country'].replace(' ', '_')}")
                g.add((country_uri, RDF.type, KG.Country))
                g.add((country_uri, KG.countryName, Literal(org_info["country"])))
                g.add((org_uri, KG.country, country_uri))

        for person_name in paper.get("acknowledged_persons", []):
            p_uri = URIRef(f"http://example.org/acknowledged_person/{person_name.replace(' ', '_')}")
            g.add((p_uri, RDF.type, KG.Person))
            g.add((p_uri, KG.name, Literal(person_name)))

            acknowledgement_node = BNode()
            g.add((acknowledgement_node, RDF.type, KG.AcknowledgementRelation))
            g.add((acknowledgement_node, KG.acknowledgementPaper, paper_uri))
            g.add((acknowledgement_node, KG.acknowledgesPerson, p_uri))
            g.add((paper_uri, KG.hasAcknowledgement, acknowledgement_node))

    for link in similarity_links or []:
        source_id = link.get("source_paper_id")
        target_id = link.get("target_paper_id")
        score = link.get("similarity_score")

        if source_id is None or target_id is None or score is None:
            continue

        uri_x = URIRef(f"http://example.org/paper/{source_id}")
        uri_y = URIRef(f"http://example.org/paper/{target_id}")

        sim_node = BNode()
        g.add((sim_node, RDF.type, KG.SimilarityRelation))
        g.add((sim_node, KG.sourcePaper, uri_x))
        g.add((sim_node, KG.targetPaper, uri_y))
        g.add((sim_node, KG.similarityScore, Literal(score, datatype=XSD.float)))
        g.add((uri_x, KG.hasSimilarityRelation, sim_node))
        g.add((uri_y, KG.hasSimilarityRelation, sim_node))

    g.serialize(destination=output_file, format="turtle")
    print(f"\n[Paso 3] ¡ÉXITO TOTAL! Grafo completo guardado en: {output_file}")
    print(f"Se han generado un total de {len(g)} triples semánticas.")

    return g
