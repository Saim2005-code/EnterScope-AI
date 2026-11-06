import React, { useState } from 'react';
import { User, Sparkles, Paperclip, Send, ShieldAlert } from 'lucide-react';
import CitationList from './CitationList';
import { queryRagAssistant } from '../../services/ragApi';

export default function ChatAssistant({ currentRole, messages, setMessages }) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMsg = { id: `user-${Date.now()}`, sender: 'user', text: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const data = await queryRagAssistant({
        query: trimmed,
        userRole: currentRole,
        topK: 3,
      });

      const assistantMsg = {
        id: `ast-${Date.now()}`,
        sender: 'assistant',
        status: data.status || 'success',
        answer: data.answer,
        citations: data.citations || [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: 'assistant',
          status: 'error',
          answer: `Unable to reach RAG backend (${err.message}). Verify enterprise_rag_api is running on port 8000.`,
          citations: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="flex-1 flex flex-col bg-[#09090b] border-r border-[#1e1e24] min-w-0">
      {/* Header Bar - Clean, no System Connected status message */}
      <header className="h-16 px-6 border-b border-[#1e1e24] flex items-center gap-3 shrink-0">
        <h2 className="text-lg font-semibold text-white">AI Search Assistant</h2>
        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#132332] text-[#38bdf8] border border-[#0284c7]/40">
          Role: {currentRole}
        </span>
      </header>

      {/* Message Feed */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg) =>
          msg.sender === 'user' ? (
            <div
              key={msg.id}
              className="p-4 rounded-xl bg-[#121215] border border-[#232329] flex items-start gap-3"
            >
              <User className="w-5 h-5 text-zinc-400 shrink-0 mt-0.5" />
              <p className="text-sm text-zinc-100 leading-relaxed">{msg.text}</p>
            </div>
          ) : (
            <div
              key={msg.id}
              className="p-5 rounded-xl bg-[#121215] border border-[#232329] flex items-start gap-3"
            >
              {msg.status === 'abstained' ? (
                <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              ) : (
                <Sparkles className="w-5 h-5 text-zinc-300 shrink-0 mt-0.5" />
              )}
              <div className="flex-1 min-w-0">
                <div className="text-sm text-zinc-200 whitespace-pre-line leading-relaxed">
                  {msg.answer}
                </div>
                <CitationList citations={msg.citations} />
              </div>
            </div>
          )
        )}

        {isLoading && (
          <div className="p-4 rounded-xl bg-[#121215] border border-[#232329] text-xs text-zinc-400 animate-pulse">
            Retrieving RBAC-filtered vectors from Qdrant & reranking via ONNX...
          </div>
        )}
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-[#1e1e24] bg-[#09090b]">
        <form
          onSubmit={handleSend}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#121215] border border-[#27272a] focus-within:border-zinc-500"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none"
          />
          <button
            type="button"
            title="Attach reference context"
            className="p-1.5 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <Paperclip className="w-4 h-4" />
          </button>
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="p-1.5 text-zinc-400 hover:text-[#2dd4bf] disabled:opacity-40 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </section>
  );
}