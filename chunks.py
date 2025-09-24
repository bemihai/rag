from pathlib import Path
from pypdf import PdfReader
from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition


def get_chunks(text: str, chunk_size: int, overlap_size: int) -> list[str]:
    """Splits a text into overlapping chunks of the same size."""
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i+chunk_size]
        chunks.append(chunk)
        i += chunk_size - overlap_size
    return chunks


def split_pdfs_v0(pdf_files: list[str | Path], chunk_size: int = 512, overlap_size: int = 128) -> list[tuple[str, str]]:
    """
    Splits a list of PDF files into chunks and metadata.
    Each chunk is a string of fixed length, and the metadata contains the name of the PDF file.
    """
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


def split_file(
        file: str | Path,
        strategy: str = "basic",
        chunk_size: int = 512,
        overlap_size: int = 128,
        **kwargs,
):
    """
    Splits a text file into chunks and metadata using the `unstructured` library.
    Available chunking strategies: `basic` and `by_title`.
    See this link for more details on unstructured chunking:
    https://docs.unstructured.io/open-source/core-functionality/chunking

    Args:
        file: The path to the text file.
        strategy: Chunking strategy to use ("basic" or "by_title"). Default is "basic".
        chunk_size: The maximum size of the chunk. Default is 512.
        overlap_size: Size of overlap between chunks when using text-splitting to break up an oversized chunk.
            Default is 128.
        kwargs: Additional arguments to pass to the chunking functions.

    Returns a list of `unstructured` chunks.
    """
    chunks = []

    try:
        elements = partition(filename=file)
        if strategy == "basic":
            chunks = chunk_elements(elements, max_characters=chunk_size, overlap=overlap_size, **kwargs)
        elif strategy == "by_title":
            chunks = chunk_by_title(elements, max_characters=chunk_size, overlap=overlap_size, **kwargs)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
    except RuntimeError as err:
        print(f"Error processing file {file}: {err}")

    return chunks


