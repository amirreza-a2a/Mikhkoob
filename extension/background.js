// بارگذاری Polyfill فقط در محیطی که importScripts وجود دارد (کروم)
if (typeof importScripts === 'function') {
  try {
    importScripts('webextension-polyfill.js');
  } catch (e) {
    console.error('Failed to load polyfill via importScripts', e);
  }
}

const SERVER_URL = 'http://localhost:9876';

// شمارندهٔ تلاش‌های امروز
let todayAttempts = 0;
let todayDate = new Date().toDateString();

function resetDailyAttemptsIfNeeded() {
  const currentDate = new Date().toDateString();
  if (currentDate !== todayDate) {
    todayDate = currentDate;
    todayAttempts = 0;
    browser.storage.local.set({ todayAttempts: 0, todayDate: currentDate });
  }
}

// بازیابی شمارنده از storage (در صورت وجود)
browser.storage.local.get(['todayAttempts', 'todayDate']).then(result => {
  const currentDate = new Date().toDateString();
  if (result.todayDate === currentDate && result.todayAttempts !== undefined) {
    todayAttempts = result.todayAttempts;
    todayDate = result.todayDate;
  } else {
    todayAttempts = 0;
    todayDate = currentDate;
    browser.storage.local.set({ todayAttempts: 0, todayDate: currentDate });
  }
});

let blockRules = {
  always: { domains: [], paths: {} },
  focus:  { domains: [], paths: {} },
  rest:   { domains: [], paths: {} }
};

async function fetchBlockRules() {
  try {
    const response = await fetch(`${SERVER_URL}/block_rules`);
    if (response.ok) {
      const data = await response.json();
      if (data && data.always) {
        blockRules.always = data.always;
        blockRules.focus  = data.focus  || { domains: [], paths: {} };
        blockRules.rest   = data.rest   || { domains: [], paths: {} };
        await browser.storage.local.set({ alwaysRules: data.always });
        console.log('Blocklist updated & always rules saved', blockRules);
      }
    }
  } catch (e) {
    console.log('Server not reachable, loading always rules from storage');
    const result = await browser.storage.local.get('alwaysRules');
    if (result.alwaysRules) {
      blockRules.always = result.alwaysRules;
      console.log('Always rules loaded from storage', blockRules.always);
    }
  }
}

function isUrlBlocked(url, rules) {
  const domain = url.hostname.replace(/^www\./, '');
  if (rules.domains.includes(domain)) {
    if (rules.paths[domain]) {
      const path = url.pathname;
      return rules.paths[domain].some(p => path.startsWith(p));
    }
    return true;
  }
  return false;
}

// تابع مرکزی برای بررسی و مسدودسازی
async function checkAndBlock(details) {
  if (details.frameId !== 0) return; // فقط فریم اصلی

  const url = new URL(details.url);

  // جلوگیری از مسدود شدن صفحهٔ سپر تمرکز
  if (url.pathname === '/blocked.html') return;

  const blocked = isUrlBlocked(url, blockRules.always) ||
                  isUrlBlocked(url, blockRules.focus)  ||
                  isUrlBlocked(url, blockRules.rest);

  if (!blocked) return;

  // افزایش شمارنده روزانه
  resetDailyAttemptsIfNeeded();
  todayAttempts++;
  browser.storage.local.set({ todayAttempts: todayAttempts, todayDate: todayDate });

  // گزارش تلاش به برنامه اصلی (در صورت باز بودن)
  fetch(`${SERVER_URL}/block_attempt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'block_attempt',
      url: details.url,
      timestamp: new Date().toISOString()
    })
  }).catch(e => console.log('Report error (server may be offline)', e));

  // ساخت URL صفحه سپر تمرکز با پارامترها
  const domain = url.hostname.replace(/^www\./, '');
  const now = new Date();
  const timeStr = now.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
  const redirectUrl = browser.runtime.getURL(
    `blocked.html?site=${encodeURIComponent(domain)}&attempts_today=${todayAttempts}&last_attempt=${encodeURIComponent(timeStr)}`
  );
  browser.tabs.update(details.tabId, { url: redirectUrl });
}

// رویدادهای ناوبری (بارگذاری کامل صفحه)
browser.webNavigation.onBeforeNavigate.addListener(checkAndBlock);

// رویداد تغییر History (برای SPAها مثل یوتیوب)
browser.webNavigation.onHistoryStateUpdated.addListener(checkAndBlock);

// رویداد تغییر Fragment (برای لینک‌های hash#)
browser.webNavigation.onReferenceFragmentUpdated.addListener(checkAndBlock);

fetchBlockRules();
setInterval(fetchBlockRules, 5000);

console.log('Mikhkoob background service worker started (cross-browser with SPA support).');