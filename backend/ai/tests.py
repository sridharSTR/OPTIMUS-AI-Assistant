from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.test import APIClient, APITestCase

from .models import Memory, NLPEvent, ResponseCache
from .nlp import detect_intent, process_message


class NLPServiceTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sridhar",
            email="sridhar@example.com",
            password="strong-pass-123",
            email_verified=True,
        )

    def test_detects_supported_intents(self):
        cases = {
            "Latest AI news": "web_search",
            "Remember my favorite language is Python": "save_memory",
            "Show my memories": "retrieve_memory",
            "Analyze my resume": "resume_analysis",
            "Who created you?": "faq",
            "Hello": "greeting",
        }

        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(detect_intent(message), expected)

    def test_process_message_extracts_memory_and_sentiment(self):
        result = process_message(self.user, "My name is Sridhar and I am very happy today")

        self.assertEqual(result["sentiment"], "positive")
        self.assertTrue(Memory.objects.filter(user=self.user, key="name", value__icontains="Sridhar").exists())


class ChatNLPFlowTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sridhar",
            email="sridhar@example.com",
            password="strong-pass-123",
            email_verified=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_faq_is_answered_without_provider_call(self):
        response = self.client.post("/api/ai/chat/", {"message": "Who created you?"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["nlp"]["intent"], "faq")
        self.assertEqual(response.data["nlp"]["route"], "faq")
        self.assertFalse(response.data["nlp"]["ai_called"])
        self.assertIn("Sridhar", response.data["message"]["content"])
        self.assertEqual(NLPEvent.objects.filter(user=self.user, intent="faq").count(), 1)

    @patch("ai.views.get_ai_response", return_value="Django middleware processes requests and responses.")
    def test_general_chat_response_is_cached(self, mocked_ai):
        payload = {"message": "What is Django middleware?"}

        first = self.client.post("/api/ai/chat/", payload, format="json")
        second = self.client.post("/api/ai/chat/", payload, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data["nlp"]["route"], "ai")
        self.assertEqual(second.data["nlp"]["route"], "cache")
        self.assertTrue(second.data["nlp"]["cache_hit"])
        self.assertEqual(mocked_ai.call_count, 1)
        self.assertEqual(ResponseCache.objects.count(), 1)
