import { test, expect } from "@playwright/test";

test.describe("LogStream AI Frontend End-to-End Tests", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to page before each test
    await page.goto("/");
  });

  test("should render the landing page layout correctly", async ({ page }) => {
    // 1. Verify header and logo
    await expect(page.locator("h1")).toContainText("LogStream AI");
    
    // 2. Verify drag and drop text is present
    await expect(page.locator("text=Drag & Drop files here or click to upload")).toBeVisible();
    
    // 3. Verify sign-in button
    await expect(page.locator("button:has-text('Sign In / Sign Up')")).toBeVisible();
  });

  test("should display guest mode limitations banner", async ({ page }) => {
    // 1. Verify guest mode banner is rendered
    const banner = page.locator("text=Guest Mode:");
    await expect(banner).toBeVisible();
    
    // 2. Verify register link inside banner
    const registerLink = page.locator("text=Sign up for unlimited uploads & Chat Q&A!");
    await expect(registerLink).toBeVisible();
  });

  test("should open and navigate the auth modal", async ({ page }) => {
    // 1. Open Auth modal
    await page.click("button:has-text('Sign In / Sign Up')");
    
    // 2. Assert Modal opens with "Welcome Back"
    await expect(page.locator("h2:has-text('Welcome Back')")).toBeVisible();
    
    // 3. Click switch to registration / sign up
    await page.click("text=Don't have an account? Register");
    await expect(page.locator("h2:has-text('Create Account')")).toBeVisible();
    
    // 4. Click switch to forgot password
    await page.click("text=Back to Login");
    await page.click("text=Forgot Password?");
    await expect(page.locator("h2:has-text('Reset Password')")).toBeVisible();
  });

  test("should allow inputting email and password inside authentication forms", async ({ page }) => {
    await page.click("button:has-text('Sign In / Sign Up')");
    
    const emailInput = page.locator("input[type='email']");
    const passwordInput = page.locator("input[type='password']");
    
    await emailInput.fill("testuser@example.com");
    await passwordInput.fill("password123");
    
    await expect(emailInput).toHaveValue("testuser@example.com");
    await expect(passwordInput).toHaveValue("password123");
  });
});
