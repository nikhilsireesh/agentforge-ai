// The interview demo, automated: create project → agents → five approvals →
// correction loop → documentation → delivery package → analytics.
import { expect, test } from "@playwright/test";

const SHOTS = process.env.E2E_SCREENSHOTS;

async function shot(page, name) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

function nav(page, name) {
  return page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name, exact: true }).click();
}

async function approveCurrent(page, checkpointLabel) {
  const panel = page.getByTestId("approval-panel").first();
  await expect(panel).toContainText(`${checkpointLabel} checkpoint`);
  await panel.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByTestId("approval-panel").filter({ hasText: `${checkpointLabel} checkpoint` })).toHaveCount(0);
}

test("full leave-management demo through the UI", async ({ page }) => {
  const consoleErrors = [];
  page.on("console", (msg) => msg.type() === "error" && consoleErrors.push(msg.text()));

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await shot(page, "01-overview-empty");

  // 1-2. Create project with the demo requirement and start the agents.
  await nav(page, "New Project");
  await page.getByRole("button", { name: "Employee Leave Management" }).click();
  await shot(page, "02-wizard");
  for (let i = 0; i < 3; i += 1) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Create & start agents" }).click();

  // 3-4. Requirement Analyst runs, workflow pauses at the first checkpoint.
  await expect(page.getByRole("heading", { name: "Workflow Monitor" })).toBeVisible();
  await expect(page.getByTestId("node-requirement_analyst")).toHaveAttribute("data-status", "completed");
  await expect(page.getByTestId("node-approval_requirements")).toHaveAttribute("data-status", "waiting_approval");
  await shot(page, "03-workflow-waiting");

  await nav(page, "Requirements");
  await expect(page.getByText(/Functional requirements \(\d+\)/)).toBeVisible();
  await expect(page.getByText("Clarification questions")).toBeVisible();
  await shot(page, "04-requirements");
  await approveCurrent(page, "Requirements");

  // 5-9. Research + architecture, then approve architecture.
  await nav(page, "Architecture");
  await expect(page.getByText("System architecture diagram")).toBeVisible();
  await shot(page, "05-architecture");
  await page.getByRole("tab", { name: /Database entities/ }).click();
  await expect(page.getByRole("heading", { name: "LeaveRequest" })).toBeVisible();
  await approveCurrent(page, "Architecture");

  // 10-11. Developer agent generates code, approve code changes.
  await nav(page, "Code Artifacts");
  await expect(page.getByText("app/main.py").first()).toBeVisible();
  await expect(page.getByText("intentionally injected").first()).toBeVisible();
  await shot(page, "06-code");
  await approveCurrent(page, "Code changes");

  // 12-13. Approve test execution → static checks catch defect → correction → re-test.
  await nav(page, "Testing Center");
  await approveCurrent(page, "Test execution");
  await expect(page.getByTestId("approval-panel")).toContainText("Final delivery checkpoint");
  await expect(page.getByText("1 / 2")).toBeVisible();
  await page.getByLabel("Test iteration").selectOption("0");
  await expect(page.getByText("static::ruff::app/main.py")).toBeVisible();
  await shot(page, "07-testing-initial-failure");
  await page.getByLabel("Test iteration").selectOption("latest");
  await shot(page, "08-testing-after-correction");

  // 14-15. Approve final artifacts → documentation agent.
  await approveCurrent(page, "Final delivery");
  await nav(page, "Documentation");
  await expect(page.getByTestId("markdown-preview")).toContainText("Project Overview");
  await page.getByRole("button", { name: /Final Delivery Report/ }).click();
  await expect(page.getByTestId("markdown-preview")).toContainText("Human approvals");
  await shot(page, "09-documentation");

  // 16. Download the delivery package.
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download delivery package" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.zip$/);

  // Workflow fully green.
  await nav(page, "Workflow Monitor");
  await expect(page.getByTestId("node-documentation")).toHaveAttribute("data-status", "completed");
  await expect(page.getByTestId("node-correction")).toHaveAttribute("data-status", "completed");
  await shot(page, "10-workflow-complete");

  await nav(page, "Agent Workspace");
  await expect(page.getByTestId("agent-card-documentation")).toContainText("Completed");
  await shot(page, "11-agents");

  // 17. Analytics reflect the real run.
  await nav(page, "Analytics");
  await expect(page.getByTestId("analytics-kpis")).toContainText("100%");
  await shot(page, "12-analytics");

  await nav(page, "Approval Center");
  await page.getByRole("tab", { name: /Approval history/ }).click();
  await expect(page.getByRole("cell", { name: "Final delivery" })).toBeVisible();
  await shot(page, "13-approval-history");

  await nav(page, "Overview");
  await expect(page.getByTestId("overview-stats")).toContainText("Successful");
  await shot(page, "14-overview");

  // Persistence: data survives a full reload.
  await page.reload();
  await expect(page.getByText("Employee Leave Management System").first()).toBeVisible();

  expect(consoleErrors).toEqual([]);
});

test("project management: search, edit and request revision", async ({ page }) => {
  await page.goto("/projects/new");
  await page.getByRole("button", { name: "Inventory Management" }).click();
  for (let i = 0; i < 3; i += 1) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Create & start agents" }).click();
  await expect(page.getByTestId("approval-panel")).toBeVisible();

  const panel = page.getByTestId("approval-panel");
  await panel.getByLabel("Approval feedback").fill("Please add barcode scanning.");
  await panel.getByRole("button", { name: "Request revision" }).click();
  await expect(page.getByText(/Checkpoint 'requirements' decision: revision_requested/)).toBeVisible();

  await nav(page, "Projects");
  await page.getByLabel("Search projects").fill("inventory");
  await expect(page.getByRole("link", { name: /Inventory Management System/ })).toBeVisible();
  await page.getByRole("button", { name: "Edit" }).first().click();
  await page.getByRole("dialog").locator("textarea").first().fill("Edited description");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Edited description")).toBeVisible();
});
