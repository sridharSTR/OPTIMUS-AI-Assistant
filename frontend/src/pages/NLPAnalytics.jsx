import { motion } from "framer-motion";
import { Activity, BarChart3, Brain, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import MarkdownRenderer from "../components/common/MarkdownRenderer.jsx";
import { nlpApi } from "../services/api.js";

function NLPAnalytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    nlpApi
      .analytics()
      .then((response) => setData(response.data))
      .catch(() => setError("Could not load NLP analytics."));
  }, []);

  const cards = [
    { label: "Total Requests", value: data?.total_requests ?? 0, icon: Activity },
    { label: "AI Requests", value: data?.ai_requests ?? 0, icon: BarChart3 },
    { label: "Saved", value: `${data?.savings_percentage ?? 0}%`, icon: Search },
    { label: "Memories", value: data?.memory_count ?? 0, icon: Brain },
    { label: "Searches", value: data?.search_count ?? 0, icon: Search },
    { label: "Cache Hits", value: data?.cached_responses ?? 0, icon: BarChart3 },
    { label: "Cache Hit Rate", value: `${data?.cache_hit_rate ?? 0}%`, icon: BarChart3 },
    { label: "Avg Sentiment", value: data?.average_sentiment ?? 0, icon: Activity },
  ];

  return (
    <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto w-full max-w-5xl p-3 sm:p-5">
      <div className="mb-4 flex items-center gap-3">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-fuchsia-300/30 bg-fuchsia-300/15 text-fuchsia-100">
          <Activity size={18} />
        </span>
        <div>
          <h2 className="text-lg font-semibold text-white">NLP Analytics</h2>
          <p className="text-sm text-slate-400">Intent, sentiment, entity, memory, and search metrics.</p>
        </div>
      </div>

      {error && <p className="rounded-md border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>}
      {!data && !error && <p className="text-sm text-slate-400">Loading analytics...</p>}

      {data && (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            {cards.map(({ label, value, icon: Icon }) => (
              <article key={label} className="rounded-lg border border-white/15 bg-white/[0.08] p-4">
                <Icon className="mb-3 text-cyan-200" size={18} />
                <p className="text-2xl font-semibold text-white">{value}</p>
                <p className="text-sm text-slate-400">{label}</p>
              </article>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <MessageVolumeChart data={data.message_volume_7_days || []} />
            <MetricList title="Intent Usage" items={data.intent_usage} labelKey="intent" />
            <MetricList title="Sentiment" items={data.sentiment_stats} labelKey="sentiment" />
            <MetricList title="Common Entities" items={data.common_entities} labelKey="entity" />
            <MetricList
              title="Optimization"
              items={[
                { label: "FAQ responses", count: data.faq_responses },
                { label: "Memory requests", count: data.memory_requests },
                { label: "Cached responses", count: data.cached_responses },
                { label: "Saved requests", count: data.saved_requests },
              ]}
              labelKey="label"
            />
            <RecentEvents events={data.recent_events} />
          </div>
        </>
      )}
    </motion.section>
  );
}

function MessageVolumeChart({ data }) {
  return (
    <article className="rounded-lg border border-white/15 bg-white/[0.08] p-4 lg:col-span-2">
      <h3 className="mb-3 text-sm font-semibold text-white">Message Volume</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid stroke="rgba(255,255,255,0.12)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: "#cbd5e1", fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} tick={{ fill: "#cbd5e1", fontSize: 12 }} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: "rgba(34,211,238,0.08)" }}
              contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8, color: "#fff" }}
            />
            <Bar dataKey="count" fill="#22d3ee" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function MetricList({ title, items, labelKey }) {
  return (
    <article className="rounded-lg border border-white/15 bg-white/[0.08] p-4">
      <h3 className="mb-3 text-sm font-semibold text-white">{title}</h3>
      <div className="space-y-2">
        {items.length === 0 && <p className="text-sm text-slate-400">No data yet.</p>}
        {items.map((item) => (
          <div key={item[labelKey]} className="flex items-center justify-between rounded-md bg-white/10 px-3 py-2 text-sm">
            <span className="capitalize text-slate-200">{item[labelKey]}</span>
            <span className="font-semibold text-cyan-100">{item.count}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function RecentEvents({ events }) {
  return (
    <article className="rounded-lg border border-white/15 bg-white/[0.08] p-4">
      <h3 className="mb-3 text-sm font-semibold text-white">Recent NLP Events</h3>
      <div className="space-y-2">
        {events.length === 0 && <p className="text-sm text-slate-400">No events yet.</p>}
        {events.map((event, index) => (
          <div key={`${event.created_at}-${index}`} className="rounded-md bg-white/10 px-3 py-2 text-sm">
            <div className="flex flex-wrap gap-2">
              <span className="rounded bg-cyan-300/15 px-2 py-0.5 text-cyan-100">{event.intent}</span>
              <span className="rounded bg-fuchsia-300/15 px-2 py-0.5 text-fuchsia-100">{event.sentiment}</span>
              <span className="rounded bg-white/10 px-2 py-0.5 text-slate-200">{event.route || "pending"}</span>
              {event.search_triggered && <span className="rounded bg-emerald-300/15 px-2 py-0.5 text-emerald-100">search</span>}
              {event.cache_hit && <span className="rounded bg-amber-300/15 px-2 py-0.5 text-amber-100">cache hit</span>}
              {event.ai_called ? <span className="rounded bg-rose-300/15 px-2 py-0.5 text-rose-100">AI</span> : <span className="rounded bg-cyan-300/15 px-2 py-0.5 text-cyan-100">local</span>}
            </div>
            {Object.keys(event.entities || {}).length > 0 && (
              <MarkdownRenderer content={formatEntities(event.entities)} className="mt-2 text-xs text-slate-300" />
            )}
          </div>
        ))}
      </div>
    </article>
  );
}

function formatEntities(entities) {
  return Object.entries(entities)
    .filter(([, values]) => values?.length)
    .map(([key, values]) => `- **${key.replaceAll("_", " ")}:** ${values.join(", ")}`)
    .join("\n");
}

export default NLPAnalytics;
