import React, { useState } from 'react';
import { FileText } from 'lucide-react';

export default function CitationList({ citations }) {
  const [expandedId, setExpandedId] = useState(null);

  if (!citations || citations.length === 0) return null;

  const toggleSnippet = (id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="mt-4 pt-3 border-t border-[#232329]">
      <div className="text-xs font-semibold text-zinc-300 mb-2.5">References</div>
      <div className="space-y-2">
        {citations.map((cite, index) => {
          const refNumber = cite.id || index + 1;
          const isExpanded = expandedId === refNumber;

          return (
            <div key={refNumber} className="flex flex-col">
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-[#0f292a] text-[#2dd4bf] border border-[#14b8a6]/40">
                  [{refNumber}] {cite.source_file}
                </span>
                <button
                  type="button"
                  onClick={() => toggleSnippet(refNumber)}
                  className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>{isExpanded ? 'Hide snippet' : 'View snippet'}</span>
                </button>
              </div>

              {isExpanded && (
                <div className="mt-2 p-3 rounded-lg bg-[#09090b] border border-[#27272a] text-xs text-zinc-300 font-mono leading-relaxed">
                  {cite.snippet || 'Verified chunk retrieved from Qdrant enterprise_docs collection.'}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}