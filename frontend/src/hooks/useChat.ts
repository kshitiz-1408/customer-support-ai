"use client";

import { useState, useEffect, useRef } from "react";
import { api } from "@/services/api";
import { ChatMessage } from "@/components/chat/MessageBubble";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [conversationId, setConversationId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("customer_support_conversation_id");
    }
    return null;
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchHistory = async (convId: string) => {
    setLoading(true);
    try {
      const response = await api.get(`/chat/conversations/${convId}/history`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const mapped = response.data.map((m: any) => ({
        id: m.message_id,
        sender: m.role as "user" | "assistant",
        text: m.content,
        timestamp: new Date(m.created_at),
      }));
      setMessages(mapped);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      console.error("Failed to load chat history", error);
      // Only clear stored conversation reference if the backend definitively confirms
      // that the thread does not exist (HTTP 404).
      if (error?.status === 404) {
        localStorage.removeItem("customer_support_conversation_id");
        setConversationId(null);
        setMessages([]);
      }
    } finally {
      setLoading(false);
    }
  };

  // Restore conversation ID and fetch history on client-side mount
  useEffect(() => {
    const savedId = localStorage.getItem("customer_support_conversation_id");
    if (savedId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchHistory(savedId);
    }
    
    // Cleanup any pending request on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const sendMessage = async (text: string) => {
    // 0. Prevent duplicate submission / rapid clicks
    if (loading) return;

    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Initialize new AbortController
    const controller = new AbortController();
    abortControllerRef.current = controller;

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
      const response = await api.post(
        "/chat/",
        {
          message: text,
          conversation_id: conversationId,
        },
        {
          signal: controller.signal,
        }
      );
      
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      // If the request was cancelled, do not append an error bubble
      if (error?.isCancelled) {
        return;
      }

      console.error("Chat routing query failed", error);
      
      const errorMsg = error?.message || "An unexpected connection error occurred.";
      const reqId = error?.requestId || null;
      
      const botText = `Failed to process chat query.\n\nError: ${errorMsg}\n\nPlease verify your FastAPI backend is running.${
        reqId ? `\n\nRequest ID: ${reqId}` : ""
      }`;

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: botText,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      // Avoid updating state if this request was aborted and replaced
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  };

  const clearChat = () => {
    // Abort any active query
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
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
