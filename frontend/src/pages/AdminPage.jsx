import {
  Activity,
  BarChart3,
  Bot,
  Brain,
  Download,
  Edit3,
  Eye,
  FileSearch,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Search,
  Settings,
  Shield,
  ShieldAlert,
  Trash2,
  UserCog,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import MarkdownRenderer from "../components/common/MarkdownRenderer.jsx";
import { adminApi } from "../services/api.js";

const tabs = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "users", label: "Users", icon: Users },
  { id: "conversations", label: "Conversations", icon: MessageSquare },
  { id: "memories", label: "Memories", icon: Brain },
  { id: "resumes", label: "Resume Analysis", icon: FileSearch },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "settings", label: "Settings", icon: Settings },
];

const adminRoles = new Set(["super_admin", "admin", "moderator"]);
const managerRoles = new Set(["super_admin", "admin"]);
const primaryAdminEmail = "sivasridhar2502@gmail.com";

function AdminPage({ user, onLogout, onNavigate }) {
  const [active, setActive] = useState("dashboard");
  const [query, setQuery] = useState("");
  const [messageQuery, setMessageQuery] = useState("");
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const canAccess = adminRoles.has(user.role);
  const canManage = managerRoles.has(user.role);

  const load = useCallback(async () => {
    if (!canAccess) return;
    setLoading(true);
    setError("");
    try {
      const loaders = {
        dashboard: () => adminApi.dashboard(),
        users: () => adminApi.users(query),
        conversations: () => adminApi.conversations(query),
        memories: () => adminApi.memories(query),
        resumes: () => adminApi.resumeAnalyses(query),
        analytics: () => adminApi.analytics(),
        settings: () => Promise.resolve({ data: {} }),
      };
      const response = await loaders[active]();
      setData((current) => ({ ...current, [active]: response.data }));
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load admin data.");
    } finally {
      setLoading(false);
    }
  }, [active, canAccess, query]);

  const loadMessages = useCallback(async () => {
    if (!canAccess || active !== "conversations") return;
    try {
      const response = await adminApi.messages({
        query: messageQuery,
        conversationId: selectedConversation?.id || "",
      });
      setData((current) => ({ ...current, messages: response.data }));
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load messages.");
    }
  }, [active, canAccess, messageQuery, selectedConversation]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  useEffect(() => {
    setQuery("");
    setMessageQuery("");
    setSelectedConversation(null);
    setNotice("");
    setError("");
  }, [active]);

  const runAction = async (action, successMessage) => {
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(successMessage);
      await load();
      await loadMessages();
    } catch (err) {
      setError(err.response?.data?.detail || "Admin action failed.");
    }
  };

  if (!canAccess) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-[#080a0f] px-4 text-slate-100">
        <div className="max-w-md rounded-lg border border-white/15 bg-[#121722] p-6 text-center shadow-2xl">
          <ShieldAlert className="mx-auto mb-3 text-rose-200" size={30} />
          <h1 className="text-xl font-semibold text-white">Admin access required</h1>
          <p className="mt-2 text-sm text-slate-400">Your account is not assigned to an admin, moderator, or super admin role.</p>
          <button onClick={() => onNavigate("/")} className="mt-5 rounded-md border border-teal-300/30 bg-teal-300/15 px-4 py-2 text-sm font-semibold text-teal-100">
            Return to app
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-dvh bg-[#080a0f] text-slate-100">
      <aside className="hidden w-72 shrink-0 border-r border-white/10 bg-[#0d1119] p-4 lg:block">
        <BrandBlock user={user} />
        <AdminNav active={active} setActive={setActive} />
      </aside>

      <section className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-[#0d1119]/95 px-3 py-3 backdrop-blur-xl sm:px-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">{tabs.find((tab) => tab.id === active)?.label}</h2>
              <p className="text-sm text-slate-400">{user.email}</p>
            </div>
            <div className="flex items-center gap-2">
              {["users", "conversations", "memories", "resumes"].includes(active) && (
                <SearchBox value={query} onChange={setQuery} placeholder={`Search ${tabs.find((tab) => tab.id === active)?.label.toLowerCase()}`} />
              )}
              <button onClick={() => onNavigate("/")} className="rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm font-medium text-slate-100 hover:bg-white/15">
                App
              </button>
              <button onClick={onLogout} className="inline-flex items-center gap-2 rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm font-medium text-slate-100 hover:bg-white/15">
                <LogOut size={15} /> Logout
              </button>
            </div>
          </div>
          <div className="mt-3 lg:hidden">
            <AdminNav active={active} setActive={setActive} compact />
          </div>
        </header>

        <div className="p-3 sm:p-5">
          {error && <p className="mb-3 rounded-md border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>}
          {notice && <p className="mb-3 rounded-md border border-emerald-300/20 bg-emerald-400/10 px-3 py-2 text-sm text-emerald-100">{notice}</p>}
          {loading && <p className="mb-3 text-sm text-teal-100">Loading admin data...</p>}
          {active === "dashboard" && <Dashboard data={data.dashboard} />}
          {active === "users" && <UsersPanel users={data.users || []} currentUser={user} canManage={canManage} runAction={runAction} />}
          {active === "conversations" && (
            <ConversationsPanel
              conversations={data.conversations || []}
              messages={data.messages || []}
              messageQuery={messageQuery}
              setMessageQuery={setMessageQuery}
              selectedConversation={selectedConversation}
              setSelectedConversation={setSelectedConversation}
              canManage={canManage}
              runAction={runAction}
            />
          )}
          {active === "memories" && <MemoriesPanel memories={data.memories || []} canManage={canManage} runAction={runAction} />}
          {active === "resumes" && <ResumesPanel analyses={data.resumes || []} canManage={canManage} runAction={runAction} />}
          {active === "analytics" && <AnalyticsPanel data={data.analytics} />}
          {active === "settings" && <SettingsPanel user={user} canManage={canManage} />}
        </div>
      </section>
    </main>
  );
}

function BrandBlock({ user }) {
  return (
    <div className="mb-6 flex items-center gap-3">
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-teal-300/30 bg-teal-300/15 text-teal-100">
        <Bot size={18} />
      </span>
      <div>
        <h1 className="font-semibold text-white">OPTIMUS Admin</h1>
        <p className="text-xs uppercase text-teal-100/70">{user.role.replace("_", " ")}</p>
      </div>
    </div>
  );
}

function AdminNav({ active, setActive, compact = false }) {
  return (
    <nav className={compact ? "flex gap-2 overflow-x-auto" : "space-y-2"}>
      {tabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => setActive(id)}
          className={`${compact ? "inline-flex h-9 shrink-0" : "flex w-full"} items-center gap-3 rounded-md border px-3 py-2 text-left text-sm font-medium transition ${active === id ? "border-teal-300/30 bg-teal-300/15 text-white" : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/10 hover:text-white"}`}
        >
          <Icon size={16} /> {label}
        </button>
      ))}
    </nav>
  );
}

function SearchBox({ value, onChange, placeholder }) {
  return (
    <label className="flex h-10 min-w-0 items-center rounded-md border border-white/15 bg-white/10 px-3 text-slate-300">
      <Search size={15} className="mr-2 text-teal-200" />
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="w-36 bg-transparent text-sm text-white outline-none placeholder:text-slate-500 sm:w-56" />
    </label>
  );
}

function Dashboard({ data = {} }) {
  const cards = [
    ["Total users", data.total_users, Users, "text-teal-200"],
    ["Verified users", data.verified_users, Shield, "text-emerald-200"],
    ["Conversations", data.active_conversations, MessageSquare, "text-sky-200"],
    ["Messages", data.total_messages, Activity, "text-indigo-200"],
    ["AI requests", data.ai_requests_count, Bot, "text-violet-200"],
    ["Cache hit ratio", `${data.cache_hit_ratio ?? 0}%`, BarChart3, "text-amber-200"],
    ["Resume analyses", data.resume_analysis_count, FileSearch, "text-orange-200"],
    ["Memories", data.memory_count, Brain, "text-pink-200"],
  ];
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value, Icon, color]) => (
          <article key={label} className="rounded-lg border border-white/15 bg-[#121722] p-4 shadow-xl shadow-black/20">
            <Icon className={`mb-3 ${color}`} size={18} />
            <p className="text-2xl font-semibold text-white">{value ?? 0}</p>
            <p className="text-sm text-slate-400">{label}</p>
          </article>
        ))}
      </div>
      <div>
        <h3 className="mb-3 text-sm font-semibold text-white">Latest users</h3>
        <AdminTable rows={data.latest_users || []} columns={["email", "display_name", "role", "email_verified"]} />
      </div>
    </div>
  );
}

function UsersPanel({ users, currentUser, canManage, runAction }) {
  const updateRole = (target, role) => runAction(() => adminApi.promoteUser({ user_id: target.id, role }), "Role updated.");
  const demote = (target) => runAction(() => adminApi.demoteUser({ user_id: target.id }), "User demoted.");
  const ban = (target) => runAction(() => adminApi.banUser({ user_id: target.id, is_banned: !target.is_banned }), target.is_banned ? "User unbanned." : "User banned.");
  const remove = (target) => {
    if (!window.confirm(`Delete ${target.email}?`)) return;
    runAction(() => adminApi.deleteUser(target.id), "User deleted.");
  };
  return (
    <AdminTable
      rows={users}
      columns={["email", "display_name", "role", "email_verified", "is_banned", "conversation_count", "message_count", "date_joined"]}
      renderActions={(target) => {
        const locked = !canManage || target.email === primaryAdminEmail || target.id === currentUser.id;
        return (
          <>
            <select value={target.role} onChange={(event) => updateRole(target, event.target.value)} disabled={locked} className="rounded border border-white/10 bg-[#080a0f] px-2 py-1 text-xs text-white disabled:opacity-50">
              <option value="user">user</option>
              <option value="moderator">moderator</option>
              <option value="admin">admin</option>
              <option value="super_admin">super_admin</option>
            </select>
            <IconButton title="Demote" onClick={() => demote(target)} disabled={locked} icon={UserCog} tone="amber" />
            <button onClick={() => ban(target)} disabled={locked} className="rounded bg-amber-300/15 px-2 py-1 text-xs text-amber-100 disabled:opacity-50">{target.is_banned ? "Unban" : "Ban"}</button>
            <IconButton title="Delete" onClick={() => remove(target)} disabled={locked} icon={Trash2} tone="rose" />
          </>
        );
      }}
    />
  );
}

function ConversationsPanel({ conversations, messages, messageQuery, setMessageQuery, selectedConversation, setSelectedConversation, canManage, runAction }) {
  const remove = (conversation) => {
    if (!window.confirm(`Delete "${conversation.title}"?`)) return;
    runAction(() => adminApi.deleteConversation(conversation.id), "Conversation deleted.");
  };
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.8fr)]">
      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-white">All conversations</h3>
          {selectedConversation && (
            <button onClick={() => setSelectedConversation(null)} className="rounded-md border border-white/15 bg-white/10 px-3 py-2 text-xs text-slate-200">
              Clear selection
            </button>
          )}
        </div>
        <AdminTable
          rows={conversations}
          columns={["title", "user_email", "message_count", "updated_at"]}
          renderActions={(conversation) => (
            <>
              <IconButton title="View messages" onClick={() => setSelectedConversation(conversation)} icon={Eye} tone="teal" />
              <IconButton title="Delete" onClick={() => remove(conversation)} disabled={!canManage} icon={Trash2} tone="rose" />
            </>
          )}
        />
      </div>
      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-white">Messages</h3>
            <p className="text-xs text-slate-400">{selectedConversation ? selectedConversation.title : "Search across all conversations"}</p>
          </div>
          <SearchBox value={messageQuery} onChange={setMessageQuery} placeholder="Search messages" />
        </div>
        <div className="space-y-3">
          {messages.length === 0 && <p className="rounded-lg border border-white/10 bg-[#121722] p-4 text-sm text-slate-400">No messages found.</p>}
          {messages.map((message) => (
            <article key={message.id} className="rounded-lg border border-white/10 bg-[#121722] p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
                <span className="font-semibold uppercase text-teal-100">{message.role}</span>
                <span>{formatDate(message.created_at)}</span>
              </div>
              <MarkdownRenderer content={message.content} />
              <p className="mt-3 text-xs text-slate-500">{message.user_email} | {message.intent || "no intent"}</p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function MemoriesPanel({ memories, canManage, runAction }) {
  const [editing, setEditing] = useState(null);
  const save = () => runAction(() => adminApi.updateMemory({ memory_id: editing.id, key: editing.key, value: editing.value, importance: Number(editing.importance) || 1 }), "Memory updated.").then(() => setEditing(null));
  const remove = (memory) => runAction(() => adminApi.deleteMemory(memory.id), "Memory deleted.");
  return (
    <div className="space-y-4">
      {editing && (
        <section className="rounded-lg border border-teal-300/20 bg-[#121722] p-4">
          <h3 className="mb-3 text-sm font-semibold text-white">Edit memory</h3>
          <div className="grid gap-3 md:grid-cols-[220px_1fr_120px_auto]">
            <input value={editing.key} onChange={(event) => setEditing({ ...editing, key: event.target.value })} className="rounded-md border border-white/10 bg-[#080a0f] px-3 py-2 text-sm text-white outline-none" />
            <textarea value={editing.value} onChange={(event) => setEditing({ ...editing, value: event.target.value })} className="min-h-24 rounded-md border border-white/10 bg-[#080a0f] px-3 py-2 text-sm text-white outline-none" />
            <input type="number" min="1" max="10" value={editing.importance} onChange={(event) => setEditing({ ...editing, importance: event.target.value })} className="rounded-md border border-white/10 bg-[#080a0f] px-3 py-2 text-sm text-white outline-none" />
            <div className="flex gap-2">
              <button onClick={save} className="h-10 rounded-md bg-teal-300/20 px-3 text-sm font-semibold text-teal-100">Save</button>
              <button onClick={() => setEditing(null)} className="h-10 rounded-md border border-white/15 px-3 text-sm text-slate-200">Cancel</button>
            </div>
          </div>
        </section>
      )}
      <AdminTable
        rows={memories}
        columns={["user_email", "key", "value", "importance", "created_at"]}
        renderCell={(memory, column) => column === "value" ? <MarkdownRenderer content={memory.value} /> : null}
        renderActions={(memory) => (
          <>
            <IconButton title="Edit" onClick={() => setEditing(memory)} disabled={!canManage} icon={Edit3} tone="teal" />
            <IconButton title="Delete" onClick={() => remove(memory)} disabled={!canManage} icon={Trash2} tone="rose" />
          </>
        )}
      />
    </div>
  );
}

function ResumesPanel({ analyses, canManage, runAction }) {
  const [selected, setSelected] = useState(null);
  const remove = (analysis) => runAction(() => adminApi.deleteResumeAnalysis(analysis.id), "Resume analysis deleted.");
  return (
    <div className="space-y-4">
      {selected && <ResumeDetail analysis={selected} onClose={() => setSelected(null)} />}
      <AdminTable
        rows={analyses}
        columns={["filename", "user_email", "score", "skills_score", "sections_score", "created_at"]}
        renderActions={(analysis) => (
          <>
            <IconButton title="View report" onClick={() => setSelected(analysis)} icon={Eye} tone="teal" />
            <IconButton title="Download JSON" onClick={() => downloadReport(analysis)} icon={Download} tone="amber" />
            <IconButton title="Delete" onClick={() => remove(analysis)} disabled={!canManage} icon={Trash2} tone="rose" />
          </>
        )}
      />
    </div>
  );
}

function ResumeDetail({ analysis, onClose }) {
  return (
    <section className="rounded-lg border border-white/15 bg-[#121722] p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-white">{analysis.filename}</h3>
          <p className="text-sm text-slate-400">{analysis.user_email} | Score {analysis.score}/100</p>
        </div>
        <button onClick={onClose} className="rounded-md border border-white/15 px-3 py-2 text-xs text-slate-200">Close</button>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <InfoList title="Found skills" items={analysis.found_skills || analysis.skills || []} />
        <InfoList title="Missing skills" items={analysis.missing_skills || []} />
        <InfoList title="Detected sections" items={analysis.detected_sections || []} />
      </div>
      {analysis.score_explanation && <p className="mt-3 rounded-md bg-white/10 p-3 text-sm text-slate-300">{analysis.score_explanation}</p>}
      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <InfoList title="Suggestions" items={analysis.suggestions || []} />
        <InfoList title="Interview questions" items={analysis.interview_questions || []} />
      </div>
    </section>
  );
}

function AnalyticsPanel({ data = {} }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="AI responses" value={data.ai_response_count ?? 0} icon={Bot} />
        <StatCard label="Cache hits" value={data.cache_performance?.cache_hits ?? 0} icon={BarChart3} />
        <StatCard label="Cache entries" value={data.cache_performance?.cache_entries ?? 0} icon={Activity} />
        <StatCard label="Avg cache hits" value={data.cache_performance?.average_cache_hits ?? 0} icon={Activity} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <MetricList title="Most Used Intents" items={data.most_used_intents || []} labelKey="intent" />
        <MetricList title="Route Usage" items={data.route_usage || []} labelKey="route" />
        <MetricList title="Sentiment" items={data.sentiment || []} labelKey="sentiment" />
        <article className="rounded-lg border border-white/15 bg-[#121722] p-4">
          <h3 className="mb-3 text-sm font-semibold text-white">Cache Performance</h3>
          <p className="text-3xl font-semibold text-amber-100">{data.cache_performance?.hit_ratio ?? 0}%</p>
          <p className="text-sm text-slate-400">Hit ratio across NLP events</p>
          <p className="mt-3 text-sm text-slate-300">Average response time: {data.average_response_time ?? "Not tracked yet"}</p>
        </article>
      </div>
    </div>
  );
}

function SettingsPanel({ user, canManage }) {
  return (
    <section className="rounded-lg border border-white/15 bg-[#121722] p-4">
      <h3 className="mb-3 text-sm font-semibold text-white">RBAC Settings</h3>
      <p className="text-sm text-slate-300">Current role: <span className="font-semibold text-teal-100">{user.role}</span></p>
      <p className="mt-2 text-sm text-slate-400">Primary super admin email: {primaryAdminEmail}</p>
      <p className="mt-2 text-sm text-slate-400">Primary admin is auto-assigned super_admin by the Django user model on registration or login verification.</p>
      <p className="mt-2 text-sm text-slate-400">{canManage ? "This role can manage users and destructive admin actions." : "Moderators can inspect admin data but cannot perform destructive actions."}</p>
      <p className="mt-2 text-sm text-slate-400">Admin APIs never expose passwords and are protected by JWT cookies plus role checks.</p>
    </section>
  );
}

function MetricList({ title, items, labelKey }) {
  return (
    <article className="rounded-lg border border-white/15 bg-[#121722] p-4">
      <h3 className="mb-3 text-sm font-semibold text-white">{title}</h3>
      <div className="space-y-2">
        {items.length === 0 && <p className="text-sm text-slate-400">No data yet.</p>}
        {items.map((item, index) => (
          <div key={`${item[labelKey]}-${index}`} className="flex justify-between rounded-md bg-white/10 px-3 py-2 text-sm">
            <span className="capitalize text-slate-200">{item[labelKey] || "unknown"}</span>
            <span className="font-semibold text-teal-100">{item.count}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function InfoList({ title, items }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/[0.04] p-3">
      <h4 className="mb-2 text-sm font-semibold text-white">{title}</h4>
      {items.length === 0 ? <p className="text-sm text-slate-500">No data.</p> : (
        <ul className="space-y-1 text-sm text-slate-300">
          {items.map((item, index) => <li key={`${title}-${index}`}>{typeof item === "string" ? item : JSON.stringify(item)}</li>)}
        </ul>
      )}
    </div>
  );
}

function StatCard({ label, value, icon: Icon }) {
  return (
    <article className="rounded-lg border border-white/15 bg-[#121722] p-4">
      <Icon className="mb-3 text-teal-200" size={18} />
      <p className="text-2xl font-semibold text-white">{value}</p>
      <p className="text-sm text-slate-400">{label}</p>
    </article>
  );
}

function AdminTable({ rows, columns, renderActions, renderCell }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-white/10 bg-[#121722]">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-white/10 text-xs uppercase text-slate-400">
          <tr>
            {columns.map((column) => <th key={column} className="px-3 py-3">{column.replaceAll("_", " ")}</th>)}
            {renderActions && <th className="px-3 py-3">Actions</th>}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={columns.length + (renderActions ? 1 : 0)} className="px-3 py-5 text-center text-slate-400">No records found.</td></tr>
          )}
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-white/10 align-top hover:bg-white/[0.04]">
              {columns.map((column) => (
                <td key={column} className="max-w-sm px-3 py-3 text-slate-200">
                  {renderCell?.(row, column) ?? formatValue(row[column])}
                </td>
              ))}
              {renderActions && <td className="px-3 py-3"><div className="flex flex-wrap gap-2">{renderActions(row)}</div></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IconButton({ title, onClick, disabled = false, icon: Icon, tone = "teal" }) {
  const tones = {
    teal: "bg-teal-300/15 text-teal-100",
    amber: "bg-amber-300/15 text-amber-100",
    rose: "bg-rose-500/15 text-rose-100",
  };
  return (
    <button title={title} aria-label={title} onClick={onClick} disabled={disabled} className={`inline-flex h-7 w-8 items-center justify-center rounded ${tones[tone]} disabled:opacity-50`}>
      <Icon size={13} />
    </button>
  );
}

function downloadReport(analysis) {
  const blob = new window.Blob([JSON.stringify(analysis, null, 2)], { type: "application/json" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${analysis.filename || "resume-analysis"}-report.json`;
  link.click();
  window.URL.revokeObjectURL(url);
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function formatValue(value) {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === null || value === undefined || value === "") return "-";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) return formatDate(value);
  return String(value);
}

export default AdminPage;
