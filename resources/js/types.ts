// Shapes of the props the Go controllers send.

export type VideoStatus = "queued" | "planning" | "rendering" | "ready" | "failed";

export interface Video {
  id: number;
  status: VideoStatus;
  stage: string;
  progress: number;
  attempts: number;
  title: string;
  brief: string;
  skill_id: string;
  model_id: string;
  prompt: string;
  plan: string;
  raw_response: string;
  error: string;
  sidecar: string;
  input_tokens: number;
  output_tokens: number;
  cost_micros: number;
  created_at: string;
}

export interface Skill {
  id: string;
  description: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  email_verified_at: string | null;
}

export interface SharedProps {
  appName: string;
  errors: Record<string, string>;
  // Present after vukem install:auth.
  auth?: { user: User | null };
  [key: string]: unknown;
}
