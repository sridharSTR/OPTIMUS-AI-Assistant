import { motion } from "framer-motion";
import { FileText, Search, Send, Trash2, UploadCloud, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import MarkdownRenderer from "../components/common/MarkdownRenderer.jsx";
import { ragApi } from "../services/api.js";

function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("all");
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [error, setError] = useState("");

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === Number(selectedId)),
    [documents, selectedId],
  );

  const loadDocuments = useCallback(() => {
    ragApi
      .documents(query)
      .then(({ data }) => setDocuments(data))
      .catch(() => setError("Could not load documents."));
  }, [query]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const uploadFile = async (event) => {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    setUploadProgress(0);
    try {
      const { data } = await ragApi.upload(file, (progressEvent) => {
        const total = progressEvent.total || file.size;
        setUploadProgress(Math.round((progressEvent.loaded / total) * 100));
      });
      setDocuments((current) => [data, ...current]);
      setFile(null);
      setSelectedId(data.id);
    } catch (err) {
      setError(formatUploadError(err, "Could not upload this document."));
    } finally {
      setUploading(false);
    }
  };

  const deleteDocument = async (id) => {
    setError("");
    try {
      await ragApi.deleteDocument(id);
      setDocuments((current) => current.filter((document) => document.id !== id));
      if (Number(selectedId) === id) setSelectedId("all");
    } catch {
      setError("Could not delete this document.");
    }
  };

  const sendQuestion = async (event) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || loadingAnswer) return;

    setMessages((current) => [...current, { role: "user", content: message }]);
    setInput("");
    setLoadingAnswer(true);
    setError("");

    try {
      const { data } = await ragApi.chat({
        message,
        document_id: selectedId === "all" ? null : Number(selectedId),
      });
      setMessages((current) => [...current, { role: "assistant", content: data.answer, sources: data.sources || [] }]);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not answer from your documents.");
    } finally {
      setLoadingAnswer(false);
    }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto grid w-full max-w-6xl gap-4 p-3 sm:p-5 lg:grid-cols-[340px_1fr]">
      <aside className="rounded-lg border border-white/15 bg-white/[0.08] p-4">
        <div className="mb-4 flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-cyan-300/30 bg-cyan-300/15 text-cyan-100">
            <FileText size={18} />
          </span>
          <div>
            <h2 className="text-lg font-semibold text-white">Documents</h2>
            <p className="text-sm text-slate-400">PDF, DOCX, and TXT up to 20 MB.</p>
          </div>
        </div>

        <form onSubmit={uploadFile} className="mb-4 rounded-md border border-dashed border-white/20 bg-white/5 p-3">
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="w-full text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-cyan-300/20 file:px-3 file:py-1.5 file:text-cyan-50"
          />
          {uploading && (
            <div className="mt-3 h-2 overflow-hidden rounded bg-white/10">
              <div className="h-full bg-cyan-300 transition-all" style={{ width: `${uploadProgress}%` }} />
            </div>
          )}
          <button disabled={!file || uploading} className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md border border-cyan-300/40 bg-cyan-300/20 px-3 py-2 text-sm font-semibold text-cyan-50 disabled:opacity-50">
            <UploadCloud size={16} /> {uploading ? "Processing..." : "Upload"}
          </button>
        </form>

        <label className="mb-3 flex items-center rounded-md border border-white/15 bg-white/10 px-3 py-2">
          <Search size={15} className="mr-2 text-cyan-200" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") loadDocuments();
            }}
            placeholder="Search documents"
            className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
          />
          {query && (
            <button type="button" onClick={() => setQuery("")} className="text-slate-400 hover:text-white">
              <X size={15} />
            </button>
          )}
        </label>

        <div className="mb-2">
          <button
            onClick={() => setSelectedId("all")}
            className={`mb-2 w-full rounded-md border px-3 py-2 text-left text-sm ${selectedId === "all" ? "border-cyan-300/30 bg-cyan-300/15 text-white" : "border-white/10 bg-white/10 text-slate-300"}`}
          >
            All Documents
          </button>
          <div className="space-y-2">
            {documents.map((document) => (
              <div key={document.id} className={`flex items-center gap-2 rounded-md border px-3 py-2 ${Number(selectedId) === document.id ? "border-cyan-300/30 bg-cyan-300/15" : "border-white/10 bg-white/10"}`}>
                <button onClick={() => setSelectedId(document.id)} className="min-w-0 flex-1 text-left">
                  <p className="truncate text-sm font-medium text-white">{document.filename}</p>
                  <p className="text-xs text-slate-400">{formatBytes(document.file_size)} · {document.chunk_count} chunks</p>
                </button>
                <button onClick={() => deleteDocument(document.id)} className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-rose-500/15 hover:text-rose-200" title="Delete">
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </aside>

      <section className="flex min-h-[70vh] flex-col rounded-lg border border-white/15 bg-white/[0.08]">
        <header className="border-b border-white/10 p-4">
          <h2 className="text-lg font-semibold text-white">Document Chat</h2>
          <p className="text-sm text-slate-400">
            Asking: {selectedDocument ? selectedDocument.filename : "All uploaded documents"}
          </p>
        </header>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
          {messages.length === 0 && <p className="text-sm text-slate-400">Ask a question about your uploaded documents.</p>}
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`rounded-lg border p-3 text-sm leading-6 ${message.role === "user" ? "ml-auto max-w-[82%] border-fuchsia-300/30 bg-fuchsia-300/15 text-fuchsia-50" : "max-w-[88%] border-white/15 bg-white/10 text-slate-100"}`}>
              {message.role === "assistant" ? (
                <MarkdownRenderer content={message.content} />
              ) : (
                <p className="whitespace-pre-wrap">{message.content}</p>
              )}
              {message.sources?.length > 0 && (
                <div className="mt-3 border-t border-white/10 pt-2">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-cyan-100">Sources</p>
                  <div className="flex flex-wrap gap-2">
                    {message.sources.map((source) => (
                      <span key={`${source.chunk_id}-${source.score}`} className="rounded bg-cyan-300/15 px-2 py-1 text-xs text-cyan-100">
                        {source.filename} {source.page_number ? `Page ${source.page_number}` : ""}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          {loadingAnswer && <p className="text-sm text-cyan-100">Searching documents...</p>}
        </div>

        <form onSubmit={sendQuestion} className="border-t border-white/10 p-3">
          {error && <p className="mb-2 rounded-md border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>}
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about uploaded documents"
              className="min-w-0 flex-1 rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/60"
            />
            <button disabled={loadingAnswer || !input.trim()} className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-cyan-300/40 bg-cyan-300/20 text-cyan-50 disabled:opacity-50">
              <Send size={17} />
            </button>
          </div>
        </form>
      </section>
    </motion.section>
  );
}

function formatUploadError(error, fallback) {
  const data = error.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  if (data.file) return Array.isArray(data.file) ? data.file.join(" ") : String(data.file);
  const firstError = Object.values(data).flat?.()[0];
  return firstError ? String(firstError) : fallback;
}

function formatBytes(value) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export default DocumentsPage;
