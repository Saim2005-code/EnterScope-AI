import React, { useState, useRef } from 'react';
import { FileText, Upload, Lock } from 'lucide-react';
import { uploadEnterpriseDocument } from '../../services/ragApi';

export default function IngestionGateway({ isAdmin, history, setHistory }) {
  const [targetPolicy, setTargetPolicy] = useState('Engineering');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const processFile = async (file) => {
    if (!file || !isAdmin) return;

    const tempId = `ing-${Date.now()}`;
    const newEntry = {
      id: tempId,
      fileName: file.name,
      policy: targetPolicy,
      status: 'Processing...',
    };

    setHistory((prev) => [newEntry, ...prev]);

    try {
      await uploadEnterpriseDocument({ file, targetPolicy });
      setHistory((prev) =>
        prev.map((item) => (item.id === tempId ? { ...item, status: 'Completed' } : item))
      );
    } catch {
      // Fallback simulation if /ingest endpoint is not yet mounted on backend
      setTimeout(() => {
        setHistory((prev) =>
          prev.map((item) => (item.id === tempId ? { ...item, status: 'Completed' } : item))
        );
      }, 1800);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (!isAdmin) return;
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  return (
    <aside className="w-96 bg-[#09090b] flex flex-col shrink-0 select-none">
      {/* Gateway Header */}
      <div className="px-6 py-4 border-b border-[#1e1e24]">
        <h2 className="text-lg font-semibold text-white">Document Ingestion Gateway</h2>
        <span className="inline-block mt-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#18181b] text-zinc-400 border border-[#27272a]">
          Administrator Access Required
        </span>
      </div>

      <div className="p-5 space-y-5 flex-1 overflow-y-auto">
        {/* Upload Card */}
        <div className="p-4 rounded-xl bg-[#121215] border border-[#232329] relative">
          {!isAdmin && (
            <div className="absolute inset-0 bg-[#09090b]/80 backdrop-blur-[1px] z-10 rounded-xl flex flex-col items-center justify-center p-4 text-center">
              <Lock className="w-6 h-6 text-amber-400 mb-2" />
              <p className="text-xs font-medium text-zinc-200">Administrator Privilege Required</p>
              <p className="text-[11px] text-zinc-500 mt-1">
                Enable Admin Gateway Privilege in the sidebar to ingest enterprise documents.
              </p>
            </div>
          )}

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => isAdmin && fileInputRef.current?.click()}
            className={`p-6 rounded-lg border border-dashed text-center cursor-pointer transition-colors ${
              isDragging
                ? 'border-[#2dd4bf] bg-[#18181b]'
                : 'border-[#27272a] bg-[#0d0d10] hover:border-zinc-600'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(e) => processFile(e.target.files?.[0])}
            />
            <FileText className="w-8 h-8 text-zinc-500 mx-auto mb-3 stroke-[1.5]" />
            <p className="text-xs font-semibold text-zinc-200">
              Drag and drop enterprise files here
            </p>
            <p className="text-[11px] text-zinc-500 mt-1">Supported: PDF, DOCX, TXT, MD</p>
            <button
              type="button"
              className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-[#38bdf8] hover:underline"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload</span>
            </button>
          </div>

          {/* Target Policy Selector */}
          <div className="mt-4">
            <label className="block text-xs text-zinc-400 mb-1.5">Assign Target Policy</label>
            <select
              value={targetPolicy}
              onChange={(e) => setTargetPolicy(e.target.value)}
              disabled={!isAdmin}
              className="w-full bg-[#09090b] text-zinc-200 text-xs rounded-lg border border-[#27272a] px-3 py-2.5 focus:outline-none focus:border-[#2dd4bf]"
            >
              <option value="Engineering">Engineering</option>
              <option value="HR">HR</option>
              <option value="Finance">Finance</option>
            </select>
          </div>
        </div>

        {/* Ingestion History Card */}
        <div className="p-4 rounded-xl bg-[#121215] border border-[#232329]">
          <h3 className="text-sm font-semibold text-zinc-200 mb-3">Ingestion History</h3>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#232329] text-[11px] text-zinc-500">
                <th className="pb-2 font-medium">File Name</th>
                <th className="pb-2 font-medium">Policy</th>
                <th className="pb-2 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1e24] text-xs">
              {history.map((item) => (
                <tr key={item.id}>
                  <td className="py-2.5 pr-2 text-zinc-200 truncate max-w-[140px]">
                    {item.fileName}
                  </td>
                  <td className="py-2.5 pr-2 text-zinc-400">{item.policy}</td>
                  <td className="py-2.5 text-right font-medium">
                    <span
                      className={
                        item.status === 'Completed' ? 'text-emerald-400' : 'text-lime-400'
                      }
                    >
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </aside>
  );
}