"use client";

import { useState } from "react";
import axios from "axios";
import { ChatMessage } from "@/components/chat/MessageBubble";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

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

    // Get root backend address
    const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      // 2. Query the unversioned POST /chat endpoint
      const response = await axios.post(`${backendBaseUrl}/chat`, { message: text });
      
      // Simulating minor network latency for animation visibility
      await new Promise((resolve) => setTimeout(resolve, 500));

      const data = response.data;
      const botText = data.intent === "unknown" ? data.message : data.response;

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
      
      const botText = `Failed to process chat query.\n\nError: ${errorMsg}\n\nPlease verify your FastAPI backend is running on ${backendBaseUrl}.`;

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
  };

  return {
    messages,
    loading,
    sendMessage,
    clearChat,
  };
}
