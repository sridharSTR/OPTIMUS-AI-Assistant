import { CheckCircle2, X } from "lucide-react";

function Toast({ toast, onClose }) {
  if (!toast) return null;

  return (
    <div className="fixed right-3 top-3 z-50 w-[min(92vw,360px)] animate-[toast-in_180ms_ease-out] rounded-lg border border-cyan-300/25 bg-slate-950/90 p-4 text-slate-100 shadow-2xl shadow-cyan-950/40 backdrop-blur-2xl">
      <div className="flex gap-3">
        <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-emerald-300/30 bg-emerald-300/15 text-emerald-100">
          <CheckCircle2 size={17} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-white">{toast.title}</p>
          <p className="mt-1 text-sm leading-5 text-slate-300">{toast.message}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-slate-400 hover:bg-white/10 hover:text-white"
          aria-label="Close notification"
        >
          <X size={15} />
        </button>
      </div>
    </div>
  );
}

export default Toast;
