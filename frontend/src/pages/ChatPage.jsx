import { Activity, Bot, Brain, Clock3, FileSearch, Files, LogOut, Menu, MessageSquarePlus, Save, Search, Send, Sparkles, Trash2, UserRound, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import AppFooter from "../components/common/AppFooter.jsx";
import MessageBubble from "../components/MessageBubble.jsx";
import DocumentsPage from "./DocumentsPage.jsx";
import MemoryManager from "./MemoryManager.jsx";
import NLPAnalytics from "./NLPAnalytics.jsx";
import ResumeAnalyzer from "./ResumeAnalyzer.jsx";
import { authApi, chatApi } from "../services/api.js";

const formatProfileError = (data) => {
  if (!data) {
    return "Could not save your profile.";
  }

  if (typeof data === "string") {
    return data;
  }

  if (data.detail) {
    return data.detail;
  }

  const fieldErrors = Object.entries(data)
    .map(([field, messages]) => {
      const text = Array.isArray(messages) ? messages.join(" ") : String(messages);
      return `${field.replaceAll("_", " ")}: ${text}`;
    })
    .filter(Boolean);

  return fieldErrors.length ? fieldErrors.join(" ") : "Could not save your profile.";
};

const formatConversationTime = (value) => {
  if (!value) return "";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
};

function ChatPage({ user, onLogout, onUserUpdate, authEvent, onNavigate }) {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [chatSearch, setChatSearch] = useState("");
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileForm, setProfileForm] = useState({
    username: user.username || "",
    email: user.email || "",
    display_name: user.display_name || "",
  });
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [workspace, setWorkspace] = useState("chat");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef(null);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeId),
    [activeId, conversations],
  );

  const savedConversations = useMemo(
    () => conversations.filter((conversation) => conversation.id !== "draft"),
    [conversations],
  );

  const visibleConversations = useMemo(() => {
    const query = chatSearch.trim().toLowerCase();
    if (!query) return savedConversations;

    return savedConversations.filter((conversation) => {
      const title = conversation.title?.toLowerCase() || "";
      const messages = conversation.messages
        ?.map((message) => message.content)
        .join(" ")
        .toLowerCase() || "";

      return title.includes(query) || messages.includes(query);
    });
  }, [chatSearch, savedConversations]);

  const recentConversations = useMemo(
    () => visibleConversations.slice(0, 8),
    [visibleConversations],
  );

  useEffect(() => {
    chatApi
      .conversations()
      .then(({ data }) => {
        setConversations(data);
        setActiveId(data[0]?.id || null);
      })
      .catch(() => setError("Could not load conversations."));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConversation?.messages, loading]);

  useEffect(() => {
    setProfileForm({
      username: user.username || "",
      email: user.email || "",
      display_name: user.display_name || "",
    });
  }, [user]);

  const startNewChat = () => {
    setActiveId(null);
    setError("");
  };

  const selectConversation = (conversationId) => {
    setActiveId(conversationId);
    setError("");
    setSidebarOpen(false);
  };

  const deleteConversation = async (event, conversationId) => {
    event.stopPropagation();
    if (loading) return;

    const confirmed = window.confirm("Delete this chat?");
    if (!confirmed) return;

    setError("");
    try {
      await chatApi.deleteConversation(conversationId);
      setConversations((current) => {
        const next = current.filter((conversation) => conversation.id !== conversationId);
        if (conversationId === activeId) {
          setActiveId(next[0]?.id || null);
        }
        return next;
      });
    } catch {
      setError("Could not delete this chat.");
    }
  };

  const sendMessage = async (event) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const optimisticConversation = activeConversation || {
      id: "draft",
      title: trimmed.slice(0, 80),
      messages: [],
    };
    const optimisticMessages = [
      ...(optimisticConversation.messages || []),
      { id: `user-${Date.now()}`, role: "user", content: trimmed },
    ];

    if (!activeConversation) {
      setConversations((current) => [{ ...optimisticConversation, messages: optimisticMessages }, ...current]);
      setActiveId("draft");
    } else {
      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === activeId ? { ...conversation, messages: optimisticMessages } : conversation,
        ),
      );
    }

    setInput("");
    setLoading(true);
    setError("");

    try {
      const { data } = await chatApi.sendMessage({
        message: trimmed,
        conversation_id: activeId === "draft" ? null : activeId,
      });
      setConversations((current) => {
        const withoutDraft = current.filter((conversation) => conversation.id !== "draft");
        const next = withoutDraft.filter((conversation) => conversation.id !== data.conversation.id);
        return [data.conversation, ...next];
      });
      setActiveId(data.conversation.id);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = Array.isArray(detail) ? detail.join(" ") : detail;
      setError(message || "The AI request failed. Check your API key and backend logs.");
    } finally {
      setLoading(false);
    }
  };

  const openProfile = () => {
    setProfileForm({
      username: user.username || "",
      email: user.email || "",
      display_name: user.display_name || "",
    });
    setProfileError("");
    setProfileOpen(true);
  };

  const updateProfileForm = (event) => {
    setProfileForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const saveProfile = async (event) => {
    event.preventDefault();
    setProfileSaving(true);
    setProfileError("");

    try {
      const payload = {
        username: profileForm.username.trim(),
        email: profileForm.email.trim(),
        display_name: profileForm.display_name.trim(),
      };
      const { data } = await authApi.updateProfile(payload);
      onUserUpdate(data);
      setProfileOpen(false);
    } catch (err) {
      setProfileError(formatProfileError(err.response?.data));
    } finally {
      setProfileSaving(false);
    }
  };

  const messages = activeConversation?.messages || [];
  const workspaces = [
    { id: "chat", label: "Chat", icon: Bot },
    { id: "memories", label: "Memory", icon: Brain },
    { id: "analytics", label: "NLP", icon: Activity },
    { id: "resume", label: "Resume", icon: FileSearch },
    { id: "documents", label: "Docs", icon: Files },
  ];
  const canOpenAdmin = ["super_admin", "admin", "moderator"].includes(user.role);

  const selectWorkspace = (workspaceId) => {
    setWorkspace(workspaceId);
    setSidebarOpen(false);
  };

  const welcomeTitle = authEvent === "register"
    ? `Welcome to OPTIMUS, ${user.display_name || user.username}`
    : `Welcome Back, ${user.display_name || user.username}`;
  const welcomeCopy = authEvent === "register"
    ? "Your account has been successfully verified. Let's build something amazing together."
    : "I'm OPTIMUS, your AI Assistant. What would you like to work on today?";

  return (
    <main className="relative flex h-dvh overflow-hidden bg-[#050814] text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_15%,rgba(20,184,166,0.25),transparent_32%),radial-gradient(circle_at_82%_18%,rgba(99,102,241,0.28),transparent_28%),radial-gradient(circle_at_50%_88%,rgba(236,72,153,0.14),transparent_34%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:44px_44px] opacity-30" />

      {sidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-20 bg-slate-950/70 backdrop-blur-sm md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation overlay"
        />
      )}

      <aside className={`fixed inset-y-0 left-0 z-30 flex h-dvh w-[min(86vw,320px)] shrink-0 flex-col border-r border-white/10 bg-slate-950/85 p-3 shadow-2xl shadow-cyan-950/40 backdrop-blur-2xl transition-transform duration-200 md:relative md:z-10 md:w-64 md:translate-x-0 lg:w-72 lg:p-4 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="mb-3 flex items-center justify-between md:hidden">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-cyan-300/30 bg-cyan-300/15 text-cyan-100">
              <Bot size={17} />
            </span>
            <span className="font-semibold text-white">OPTIMUS</span>
          </div>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-300 hover:bg-white/10 hover:text-white"
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>
        <button
          type="button"
          onClick={startNewChat}
          className="mb-3 flex items-center justify-center gap-2 rounded-md border border-cyan-300/30 bg-cyan-300/15 px-3 py-2 text-sm font-semibold text-cyan-100 shadow-lg shadow-cyan-950/30 transition hover:bg-cyan-300/25"
        >
          <MessageSquarePlus size={16} /> New chat
        </button>

        <label className="mb-4 block">
          <span className="sr-only">Search chats</span>
          <div className="flex h-10 items-center rounded-md border border-white/15 bg-white/10 px-3 text-slate-300 transition focus-within:border-cyan-300/60 focus-within:ring-2 focus-within:ring-cyan-300/15">
            <Search className="mr-2 shrink-0 text-cyan-200" size={16} />
            <input
              value={chatSearch}
              onChange={(event) => setChatSearch(event.target.value)}
              placeholder="Search chats"
              className="min-w-0 flex-1 border-0 bg-transparent p-0 text-sm text-white outline-none placeholder:text-slate-500"
            />
            {chatSearch && (
              <button
                type="button"
                onClick={() => setChatSearch("")}
                className="ml-2 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-slate-400 transition hover:bg-white/10 hover:text-white"
                aria-label="Clear chat search"
                title="Clear"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </label>

        <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          <Clock3 size={14} />
          <span>Recents</span>
        </div>

        <div className="flex-1 space-y-2 overflow-y-auto">
          {recentConversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`group flex items-center gap-1 rounded-md border transition ${conversation.id === activeId ? "border-cyan-300/30 bg-cyan-300/15 text-white shadow-lg shadow-cyan-950/30" : "border-transparent text-slate-300 hover:border-white/10 hover:bg-white/10 hover:text-white"}`}
            >
              <button
                type="button"
                onClick={() => selectConversation(conversation.id)}
                className="min-w-0 flex-1 px-3 py-2 text-left text-sm"
              >
                <span className="line-clamp-2">{conversation.title}</span>
                <span className="mt-1 block truncate text-xs text-slate-500">
                  {formatConversationTime(conversation.updated_at)}
                </span>
              </button>
              <button
                type="button"
                onClick={(event) => deleteConversation(event, conversation.id)}
                className={`mr-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md opacity-100 transition md:opacity-0 md:group-hover:opacity-100 ${conversation.id === activeId ? "text-white hover:bg-white/10" : "text-slate-400 hover:bg-rose-500/15 hover:text-rose-200"}`}
                aria-label={`Delete ${conversation.title}`}
                title="Delete chat"
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}

          {recentConversations.length === 0 && (
            <div className="rounded-md border border-white/10 bg-white/[0.06] px-3 py-4 text-sm text-slate-400">
              {chatSearch.trim() ? "No chats match your search." : "No recent chats yet."}
            </div>
          )}
        </div>
        <div className="mt-3 hidden md:block">
          <AppFooter compact />
        </div>
      </aside>

      <section className="relative z-10 flex h-dvh min-w-0 flex-1 flex-col">
        <header className="shrink-0 border-b border-white/10 bg-slate-950/45 backdrop-blur-2xl">
          <div className="flex items-center justify-between gap-3 px-3 py-3 sm:px-4">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-white/15 bg-white/10 text-slate-100 transition hover:bg-white/15 md:hidden"
              aria-label="Open sidebar"
              title="Menu"
            >
              <Menu size={18} />
            </button>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-cyan-300/30 bg-cyan-300/15 text-cyan-100 shadow-lg shadow-cyan-950/30">
                <Bot size={16} />
              </span>
              <h1 className="truncate text-base font-semibold text-white">OPTIMUS</h1>
            </div>
            <p className="mt-1 truncate text-sm text-cyan-100/70">{user.display_name || user.username}</p>
          </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {canOpenAdmin && (
              <button
                type="button"
                onClick={() => onNavigate("/admin")}
                className="inline-flex h-10 items-center gap-2 rounded-md border border-cyan-300/30 bg-cyan-300/15 px-3 text-sm font-medium text-cyan-100 transition hover:bg-cyan-300/25"
              >
                Admin
              </button>
            )}
            <button
              type="button"
              onClick={openProfile}
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-white/15 bg-white/10 text-slate-100 transition hover:bg-white/15"
              aria-label="Edit profile"
              title="Profile"
            >
              <UserRound size={17} />
            </button>
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex h-10 items-center gap-2 rounded-md border border-white/15 bg-white/10 px-3 text-sm font-medium text-slate-100 transition hover:bg-white/15"
            >
              <LogOut size={16} /> <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
          </div>

          <div className="border-t border-white/10 px-3 py-2 md:hidden">
            <div className="flex gap-2 overflow-x-auto pb-1">
              <button
                type="button"
                onClick={startNewChat}
                className="inline-flex h-9 shrink-0 items-center gap-2 rounded-md border border-cyan-300/30 bg-cyan-300/15 px-3 text-sm font-semibold text-cyan-100"
              >
                <MessageSquarePlus size={15} /> New
              </button>
              {conversations.filter((item) => item.id !== "draft").map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => selectConversation(conversation.id)}
                  className={`h-9 max-w-44 shrink-0 truncate rounded-md border px-3 text-sm font-medium ${conversation.id === activeId ? "border-cyan-300/30 bg-cyan-300/15 text-white" : "border-white/10 bg-white/10 text-slate-300"}`}
                >
                  {conversation.title}
                </button>
              ))}
            </div>
          </div>

          <nav className="hidden border-t border-white/10 px-3 py-2 sm:px-4 md:block">
            <div className="flex gap-2 overflow-x-auto">
              {workspaces.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => selectWorkspace(id)}
                  className={`inline-flex h-9 shrink-0 items-center gap-2 rounded-md border px-3 text-sm font-medium transition ${
                    workspace === id
                      ? "border-cyan-300/30 bg-cyan-300/15 text-white"
                      : "border-white/10 bg-white/10 text-slate-300 hover:bg-white/15 hover:text-white"
                  }`}
                >
                  <Icon size={15} /> {label}
                </button>
              ))}
            </div>
          </nav>
        </header>

        {workspace === "chat" ? (
          <>
            <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-4 sm:py-6">
              <div className="mx-auto max-w-3xl space-y-4">
                {messages.length === 0 && (
                  <div className="rounded-lg border border-white/15 bg-white/[0.08] p-5 shadow-2xl shadow-cyan-950/25 backdrop-blur-2xl sm:p-8">
                    <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-md border border-cyan-300/30 bg-cyan-300/15 text-cyan-100">
                      <Sparkles size={20} />
                    </div>
                    <h2 className="text-center text-lg font-semibold text-white sm:text-xl">{authEvent === "register" ? "🎉 " : "👋 "}{welcomeTitle}</h2>
                    <p className="mx-auto mt-2 max-w-xl text-center text-sm leading-6 text-slate-300">{welcomeCopy}</p>
                    <div className="mt-5 grid gap-2 sm:grid-cols-2">
                      {[
                        "✨ AI Conversations",
                        "📄 Resume Analysis",
                        "📝 Documentation Generation",
                        "💻 Coding Assistance",
                        "🚀 Project Development",
                        "🧠 Smart Memory",
                      ].map((item) => (
                        <button
                          key={item}
                          type="button"
                          onClick={() => {
                            if (item.includes("Resume")) selectWorkspace("resume");
                            else if (item.includes("Memory")) selectWorkspace("memories");
                            else selectWorkspace("chat");
                          }}
                          className="rounded-md border border-white/10 bg-white/10 px-3 py-2 text-left text-sm text-slate-100 transition hover:border-cyan-300/30 hover:bg-cyan-300/15"
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}

                {loading && <MessageBubble message={{ role: "assistant", content: "Thinking..." }} isLoading />}
                <div ref={bottomRef} />
              </div>
            </div>

            <form onSubmit={sendMessage} className="mb-16 shrink-0 border-t border-white/10 bg-slate-950/45 px-3 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur-2xl sm:px-4 sm:py-4 md:mb-0 md:pb-4">
              <div className="mx-auto flex max-w-3xl gap-2 sm:gap-3">
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  rows={1}
                  placeholder="Send a message"
                  className="max-h-32 min-h-11 min-w-0 flex-1 resize-none rounded-md border border-white/15 bg-white/10 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-400 focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/15 sm:max-h-36 sm:text-base"
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md border border-cyan-300/40 bg-cyan-300/20 text-cyan-50 shadow-lg shadow-cyan-950/30 transition hover:bg-cyan-300/30 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/10 disabled:text-slate-500"
                  aria-label="Send message"
                >
                  <Send size={18} />
                </button>
              </div>
              {error && <p className="mx-auto mt-2 max-w-3xl text-sm text-rose-300">{error}</p>}
              <p className="mx-auto mt-2 max-w-3xl text-center text-xs font-medium text-slate-400 sm:mt-3">
                Made by Sridhar M
              </p>
            </form>
          </>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto pb-20 md:pb-0">
            {workspace === "memories" && <MemoryManager />}
            {workspace === "analytics" && <NLPAnalytics />}
            {workspace === "resume" && <ResumeAnalyzer />}
            {workspace === "documents" && <DocumentsPage />}
            <div className="mx-auto max-w-5xl px-3 pb-5 sm:px-5">
              <AppFooter />
            </div>
          </div>
        )}
      </section>

      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-white/10 bg-slate-950/85 px-2 py-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] backdrop-blur-2xl md:hidden">
        <div className="grid grid-cols-5 gap-1">
          {workspaces.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => selectWorkspace(id)}
              className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-md text-[11px] font-medium transition ${workspace === id ? "bg-cyan-300/15 text-cyan-100" : "text-slate-400 hover:bg-white/10 hover:text-white"}`}
            >
              <Icon size={17} />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </nav>

      {profileOpen && (
        <div className="fixed inset-0 z-20 flex items-center justify-center overflow-y-auto bg-slate-950/75 px-3 py-6 backdrop-blur-sm sm:px-4">
          <form
            onSubmit={saveProfile}
            className="w-full max-w-md rounded-lg border border-white/15 bg-white/[0.08] p-4 text-slate-100 shadow-2xl shadow-cyan-950/40 backdrop-blur-2xl sm:p-5"
          >
            <div className="mb-5 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-lg font-semibold text-white">Profile</h2>
                <p className="truncate text-sm text-slate-400">{user.email || user.username}</p>
              </div>
              <button
                type="button"
                onClick={() => setProfileOpen(false)}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-slate-300 transition hover:bg-white/10 hover:text-white"
                aria-label="Close profile"
                title="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="text-sm font-medium text-slate-300">Username</span>
                <input
                  name="username"
                  value={profileForm.username}
                  onChange={updateProfileForm}
                  required
                  className="mt-1 w-full rounded-md border border-white/15 bg-white/10 px-3 py-2 text-white outline-none focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/15"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-slate-300">Email</span>
                <input
                  name="email"
                  type="email"
                  value={profileForm.email}
                  readOnly
                  className="mt-1 w-full rounded-md border border-white/15 bg-white/5 px-3 py-2 text-slate-400 outline-none"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-slate-300">Display name</span>
                <input
                  name="display_name"
                  value={profileForm.display_name}
                  onChange={updateProfileForm}
                  className="mt-1 w-full rounded-md border border-white/15 bg-white/10 px-3 py-2 text-white outline-none focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/15"
                />
              </label>
            </div>

            {profileError && (
              <p className="mt-4 rounded-md border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{profileError}</p>
            )}

            <div className="mt-6 grid gap-2 sm:flex sm:justify-end">
              <button
                type="button"
                onClick={() => setProfileOpen(false)}
                className="rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/15"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={profileSaving}
                className="inline-flex items-center gap-2 rounded-md border border-cyan-300/40 bg-cyan-300/20 px-3 py-2 text-sm font-semibold text-cyan-50 transition hover:bg-cyan-300/30 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/10 disabled:text-slate-500"
              >
                <Save size={16} /> {profileSaving ? "Saving..." : "Save"}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}

export default ChatPage;
