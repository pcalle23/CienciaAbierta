import time

from grobid_client.grobid_client import GrobidClient
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

def process_pdf_with_grobid(pdf_path, client: GrobidClient):
    """
    Process a PDF file with GROBID and extract abstract, figures count, and links.
    
    Args:
        pdf_path: Path to the PDF file
        client: GrobidClient instance
    
    Returns:
        Dictionary with extracted information: {
            'title': str,
            'abstract': str,
            'figures_count': int,
            'links': list of str
        }
    """
    # Process PDF with GROBID client
    xml_content = client.process_pdf( service="processFulltextDocument",
                                      generateIDs=False,
                                      pdf_file=str(pdf_path),
                                      consolidate_header=True,
                                      consolidate_citations=False,
                                      include_raw_citations=False,
                                      include_raw_affiliations=False,
                                      tei_coordinates=False,
                                      segment_sentences=False)
        
    return extract_paper_info(xml_content[2])


def extract_paper_info(xml_content):
    """
    Extract abstract, figures count, and links from GROBID XML output.
    
    Args:
        xml_content: XML string from GROBID
    
    Returns:
        Dictionary with extracted information
    """
    root = ET.fromstring(xml_content)
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    # Extract title
    title_elem = root.find('.//tei:titleStmt/tei:title', ns)
    title = title_elem.text if title_elem is not None and title_elem.text else ""
    
    # Extract abstract
    abstract_elem = root.find('.//tei:abstract', ns)
    abstract = ""
    if abstract_elem is not None:
        abstract = ''.join(abstract_elem.itertext()).strip()

    ack_elem = root.find('.//tei:div[@type="acknowledgement"]', ns)    
    ack_text = ""
    if ack_elem is not None:
        ack_text = ''.join(ack_elem.itertext()).strip()
    
    return {
        'title': title,
        'abstract': abstract,
        'acknowledgement': ack_text
    }


def process_dataset(dataset_dir, grobid_url):
    """
    Process all PDFs in a dataset directory with GROBID.
    
    Args:
        dataset_dir: Directory containing PDF files
        grobid_url: URL of the GROBID service
    
    Returns:
        List of dictionaries with paper information
    """

    try:
        if grobid_url != "http://localhost:8070" and grobid_url != "http://127.0.0.1:8070":
            time.sleep(30) # Wait for GROBID to be ready
        client = GrobidClient(grobid_server=grobid_url)
    except Exception as e:
        print(f"Error initializing GROBID client: {str(e)}")
        sys.exit(1)
        
    dataset_path = Path(dataset_dir)
    pdf_files = list(dataset_path.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    results = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        try:
            print(f"[{i}/{len(pdf_files)}] Processing {pdf_file.name}...")
            
            info = process_pdf_with_grobid(pdf_file, client)
            info['paper_id'] = pdf_file.stem   
            results.append(info)
            
        except Exception as e:
            print(f"Error: {str(e)}")
    
    return results