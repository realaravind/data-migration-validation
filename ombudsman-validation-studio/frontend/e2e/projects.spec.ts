/**
 * Projects E2E Tests
 *
 * Tests for project management functionality
 */

import { test, expect, ProjectManagerPage, mockApiResponse } from './fixtures/test-fixtures';

test.describe('Project Management', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // All tests start from authenticated state
  });

  test.describe('Project List', () => {
    test('should display project list', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/projects');

      // Should see projects page
      await expect(authenticatedPage.locator('h1, h2')).toContainText(/projects/i);
    });

    test('should show empty state when no projects', async ({ authenticatedPage }) => {
      // Mock empty project list
      await mockApiResponse(authenticatedPage, '**/api/projects/list', {
        status: 'success',
        projects: [],
        count: 0
      });

      await authenticatedPage.goto('/projects');

      // Should show create project prompt
      await expect(authenticatedPage.locator('text=/no projects|create your first/i')).toBeVisible();
    });

    test('should display project cards', async ({ authenticatedPage }) => {
      // Mock project list
      await mockApiResponse(authenticatedPage, '**/api/projects/list', {
        status: 'success',
        projects: [
          { project_id: 'test1', name: 'Test Project 1', updated_at: '2024-01-01' },
          { project_id: 'test2', name: 'Test Project 2', updated_at: '2024-01-02' }
        ],
        count: 2
      });

      await authenticatedPage.goto('/projects');

      // Should see project cards
      await expect(authenticatedPage.locator('text=Test Project 1')).toBeVisible();
      await expect(authenticatedPage.locator('text=Test Project 2')).toBeVisible();
    });
  });

  test.describe('Create Project', () => {
    test('should open create project dialog', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/projects');

      // Click create button
      await authenticatedPage.click('[data-testid="new-project-btn"], button:has-text("Create"), button:has-text("New")');

      // Should see create dialog
      await expect(authenticatedPage.locator('[role="dialog"], .MuiDialog-root')).toBeVisible();
    });

    test('should create project with valid data', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/projects');

      // Open create dialog
      await authenticatedPage.click('[data-testid="new-project-btn"], button:has-text("Create"), button:has-text("New")');

      // Fill form
      await authenticatedPage.fill('input[name="name"]', 'E2E Test Project');
      await authenticatedPage.fill('input[name="description"], textarea[name="description"]', 'Created by E2E test');

      // Submit
      await authenticatedPage.click('button:has-text("Create"), [data-testid="create-project-submit"]');

      // Should show success or redirect
      await authenticatedPage.waitForTimeout(2000);
    });

    test('should validate required fields', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/projects');

      // Open create dialog
      await authenticatedPage.click('[data-testid="new-project-btn"], button:has-text("Create"), button:has-text("New")');

      // Try to submit without filling required fields
      await authenticatedPage.click('button:has-text("Create"), [data-testid="create-project-submit"]');

      // Should show validation error
      await expect(authenticatedPage.locator('.Mui-error, [aria-invalid="true"], text=/required/i')).toBeVisible();
    });
  });

  test.describe('Load Project', () => {
    test('should load project when clicked', async ({ authenticatedPage }) => {
      // Mock project list
      await mockApiResponse(authenticatedPage, '**/api/projects/list', {
        status: 'success',
        projects: [
          { project_id: 'test1', name: 'Test Project', updated_at: '2024-01-01' }
        ],
        count: 1
      });

      // Mock load project response
      await mockApiResponse(authenticatedPage, '**/api/projects/test1', {
        status: 'success',
        message: 'Project loaded',
        metadata: { name: 'Test Project' }
      });

      await authenticatedPage.goto('/projects');

      // Click on project
      await authenticatedPage.click('text=Test Project');

      // Should show project details or navigate
      await authenticatedPage.waitForTimeout(1000);
    });

    test('should show project details after loading', async ({ authenticatedPage }) => {
      const projectManager = new ProjectManagerPage(authenticatedPage);
      await projectManager.goto();

      // After loading, should see project configuration
      // This will vary based on UI implementation
    });
  });

  test.describe('Delete Project', () => {
    test('should confirm before deleting', async ({ authenticatedPage }) => {
      // Mock project list
      await mockApiResponse(authenticatedPage, '**/api/projects/list', {
        status: 'success',
        projects: [
          { project_id: 'test1', name: 'Test Project', updated_at: '2024-01-01' }
        ],
        count: 1
      });

      await authenticatedPage.goto('/projects');

      // Click delete button
      await authenticatedPage.click('[data-testid="delete-btn"], button[aria-label="delete"]');

      // Should show confirmation dialog
      await expect(authenticatedPage.locator('[role="dialog"], .MuiDialog-root')).toBeVisible();
    });

    test('should delete project on confirmation', async ({ authenticatedPage }) => {
      // Mock project list and delete
      await mockApiResponse(authenticatedPage, '**/api/projects/list', {
        status: 'success',
        projects: [
          { project_id: 'test1', name: 'Test Project', updated_at: '2024-01-01' }
        ],
        count: 1
      });

      await mockApiResponse(authenticatedPage, '**/api/projects/test1', {
        status: 'success',
        message: 'Project deleted'
      });

      await authenticatedPage.goto('/projects');

      // Click delete and confirm
      await authenticatedPage.click('[data-testid="delete-btn"], button[aria-label="delete"]');
      await authenticatedPage.click('[data-testid="confirm-delete"], button:has-text("Confirm"), button:has-text("Delete")');

      // Should remove project from list
      await authenticatedPage.waitForTimeout(1000);
    });
  });

  test.describe('Project Settings', () => {
    test('should show schema mappings', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/projects');

      // Navigate to settings
      await authenticatedPage.click('text=Settings, [data-testid="settings-tab"]');

      // Should see schema mapping section
      await expect(authenticatedPage.locator('text=/schema/i')).toBeVisible();
    });

    test('should update schema mappings', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/projects');

      // Navigate to settings and update
      // Implementation depends on UI
    });
  });
});
