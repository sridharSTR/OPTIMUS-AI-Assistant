import { motion } from "framer-motion";
import { Brain, Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import MarkdownRenderer from "../components/common/MarkdownRenderer.jsx";
import { nlpApi } from "../services/api.js";

const emptyForm = { key: "", value: "", importance: 3 };

function MemoryManager({ memorySync }) {
  const [memories, setMemories] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadMemories = () => {
    setLoading(true);
    nlpApi
      .memories()
      .then(({ data }) => setMemories(data))
      .catch(() => setError("Could not load memories."))
      .finally(() => setLoading(false));
  };

  useEffect(loadMemories, []);

  useEffect(() => {
    if (!memorySync?.updated_memory_list) return;
    setMemories(memorySync.updated_memory_list);
    setLoading(false);
  }, [memorySync]);

  useEffect(() => {
    const syncMemories = (event) => {
      if (!event.detail?.updated_memory_list) return;
      setMemories(event.detail.updated_memory_list);
      setLoading(false);
    };

    window.addEventListener("memory:sync", syncMemories);
    return () => window.removeEventListener("memory:sync", syncMemories);
  }, []);

  const createMemory = async (event) => {
    event.preventDefault();
    if (!form.key.trim() || !form.value.trim()) return;
    setSaving(true);
    setError("");
    try {
      const { data } = await nlpApi.createMemory({
        key: form.key.trim(),
        value: form.value.trim(),
        importance: Number(form.importance),
      });
      setMemories((current) => [data, ...current]);
      setForm(emptyForm);
    } catch {
      setError("Could not save this memory.");
    } finally {
      setSaving(false);
    }
  };

  const deleteMemory = async (id) => {
    setError("");
    try {
      await nlpApi.deleteMemory(id);
      setMemories((current) => current.filter((memory) => memory.id !== id));
    } catch {
      setError("Could not delete this memory.");
    }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto w-full max-w-5xl p-3 sm:p-5">
      <div className="mb-4 flex items-center gap-3">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-cyan-300/30 bg-cyan-300/15 text-cyan-100">
          <Brain size={18} />
        </span>
        <div>
          <h2 className="text-lg font-semibold text-white">Memory Manager</h2>
          <p className="text-sm text-slate-400">Review, add, and remove facts OPTIMUS uses for personalization.</p>
        </div>
      </div>

      <form onSubmit={createMemory} className="mb-4 grid gap-3 rounded-lg border border-white/15 bg-white/[0.08] p-4 sm:grid-cols-[160px_1fr_120px_auto]">
        <input
          value={form.key}
          onChange={(event) => setForm((current) => ({ ...current, key: event.target.value }))}
          placeholder="key"
          className="rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300/60"
        />
        <input
          value={form.value}
          onChange={(event) => setForm((current) => ({ ...current, value: event.target.value }))}
          placeholder="value"
          className="rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300/60"
        />
        <input
          type="number"
          min="1"
          max="5"
          value={form.importance}
          onChange={(event) => setForm((current) => ({ ...current, importance: event.target.value }))}
          className="rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300/60"
        />
        <button disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-md border border-cyan-300/40 bg-cyan-300/20 px-3 py-2 text-sm font-semibold text-cyan-50 disabled:opacity-50">
          {saving ? <Save size={16} /> : <Plus size={16} />} Save
        </button>
      </form>

      {error && <p className="mb-3 rounded-md border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>}

      <div className="grid gap-3 sm:grid-cols-2">
        {loading && <p className="text-sm text-slate-400">Loading memories...</p>}
        {!loading && memories.length === 0 && <p className="text-sm text-slate-400">No memories saved yet.</p>}
        {memories.map((memory) => (
          <article key={memory.id} className="rounded-lg border border-white/15 bg-white/[0.08] p-4">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-cyan-100">{memory.key}</h3>
                <MarkdownRenderer content={memory.value} className="mt-2 text-sm leading-6 text-slate-100" />
              </div>
              <button onClick={() => deleteMemory(memory.id)} className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-rose-500/15 hover:text-rose-200" title="Delete memory">
                <Trash2 size={15} />
              </button>
            </div>
            <span className="text-xs text-slate-500">Importance {memory.importance}/5</span>
          </article>
        ))}
      </div>
    </motion.section>
  );
}

export default MemoryManager;
