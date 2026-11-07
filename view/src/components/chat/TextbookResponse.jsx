import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

/**
 * Preprocesses content before parsing with remarkMath and ReactMarkdown:
 * 1. Converts LaTeX \[ ... \] display blocks to $$ ... $$
 * 2. Converts LaTeX \( ... \) inline blocks to $ ... $
 * 3. Protects standalone currency values ($1.2M, $10,000, $500, etc.) from being
 *    eaten by remark-math's standard dollar delimiter parser.
 */
function preprocessTextbookContent(content) {
  if (!content) return '';
  let text = String(content);

  // Normalize display math \[ ... \] to standard $$ ... $$
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => `\n\n$$\n${math.trim()}\n$$\n\n`);

  // Normalize inline math \( ... \) to standard $ ... $
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => `$${math.trim()}$`);

  // Protect standalone currency figures ($1.2M, $10,000, $500, etc.)
  text = text.replace(/(^|[\s(])\$(\d+(?:\.\d+)?(?:[kKmMbBtT]|,\d+)*)(?=\s|[.,;)]|$)/g, '$1\\$$$2');

  return text;
}

export default function TextbookResponse({ content, isAbstained = false }) {
  const processed = useMemo(() => preprocessTextbookContent(content), [content]);

  if (isAbstained) {
    return (
      <div className="font-serif text-amber-200/90 text-sm sm:text-[15px] leading-relaxed italic bg-amber-950/20 border border-amber-800/30 rounded-lg p-3.5">
        {content}
      </div>
    );
  }

  return (
    <div
      className="textbook-prose prose prose-invert max-w-none font-serif text-[15px] sm:text-[16px] leading-[1.85] text-zinc-200
        prose-headings:font-serif prose-headings:font-bold prose-headings:text-zinc-100 prose-headings:tracking-tight
        prose-h1:text-xl prose-h1:my-3 prose-h1:border-b prose-h1:border-zinc-800 prose-h1:pb-1.5
        prose-h2:text-lg prose-h2:my-2.5 prose-h2:text-amber-100/90
        prose-h3:text-base prose-h3:my-2 prose-h3:text-zinc-200
        prose-p:my-2.5 prose-p:leading-[1.85]
        prose-ul:my-2.5 prose-ul:list-disc prose-ul:pl-6
        prose-ol:my-2.5 prose-ol:list-decimal prose-ol:pl-6
        prose-li:my-1 prose-li:leading-[1.75]
        prose-strong:font-bold prose-strong:text-amber-200/95
        prose-em:italic prose-em:text-zinc-300
        prose-blockquote:border-l-2 prose-blockquote:border-amber-400/50 prose-blockquote:bg-zinc-900/40 prose-blockquote:py-1.5 prose-blockquote:px-4 prose-blockquote:rounded-r prose-blockquote:italic prose-blockquote:text-zinc-300
        prose-code:font-mono prose-code:text-[13px] prose-code:bg-zinc-800/70 prose-code:text-teal-300 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none
        prose-pre:bg-zinc-950 prose-pre:border prose-pre:border-zinc-800 prose-pre:rounded-lg prose-pre:p-3
        prose-table:my-3 prose-table:border-collapse prose-th:border prose-th:border-zinc-700 prose-th:bg-zinc-800/60 prose-th:p-2.5 prose-td:border prose-td:border-zinc-800 prose-td:p-2.5"
    >
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}
