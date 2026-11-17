// End-to-end tests: starts a fresh backend (separate DB) and the Vite dev server.
import { defineConfig, devices } from "@playwright/test";

const BACKEND_PORT = 8011;
const FRONTEND_PORT = 5181;

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: [
    {
      command:
        "rm -rf .e2e && mkdir -p .e2e && .venv/bin/alembic upgrade head && " +
        `.venv/bin/uvicorn app.main:app --port ${BACKEND_PORT}`,
      cwd: "../backend",
      url: `http://127.0.0.1:${BACKEND_PORT}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATABASE_URL: "sqlite:///./.e2e/e2e.db",
        CHECKPOINT_DB_PATH: "./.e2e/checkpoints.db",
        GENERATED_PROJECTS_DIR: "./.e2e/generated",
        LLM_API_KEY: "",
        AUTH_ENABLED: "false",
        SANDBOX_MODE: "disabled",
        MOCK_INJECT_DEFECT: "true",
        RATE_LIMIT_PER_MINUTE: "1000",
        CORS_ORIGINS: `http://127.0.0.1:${FRONTEND_PORT}`,
      },
    },
    {
      command: `npx vite --port ${FRONTEND_PORT} --strictPort --host 127.0.0.1`,
      url: `http://127.0.0.1:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { VITE_PROXY_TARGET: `http://127.0.0.1:${BACKEND_PORT}` },
    },
  ],
});
