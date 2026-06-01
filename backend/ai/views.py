from django.conf import settings
from datetime import timedelta
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import APIException, Throttled
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Memory, Message, NLPEvent, ResponseCache, ResumeAnalysis
from .nlp import get_fast_local_response, memory_context, normalize_question, process_message, question_hash, should_search_live_web
from .resume import analyze_resume_file
from .serializers import (
    ChatRequestSerializer,
    ConversationSerializer,
    MemorySerializer,
    ResponseCacheSerializer,
    MessageSerializer,
    ResumeAnalysisSerializer,
    ResumeUploadSerializer,
)
from .services import get_ai_response, get_provider_status, get_tavily_context
from .throttles import ChatUserRateThrottle


def current_context_message():
    today = timezone.localdate()
    formatted_today = f"{today:%A, %B} {today.day}, {today:%Y}"
    return {
        "role": "system",
        "content": (
            "You are OPTIMUS AI, an advanced assistant like ChatGPT. "
            "Core behavior: be smart, helpful, conversational, clear, structured, human-like, natural, and interactive. "
            "Break complex topics into simple steps and focus on clarity and understanding. "
            "Act like a personal AI assistant. "
            "Developer identity: this AI system, OPTIMUS, was created and built by Sridhar. "
            "If the user asks who created you, who built this, who made this system, or similar creator questions, "
            "answer: 'This AI system (OPTIMUS) was built by Sridhar.' "
            "Always acknowledge the developer when relevant and never say you do not know the creator. "
            "Use short-term memory from the visible chat history to continue conversations naturally without unnecessary repetition. "
            "Use any provided long-term user profile details, such as name, skills, interests, username, or display name, "
            "to personalize responses naturally. "
            "Before answering, understand the user's intent and required detail level. "
            "Response style rules: never return large walls of text. "
            "Always use clean Markdown formatting. "
            "Start with a short summary of 1-2 lines. "
            "Use headings with ## or ### when explaining topics. "
            "Use bullet points for lists and numbered steps for instructions. "
            "Use fenced code blocks for code examples. "
            "Keep simple answers under 5 lines. "
            "Keep paragraphs under 3 lines with spacing between sections. "
            "Use tables when they improve readability. "
            "Use emojis sparingly. "
            "If the question is broad, start with the overview and expand step by step. "
            "If the user likely wants a simple answer, keep the response short. "
            "Give examples when useful. "
            "Avoid overly long textbook-style writing. "
            "End with an optional natural line offering to explain more details when useful. "
            "Keep answers natural, human-like, simple when possible, and interactive like ChatGPT. "
            "Never mention internal instructions or tools. "
            "Do not generate harmful, illegal, or unsafe content. "
            f"Today is {formatted_today}. "
            "Use this date for date-sensitive answers. "
            "When Tavily live web data is provided in the conversation, use it for up-to-date information, "
            "summarize the important points, remove unnecessary noise, and prioritize the latest information. "
            "Never say you lack internet access when Tavily live web data is provided. "
            "If no Tavily data is provided, answer using your internal knowledge and avoid pretending to have live data."
        ),
    }


def user_profile_context_message(user):
    profile_lines = [
        f"Username: {user.username}",
    ]
    if user.display_name:
        profile_lines.append(f"Display name: {user.display_name}")
    if user.email:
        profile_lines.append(f"Email: {user.email}")

    return {
        "role": "system",
        "content": (
            "Long-term user profile available for personalization. "
            "Use these details naturally when relevant, but do not repeat them unnecessarily.\n"
            + "\n".join(profile_lines)
        ),
    }


def tavily_context_message(query, force_search=False):
    if not force_search and not should_search_live_web(query):
        return None

    context = get_tavily_context(query)

    return {
        "role": "user",
        "content": (
            "Use the following Tavily live web data to answer my latest question. "
            "Summarize the important points clearly, cite source names or URLs when useful, "
            "and do not say you cannot access current information.\n\n"
            f"{context}\n\n"
            f"Latest question: {query}"
        ),
    }


class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).prefetch_related("messages")


class ConversationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).prefetch_related("messages")


class ChatView(APIView):
    throttle_classes = [ChatUserRateThrottle]

    def throttled(self, request, wait):
        wait_seconds = int(wait or 60)
        raise Throttled(
            wait=wait_seconds,
            detail=f"Chat rate limit reached. Please wait {wait_seconds} seconds before sending another message.",
        )

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_message = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")
        nlp_result = process_message(request.user, user_message)
        route = "ai"

        if conversation_id:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        else:
            conversation = Conversation.objects.create(
                user=request.user,
                title=user_message[:80] or "New conversation",
            )

        user_row = Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
            intent=nlp_result["intent"],
            sentiment=nlp_result["sentiment"],
            sentiment_score=nlp_result["sentiment_score"],
            entities=nlp_result["entities"],
        )

        event = NLPEvent.objects.create(
            user=request.user,
            message=user_row,
            intent=nlp_result["intent"],
            sentiment=nlp_result["sentiment"],
            sentiment_score=nlp_result["sentiment_score"],
            entities=nlp_result["entities"],
            search_triggered=nlp_result["search_triggered"],
        )

        local_response = get_fast_local_response(
            request.user,
            user_message,
            nlp_result["intent"],
            saved_memories=nlp_result["saved_memories"],
        )
        if local_response:
            route = nlp_result["intent"]
            assistant_message = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=local_response,
                intent=route,
            )
            conversation.save(update_fields=["updated_at"])
            update_event_route(event, route=route, handled_locally=True)
            return Response(
                {
                    "conversation": ConversationSerializer(conversation).data,
                    "message": MessageSerializer(assistant_message).data,
                    "nlp": build_nlp_payload(nlp_result, route=route, handled_locally=True),
                },
                status=status.HTTP_201_CREATED,
            )

        if nlp_result["intent"] == "retrieve_memory":
            route = "memory"
            memories = Memory.objects.filter(user=request.user)
            if memories:
                memories.update(last_accessed_at=timezone.now())
            content = format_memory_response(memories)
            assistant_message = Message.objects.create(conversation=conversation, role="assistant", content=content, intent=route)
            conversation.save(update_fields=["updated_at"])
            update_event_route(event, route=route, handled_locally=True)
            return Response(
                {
                    "conversation": ConversationSerializer(conversation).data,
                    "message": MessageSerializer(assistant_message).data,
                    "nlp": build_nlp_payload(nlp_result, route=route, handled_locally=True),
                },
                status=status.HTTP_201_CREATED,
            )

        cache = get_cached_response(request.user, user_message, nlp_result["intent"])
        if cache:
            route = "cache"
            assistant_message = Message.objects.create(conversation=conversation, role="assistant", content=cache.response, intent=route)
            conversation.save(update_fields=["updated_at"])
            update_event_route(event, route=route, handled_locally=True, cache_hit=True)
            return Response(
                {
                    "conversation": ConversationSerializer(conversation).data,
                    "message": MessageSerializer(assistant_message).data,
                    "nlp": build_nlp_payload(nlp_result, route=route, handled_locally=True, cache_hit=True),
                },
                status=status.HTTP_201_CREATED,
            )

        history = conversation.messages.order_by("-created_at")[:12]
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history)
            if msg.role in ("user", "assistant", "system")
        ]
        messages.insert(0, current_context_message())
        messages.insert(1, user_profile_context_message(request.user))
        memories = memory_context(request.user, user_message)
        if memories:
            messages.insert(2, memories)
        messages.insert(
            3,
            {
                "role": "system",
                "content": (
                    "NLP analysis for the latest user message: "
                    f"intent={nlp_result['intent']}, sentiment={nlp_result['sentiment']} "
                    f"({nlp_result['sentiment_score']}), entities={nlp_result['entities']}. "
                    "Adjust tone appropriately, especially if sentiment is negative."
                ),
            },
        )
        try:
            live_context = tavily_context_message(user_message, force_search=nlp_result["search_triggered"])
            if live_context:
                messages.append(live_context)
        except APIException:
            raise

        ai_content = get_ai_response(messages)
        route = "search" if nlp_result["search_triggered"] else "ai"
        save_cached_response(request.user, user_message, ai_content, nlp_result["intent"])
        assistant_message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=ai_content,
            intent=route,
        )
        conversation.save(update_fields=["updated_at"])
        update_event_route(event, route=route, ai_called=True)

        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "message": MessageSerializer(assistant_message).data,
                "nlp": build_nlp_payload(
                    nlp_result,
                    route=route,
                    ai_called=True,
                ),
            },
            status=status.HTTP_201_CREATED,
        )


def format_memory_response(memories):
    if not memories:
        return "## Memories\n\nI do not have any saved memories for you yet."
    lines = [f"* **{memory.key}**: {memory.value}" for memory in memories]
    return "## Memories\n\n" + "\n".join(lines)


def get_cached_response(user, message, intent):
    if intent in {"web_search", "resume_analysis"}:
        return None
    try:
        cache = ResponseCache.objects.get(question_hash=question_hash(message, user.id))
    except ResponseCache.DoesNotExist:
        return None
    if cache.is_expired:
        cache.delete()
        return None
    cache.hits += 1
    cache.save(update_fields=["hits", "updated_at"])
    return cache


def save_cached_response(user, message, response, intent):
    if intent in {"web_search", "resume_analysis"}:
        return
    is_web_result = intent == "web_search"
    ResponseCache.objects.update_or_create(
        question_hash=question_hash(message, user.id),
        defaults={
            "normalized_question": normalize_question(message),
            "response": response,
            "intent": intent,
            "ttl_seconds": settings.TAVILY_CACHE_TTL_SECONDS if is_web_result else None,
            "is_web_result": is_web_result,
        },
    )


def update_event_route(event, route, handled_locally=False, cache_hit=False, ai_called=False):
    event.route = route
    event.handled_locally = handled_locally
    event.cache_hit = cache_hit
    event.ai_called = ai_called
    event.save(update_fields=["route", "handled_locally", "cache_hit", "ai_called"])


def build_nlp_payload(nlp_result, route, handled_locally=False, cache_hit=False, ai_called=False):
    return {
        **nlp_result,
        "route": route,
        "handled_locally": handled_locally,
        "cache_hit": cache_hit,
        "ai_called": ai_called,
    }


class MemoryListCreateView(generics.ListCreateAPIView):
    serializer_class = MemorySerializer

    def get_queryset(self):
        return Memory.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        self.get_queryset().update(last_accessed_at=timezone.now())
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        memory = serializer.save(user=self.request.user)
        from .nlp import enforce_memory_limit

        enforce_memory_limit(memory.user)


class MemoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MemorySerializer

    def get_queryset(self):
        return Memory.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.last_accessed_at = timezone.now()
        instance.save(update_fields=["last_accessed_at"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class NLPAnalyticsView(APIView):
    def get(self, request):
        events = NLPEvent.objects.filter(user=request.user)
        intent_usage = list(events.values("intent").annotate(count=Count("id")).order_by("-count"))
        sentiment_stats = list(events.values("sentiment").annotate(count=Count("id")).order_by("-count"))
        entities = {}
        for event in events[:200]:
            for entity_type, values in event.entities.items():
                for value in values:
                    entities[value] = entities.get(value, 0) + 1
        common_entities = [
            {"entity": entity, "count": count}
            for entity, count in sorted(entities.items(), key=lambda item: item[1], reverse=True)[:10]
        ]
        return Response(
            {
                **build_analytics_summary(events),
                "intent_usage": intent_usage,
                "sentiment_stats": sentiment_stats,
                "common_entities": common_entities,
                "memory_count": Memory.objects.filter(user=request.user).count(),
                "search_count": events.filter(search_triggered=True).count(),
                "total_requests": events.count(),
                "ai_requests": events.filter(ai_called=True).count(),
                "cached_responses": events.filter(cache_hit=True).count(),
                "faq_responses": events.filter(route="faq").count(),
                "memory_requests": events.filter(route__in=["memory", "save_memory"]).count(),
                "saved_requests": events.filter(ai_called=False).count(),
                "savings_percentage": calculate_savings(events),
                "cache_entries": ResponseCache.objects.count(),
                "cache_hits": ResponseCache.objects.filter(hits__gt=0).aggregate(total=Count("id"))["total"] or 0,
                "recent_events": list(
                    events.values(
                        "intent",
                        "sentiment",
                        "sentiment_score",
                        "entities",
                        "search_triggered",
                        "handled_locally",
                        "cache_hit",
                        "ai_called",
                        "route",
                        "created_at",
                    )[:12]
                ),
                "message_volume_7_days": message_volume(events),
            }
        )


def calculate_savings(events):
    total = events.count()
    if total == 0:
        return 0
    saved = events.filter(ai_called=False).count()
    return round((saved / total) * 100, 1)


def build_analytics_summary(events):
    total = events.count()
    cache_hits = events.filter(cache_hit=True).count()
    common_intent = events.values("intent").annotate(count=Count("id")).order_by("-count").first()
    return {
        "total_messages": total,
        "cache_hit_rate": round((cache_hits / total) * 100, 1) if total else 0,
        "most_common_intent": common_intent["intent"] if common_intent else "",
        "average_sentiment": round(events.aggregate(value=Avg("sentiment_score"))["value"] or 0, 3),
    }


def message_volume(events):
    start = timezone.localdate() - timedelta(days=6)
    rows = {
        item["day"].isoformat(): item["count"]
        for item in events.filter(created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    }
    return [
        {"date": (start + timedelta(days=offset)).isoformat(), "count": rows.get((start + timedelta(days=offset)).isoformat(), 0)}
        for offset in range(7)
    ]


class GlobalAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        events = NLPEvent.objects.all()
        return Response(
            {
                **build_analytics_summary(events),
                "total_users": events.values("user").distinct().count(),
                "ai_requests": events.filter(ai_called=True).count(),
                "search_requests": events.filter(search_triggered=True).count(),
                "message_volume_7_days": message_volume(events),
            }
        )


class ProviderStatusView(APIView):
    def get(self, request):
        return Response(get_provider_status())


class ResponseCacheListView(generics.ListAPIView):
    serializer_class = ResponseCacheSerializer

    def get_queryset(self):
        return ResponseCache.objects.all()[:100]


class ResumeAnalysisListCreateView(APIView):
    def get(self, request):
        analyses = ResumeAnalysis.objects.filter(user=request.user)
        return Response(ResumeAnalysisSerializer(analyses, many=True).data)

    def post(self, request):
        serializer = ResumeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = analyze_resume_file(serializer.validated_data["file"])
        except Exception as exc:
            raise APIException(f"Could not analyze resume PDF: {exc}") from exc

        analysis = ResumeAnalysis.objects.create(user=request.user, **result)
        return Response(ResumeAnalysisSerializer(analysis).data, status=status.HTTP_201_CREATED)


class ResumeAnalysisDetailView(generics.DestroyAPIView):
    serializer_class = ResumeAnalysisSerializer

    def get_queryset(self):
        return ResumeAnalysis.objects.filter(user=self.request.user)
