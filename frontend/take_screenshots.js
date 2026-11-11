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
  console.log('Navigating to http://localhost:5173...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
  await page.waitForSelector('.stat-card', { timeout: 10000 });
  await page.waitForSelector('.ticket-item', { timeout: 10000 });
  await sleep(1000);

  // 1. Main Dashboard
  console.log('Capturing 01_main_dashboard.png...');
  await page.screenshot({ path: path.join(evidenceDir, '01_main_dashboard.png') });

  // 2. Ticket Inbox
  console.log('Capturing 02_ticket_inbox.png...');
  const inboxEl = await page.$('.inbox-panel');
  if (inboxEl) {
    await inboxEl.screenshot({ path: path.join(evidenceDir, '02_ticket_inbox.png') });
  } else {
    await page.screenshot({ path: path.join(evidenceDir, '02_ticket_inbox.png') });
  }

  // 3. Order Issue Analysis & 7. Generated AI Response & 8. Draft Before Editing
  console.log('Selecting Order Issue ticket (TCK-1001 or TICKET-1)...');
  await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.ticket-item'));
    const orderItem = items.find((el) => el.textContent.includes('TCK-1001') || el.textContent.includes('TICKET-1'));
    if (orderItem) orderItem.click();
  });
  await sleep(1000);

  console.log('Capturing 03_order_issue_analysis.png...');
  await page.screenshot({ path: path.join(evidenceDir, '03_order_issue_analysis.png') });

  console.log('Capturing 07_generated_ai_response.png...');
  const responseCard = await page.$('.detail-card:last-of-type');
  if (responseCard) {
    await responseCard.screenshot({ path: path.join(evidenceDir, '07_generated_ai_response.png') });
  } else {
    await page.screenshot({ path: path.join(evidenceDir, '07_generated_ai_response.png') });
  }

  console.log('Capturing 08_draft_before_editing.png...');
  await page.screenshot({ path: path.join(evidenceDir, '08_draft_before_editing.png') });

  // 4. Refund Analysis & 6. Missing Order ID Warning
  console.log('Selecting Refund Ticket (TICKET-2 or TCK-1002)...');
  await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.ticket-item'));
    const refundItem = items.find((el) => el.textContent.includes('TICKET-2') || (el.textContent.includes('refund') && el.textContent.includes('Missing')));
    if (refundItem) {
      refundItem.click();
    } else {
      const anyRefund = items.find((el) => el.textContent.toLowerCase().includes('refund'));
      if (anyRefund) anyRefund.click();
    }
  });
  await sleep(1000);

  console.log('Capturing 04_refund_analysis.png...');
  await page.screenshot({ path: path.join(evidenceDir, '04_refund_analysis.png') });

  console.log('Capturing 06_missing_order_id_warning.png...');
  const warningBanner = await page.$('.alert-banner-warning');
  if (warningBanner) {
    await warningBanner.screenshot({ path: path.join(evidenceDir, '06_missing_order_id_warning.png') });
  } else {
    await page.screenshot({ path: path.join(evidenceDir, '06_missing_order_id_warning.png') });
  }

  // 5. Technical Issue Analysis
  console.log('Selecting Technical Issue Ticket (TCK-1003 or TICKET-3)...');
  await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.ticket-item'));
    const techItem = items.find((el) => el.textContent.includes('TCK-1003') || el.textContent.includes('TICKET-3') || el.textContent.toLowerCase().includes('technical'));
    if (techItem) techItem.click();
  });
  await sleep(1000);

  console.log('Capturing 05_technical_issue_analysis.png...');
  await page.screenshot({ path: path.join(evidenceDir, '05_technical_issue_analysis.png') });

  // 9. Draft After Editing
  console.log('Editing response textarea for TCK-1003...');
  const textarea = await page.$('.response-textarea');
  if (textarea) {
    await textarea.click();
    await page.evaluate(() => {
      const ta = document.querySelector('.response-textarea');
      if (ta) {
        ta.value = 'Dear David,\n\nOur DevOps team investigated the 500 Internal Server Error and deployed an emergency hotfix to the payment checkout microservice. You can now complete your purchase smoothly. We apologize for the inconvenience!\n\nBest regards,\nSenior Incident Lead';
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
    await sleep(600);
  }

  console.log('Capturing 09_draft_after_editing.png...');
  await page.screenshot({ path: path.join(evidenceDir, '09_draft_after_editing.png') });

  // Save the draft
  console.log('Clicking Save Draft...');
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const saveBtn = buttons.find((b) => b.textContent.includes('Save Draft'));
    if (saveBtn) saveBtn.click();
  });
  await sleep(1200);

  // 10. Approved Mock Response
  console.log('Clicking Approve & Send...');
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const approveBtn = buttons.find((b) => b.textContent.includes('Approve & Send'));
    if (approveBtn) approveBtn.click();
  });
  await sleep(1500);

  console.log('Capturing 10_approved_mock_response.png...');
  await page.screenshot({ path: path.join(evidenceDir, '10_approved_mock_response.png') });

  // Dismiss modal
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('.modal-footer button'));
    const okBtn = buttons.find((b) => b.textContent.includes('Understood'));
    if (okBtn) okBtn.click();
  });
  await sleep(800);

  // 11. Resolved Ticket
  console.log('Clicking Mark Resolved...');
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const resolveBtn = buttons.find((b) => b.textContent.includes('Mark Resolved'));
    if (resolveBtn) resolveBtn.click();
  });
  await sleep(1500);

  console.log('Capturing 11_resolved_ticket.png...');
  await page.screenshot({ path: path.join(evidenceDir, '11_resolved_ticket.png') });

  // 12. Export Functionality
  console.log('Navigating to Reports / Export tab...');
  await page.evaluate(() => {
    const navButtons = Array.from(document.querySelectorAll('.nav-item'));
    const reportsBtn = navButtons.find((b) => b.textContent.includes('Reports'));
    if (reportsBtn) reportsBtn.click();
  });
  await sleep(1200);

  console.log('Capturing 12_export_functionality.png...');
  await page.screenshot({ path: path.join(evidenceDir, '12_export_functionality.png') });

  console.log('All 12 screenshots captured successfully!');
  await browser.close();
}

capture().catch((err) => {
  console.error('Error capturing screenshots:', err);
  process.exit(1);
});

