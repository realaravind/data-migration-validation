/**
 * Authentication E2E Tests
 *
 * Tests for login, logout, and authentication flows
 */

import { test, expect, LoginPage, TEST_USER } from './fixtures/test-fixtures';

test.describe('Authentication', () => {
  test.describe('Login', () => {
    test('should display login form', async ({ page }) => {
      await page.goto('/login');

      // Check form elements exist
      await expect(page.locator('input[name="username"]')).toBeVisible();
      await expect(page.locator('input[name="password"]')).toBeVisible();
      await expect(page.locator('button[type="submit"]')).toBeVisible();
    });

    test('should login with valid credentials', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USER.username, TEST_USER.password);

      // Should redirect to dashboard
      await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 10000 });
    });

    test('should show error with invalid credentials', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('invalid', 'invalid');

      // Should show error message
      await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 });
    });

    test('should prevent empty form submission', async ({ page }) => {
      await page.goto('/login');

      // Try to submit empty form
      await page.click('button[type="submit"]');

      // Should still be on login page
      await expect(page).toHaveURL(/.*login.*/);
    });

    test('should redirect unauthenticated users to login', async ({ page }) => {
      // Try to access protected route without auth
      await page.goto('/projects');

      // Should redirect to login
      await expect(page).toHaveURL(/.*login.*/);
    });
  });

  test.describe('Logout', () => {
    test('should logout successfully', async ({ authenticatedPage }) => {
      // Click logout button/menu
      await authenticatedPage.click('[data-testid="user-menu"]');
      await authenticatedPage.click('[data-testid="logout-btn"]');

      // Should redirect to login
      await expect(authenticatedPage).toHaveURL(/.*login.*/);
    });

    test('should clear session after logout', async ({ authenticatedPage }) => {
      // Logout
      await authenticatedPage.click('[data-testid="user-menu"]');
      await authenticatedPage.click('[data-testid="logout-btn"]');

      // Try to access protected route
      await authenticatedPage.goto('/dashboard');

      // Should redirect to login
      await expect(authenticatedPage).toHaveURL(/.*login.*/);
    });
  });

  test.describe('Session Management', () => {
    test('should maintain session across page refreshes', async ({ authenticatedPage }) => {
      // Refresh page
      await authenticatedPage.reload();

      // Should still be on dashboard
      await expect(authenticatedPage).toHaveURL(/.*dashboard.*/);
    });

    test('should handle token expiration gracefully', async ({ authenticatedPage }) => {
      // Clear local storage to simulate token expiration
      await authenticatedPage.evaluate(() => {
        localStorage.removeItem('token');
      });

      // Navigate to trigger auth check
      await authenticatedPage.goto('/projects');

      // Should redirect to login
      await expect(authenticatedPage).toHaveURL(/.*login.*/);
    });
  });
});
