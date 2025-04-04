from pathlib import Path
from pypdf import PdfReader


def get_chunks(text: str, chunk_size: int, overlap_size: int) -> list[str]:
    """Splits a text into overlapping chunks of the same size."""
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i+chunk_size]
        chunks.append(chunk)
        i += chunk_size - overlap_size
    return chunks


def split_pdfs(pdf_files: list[str | Path], chunk_size: int = 512, overlap_size: int = 128) -> list[tuple[str, str]]:
    """Splits a list of PDF files into chunks and metadata."""
    docs = []
    for pdf in pdf_files:
        reader = PdfReader(pdf)
        num_pages = len(reader.pages)

        full_text = ""
        for i in range(num_pages):
            full_text += reader.pages[i].extract_text()

        chunks = get_chunks(full_text, chunk_size, overlap_size)
        chunks_metadata = [(chunk, pdf.name) for chunk in chunks]
        docs.extend(chunks_metadata)

    return docs

