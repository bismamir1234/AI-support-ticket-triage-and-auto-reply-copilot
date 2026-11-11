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
  console.log('Testing Dark Mode in Chrome...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--window-size=1440,920'],
    defaultViewport: { width: 1440, height: 920 },
  });

  const page = await browser.newPage();
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
  await page.waitForSelector('.stat-card', { timeout: 10000 });
  await page.waitForSelector('.theme-toggle-btn', { timeout: 10000 });

  // Click Dark Mode Toggle
  console.log('Clicking Dark Mode Toggle...');
  await page.click('.theme-toggle-btn');
  await sleep(1000);

  console.log('Capturing 13_dark_mode_dashboard.png...');
  await page.screenshot({ path: path.join(evidenceDir, '13_dark_mode_dashboard.png') });

  // Select a ticket to show the detail view in dark mode
  console.log('Selecting ticket in Dark Mode...');
  await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.ticket-item'));
    if (items.length > 0) items[0].click();
  });
  await sleep(800);

  console.log('Capturing 14_dark_mode_detail.png...');
  await page.screenshot({ path: path.join(evidenceDir, '14_dark_mode_detail.png') });

  console.log('Dark mode screenshots captured successfully!');
  await browser.close();
}

capture().catch((err) => {
  console.error('Error capturing dark mode screenshot:', err);
  process.exit(1);
});

