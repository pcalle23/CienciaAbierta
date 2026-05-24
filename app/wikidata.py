import requests

def get_wikidata_id(org_name):
    """Obtiene el identificador Q de Wikidata (ej. Q37156) para una entidad dada."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "search": org_name
    }
    
    headers = {
        "User-Agent": "CienciaAbiertaExtractor/1.0"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("search"):
            keywords = ["agency", "organization", "university", "company", "research", "administration", "institute", "institution", "department", "agencia", "universidad", "empresa"]
            
            for result in data["search"]:
                desc = result.get("description", "").lower()
                if any(kw in desc for kw in keywords):
                    return result["id"]
                    
            return data["search"][0]["id"]
            
    except Exception as e:
        print(f"Error al buscar en Wikidata '{org_name}': {e}")
        
    return None

def get_organization_info(org_name):
    """
    Obtiene tipo (P31), nombre oficial (P1448) y país (P17) de una organización desde Wikidata.
    """
    wikidata_id = get_wikidata_id(org_name)
    if not wikidata_id:
        return {"error": f"No se encontró entidad para '{org_name}'"}
        
    sparql_url = "https://query.wikidata.org/sparql"
    
    query = f"""
    SELECT ?typeLabel ?officialName ?countryLabel ?countryCode WHERE {{
      BIND(wd:{wikidata_id} AS ?org)
      OPTIONAL {{ ?org wdt:P31 ?type. }}
      OPTIONAL {{ ?org wdt:P1448 ?officialName. }}
      OPTIONAL {{ 
        ?org wdt:P17 ?country. 
        OPTIONAL {{ ?country wdt:P298 ?countryCode. }}
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en", "es". }}
    }}
    LIMIT 1
    """
    
    headers = {
        "User-Agent": "CienciaAbiertaExtractor/1.0",
        "Accept": "application/sparql-results+json"
    }
    
    try:
        response = requests.get(sparql_url, params={"query": query}, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        bindings = data.get("results", {}).get("bindings", [])
        if bindings:
            item = bindings[0]
            return {
                "wikidata_id": wikidata_id,
                "organization_type": item.get("typeLabel", {}).get("value", "Desconocido"),
                "official_name": item.get("officialName", {}).get("value", org_name),
                "country": item.get("countryLabel", {}).get("value", "Desconocido"),
                "country_iso3": item.get("countryCode", {}).get("value", "Desconocido")
            }
        else:
            return {"error": f"No se encontraron propiedades (P31, P1448, P17) para {wikidata_id}"}
            
    except Exception as e:
        return {"error": f"Error en la consulta SPARQL: {e}"}