/**
 * api.ts — Thin, typed wrapper around the Django backend.
 *
 * Every endpoint here maps 1:1 to a verified backend route (see
 * illusions_backend/story/urls.py). No client-side business logic lives
 * here beyond attaching the auth header and parsing JSON — the backend
 * remains the single source of truth for the reading loop, scoring, and
 * validation.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export interface StoryTheme {
  slug: string;
  name: string;
  description: string;
}

export interface StorySummary {
  id: string;
  slug: string;
  title: string;
  description: string;
  cover_image_url: string;
  estimated_minutes: number;
  themes: StoryTheme[];
}

export interface ChoiceOption {
  id: string;
  display_text: string;
  order_index: number;
}

export interface StoryNodeView {
  id: string;
  slug: string;
  chapter_title: string;
  text_content: string;
  node_type: "standard" | "choice_point" | "reflection" | "ending";
  is_ending: boolean;
  ending_label: string;
  choices: ChoiceOption[];
}

export interface ProfileView {
  profile: Record<string, number>;
  flags: string[];
  is_completed: boolean;
  run_number: number;
}

export interface Interpretation {
  id: string;
  tag_slug: string;
  tag_name: string;
  reader_facing_description: string;
  weight: number;
  choice_text: string;
  created_at: string;
}

export interface ReflectionView {
  id: string;
  summary_text: string;
  strongest_tag_slug: string | null;
  interpretations: Interpretation[];
  generated_at: string;
}

export interface RunComparison {
  run_a: number;
  run_b: number;
  profile_a: Record<string, number>;
  profile_b: Record<string, number>;
  diverging_choices: { node_slug: string; run_a_choice: string; run_b_choice: string }[];
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, token: string | null, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let code = "error";
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch {
      // Response wasn't JSON (e.g. a proxy error page) — fall back to the generic message.
    }
    throw new ApiError(response.status, code, message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function login(username: string, password: string) {
  return request<{ access: string; refresh: string }>("/api/auth/token/", null, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function fetchLibrary(token: string) {
  return request<StorySummary[]>("/api/stories/", token);
}

export async function fetchCurrentNode(token: string, storyId: string) {
  return request<StoryNodeView>(`/api/stories/${storyId}/session/`, token);
}

export async function submitChoice(token: string, storyId: string, choiceId: string) {
  return request<{ node: StoryNodeView; profile: ProfileView }>(
    `/api/stories/${storyId}/session/choice/`,
    token,
    { method: "POST", body: JSON.stringify({ choice_id: choiceId }) }
  );
}

export async function fetchProfile(token: string, storyId: string) {
  return request<ProfileView>(`/api/stories/${storyId}/session/profile/`, token);
}

export async function fetchReflection(token: string, storyId: string) {
  return request<ReflectionView>(`/api/stories/${storyId}/session/reflection/`, token);
}

export async function startReplay(token: string, storyId: string) {
  return request<{ run_number: number; node: StoryNodeView }>(
    `/api/stories/${storyId}/replay/`,
    token,
    { method: "POST" }
  );
}

export async function compareRuns(token: string, storyId: string, a: number, b: number) {
  return request<RunComparison>(`/api/stories/${storyId}/compare/?a=${a}&b=${b}`, token);
}
