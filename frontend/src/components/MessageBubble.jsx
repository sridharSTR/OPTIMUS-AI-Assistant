import { Bot, User } from "lucide-react";

import MarkdownRenderer from "./common/MarkdownRenderer.jsx";

function MessageBubble({ message, isLoading = false }) {
  const isUser = message.role === "user";
  const entityCount = message.entities
    ? Object.values(message.entities).reduce((total, values) => total + values.length, 0)
    : 0;

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-cyan-300/30 bg-cyan-300/15 text-cyan-100 shadow-lg shadow-cyan-950/30 backdrop-blur-xl">
          <Bot size={16} />
        </div>
      )}
      <div
        className={`max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6 shadow-2xl backdrop-blur-2xl ${
          isUser
            ? "border border-fuchsia-300/30 bg-fuchsia-300/15 text-fuchsia-50 shadow-fuchsia-950/25"
            : "border border-white/15 bg-white/[0.08] text-slate-100 shadow-cyan-950/25"
        }`}
      >
        {isUser || isLoading ? (
          <>
            <p className={`whitespace-pre-wrap ${isLoading ? "animate-pulse" : ""}`}>{message.content}</p>
            {(message.intent || (isUser && (message.sentiment || entityCount > 0))) && (
              <div className="mt-3 flex flex-wrap gap-2 border-t border-white/10 pt-2 text-xs">
                {message.intent && <span className="rounded bg-cyan-300/15 px-2 py-0.5 text-cyan-100">{message.intent}</span>}
                {isUser && message.sentiment && <span className="rounded bg-fuchsia-300/15 px-2 py-0.5 text-fuchsia-100">{message.sentiment}</span>}
                {isUser && entityCount > 0 && <span className="rounded bg-emerald-300/15 px-2 py-0.5 text-emerald-100">{entityCount} entities</span>}
              </div>
            )}
          </>
        ) : (
          <div className="markdown-response">
            <MarkdownRenderer content={message.content} />
            {message.intent && (
              <div className="mt-3 flex flex-wrap gap-2 border-t border-white/10 pt-2 text-xs">
                <span className="rounded bg-cyan-300/15 px-2 py-0.5 text-cyan-100">{message.intent}</span>
              </div>
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-fuchsia-300/30 bg-fuchsia-300/15 text-fuchsia-100 shadow-lg shadow-fuchsia-950/30 backdrop-blur-xl">
          <User size={16} />
        </div>
      )}
    </div>
  );
}

export default MessageBubble;
