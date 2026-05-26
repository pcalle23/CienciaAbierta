# Artificial Intelligence And Open Science In Research Software Engineering

## Miembros

| Nº  | Nombre                    | Usuario GitHub |
| --- | ------------------------- | -------------- |
| 1   | Pablo Calle Tercero       | @pcalle23      |
| 2   | Javier de la Luna Jimenez | @javierlj04    |
| 3   | Miguel Jimenez Sandoval   | @MiguelJS-UPM  |
| 4   | Mario Jimenez Gordo       | @02mario       |

## Descripción del Proyecto

Este proyecto desarrolla un **Knowledge Graph (Grafo de Conocimiento)** que integra datos de investigación científica mediante el uso de Inteligencia Artificial y Web Semántica. El sistema procesa automáticamente 30 artículos científicos (PDFs) para extraer metadatos, identificar entidades financiadoras, asignar tópicos mediante modelos de lenguaje y establecer redes de colaboración internacional. Además, cuenta con una interfaz visual para la consulta interactiva de los datos.

## Arquitectura y Tecnologías

Hemos implementado una arquitectura basada en microservicios:

- **Procesamiento de Lenguaje:** [Grobid](https://grobid.readthedocs.io/) para la extracción de texto estructurado de PDFs.
- **Inteligencia Artificial:** Modelos de [Hugging Face](https://huggingface.co/) (BERT para NER, SentenceTransformers para similitud y BART para clasificación de tópicos).
- **Integración de Datos:** Consultas en tiempo real a APIs de [OpenAlex](https://openalex.org/), [ORCID](https://orcid.org/) y [Wikidata](https://www.wikidata.org/).
- **Modelado Semántico:** Generación de grafos en formato Turtle (`.ttl`) cumpliendo estándares W3C (schema.org, FOAF, ORG).
- **Almacenamiento y Consulta:** Servidor [Apache Jena Fuseki](https://jena.apache.org/documentation/fuseki2/) para alojar el grafo.
- **Visualización:** [Streamlit](https://streamlit.io/) para el dashboard interactivo y consultas SPARQL.

---

## Instalación y Ejecución

Para ejecutar el sistema desde cero, asegúrese de tener instalado [Docker](https://www.docker.com/) y Python 3.12+.

### 1. Clonar el repositorio e instalar dependencias

```bash
git clone https://github.com/pcalle23/CienciaAbierta.git
cd CienciaAbierta

# Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate  # (En Windows usar: venv\Scripts\activate)

# Instalar librerías
pip install -r requirements.txt
```

### 2. Levantar los servidores (Docker)

```
Es necesario iniciar el motor de extracción de PDFs y la base de datos en grafo. Abra una terminal y ejecute:

# Servidor Grobid (Puerto 8070)
docker run -d --rm --name grobid -p 8070:8070 lfoppiano/grobid:0.8.2

# Servidor Apache Jena Fuseki (Puerto 3030)
docker run -d --name fuseki -p 3030:3030 -e ADMIN_PASSWORD=admin secoresearch/fuseki
```

### 3. Ejecutar el Pipeline de IA (Generación del Grafo)

```
Para cargar los datos de los artículos científicos, es necesario que estos tengan como nombre su identificador de arXiv (por ejemplo, 1234.12345.pdf) otra opción es usar el identificador propio de OpenAlex (W123456) y estén ubicados en la carpeta `dataset/`. Luego, ejecute el script principal para procesar los PDFs de la carpeta dataset/ y generar el archivo knowledge_graph.ttl.
```

```bash
cd app
python main.py
```

### 4. Cargar datos en Fuseki

```
Acceda a http://localhost:3030 (Usuario: admin, Contraseña: admin).

Vaya a Manage datasets -> Add new dataset.

Nombre: graph | Tipo: In-memory (o Persistent).

Suba el archivo knowledge_graph.ttl generado en el paso anterior.
```

### 5. Iniciar el Dashboard Interactivo (Demo)

```
Para lanzar la aplicación visual y realizar consultas al grafo:
```

```bash
python -m streamlit run app.py
```

```
📊 Demostración del Caso de Uso
La interfaz gráfica expone varios gráficos y tablas que permiten explorar los datos del grafo. Por ejemplo, se puede visualizar los países y sus proyectos, filtrar por un tópico específico, ver las redes de colaboración entre instituciones y obtener toda la información de un artículo.
```:

Usos de IA en el desarrollo
Se ha utilizado Inteligencia Artificial como asistencia para:

Asegurar que las propiedades no son redundantes entre ellas y son coherentes con el diagrama.

Asegurar que las relaciones entre las entidades son correctas.

Asistencia en la generación del código.
```
