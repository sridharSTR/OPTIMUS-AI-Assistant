import hashlib
import math
import re
from io import BytesIO

from django.conf import settings
from django.db import models
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import Document, DocumentChunk
from .services import get_ai_response


ALLOWED_TYPES = {"pdf", "docx", "txt"}


def validate_upload(uploaded_file):
    extension = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if extension not in ALLOWED_TYPES:
        raise ValidationError("Only PDF, DOCX, and TXT files are supported.")
    max_bytes = settings.RAG_MAX_UPLOAD_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValidationError(f"File must be {settings.RAG_MAX_UPLOAD_MB} MB or smaller.")
    return extension


def create_and_process_document(user, uploaded_file):
    file_type = validate_upload(uploaded_file)
    uploaded_file.seek(0)
    file_data = uploaded_file.read()
    document = Document.objects.create(
        user=user,
        filename=uploaded_file.name,
        file_data=file_data,
        file_type=file_type,
        file_size=uploaded_file.size,
    )
    try:
        process_document(document)
    except Exception:
        document.delete()
        raise
    return document


def process_document(document):
    try:
        text, page_map = extract_text(document)
        text = sanitize_text(text)
        chunks = chunk_text(text, page_map)
        with transaction.atomic():
            document.extracted_text = text
            document.processed = True
            document.processing_error = ""
            document.save(update_fields=["extracted_text", "processed", "processing_error"])
            document.chunks.all().delete()
            chunk_rows = [
                DocumentChunk(
                    document=document,
                    chunk_index=index,
                    chunk_text=item["text"],
                    page_number=item.get("page_number"),
                )
                for index, item in enumerate(chunks)
            ]
            DocumentChunk.objects.bulk_create(chunk_rows)
        index_document(document)
    except Exception as exc:
        document.processed = False
        document.processing_error = str(exc)
        document.save(update_fields=["processed", "processing_error"])
        raise


def extract_text(document):
    data = bytes(document.file_data)

    if document.file_type == "pdf":
        return extract_pdf_text(data)
    if document.file_type == "docx":
        return extract_docx_text(data), []
    if document.file_type == "txt":
        return data.decode("utf-8", errors="ignore"), []
    raise ValidationError("Unsupported file type.")


def extract_pdf_text(data):
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader

    reader = PdfReader(BytesIO(data))
    pages = []
    page_map = []
    cursor = 0
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(page_text)
        page_map.append((cursor, cursor + len(page_text), index))
        cursor += len(page_text) + 1
    return "\n".join(pages), page_map


def extract_docx_text(data):
    from docx import Document as DocxDocument

    doc = DocxDocument(BytesIO(data))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())


def sanitize_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text, page_map=None):
    if not text:
        raise ValidationError("No readable text was found in this document.")
    size = settings.RAG_CHUNK_SIZE
    overlap = settings.RAG_CHUNK_OVERLAP
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"text": chunk, "page_number": page_for_offset(start, page_map or [])})
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def page_for_offset(offset, page_map):
    for start, end, page in page_map:
        if start <= offset <= end:
            return page
    return None


def index_document(document):
    return None


def delete_document_vectors(document):
    return None


def search_documents(user, query, document_id=None, top_k=None):
    top_k = top_k or settings.RAG_TOP_K
    return database_vector_search(user, query, document_id=document_id, top_k=top_k)


def answer_document_question(user, message, document_id=None):
    chunks = search_documents(user, message, document_id=document_id)
    if not chunks:
        return {
            "answer": "I could not find that information in the uploaded documents.",
            "sources": [],
        }
    context = "\n\n".join(
        f"Source {index}: {chunk['filename']} page {chunk['page_number'] or 'N/A'}\n{chunk['text']}"
        for index, chunk in enumerate(chunks, start=1)
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are OPTIMUS. Answer using ONLY the retrieved document context. "
                "If the answer is not present, say: I could not find that information in the uploaded documents. "
                "Include a short Sources section using the provided filenames and pages."
            ),
        },
        {
            "role": "user",
            "content": f"Retrieved document context:\n\n{context}\n\nQuestion: {message}",
        },
    ]
    answer = get_ai_response(messages)
    return {"answer": answer, "sources": source_list(chunks)}


def source_list(chunks):
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk["document_id"], chunk["page_number"], chunk["chunk_id"])
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "document_id": chunk["document_id"],
                "chunk_id": chunk["chunk_id"],
                "filename": chunk["filename"],
                "page_number": chunk["page_number"],
                "score": chunk["score"],
            }
        )
    return sources


def database_vector_search(user, query, document_id=None, top_k=5):
    queryset = DocumentChunk.objects.filter(document__user=user, document__processed=True)
    if document_id:
        queryset = queryset.filter(document_id=document_id)
    query_vector = hash_embedding(query)
    scored = []
    for chunk in queryset.select_related("document"):
        chunk_vector = hash_embedding(chunk.chunk_text)
        scored.append(
            (
                cosine_similarity(query_vector, chunk_vector),
                {
                    "text": chunk.chunk_text,
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "filename": chunk.document.filename,
                    "page_number": chunk.page_number,
                    "score": None,
                },
            )
        )
    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, item in scored[:top_k]:
        item["score"] = round(score, 4)
        results.append(item)
    return results


def cosine_similarity(left, right):
    return sum(a * b for a, b in zip(left, right))


def hash_embedding(text, dimensions=384):
    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1 if digest[4] % 2 == 0 else -1
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def rag_analytics(user):
    documents = Document.objects.filter(user=user)
    return {
        "total_documents": documents.count(),
        "total_chunks": DocumentChunk.objects.filter(document__user=user).count(),
        "search_count": user.rag_queries.count(),
        "chat_count": user.rag_queries.exclude(answer="").count(),
        "most_queried_documents": list(
            documents.filter(queries__isnull=False)
            .values("id", "filename")
            .annotate(query_count=models.Count("queries"))
            .order_by("-query_count")[:5]
        ),
    }
