(() => {
  "use strict";

  const root = document.documentElement;
  root.classList.add("js");
  const menuButton = document.querySelector("[data-menu-button]");
  const primaryNav = document.querySelector("[data-primary-nav]");
  const themeButton = document.querySelector("[data-theme-button]");
  const starCounts = document.querySelectorAll("[data-star-count]");
  const statsState = document.querySelector("[data-stats-state]");
  const forksCount = document.querySelector("[data-forks-count]");
  const verificationStatus = document.querySelector("[data-verification-status]");
  const receiptCommit = document.querySelector("[data-receipt-commit]");
  const statsCacheKey = "agi-super-team:repository-stats:v1";
  const themeCacheKey = "agi-super-team:theme:v1";
  const fifteenMinutes = 15 * 60 * 1000;
  const oneDay = 24 * 60 * 60 * 1000;
  const isZh = root.lang.startsWith("zh");
  const ui = (en, zh) => (isZh ? zh : en);
  const dataBase = new URL("../data/", document.currentScript?.src || new URL("assets/site.js", location.href));

  function readStorage(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function writeStorage(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (_error) {
      // Storage can be unavailable in private or locked-down browsing modes.
    }
  }

  function applyTheme(theme) {
    root.dataset.theme = theme;
    if (themeButton) {
      const nextTheme = theme === "dark" ? "light" : "dark";
      themeButton.setAttribute("aria-label", ui(`Switch to ${nextTheme} theme`, nextTheme === "dark" ? "切换到深色主题" : "切换到浅色主题"));
    }
  }

  const savedTheme = readStorage(themeCacheKey);
  const preferredTheme = document.body.classList.contains("homepage")
    ? "dark"
    : window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
  applyTheme(savedTheme === "light" || savedTheme === "dark" ? savedTheme : preferredTheme);

  themeButton?.addEventListener("click", () => {
    const theme = root.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(theme);
    writeStorage(themeCacheKey, theme);
  });

  function setMenu(open) {
    if (!menuButton || !primaryNav) return;
    menuButton.setAttribute("aria-expanded", String(open));
    primaryNav.dataset.open = String(open);
    const label = menuButton.querySelector(".sr-only");
    if (label) label.textContent = open ? ui("Close navigation", "关闭导航") : ui("Open navigation", "打开导航");
  }

  menuButton?.addEventListener("click", () => {
    setMenu(menuButton.getAttribute("aria-expanded") !== "true");
  });
  primaryNav?.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest("a")) setMenu(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menuButton?.getAttribute("aria-expanded") === "true") {
      setMenu(false);
      menuButton.focus();
    }
  });

  const frameworkChoice = document.querySelector("[data-framework-choice]");
  const frameworkNames = {
    "claude-code": "Claude Code",
    codex: "Codex",
    openclaw: "OpenClaw",
    hermes: "Hermes Agent",
  };
  function updateFrameworkPreview() {
    const framework = frameworkChoice?.value;
    if (!Object.hasOwn(frameworkNames, framework)) return;
    const command = document.querySelector("#install-command code");
    const label = document.querySelector("[data-command-label]");
    if (command) {
      command.textContent = `git clone --depth 1 --branch main https://github.com/aAAaqwq/AGI-Super-Team.git
cd AGI-Super-Team

${ui("# Inspect the checkout, then preview. No files installed.", "# 先检查仓库副本，再预览。不会写入任何文件。")}
node bin/agi-super-team.mjs --tool ${framework}`;
    }
    if (label) label.textContent = `${frameworkNames[framework].toUpperCase()} / ${ui("PREVIEW", "预览")}`;
    const status = document.querySelector("[data-copy-status]");
    if (status) status.textContent = ui(`${frameworkNames[framework]} preview commands ready.`, `${frameworkNames[framework]} 预览命令已就绪。`);
  }
  frameworkChoice?.addEventListener("change", updateFrameworkPreview);
  if (frameworkChoice) updateFrameworkPreview();

  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const targetId = button.getAttribute("data-copy-target");
      const target = targetId ? document.getElementById(targetId) : null;
      if (!target) return;
      const value = target.textContent || "";
      try {
        await navigator.clipboard.writeText(value);
        const label = button.querySelector("span");
        const status = document.querySelector("[data-copy-status]");
        if (label) label.textContent = ui("Copied", "已复制");
        if (status) status.textContent = ui("Installation commands copied.", "安装命令已复制。");
        window.setTimeout(() => {
          if (label) label.textContent = ui("Copy", "复制");
        }, 1800);
      } catch (_error) {
        const range = document.createRange();
        range.selectNodeContents(target);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);
        const status = document.querySelector("[data-copy-status]");
        if (status) status.textContent = ui("Copy unavailable. Installation commands selected.", "无法使用剪贴板，已选中安装命令。");
      }
    });
  });

  function isRepositoryStats(value) {
    return Boolean(
      value &&
      value.schemaVersion === 1 &&
      value.repository === "aAAaqwq/AGI-Super-Team" &&
      Number.isInteger(value.stars) &&
      value.stars >= 0 &&
      Number.isInteger(value.forks) &&
      value.forks >= 0 &&
      !Number.isNaN(Date.parse(value.fetchedAt))
    );
  }

  function renderStats(stats, source) {
    if (!isRepositoryStats(stats)) return false;
    starCounts.forEach((starCount) => {
      starCount.textContent = new Intl.NumberFormat().format(stats.stars);
      starCount.hidden = false;
    });
    if (forksCount) {
      forksCount.textContent = new Intl.NumberFormat().format(stats.forks);
    }
    if (statsState) {
      const age = Date.now() - Date.parse(stats.fetchedAt);
      const label = source === "live" && age <= fifteenMinutes ? "Live" : "Cached";
      const stale = age > oneDay ? ". Older than 24 hours" : "";
      statsState.textContent = isZh ? `GitHub 数据：${label === "Live" ? "实时" : "缓存"}${stale ? "。数据超过 24 小时。" : "。"}` : `${label} GitHub data${stale}.`;
    }
    return true;
  }

  async function fetchJson(url, timeout = 3000) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(url, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`Request failed with ${response.status}`);
      return await response.json();
    } finally {
      window.clearTimeout(timer);
    }
  }

  async function loadRepositoryStats() {
    let rendered = false;
    let newestStats = null;
    const localCache = readStorage(statsCacheKey);
    if (localCache) {
      try {
        const cached = JSON.parse(localCache);
        if (isRepositoryStats(cached)) {
          newestStats = cached;
          rendered = renderStats(cached, "cached") || rendered;
        }
      } catch (_error) {
        // Ignore malformed browser cache and continue to the versioned site cache.
      }
    }

    try {
      const built = await fetchJson(new URL("repo-stats.json", dataBase));
      if (isRepositoryStats(built)) {
        const isNewer =
          !newestStats || Date.parse(built.fetchedAt) > Date.parse(newestStats.fetchedAt);
        if (isNewer) {
          newestStats = built;
          rendered = renderStats(built, "cached") || rendered;
          writeStorage(statsCacheKey, JSON.stringify(built));
        }
      }
    } catch (_error) {
      // The browser cache, when available, remains visible.
    }

    if (
      newestStats &&
      Date.now() - Date.parse(newestStats.fetchedAt) <= fifteenMinutes
    ) {
      return;
    }

    try {
      const payload = await fetchJson("https://api.github.com/repos/aAAaqwq/AGI-Super-Team");
      const live = {
        schemaVersion: 1,
        repository: "aAAaqwq/AGI-Super-Team",
        stars: payload.stargazers_count,
        forks: payload.forks_count,
        fetchedAt: new Date().toISOString(),
        source: "github-rest-api-browser",
      };
      if (isRepositoryStats(live)) {
        renderStats(live, "live");
        writeStorage(statsCacheKey, JSON.stringify(live));
        rendered = true;
      }
    } catch (_error) {
      if (!rendered && statsState) {
        statsState.textContent = ui("GitHub data is temporarily unavailable.", "GitHub 数据暂时不可用。");
      }
    }
  }

  async function loadVerificationReceipt() {
    try {
      const receipt = await fetchJson(new URL("verification-receipt.json", dataBase));
      if (!window.AGISuperTeamReceipt?.isVerifiedReceipt(receipt)) return;
      if (verificationStatus) {
        verificationStatus.textContent = ui("Verified", "已验证");
        verificationStatus.classList.remove("status-pending");
        verificationStatus.classList.add("status-verified");
      }
      if (receiptCommit) receiptCommit.textContent = receipt.commit.slice(0, 12);
    } catch (_error) {
      // Static pending state is intentional when the receipt is absent or stale.
    }
  }

  loadRepositoryStats();
  loadVerificationReceipt();
})();
