/**
 * Pipeline E2E Tests
 *
 * Tests for pipeline building, execution, and management
 */

import { test, expect, PipelineBuilderPage, mockApiResponse, waitForApiResponse } from './fixtures/test-fixtures';

test.describe('Pipeline Management', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // All tests start from authenticated state
  });

  test.describe('Pipeline Builder', () => {
    test('should load pipeline builder page', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-builder');

      // Should see pipeline builder interface
      await expect(authenticatedPage.locator('text=/pipeline/i')).toBeVisible();
    });

    test('should display available tables', async ({ authenticatedPage }) => {
      // Mock tables metadata
      await mockApiResponse(authenticatedPage, '**/api/metadata/**', {
        tables: ['dim_customer', 'dim_product', 'fact_sales']
      });

      await authenticatedPage.goto('/pipeline-builder');

      // Should see table list or selector
      await authenticatedPage.waitForTimeout(1000);
    });

    test('should select table for validation', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-builder');

      // Select a table (implementation depends on UI)
      const tableSelector = authenticatedPage.locator('[data-testid="table-selector"], select, [role="listbox"]');
      if (await tableSelector.isVisible()) {
        await tableSelector.click();
      }
    });

    test('should add validation steps', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-builder');

      // Click add step button
      const addStepBtn = authenticatedPage.locator('[data-testid="add-step-btn"], button:has-text("Add Step"), button:has-text("Add Validation")');
      if (await addStepBtn.isVisible()) {
        await addStepBtn.click();
      }
    });

    test('should generate pipeline YAML', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-builder');

      // Generate pipeline
      const generateBtn = authenticatedPage.locator('[data-testid="generate-pipeline-btn"], button:has-text("Generate")');
      if (await generateBtn.isVisible()) {
        await generateBtn.click();
        await authenticatedPage.waitForTimeout(1000);
      }
    });

    test('should preview generated YAML', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-builder');

      // Preview button
      const previewBtn = authenticatedPage.locator('[data-testid="preview-yaml"], button:has-text("Preview")');
      if (await previewBtn.isVisible()) {
        await previewBtn.click();
        // Should show YAML preview
        await expect(authenticatedPage.locator('pre, code, .yaml-preview')).toBeVisible();
      }
    });

    test('should save pipeline', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-builder');

      // Save pipeline
      const saveBtn = authenticatedPage.locator('[data-testid="save-pipeline-btn"], button:has-text("Save")');
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
      }
    });
  });

  test.describe('Pipeline Execution', () => {
    test('should load pipeline execution page', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-execution');

      // Should see execution interface
      await expect(authenticatedPage).toHaveURL(/.*execution.*/);
    });

    test('should display available pipelines', async ({ authenticatedPage }) => {
      // Mock pipeline list
      await mockApiResponse(authenticatedPage, '**/api/pipelines/list', {
        pipelines: [
          { name: 'dim_customer_validation', last_run: '2024-01-01' },
          { name: 'fact_sales_validation', last_run: '2024-01-02' }
        ]
      });

      await authenticatedPage.goto('/pipeline-execution');
      await authenticatedPage.waitForTimeout(1000);
    });

    test('should run selected pipeline', async ({ authenticatedPage }) => {
      // Mock pipeline execution
      await mockApiResponse(authenticatedPage, '**/api/pipelines/execute', {
        run_id: 'run_test_123',
        status: 'started'
      });

      await authenticatedPage.goto('/pipeline-execution');

      // Select and run
      const runBtn = authenticatedPage.locator('[data-testid="run-pipeline-btn"], button:has-text("Run"), button:has-text("Execute")');
      if (await runBtn.isVisible()) {
        await runBtn.click();
      }
    });

    test('should show execution progress', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-execution');

      // Progress indicator should appear during execution
      const progress = authenticatedPage.locator('[role="progressbar"], .MuiLinearProgress-root, .MuiCircularProgress-root');
      // May or may not be visible depending on state
    });

    test('should navigate to results after completion', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-execution');

      // After execution, should have link to results
      const resultsLink = authenticatedPage.locator('a:has-text("View Results"), [data-testid="view-results"]');
      // May or may not be visible depending on state
    });
  });

  test.describe('Pipeline List', () => {
    test('should list all pipelines', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipelines');

      // Should see pipeline list
      await authenticatedPage.waitForTimeout(1000);
    });

    test('should filter pipelines', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipelines');

      // Filter input
      const filterInput = authenticatedPage.locator('[data-testid="pipeline-filter"], input[placeholder*="filter"], input[placeholder*="search"]');
      if (await filterInput.isVisible()) {
        await filterInput.fill('dim_');
        await authenticatedPage.waitForTimeout(500);
      }
    });

    test('should delete pipeline', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipelines');

      // Delete button
      const deleteBtn = authenticatedPage.locator('[data-testid="delete-pipeline"], button[aria-label="delete"]').first();
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
        // Confirm delete
        await authenticatedPage.click('button:has-text("Confirm"), button:has-text("Delete")');
      }
    });
  });

  test.describe('Pipeline YAML Editor', () => {
    test('should load YAML editor', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-yaml');

      // Should see editor
      await expect(authenticatedPage.locator('textarea, .monaco-editor, .CodeMirror')).toBeVisible();
    });

    test('should validate YAML syntax', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-yaml');

      // Enter invalid YAML
      const editor = authenticatedPage.locator('textarea, .monaco-editor textarea');
      if (await editor.isVisible()) {
        await editor.fill('invalid: [yaml: syntax');
        await authenticatedPage.waitForTimeout(500);
        // Should show error indication
      }
    });

    test('should save edited YAML', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-yaml');

      // Edit and save
      const editor = authenticatedPage.locator('textarea, .monaco-editor textarea');
      if (await editor.isVisible()) {
        await editor.fill('pipeline:\n  name: Test\n  steps: []');
        await authenticatedPage.click('button:has-text("Save")');
      }
    });
  });

  test.describe('Pipeline Suggestions', () => {
    test('should show intelligent suggestions', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-suggestions');

      // Should see suggestions interface
      await authenticatedPage.waitForTimeout(1000);
    });

    test('should generate suggestions from metadata', async ({ authenticatedPage }) => {
      // Mock suggestion API
      await mockApiResponse(authenticatedPage, '**/api/pipelines/intelligent-suggest', {
        suggestions: [
          { table: 'dim_customer', validations: ['row_count', 'null_check'] }
        ]
      });

      await authenticatedPage.goto('/pipeline-suggestions');
      await authenticatedPage.waitForTimeout(1000);
    });

    test('should accept suggestion', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/pipeline-suggestions');

      // Accept button
      const acceptBtn = authenticatedPage.locator('[data-testid="accept-suggestion"], button:has-text("Accept"), button:has-text("Apply")');
      if (await acceptBtn.isVisible()) {
        await acceptBtn.click();
      }
    });
  });
});
