import os
# Desactivar advertencias de symlinks en Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

class AIProcessor:
    def __init__(self):
        print("Cargando modelos de IA (esto puede tardar la primera vez)...")
        # Modelo 1: NER (Named Entity Recognition) para los Acknowledgements
        self.ner_pipeline = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
        
        # Modelo 2: Similitud de abstracts (Embeddings)
        self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Modelo 3: Zero-Shot Classification para el Topic Modeling (con probabilidad)
        self.topic_pipeline = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        
        # Tópicos predefinidos de ejemplo basados en IA y Ciencia
        self.candidate_topics = [
            "Machine Learning", "Natural Language Processing", "Computer Vision",
            "Data Science", "Open Science", "Robotics", "Bioinformatics", "Cloud Computing", "Physics", "Chemistry"
        ]
        print("Modelos cargados correctamente.")

    def extract_entities(self, text):
        """
        Extrae Personas (PER), Organizaciones (ORG) y otras entidades (MISC/LOC) 
        de la sección de Agradecimientos.
        """
        if not text or len(text.strip()) == 0:
            return {"organizations": [], "persons": [], "projects": []}
            
        # El modelo a veces falla con textos excesivamente largos, recortamos si es necesario
        if len(text) > 1500:
            text = text[:1500]
            
        results = self.ner_pipeline(text)
        
        entities = {
            "organizations": set(),
            "persons": set(),
            "projects": set()
        }
        
        filtered_results = [entity for entity in results if entity['score'] > 0.85]
        filtered_results.sort(key=lambda x: x['score'], reverse=True)

        for entity in filtered_results:
            if entity['entity_group'] == 'ORG' and len(entity['word']) > 1:
                entities["organizations"].add(entity['word'])
            elif entity['entity_group'] == 'PER':
                entities["persons"].add(entity['word'])
            elif entity['entity_group'] == 'MISC': # A menudo los proyectos caen aquí
                entities["projects"].add(entity['word'])

        return {
            key: list(value)[:5]
            for key, value in entities.items()
        }

    def assign_topics(self, abstract):
        """
        Asigna tópicos a un abstract devolviendo el tópico y su probabilidad (Clase N-Aria).
        """
        if not abstract:
            return []
            
        result = self.topic_pipeline(abstract, self.candidate_topics, multi_label=True)
        
        ranked_topics = [
            {"topic": label, "probability": round(score, 4)}
            for label, score in sorted(
                zip(result['labels'], result['scores']),
                key=lambda item: item[1],
                reverse=True,
            )
            if score > 0.6
        ]

        unique_topics = []
        seen_topics = set()
        for topic in ranked_topics:
            if topic["topic"] in seen_topics:
                continue
            seen_topics.add(topic["topic"])
            unique_topics.append(topic)
            if len(unique_topics) == 5:
                break

        return unique_topics

    def compute_similarity(self, abstract_1, abstract_2):
        """
        Calcula la similitud de coseno entre dos abstracts.
        """
        if not abstract_1 or not abstract_2:
            return 0.0
            
        emb1 = self.similarity_model.encode(abstract_1)
        emb2 = self.similarity_model.encode(abstract_2)
        
        cos_sim = util.cos_sim(emb1, emb2)
        # Retorna el valor float
        return round(cos_sim.item(), 4)

# ==== Código de prueba local ====
if __name__ == "__main__":
    ai = AIProcessor()
    
    # 1. Prueba de NER (Agradecimientos)
    ack_text = "We would like to thank our collaborators at Stanford University, specifically Dr. Andrew Ng, for funding the DeepLearning project."
    print("\n--- Extracción de Entidades NER ---")
    print(ai.extract_entities(ack_text))
    
    # 2. Prueba de Tópicos (N-aria con probabilidad)
    abstract = "This paper introduces a new neural network architecture for parsing natural language text efficiently."
    print("\n--- Asignación de Tópicos ---")
    print(ai.assign_topics(abstract))
    
    # 3. Prueba de Similitud
    abstract_2 = "We propose an efficient deep learning model focused on text parsing and NLP tasks."
    print("\n--- Similitud (Threshold) ---")
    print(f"Score de similitud: {ai.compute_similarity(abstract, abstract_2)}")