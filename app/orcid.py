import requests

def get_author_info(orcid_id):
    """
    Obtiene las palabras clave (keywords) y el país (country) de un autor
    usando la API pública de ORCID.
    """
    # Limpiamos el ORCID por si viene con la URL completa desde OpenAlex
    orcid_id = orcid_id.replace("https://orcid.org/", "").strip()
    
    url = f"https://pub.orcid.org/v3.0/{orcid_id}"
    
    # ORCID requiere que le pidamos explícitamente formato JSON
    headers = {
        "Accept": "application/json"
    }
    
    result = {
        "orcid": orcid_id,
        "keywords": [],
        "country": "Unknown"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extraer Keywords (Área de especialización)
        keywords_path = data.get("person", {}).get("keywords", {}).get("keyword", [])
        result["keywords"] = [kw.get("content") for kw in keywords_path if kw.get("content")]
        
        # Extraer País (Address)
        addresses_path = data.get("person", {}).get("addresses", {}).get("address", [])
        if addresses_path:
            # Cogemos el código de país de la primera dirección registrada
            country_code = addresses_path[0].get("country", {}).get("value")
            if country_code:
                result["country"] = country_code
                
    except Exception as e:
        print(f"Error al consultar ORCID {orcid_id}: {e}")
        
    return result

# ==== Código de prueba local ====
if __name__ == "__main__":
    # Probamos con el ORCID de Daniel Garijo (el profesor de las diapositivas)
    test_orcid = "0000-0003-0454-7145" 
    print(f"\n--- Consultando datos en ORCID para: {test_orcid} ---")
    datos_autor = get_author_info(test_orcid)
    print(datos_autor)