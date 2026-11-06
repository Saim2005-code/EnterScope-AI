import React, { useState } from 'react';
import Sidebar from './components/layouts/Sidebar';
import ChatAssistant from './components/chat/ChatAssistant';
import IngestionGateway from './components/Admin/IngestionGateway';
import { INITIAL_MESSAGES, INITIAL_INGESTION_HISTORY } from './config/constants';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [currentRole, setCurrentRole] = useState('engineering');
  const [isAdmin, setIsAdmin] = useState(true);
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [ingestionHistory, setIngestionHistory] = useState(INITIAL_INGESTION_HISTORY);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#09090b] text-zinc-100 antialiased">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentRole={currentRole}
        setCurrentRole={setCurrentRole}
        isAdmin={isAdmin}
        setIsAdmin={setIsAdmin}
      />

      <main className="flex-1 flex min-w-0">
        <ChatAssistant
          currentRole={currentRole}
          messages={messages}
          setMessages={setMessages}
        />

        <IngestionGateway
          isAdmin={isAdmin}
          history={ingestionHistory}
          setHistory={setIngestionHistory}
        />
      </main>
    </div>
  );
}