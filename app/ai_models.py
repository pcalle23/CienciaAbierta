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
            "Data Science", "Open Science", "Robotics", "Bioinformatics", "Cloud Computing"
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
        
        for entity in results:
            # Filtrar por un score de confianza (threshold)
            if entity['score'] > 0.75:
                if entity['entity_group'] == 'ORG':
                    entities["organizations"].add(entity['word'])
                elif entity['entity_group'] == 'PER':
                    entities["persons"].add(entity['word'])
                elif entity['entity_group'] == 'MISC': # A menudo los proyectos caen aquí
                    entities["projects"].add(entity['word'])
                    
        # Convertir sets a listas para retornarlo
        return {k: list(v) for k, v in entities.items()}

    def assign_topics(self, abstract):
        """
        Asigna tópicos a un abstract devolviendo el tópico y su probabilidad (Clase N-Aria).
        """
        if not abstract:
            return []
            
        result = self.topic_pipeline(abstract, self.candidate_topics, multi_label=True)
        
        # Emparejar cada tópico con su probabilidad (score)
        topics_with_scores = []
        for label, score in zip(result['labels'], result['scores']):
            if score > 0.6: # Threshold para considerar que pertenece al topic
                topics_with_scores.append({
                    "topic": label,
                    "probability": round(score, 4)
                })
                
        return topics_with_scores

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