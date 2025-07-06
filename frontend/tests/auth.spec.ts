import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should allow user to register and login', async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // Click on register link
    await page.click('text=Register');
    
    // Fill in registration form
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.selectOption('select[name="role"]', 'REPORTER');
    
    // Submit registration
    await page.click('button[type="submit"]');
    
    // Should be redirected to login
    await expect(page).toHaveURL('/login');
    
    // Login with the created account
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Should be redirected to dashboard
    await expect(page).toHaveURL('/dashboard');
    
    // Should see dashboard content
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should show error for invalid login', async ({ page }) => {
    await page.goto('/login');
    
    // Try to login with invalid credentials
    await page.fill('input[name="email"]', 'invalid@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('.text-red-600')).toBeVisible();
  });
}); 