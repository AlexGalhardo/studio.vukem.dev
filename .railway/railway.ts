import { defineRailway, project, service } from "railway/iac";
// This repository manages only its own resources in the environment. Other
// repositories export their own partial name.
// See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "studio";
export default defineRailway(() => {
  const studio = service("studio", {
    build: { buildEnvironment: "V3", builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    healthcheck: "/docs/introduction",
    healthcheckTimeout: 300,
    replicas: { "us-east4-eqdc4a": 1 },
  });

  return project("studio", {
    variables: { managed: false },
    resources: [studio],
  });
});
