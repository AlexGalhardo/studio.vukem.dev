// Shapes of the props the Go controllers send.

export interface Post {
  id: number;
  title: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  email_verified_at: string | null;
}

export interface JobListItem {
  id: number;
  subject: string;
  status: string;
  duration: number;
  style_skill: string;
  ratio: string;
}

export interface VideoJob extends JobListItem {
  goal: string;
  audience: string;
  language: string;
  facts: string;
  links: string;
  call_to_action: string;
  voice: string;
  music_license: string;
  prompt: string;
  model_id: string;
  script: string;
  failure: string;
  sidecar_json: string;
  pack_platform: string;
  pack_title: string;
  pack_description: string;
  pack_hashtags: string;
}

export interface SharedProps {
  appName: string;
  errors: Record<string, string>;
  // Present after vukem install:auth.
  auth?: { user: User | null };
  [key: string]: unknown;
}
