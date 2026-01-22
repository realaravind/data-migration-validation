/**
 * Playwright Test Fixtures for Ombudsman Validation Studio
 *
 * Provides reusable fixtures for authentication, test data, and page objects
 */

import { test as base, expect, Page } from '@playwright/test';

// Test user credentials
export const TEST_USER = {
  username: 'admin',
  password: 'admin123',
};

// API endpoints
export const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

/**
 * Custom test fixtures extending Playwright's base test
 */
export const test = base.extend<{
  authenticatedPage: Page;
  apiContext: {
    get: (endpoint: string) => Promise<Response>;
    post: (endpoint: string, data?: unknown) => Promise<Response>;
  };
}>({
  // Fixture for authenticated page
  authenticatedPage: async ({ page }, use) => {
    // Navigate to login page
    await page.goto('/login');

    // Fill login form
    await page.fill('input[name="username"]', TEST_USER.username);
    await page.fill('input[name="password"]', TEST_USER.password);

    // Submit login
    await page.click('button[type="submit"]');

    // Wait for navigation to dashboard
    await page.waitForURL('**/dashboard**', { timeout: 10000 });

    // Use the authenticated page
    await use(page);

    // Cleanup: logout if needed
    try {
      if (page.url().includes('/dashboard') || page.url().includes('/projects')) {
        // Optional: perform logout
      }
    } catch {
      // Page might already be closed
    }
  },

  // Fixture for API context
  apiContext: async ({}, use) => {
    const context = {
      get: async (endpoint: string) => {
        return fetch(`${API_BASE_URL}${endpoint}`);
      },
      post: async (endpoint: string, data?: unknown) => {
        return fetch(`${API_BASE_URL}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: data ? JSON.stringify(data) : undefined,
        });
      },
    };

    await use(context);
  },
});

export { expect };

/**
 * Page Object Models
 */

export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login');
  }

  async login(username: string, password: string) {
    await this.page.fill('input[name="username"]', username);
    await this.page.fill('input[name="password"]', password);
    await this.page.click('button[type="submit"]');
  }

  async expectError(message: string) {
    await expect(this.page.locator('text=' + message)).toBeVisible();
  }
}

export class DashboardPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/dashboard');
  }

  async expectLoaded() {
    await expect(this.page).toHaveURL(/.*dashboard.*/);
  }

  async getProjectCards() {
    return this.page.locator('[data-testid="project-card"]');
  }

  async clickCreateProject() {
    await this.page.click('[data-testid="create-project-btn"]');
  }
}

export class ProjectManagerPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/projects');
  }

  async createProject(name: string, options?: {
    sqlDatabase?: string;
    snowflakeDatabase?: string;
  }) {
    await this.page.click('[data-testid="new-project-btn"]');
    await this.page.fill('input[name="name"]', name);

    if (options?.sqlDatabase) {
      await this.page.fill('input[name="sqlDatabase"]', options.sqlDatabase);
    }
    if (options?.snowflakeDatabase) {
      await this.page.fill('input[name="snowflakeDatabase"]', options.snowflakeDatabase);
    }

    await this.page.click('[data-testid="create-project-submit"]');
  }

  async selectProject(projectName: string) {
    await this.page.click(`text=${projectName}`);
  }

  async deleteProject(projectName: string) {
    await this.page.locator(`[data-testid="project-${projectName}"]`).locator('[data-testid="delete-btn"]').click();
    await this.page.click('[data-testid="confirm-delete"]');
  }
}

export class PipelineBuilderPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/pipeline-builder');
  }

  async selectTable(tableName: string) {
    await this.page.click(`[data-testid="table-${tableName}"]`);
  }

  async addValidationStep(stepType: string) {
    await this.page.click('[data-testid="add-step-btn"]');
    await this.page.click(`[data-testid="step-type-${stepType}"]`);
  }

  async generatePipeline() {
    await this.page.click('[data-testid="generate-pipeline-btn"]');
  }

  async savePipeline(name: string) {
    await this.page.fill('input[name="pipelineName"]', name);
    await this.page.click('[data-testid="save-pipeline-btn"]');
  }
}

export class ValidationResultsPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/results');
  }

  async getResultRows() {
    return this.page.locator('[data-testid="result-row"]');
  }

  async selectRun(runId: string) {
    await this.page.click(`[data-testid="run-${runId}"]`);
  }

  async getPassedCount() {
    return this.page.locator('[data-testid="passed-count"]').textContent();
  }

  async getFailedCount() {
    return this.page.locator('[data-testid="failed-count"]').textContent();
  }
}

export class BatchOperationsPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/batch');
  }

  async createBatchJob(name: string, pipelines: string[]) {
    await this.page.click('[data-testid="create-batch-btn"]');
    await this.page.fill('input[name="jobName"]', name);

    for (const pipeline of pipelines) {
      await this.page.click(`[data-testid="pipeline-checkbox-${pipeline}"]`);
    }

    await this.page.click('[data-testid="submit-batch-btn"]');
  }

  async getJobStatus(jobId: string) {
    return this.page.locator(`[data-testid="job-${jobId}-status"]`).textContent();
  }
}

/**
 * Helper functions
 */

export async function waitForApiResponse(page: Page, urlPattern: string | RegExp) {
  return page.waitForResponse(response =>
    typeof urlPattern === 'string'
      ? response.url().includes(urlPattern)
      : urlPattern.test(response.url())
  );
}

export async function mockApiResponse(page: Page, url: string, response: unknown) {
  await page.route(url, route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

export async function interceptApiCall(page: Page, url: string) {
  const requestPromise = page.waitForRequest(url);
  return requestPromise;
}
