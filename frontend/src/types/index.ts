export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type TicketCategory = "billing" | "technical" | "account" | "general";

export interface Ticket {
  id: number;
  customer_name: string;
  customer_email: string;
  subject: string;
  description: string;
  priority: TicketPriority;
  category: TicketCategory;
  status: TicketStatus;
  created_at: string;
  updated_at: string;
  assigned_agent?: string;
  resolution_notes?: string;
}

export interface TicketCreate {
  customer_name: string;
  customer_email: string;
  subject: string;
  description: string;
  priority: TicketPriority;
  category: TicketCategory;
}

export interface TicketUpdate {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: TicketCategory;
  assigned_agent?: string;
  resolution_notes?: string;
}

export interface KBArticle {
  id: number;
  title: string;
  content: string;
  category: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface KBArticleCreate {
  title: string;
  content: string;
  category: string;
  tags: string[];
}

export interface KBSearchResult {
  article: KBArticle;
  score: number;
}
