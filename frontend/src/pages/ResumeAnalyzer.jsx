import { motion } from "framer-motion";
import { FileSearch, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";

import MarkdownRenderer from "../components/common/MarkdownRenderer.jsx";
import { nlpApi } from "../services/api.js";

function ResumeAnalyzer() {
  const [file, setFile] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadAnalyses = () => {
    nlpApi
      .resumeAnalyses()
      .then(({ data }) => setAnalyses(data))
      .catch(() => setError("Could not load resume analyses."));
  };

  useEffect(loadAnalyses, []);

  const submit = async (event) => {
    event.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const { data } = await nlpApi.analyzeResume(file);
      setAnalyses((current) => [data, ...current]);
      setFile(null);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not analyze this resume.");
    } finally {
      setLoading(false);
    }
  };

  const deleteAnalysis = async (id) => {
    const confirmed = window.confirm("Delete this resume analysis?");
    if (!confirmed) return;

    setError("");
    try {
      await nlpApi.deleteResumeAnalysis(id);
      setAnalyses((current) => current.filter((analysis) => analysis.id !== id));
    } catch (err) {
      setError(err.response?.data?.detail || "Could not delete this resume analysis.");
    }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto w-full max-w-5xl p-3 sm:p-5">
      <div className="mb-4 flex items-center gap-3">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-emerald-300/30 bg-emerald-300/15 text-emerald-100">
          <FileSearch size={18} />
        </span>
        <div>
          <h2 className="text-lg font-semibold text-white">Resume Analyzer</h2>
          <p className="text-sm text-slate-400">Upload a PDF to extract skills, projects, experience, gaps, and interview questions.</p>
        </div>
      </div>

      <form onSubmit={submit} className="mb-4 rounded-lg border border-white/15 bg-white/[0.08] p-4">
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-slate-300">PDF Resume</span>
          <input
            type="file"
            accept="application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="w-full rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm text-slate-200 file:mr-3 file:rounded-md file:border-0 file:bg-cyan-300/20 file:px-3 file:py-1.5 file:text-cyan-50"
          />
        </label>
        <button disabled={!file || loading} className="mt-3 inline-flex items-center gap-2 rounded-md border border-cyan-300/40 bg-cyan-300/20 px-3 py-2 text-sm font-semibold text-cyan-50 disabled:opacity-50">
          <Upload size={16} /> {loading ? "Analyzing..." : "Analyze Resume"}
        </button>
      </form>

      {error && <p className="mb-3 rounded-md border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>}

      <div className="space-y-4">
        {analyses.length === 0 && <p className="text-sm text-slate-400">No resume analyses yet.</p>}
        {analyses.map((analysis) => (
          <article key={analysis.id} className="rounded-lg border border-white/15 bg-white/[0.08] p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-base font-semibold text-white">{analysis.filename}</h3>
                <p className="text-sm text-slate-400">Resume score: {analysis.score}/100</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <div className="h-12 w-12 rounded-md border border-cyan-300/30 bg-cyan-300/15 text-center text-lg font-semibold leading-[3rem] text-cyan-100">
                  {analysis.score}
                </div>
                <button
                  type="button"
                  onClick={() => deleteAnalysis(analysis.id)}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-rose-300/25 bg-rose-500/10 text-rose-200 transition hover:bg-rose-500/20 hover:text-rose-100"
                  aria-label={`Delete ${analysis.filename}`}
                  title="Delete resume analysis"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              {analysis.score_explanation && (
                <div className="rounded-md bg-white/10 p-3 lg:col-span-2">
                  <h4 className="mb-2 text-sm font-semibold text-cyan-100">Score Breakdown</h4>
                  <MarkdownRenderer
                    content={`**Skills:** ${analysis.skills_score ?? 0}/60\n\n**Sections:** ${analysis.sections_score ?? 0}/40\n\n${analysis.score_explanation}`}
                    className="text-sm text-slate-200"
                  />
                </div>
              )}
              <InfoList title="Skills" items={analysis.found_skills || analysis.skills} />
              <InfoList title="Missing Skills" items={analysis.missing_skills} />
              <InfoList title="Detected Sections" items={analysis.detected_sections || []} />
              <InfoList title="Missing Sections" items={analysis.missing_sections || []} />
              <InfoList title="Suggestions" items={analysis.suggestions} />
              <InfoList title="Interview Questions" items={analysis.interview_questions} />
            </div>
          </article>
        ))}
      </div>
    </motion.section>
  );
}

function InfoList({ title, items = [] }) {
  return (
    <div className="rounded-md bg-white/10 p-3">
      <h4 className="mb-2 text-sm font-semibold text-cyan-100">{title}</h4>
      {items.length === 0 ? (
        <p className="text-sm text-slate-400">No items detected.</p>
      ) : (
        <MarkdownRenderer content={items.map((item) => `- ${item}`).join("\n")} className="text-sm text-slate-200" />
      )}
    </div>
  );
}

export default ResumeAnalyzer;
