import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import "./MarkdownRenderer.css";

const markdownComponents = {
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
  input: ({ checked, type }) => {
    if (type !== "checkbox") return null;
    return <input type="checkbox" checked={checked} readOnly />;
  },
};

function MarkdownRenderer({ content = "", className = "" }) {
  const normalizedContent = useMemo(() => {
    if (content === null || content === undefined) return "";
    if (Array.isArray(content)) return content.join("\n");
    return String(content);
  }, [content]);

  return (
    <div className={`markdown-renderer ${className}`.trim()}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={markdownComponents}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}

export default memo(MarkdownRenderer);
