"use client";

import { useState, useEffect } from "react";
import { api } from "@/services/api";
import { ChatMessage } from "@/components/chat/MessageBubble";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  // Restore conversation ID and fetch history on client-side mount
  useEffect(() => {
    const savedId = localStorage.getItem("customer_support_conversation_id");
    if (savedId) {
      setConversationId(savedId);
      fetchHistory(savedId);
    }
  }, []);

  const fetchHistory = async (convId: string) => {
    setLoading(true);
    try {
      const response = await api.get(`/chat/conversations/${convId}/history`);
      const mapped = response.data.map((m: any) => ({
        id: m.message_id,
        sender: m.role as "user" | "assistant",
        text: m.content,
        timestamp: new Date(m.created_at),
      }));
      setMessages(mapped);
    } catch (error: any) {
      console.error("Failed to load chat history", error);
      // Only clear stored conversation reference if the backend definitively confirms
      // that the thread does not exist (HTTP 404).
      if (error?.status === 404 || error?.response?.status === 404) {
        localStorage.removeItem("customer_support_conversation_id");
        setConversationId(null);
        setMessages([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (text: string) => {
    // 1. Append user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      // 2. Query the canonical versioned /api/v1/chat/ endpoint
      const response = await api.post("/chat/", {
        message: text,
        conversation_id: conversationId,
      });
      
      // Simulating minor network latency for animation visibility
      await new Promise((resolve) => setTimeout(resolve, 500));

      const data = response.data;
      const botText = data.intent === "unknown" ? data.message : data.response;

      // Update conversation_id for subsequent message turns to maintain thread context
      if (data.conversation_id) {
        setConversationId(data.conversation_id);
        localStorage.setItem("customer_support_conversation_id", data.conversation_id);
      }

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: botText,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error("Chat routing query failed", error);
      
      let errorMsg = "An unexpected connection error occurred.";
      if (error.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error.message) {
        errorMsg = error.message;
      }
      
      const botText = `Failed to process chat query.\n\nError: ${errorMsg}\n\nPlease verify your FastAPI backend is running.`;

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: botText,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setConversationId(null);
    localStorage.removeItem("customer_support_conversation_id");
  };

  return {
    messages,
    loading,
    sendMessage,
    clearChat,
  };
}
