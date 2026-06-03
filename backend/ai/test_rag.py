from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase
from unittest.mock import patch

from .models import Document, DocumentChunk, RAGQuery
from .rag_services import chunk_text


class RAGServiceTests(APITestCase):
    def test_chunk_text_uses_overlap(self):
        text = "a" * 1200
        chunks = chunk_text(text)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(len(chunks[0]["text"]), 1000)


class RAGAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="raguser",
            email="rag@example.com",
            password="strong-pass-123",
            email_verified=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("ai.rag_services.index_document")
    def test_upload_txt_document_creates_chunks(self, mocked_index):
        upload = SimpleUploadedFile(
            "notes.txt",
            b"Python skills include Django, REST API, SQL, and React.",
            content_type="text/plain",
        )

        response = self.client.post("/api/rag/upload/", {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Document.objects.filter(user=self.user).count(), 1)
        self.assertEqual(DocumentChunk.objects.count(), 1)
        mocked_index.assert_called_once()

    @patch("ai.rag_views.answer_document_question")
    def test_rag_chat_stores_query(self, mocked_answer):
        document = Document.objects.create(
            user=self.user,
            filename="notes.txt",
            file_data=b"Python skills include Django.",
            file_type="txt",
            file_size=10,
            processed=True,
        )
        mocked_answer.return_value = {
            "answer": "Python and Django are mentioned.",
            "sources": [{"filename": "notes.txt", "page_number": None}],
        }

        response = self.client.post(
            "/api/rag/chat/",
            {"message": "What skills are mentioned?", "document_id": document.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(RAGQuery.objects.filter(user=self.user).count(), 1)
        self.assertIn("Python", response.data["answer"])
