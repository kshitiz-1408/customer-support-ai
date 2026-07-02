"use client";

import React from "react";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import ChatWindow from "@/components/chat/ChatWindow";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const { messages, loading, sendMessage } = useChat();

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col selection:bg-indigo-500/30">
      {/* Navbar Header */}
      <Navbar />

      <div className="flex-1 flex max-w-7xl mx-auto w-full relative">
        {/* Navigation Sidebar */}
        <Sidebar />

        {/* Messaging Container */}
        <main className="flex-1 p-6 flex flex-col justify-between">
          <ChatWindow 
            messages={messages} 
            loading={loading} 
            onSendMessage={sendMessage} 
          />
        </main>
      </div>
    </div>
  );
}
