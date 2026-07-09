// خواندن پارامترهای URL
const params = new URLSearchParams(window.location.search);
const siteName = params.get('site') || 'نامشخص';
const attemptsToday = params.get('attempts_today') || '0';
const lastAttempt = params.get('last_attempt') || '---';

document.getElementById('siteName').textContent = siteName;
document.getElementById('attemptsToday').textContent = attemptsToday;
document.getElementById('lastAttempt').textContent = lastAttempt;
document.getElementById('focusScore').textContent = '-';

// جملات انگیزشی تصادفی
const quotes = [
  { text: "بهترین راه برای پیش‌بینی آینده، ساختن آن است.", author: "آبراهام لینکلن" },
  { text: "موفقیت سفر است، نه مقصد.", author: "بن سوئیتلند" },
  { text: "ذهن همه چیز است. هرچه فکر کنی، همان می‌شوی.", author: "بودا" },
  { text: "فاصلهٔ بین «دانستن» و «انجام دادن» را اراده پر می‌کند.", author: "ناشناس" },
];
const randomQuote = quotes[Math.floor(Math.random() * quotes.length)];
document.getElementById('quoteText').textContent = `"${randomQuote.text}"`;
document.querySelector('.quote-author').textContent = `— ${randomQuote.author}`;

// میانبرهای پیش‌فرض
const defaultShortcuts = [
  { title: "Trello", url: "https://trello.com/", icon: "https://trello.com/favicon.ico" },
  { title: "Notion", url: "https://notion.so/", icon: "https://notion.so/front-static/favicon.ico" },
  { title: "GitHub", url: "https://github.com/", icon: "https://github.com/favicon.ico" },
  { title: "Docs", url: "https://docs.google.com/", icon: "https://ssl.gstatic.com/docs/documents/images/kix-favicon7.ico" },
];

const MAX_SLOTS = 10;

function renderShortcuts(shortcuts) {
  const grid = document.getElementById('shortcutsGrid');
  grid.innerHTML = '';
  const filled = shortcuts.slice(0, MAX_SLOTS);

  for (let i = 0; i < MAX_SLOTS; i++) {
    const item = filled[i];
    const div = document.createElement('div');
    div.className = 'shortcut-btn';
    if (item) {
      const img = document.createElement('img');
      img.className = 'favicon';
      img.src = item.icon;
      img.alt = '';
      img.addEventListener('error', () => { img.style.display = 'none'; });
      div.appendChild(img);
      div.appendChild(document.createTextNode(' ' + item.title));
      div.addEventListener('click', (e) => {
        e.preventDefault();
        window.open(item.url, '_blank');
      });
    } else {
      div.classList.add('empty-slot');
      div.textContent = '+';
      div.addEventListener('click', () => addShortcut(i));
    }
    grid.appendChild(div);
  }
}

function addShortcut(index) {
  const title = prompt('عنوان سایت مفید را وارد کنید:');
  if (!title) return;
  let url = prompt('آدرس کامل (با https://) را وارد کنید:');
  if (!url) return;
  if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
  const icon = url.replace(/\/$/, '') + '/favicon.ico';

  const storageAPI = (typeof chrome !== 'undefined' && chrome.storage) ? chrome.storage.local :
                     (typeof browser !== 'undefined' && browser.storage) ? browser.storage.local : null;

  if (storageAPI) {
    const get = storageAPI.get.bind(storageAPI);
    const set = storageAPI.set.bind(storageAPI);
    get('focusShortcuts', (result) => {
      const shortcuts = result.focusShortcuts || defaultShortcuts;
      while (shortcuts.length < MAX_SLOTS) shortcuts.push(null);
      shortcuts[index] = { title, url, icon };
      const cleaned = shortcuts.filter(Boolean);
      set({ focusShortcuts: cleaned }, () => {
        renderShortcuts(cleaned);
      });
    });
  }
}

// بارگذاری از storage
const storageAPI = (typeof chrome !== 'undefined' && chrome.storage) ? chrome.storage.local :
                   (typeof browser !== 'undefined' && browser.storage) ? browser.storage.local : null;

if (storageAPI) {
  storageAPI.get('focusShortcuts', (result) => {
    const shortcuts = result.focusShortcuts || defaultShortcuts;
    renderShortcuts(shortcuts);
  });
} else {
  renderShortcuts(defaultShortcuts);
}

// دکمهٔ بازگشت
document.getElementById('btnReturn').addEventListener('click', () => {
  if (typeof chrome !== 'undefined' && chrome.tabs) {
    chrome.tabs.getCurrent(tab => { if (tab) chrome.tabs.remove(tab.id); else window.close(); });
  } else if (typeof browser !== 'undefined' && browser.tabs) {
    browser.tabs.getCurrent().then(tab => { if (tab) browser.tabs.remove(tab.id); else window.close(); });
  } else {
    window.close();
  }
});