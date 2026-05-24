from grobid import process_dataset
import os

def main():
    # Resolve dataset and output paths relative to workdir if not absolute
    dataset_path = "dataset"
    grobid_url = "http://127.0.0.1:8070"

    if not os.path.exists(dataset_path):
        os.makedirs(dataset_path, exist_ok=True)

    # Se obtiene diccionario con claves {'title', 'abstract', 'acknowledgement', 'paper_id'} y su contenido
    grobid_results = process_dataset(dataset_path, grobid_url)
    print(grobid_results)

if __name__ == "__main__":
    main()