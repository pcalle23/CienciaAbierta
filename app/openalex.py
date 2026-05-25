import requests

def get_paper_info_from_arxiv(id):
    """Obtiene información de un paper utilizando su ID de arXiv."""
    # Obtener papers en OpenAlex usando el DOI de arXiv (no están todos)
    if id.lower().startswith("w"):
        url = f"https://api.openalex.org/works/{id}"
    else:
        url = f"https://api.openalex.org/works/https://doi.org/10.48550/arXiv.{id}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        cited_by_count = data.get("cited_by_count", 0)

        # Extraer información de autores: nombre, ORCID, instituciones y país
        authors = []
        for authorship in data.get("authorships", []):
            author = authorship.get("author") or {}
            name = author.get("display_name")
            orcid = author.get("orcid")

            institutions = []
            for inst in authorship.get("institutions", []) or []:
                inst_name = inst.get("display_name")
                country = inst.get("country") or {}
                country_code = inst.get("country_code")
                country_code = country.get("country_code") or country.get("iso_code") or country_code

                institutions.append({
                    "name": inst_name,
                    "country_code": country_code,
                })

            authors.append({
                "name": name,
                "orcid": orcid,
                "institutions": institutions,
            })

        concepts = []
        for concept in data.get("concepts", []):
            concepts.append({
                "name": concept.get("display_name"),
                "level": concept.get("level"),
                "score": concept.get("score")
            })

        publication_date = data.get("publication_date")

        return {
            "id": id,
            "cited_by_count": cited_by_count,
            "publication_date": publication_date,
            "authors": authors,
            "concepts": concepts
        }
        
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            return {"error": f"No se encontró el paper con ID:{id}"}
        return {"error": f"Error HTTP en la petición: {e}"}
    except Exception as e:
        return {"error": f"Error inesperado: {e}"}