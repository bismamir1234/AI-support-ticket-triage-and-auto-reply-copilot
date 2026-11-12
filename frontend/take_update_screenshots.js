import puppeteer from 'puppeteer-core';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const evidenceDir = path.resolve(__dirname, '..', 'evidence', 'screenshots');

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function capture() {
  console.log('Launching Chrome via puppeteer-core...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--window-size=1440,920'],
    defaultViewport: { width: 1440, height: 920 },
  });

  const page = await browser.newPage();
  // Ensure clean light mode for readable screenshots
  await page.evaluateOnNewDocument(() => {
    localStorage.setItem('theme', 'light');
  });

  console.log('Navigating to http://localhost:5173...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
  await page.waitForSelector('.stat-card', { timeout: 10000 });
  await page.waitForSelector('.ticket-item', { timeout: 10000 });
  await sleep(1000);

  // 1. Updated dashboard
  console.log('Capturing 15_updated_dashboard.png...');
  await page.screenshot({ path: path.join(evidenceDir, '15_updated_dashboard.png') });

  // 2. Ticket inbox with P1/P2/P3 labels
  console.log('Capturing 16_ticket_inbox_p1_p2_p3.png...');
  const inboxEl = await page.$('.inbox-panel');
  if (inboxEl) {
    await inboxEl.screenshot({ path: path.join(evidenceDir, '16_ticket_inbox_p1_p2_p3.png') });
  } else {
    await page.screenshot({ path: path.join(evidenceDir, '16_ticket_inbox_p1_p2_p3.png') });
  }

  // 3. Ticket details and AI analysis (Select mixed-category ticket T10-007 or T10-002)
  console.log('Selecting T10-007 (Mixed Refund + Technical Issue) for details & AI analysis...');
  await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.ticket-item'));
    const target = items.find((el) => el.textContent.includes('T10-007')) || items[0];
    if (target) target.click();
  });
  await sleep(800);

  console.log('Capturing 17_ticket_details_and_ai_analysis.png...');
  await page.screenshot({ path: path.join(evidenceDir, '17_ticket_details_and_ai_analysis.png') });

  // 8. Generated customer response
  console.log('Capturing 22_generated_customer_response.png...');
  const detailCards = await page.$$('.detail-card');
  if (detailCards.length >= 3) {
    await detailCards[2].screenshot({ path: path.join(evidenceDir, '22_generated_customer_response.png') });
  } else {
    await page.screenshot({ path: path.join(evidenceDir, '22_generated_customer_response.png') });
  }

  // 7. Prompt injection test result (Select T10-009)
  console.log('Selecting T10-009 (Prompt Injection Test)...');
  await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.ticket-item'));
    const target = items.find((el) => el.textContent.includes('T10-009'));
    if (target) target.click();
  });
  await sleep(800);

  console.log('Capturing 21_prompt_injection_test_result.png...');
  await page.screenshot({ path: path.join(evidenceDir, '21_prompt_injection_test_result.png') });

  // 4. Empty state (search query returning 0 matching tickets)
  console.log('Testing search empty state...');
  const searchInput = await page.$('.search-input');
  if (searchInput) {
    await searchInput.click();
    await searchInput.type('NON_EXISTENT_TICKET_QUERY_999');
    await sleep(600);
  }
  console.log('Capturing 18_empty_state.png...');
  await page.screenshot({ path: path.join(evidenceDir, '18_empty_state.png') });

  // Clear search
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const clearBtn = buttons.find((b) => b.textContent.includes('Clear Search'));
    if (clearBtn) clearBtn.click();
  });
  await sleep(500);

  // 5. Input validation error (Open New Ticket modal & submit empty/oversized input)
  console.log('Testing New Ticket input validation error...');
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const newBtn = buttons.find((b) => b.textContent.includes('New Ticket'));
    if (newBtn) newBtn.click();
  });
  await sleep(600);

  await page.evaluate(() => {
    const inputs = document.querySelectorAll('.modal-content input');
    if (inputs[1]) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(inputs[1], 'Jane Validation');
      inputs[1].dispatchEvent(new Event('input', { bubbles: true }));
    }
    if (inputs[2]) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(inputs[2], 'jane@example.com');
      inputs[2].dispatchEvent(new Event('input', { bubbles: true }));
    }
    if (inputs[3]) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(inputs[3], 'Validation check');
      inputs[3].dispatchEvent(new Event('input', { bubbles: true }));
    }
    const ta = document.querySelector('.modal-content textarea');
    if (ta) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(ta, '   \n   ');
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
  });
  await sleep(300);

  await page.evaluate(() => {
    const submitBtn = document.querySelector('.modal-footer button[type="submit"]');
    if (submitBtn) submitBtn.click();
  });
  await sleep(600);

  console.log('Capturing 19_input_validation_error.png...');
  await page.screenshot({ path: path.join(evidenceDir, '19_input_validation_error.png') });

  // Close modal
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('.modal-footer button'));
    const cancelBtn = buttons.find((b) => b.textContent.includes('Cancel'));
    if (cancelBtn) cancelBtn.click();
  });
  await sleep(400);

  // 6. API key error state (Simulate auth_error on /api/v1/tickets/ai-status cleanly in browser)
  console.log('Simulating API key authentication error state in browser UI...');
  await page.setRequestInterception(true);
  page.on('request', (req) => {
    if (req.url().includes('/api/v1/tickets/ai-status')) {
      req.respond({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'auth_error',
          configured: true,
          model: 'openai/gpt-oss-120b',
          max_message_length: 10000,
          error_code: 'AUTHENTICATION_FAILED',
          message:
            'AI authentication failed: the configured Groq API key is invalid, revoked, or lacks permission. Please verify your API key.',
        }),
      });
    } else {
      req.continue();
    }
  });

  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
  await page.waitForSelector('.ai-status-banner', { timeout: 10000 });
  await sleep(800);

  console.log('Capturing 20_api_key_error_state.png...');
  await page.screenshot({ path: path.join(evidenceDir, '20_api_key_error_state.png') });

  console.log('All 8 new evidence screenshots captured successfully!');
  await browser.close();
}

capture().catch((err) => {
  console.error('Error capturing screenshots:', err);
  process.exit(1);
});

