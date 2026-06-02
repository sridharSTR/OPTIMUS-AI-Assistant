from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.test import APIClient, APITestCase

from .models import Memory, NLPEvent, ResponseCache
from .nlp import detect_intent, process_message
from .services import ProviderAPIException, get_ai_response


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

    def test_chat_save_memory_returns_sync_payload(self):
        response = self.client.post("/api/ai/chat/", {"message": "Save my favorite color is blue"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["memory_sync"]["action"], "save")
        self.assertEqual(response.data["memory_sync"]["status"], "success")
        self.assertEqual(response.data["memory_sync"]["updated_memory_list"][0]["key"], "color")
        self.assertEqual(response.data["memory_sync"]["updated_memory_list"][0]["value"], "blue")
        self.assertTrue(Memory.objects.filter(user=self.user, key="color", value="blue").exists())

    def test_chat_save_memory_deduplicates_overlapping_patterns(self):
        response = self.client.post("/api/ai/chat/", {"message": "save my favourite movie name is jersy"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["nlp"]["intent"], "save_memory")
        self.assertEqual(len(response.data["nlp"]["saved_memories"]), 1)
        self.assertEqual(response.data["nlp"]["saved_memories"][0]["key"], "movie_name")
        self.assertEqual(response.data["nlp"]["saved_memories"][0]["value"], "jersy")
        self.assertEqual(response.data["message"]["content"].count("movie_name"), 1)
        self.assertEqual(Memory.objects.filter(user=self.user, key="movie_name", value="jersy").count(), 1)

    def test_chat_update_memory_returns_sync_payload(self):
        Memory.objects.create(user=self.user, key="color", value="blue")

        response = self.client.post("/api/ai/chat/", {"message": "Update my favorite color to red"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["memory_sync"]["action"], "update")
        self.assertEqual(response.data["memory_sync"]["status"], "success")
        self.assertEqual(response.data["memory_sync"]["updated_memory_list"][0]["value"], "red")
        self.assertTrue(Memory.objects.filter(user=self.user, key="color", value="red").exists())

    def test_chat_delete_memory_returns_sync_payload(self):
        Memory.objects.create(user=self.user, key="color", value="blue")

        response = self.client.post("/api/ai/chat/", {"message": "Remove my color"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["memory_sync"]["action"], "delete")
        self.assertEqual(response.data["memory_sync"]["status"], "success")
        self.assertEqual(response.data["memory_sync"]["updated_memory_list"], [])
        self.assertFalse(Memory.objects.filter(user=self.user, key="color").exists())

    def test_chat_delete_memory_handles_typo_and_british_spelling(self):
        Memory.objects.create(user=self.user, key="color", value="blue")

        response = self.client.post("/api/ai/chat/", {"message": "delete you memory my favourite colour is blue"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["nlp"]["intent"], "delete_memory")
        self.assertFalse(response.data["nlp"]["ai_called"])
        self.assertEqual(response.data["memory_sync"]["action"], "delete")
        self.assertEqual(response.data["memory_sync"]["status"], "success")
        self.assertEqual(response.data["memory_sync"]["updated_memory_list"], [])
        self.assertFalse(Memory.objects.filter(user=self.user, key="color").exists())

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


class AIProviderFallbackTests(APITestCase):
    @patch("ai.services._gemini_response", return_value="Gemini fallback response")
    @patch("ai.services._openrouter_response", side_effect=ProviderAPIException("OpenRouter API error: invalid key", status_code=401))
    def test_auto_provider_falls_back_from_openrouter_auth_error(self, mocked_openrouter, mocked_gemini):
        with self.settings(AI_PROVIDER="auto", OPENROUTER_API_KEY="configured", GEMINI_API_KEY="configured"):
            response = get_ai_response([{"role": "user", "content": "Hello"}])

        self.assertEqual(response, "Gemini fallback response")
        self.assertEqual(mocked_openrouter.call_count, 1)
        self.assertEqual(mocked_gemini.call_count, 1)
