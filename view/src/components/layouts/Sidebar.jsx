import React from 'react';
import { MessageSquare, FileText, Users, Info, Lock, User } from 'lucide-react';
import { ROLES } from '../../config/constants';

export default function Sidebar({ activeTab, setActiveTab, currentRole, setCurrentRole, isAdmin, setIsAdmin }) {
  const navItems = [
    { id: 'chat', label: 'AI Chat', icon: MessageSquare },
    { id: 'ingest', label: 'Document Ingestion', subLabel: 'Admin only', icon: FileText, locked: true },
    { id: 'rbac', label: 'Access Control (RBAC)', icon: Users },
    { id: 'status', label: 'System Status', icon: Info },
  ];

  return (
    <aside className="w-64 bg-[#09090b] border-r border-[#1e1e24] flex flex-col justify-between select-none shrink-0">
      <div>
        {/* Typographic Branding Only - No Graphic Logo */}
        <div className="px-6 py-6 border-b border-[#1e1e24]">
          <h1 className="text-lg font-bold tracking-wider text-white">
            ENTERSCOPE <span className="text-[#2dd4bf]">AI</span>
          </h1>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-[#18181b] text-white font-medium border border-[#27272a]'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#121215]'
                }`}
              >
                <div className="flex items-center gap-3 text-left">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#2dd4bf]' : 'text-zinc-400'}`} />
                  <div>
                    <div>{item.label}</div>
                    {item.subLabel && <div className="text-[11px] text-zinc-500">{item.subLabel}</div>}
                  </div>
                </div>
                {item.locked && <Lock className="w-3.5 h-3.5 text-zinc-500" />}
              </button>
            );
          })}
        </nav>

        {/* RBAC Role Switcher Panel */}
        <div className="mx-3 mt-4 p-3 rounded-lg bg-[#121215] border border-[#1e1e24]">
          <label className="block text-[11px] uppercase tracking-wider text-zinc-500 font-semibold mb-2">
            Active RBAC Tenant Role
          </label>
          <select
            value={currentRole}
            onChange={(e) => setCurrentRole(e.target.value)}
            className="w-full bg-[#09090b] text-zinc-200 text-xs rounded border border-[#27272a] px-2.5 py-2 focus:outline-none focus:border-[#2dd4bf]"
          >
            {ROLES.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>

          <div className="mt-3 pt-3 border-t border-[#1e1e24] flex items-center justify-between">
            <span className="text-xs text-zinc-400">Admin Gateway Privilege</span>
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
              className="accent-[#2dd4bf] h-3.5 w-3.5 cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-[#1e1e24] flex items-center justify-between bg-[#09090b]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[#18181b] border border-[#27272a] flex items-center justify-center text-zinc-400">
            <User className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-medium text-zinc-200">
              {isAdmin ? 'Admin: Sarah J.' : 'User: Alex M.'}
            </div>
            <div className="text-[11px] text-zinc-500 capitalize">({currentRole})</div>
          </div>
        </div>
        <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-[#18181b] text-zinc-400 border border-[#27272a]">
          {isAdmin ? 'High' : 'Std'}
        </span>
      </div>
    </aside>
  );
}