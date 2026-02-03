// Kiroku Memory Desktop - Tauri API Types and Functions

import { invoke } from "@tauri-apps/api/core";

// ============================================================================
// Types
// ============================================================================

export type ServiceStatus =
  | "Starting"
  | "Running"
  | "Stopped"
  | "Restarting"
  | { Error: string };

export interface HealthResponse {
  status: string;
  version: string;
}

export interface StatsResponse {
  backend: string;
  items: {
    total: number;
    active: number;
    archived: number;
  };
  categories: number;
}

export interface AppSettings {
  auto_start_service: boolean;
  service_port: number;
  start_hidden: boolean;
  launch_at_login: boolean;
}

// Memory Types
export interface Resource {
  id: string;
  created_at: string;
  source: string;
  content: string;
  metadata_: Record<string, unknown>;
}

export interface Item {
  id: string;
  created_at: string;
  subject: string | null;
  predicate: string | null;
  object: string | null;
  category: string | null;
  confidence: number;
  status: string;
}

export interface Category {
  id: string;
  name: string;
  summary: string | null;
  updated_at: string;
}

export interface RetrievalResponse {
  query: string;
  categories: Category[];
  items: Item[];
  total_items: number;
}

// ============================================================================
// Service Commands
// ============================================================================

export async function getServiceStatus(): Promise<ServiceStatus> {
  return invoke<ServiceStatus>("get_service_status");
}

export async function checkHealth(): Promise<HealthResponse> {
  const json = await invoke<string>("check_health");
  return JSON.parse(json);
}

export async function getStats(): Promise<StatsResponse> {
  const json = await invoke<string>("get_stats");
  return JSON.parse(json);
}

export async function restartService(): Promise<void> {
  return invoke<void>("restart_service");
}

export async function stopService(): Promise<void> {
  return invoke<void>("stop_service");
}

// ============================================================================
// Config Commands
// ============================================================================

export async function setOpenAIKey(key: string): Promise<void> {
  return invoke<void>("set_openai_key", { key });
}

export async function hasOpenAIKey(): Promise<boolean> {
  return invoke<boolean>("has_openai_key");
}

export async function deleteOpenAIKey(): Promise<void> {
  return invoke<void>("delete_openai_key");
}

export async function getSettings(): Promise<AppSettings> {
  return invoke<AppSettings>("get_settings");
}

export async function saveSettings(newSettings: AppSettings): Promise<void> {
  return invoke<void>("save_settings", { newSettings });
}

export async function getDataDir(): Promise<string> {
  return invoke<string>("get_data_dir");
}

// ============================================================================
// Memory API (Direct HTTP to Python FastAPI)
// ============================================================================

const API_BASE = "http://127.0.0.1:8000";

export async function getResources(options?: {
  limit?: number;
  offset?: number;
  source?: string;
}): Promise<Resource[]> {
  const params = new URLSearchParams();
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.offset) params.set("offset", String(options.offset));
  if (options?.source) params.set("source", options.source);

  const url = `${API_BASE}/v2/resources${params.toString() ? `?${params}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch resources: ${res.status}`);
  return res.json();
}

export async function getItems(options?: {
  limit?: number;
  offset?: number;
  category?: string;
  status?: string;
}): Promise<Item[]> {
  const params = new URLSearchParams();
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.offset) params.set("offset", String(options.offset));
  if (options?.category) params.set("category", options.category);
  if (options?.status) params.set("status", options.status);

  const url = `${API_BASE}/v2/items${params.toString() ? `?${params}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch items: ${res.status}`);
  return res.json();
}

export async function getCategories(): Promise<Category[]> {
  const res = await fetch(`${API_BASE}/v2/categories`);
  if (!res.ok) throw new Error(`Failed to fetch categories: ${res.status}`);
  return res.json();
}

export async function searchMemories(query: string): Promise<RetrievalResponse> {
  const params = new URLSearchParams({ query });
  const res = await fetch(`${API_BASE}/retrieve?${params}`);
  if (!res.ok) throw new Error(`Failed to search: ${res.status}`);
  return res.json();
}

export async function ingestMemory(content: string, source: string): Promise<{ resource_id: string }> {
  const res = await fetch(`${API_BASE}/v2/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, source }),
  });
  if (!res.ok) throw new Error(`Failed to ingest: ${res.status}`);
  return res.json();
}

// ============================================================================
// Helpers
// ============================================================================

export function isServiceRunning(status: ServiceStatus): boolean {
  return status === "Running";
}

export function isServiceError(
  status: ServiceStatus
): status is { Error: string } {
  return typeof status === "object" && "Error" in status;
}

export function getServiceStatusText(status: ServiceStatus): string {
  if (typeof status === "string") {
    return status;
  }
  return `Error: ${status.Error}`;
}
