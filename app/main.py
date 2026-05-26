from grobid import process_dataset
from openalex import get_paper_info_from_arxiv
from wikidata import get_wikidata_id, get_organization_info
from orcid import get_author_info
from ai_models import AIProcessor
from graph_builder import build_knowledge_graph


def enrich_papers_data(papers_data, ai):
    enriched_papers = []

    for i, paper in enumerate(papers_data):
        paper_id = paper.get("paper_id", i)
        print(f"\n--> Procesando Artículo {i + 1}/{len(papers_data)} (arXiv ID: {paper_id})")

        openalex_data = {}
        if paper_id:
            try:
                openalex_data = get_paper_info_from_arxiv(paper_id)
                if "error" in openalex_data:
                    print(f"    ✗ OpenAlex devolvió un error para {paper_id}: {openalex_data['error']}")
                    openalex_data = {}
                else:
                    print("    ✓ Datos de OpenAlex recuperados con éxito.")
            except Exception as e:
                print(f"    ✗ No se pudieron obtener datos de OpenAlex para {paper_id}: {e}")

        paper_record = {
            "paper_id": paper_id,
            "title": paper.get("title"),
            "cited_by_count": openalex_data.get("cited_by_count"),
            "publication_date": openalex_data.get("publication_date"),
            "abstract": paper.get("abstract", ""),
            "acknowledgement": paper.get("acknowledgement", ""),
            "authors": [],
            "topics": [],
            "organizations": [],
            "organization_info": {},
            "acknowledged_persons": [],
        }

        for author in openalex_data.get("authors", []):
            enriched_author = {
                "name": author.get("name", "Unknown"),
                "orcid": author.get("orcid"),
                "country": "Unknown",
                "institutions": author.get("institutions", []),
            }

            orcid_url = enriched_author.get("orcid")
            if orcid_url:
                try:
                    print(f"    ✓ Obteniendo datos de ORCID para {enriched_author['name']} ({orcid_url})...")
                    orcid_data = get_author_info(orcid_url)
                    enriched_author["orcid"] = orcid_data.get("orcid", orcid_url)
                    enriched_author["country"] = orcid_data.get("country", "Unknown")
                except Exception as e:
                    print(f"    ✗ No se pudieron obtener datos de ORCID para {orcid_url}: {e}")

            paper_record["authors"].append(enriched_author)

        if paper_record["abstract"]:
            paper_record["topics"] = ai.assign_topics(paper_record["abstract"])

        if paper_record["acknowledgement"]:
            entities = ai.extract_entities(paper_record["acknowledgement"])

            for org_name in entities.get("organizations", []):
                paper_record["organizations"].append(org_name)
                paper_record["organization_info"][org_name] = {}

                try:
                    print(f"    ✓ Obteniendo información de Wikidata para la organización '{org_name}'...")
                    wd_id = get_wikidata_id(org_name)
                    if wd_id:
                        wd_info = get_organization_info(wd_id)
                        if wd_info.get("organization_type"):
                            paper_record["organization_info"][org_name]["organization_type"] = wd_info["organization_type"]
                        if wd_info.get("country"):
                            paper_record["organization_info"][org_name]["country"] = wd_info["country"]
                except Exception as e:
                    print(f"    ✗ No se pudo obtener información para {org_name} desde Wikidata: {e}")

            paper_record["acknowledged_persons"] = entities.get("persons", [])

            for author in paper_record["authors"]:
                if author.get("orcid"):
                    try:
                        orcid_data = get_author_info(author["orcid"])
                        if orcid_data.get("keywords"):
                            author["keywords"] = orcid_data["keywords"]
                    except Exception as e:
                        print(f"    ✗ No se pudieron obtener keywords de ORCID para {author.get('orcid')}: {e}")

        enriched_papers.append(paper_record)

    return enriched_papers


def compute_similarity_links(papers_data, ai):
    similarity_links = []

    print("\n[Paso 2.5] Calculando similitud semántica entre artículos...")
    for x in range(len(papers_data)):
        for y in range(x + 1, len(papers_data)):
            abs1 = papers_data[x].get("abstract", "")
            abs2 = papers_data[y].get("abstract", "")

            if abs1 and abs2:
                sim_score = ai.compute_similarity(abs1, abs2)

                id_x = papers_data[x].get("paper_id", str(x))
                id_y = papers_data[y].get("paper_id", str(y))
                similarity_links.append(
                    {
                        "source_paper_id": id_x,
                        "target_paper_id": id_y,
                        "similarity_score": sim_score,
                    }
                )
                print(f"    ✓ Conectados Paper {id_x} y Paper {id_y} (Similitud: {sim_score})")

    return similarity_links


def run_pipeline():
    print("=== INICIANDO EL SISTEMA COMPLETO DE CIENCIA ABIERTA ===")

    ai = AIProcessor()

    dataset_path = "dataset"
    grobid_url = "http://127.0.0.1:8070"

    print("\n[Paso 1] Extrayendo datos de los PDFs con Grobid...")
    papers_data = process_dataset(dataset_path, grobid_url)

    print("\n[Paso 2] Enriqueciendo datos...")
    enriched_papers = enrich_papers_data(papers_data, ai)

    similarity_links = compute_similarity_links(enriched_papers, ai)

    build_knowledge_graph(enriched_papers, similarity_links)


if __name__ == "__main__":
    run_pipeline()
