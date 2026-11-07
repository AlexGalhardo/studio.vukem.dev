/**
 * Sidebar navigation. Each category maps to a folder in content/docs and
 * lists its pages in display order. A page "<dir>/<slug>.mdx" is served at
 * /docs/<prefix>/<slug> (prefix defaults to the folder name; the
 * "Getting started" pages live at the root of /docs).
 */
export type NavCategory = {
  title: string;
  dir: string;
  prefix?: string;
  pages: string[];
};

export const navigation: NavCategory[] = [
  {
    title: "Getting started",
    dir: "getting-started",
    prefix: "",
    pages: ["introduction", "quickstart", "configuration", "repository", "status"],
  },
  {
    title: "Pipeline",
    dir: "pipeline",
    pages: ["overview", "brief", "jobs", "render", "qa"],
  },
  {
    title: "Tools",
    dir: "tools",
    pages: ["overview", "renderers", "audio", "models"],
  },
  {
    title: "Skills",
    dir: "skills",
    pages: ["catalog"],
  },
  {
    title: "Deployment",
    dir: "deployment",
    pages: ["railway", "app", "releases"],
  },
  {
    title: "Security",
    dir: "security",
    pages: ["overview"],
  },
];
