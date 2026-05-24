# Artificial Intelligence And Open Science In Research Software Engineering

## Miembros

| Nº  | Nombre                    | Usuario GitHub |
| --- | ------------------------- | -------------- |
| 1   | Pablo Calle Tercero       | @pcalle23      |
| 2   | Javier de la Luna Jimenez | @javierlj04    |
| 3   | Miguel Jimenez Sandoval   | @MiguelJS-UPM  |
| 4   | Mario Jimenez Gordo       | @02mario       |

## Descripción del Proyecto

Este proyecto desarrolla un **Knowledge Graph (Grafo de Conocimiento)** que integra datos de investigación científica mediante el uso de Inteligencia Artificial y Web Semántica. El sistema procesa automáticamente artículos científicos (PDFs) para extraer metadatos, identificar entidades financiadoras, asignar tópicos mediante modelos de lenguaje y establecer redes de colaboración internacional.

## Arquitectura y Tecnologías

Hemos implementado una arquitectura basada en microservicios:

- **Procesamiento de Lenguaje:** [Grobid](https://grobid.readthedocs.io/) para la extracción de texto estructurado de PDFs.
- **Inteligencia Artificial:** Modelos de [Hugging Face](https://huggingface.co/) (BERT para NER, SentenceTransformers para similitud y BART para clasificación de tópicos).
- **Integración de Datos:** Consultas en tiempo real a APIs de [OpenAlex](https://openalex.org/), [ORCID](https://orcid.org/) y [Wikidata](https://www.wikidata.org/).
- **Modelado Semántico:** Generación de grafos en formato Turtle (`.ttl`) cumpliendo estándares W3C (schema.org, FOAF, ORG).

## Instalación y Ejecución

Para ejecutar el sistema desde cero, asegúrese de tener instalado [Docker](https://www.docker.com/) y Python 3.12+.

1. **Clonar el repositorio:**

   ```
   git clone [https://github.com/pcalle23/CienciaAbierta.git](https://github.com/pcalle23/CienciaAbierta.git)
   cd entrega-final/app
   ```

2. **Crear y activar entorno virtual:**

   ```
   python3 -m venv venv
   source venv/bin/activate  # (En Windows usar venv\Scripts\activate)
   ```

3. **Instalar dependencias:**

   ```
   pip install -r requirements.txt
   ```

4. **Levantar el servidor Grobid (Docker):**

   ```
   docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.1
   ```

5. **Ejecutar el pipeline:**
   ```
   python main.py
   ```

### Usos de IA

Se ha utilizado para:

- Asegurar que las propiedades no son redundantes entre ellas y son coherentes con el diagrama.
- Asegurar que las relaciones entre las entidades son correctas.
