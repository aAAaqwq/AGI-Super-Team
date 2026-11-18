(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const PAGE_SIZE = 48;
  const STORAGE_THEME = "agi-skills-atlas:theme";
  const STORAGE_LOCAL = "agi-skills-atlas:local:v1";
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(pointer: fine)");

  const state = {
    data: null,
    skills: [],
    categories: [],
    skillMap: new Map(),
    categoryMap: new Map(),
    query: "",
    category: "all",
    originalsOnly: false,
    sort: "curated",
    page: 1,
    local: [],
    pending: [],
    activeSkill: null,
    detailCache: new Map(),
    detailTrigger: null,
    uploadTrigger: null,
    detailFocusCleanup: null,
    uploadFocusCleanup: null,
    clearLocalArmed: false,
    searchTimer: 0,
  };

  const el = {
    categoryGrid: $("#category-grid"),
    featuredGrid: $("#featured-grid"),
    filterRow: $("#filter-row"),
    skillGrid: $("#skill-grid"),
    catalogCount: $("#catalog-count"),
    loadMore: $("#load-more"),
    emptyState: $("#empty-state"),
    catalogSearch: $("#catalog-search"),
    heroSearch: $("#hero-search"),
    heroSearchForm: $("#hero-search-form"),
    sortSelect: $("#sort-select"),
    localSection: $("#local-section"),
    localGrid: $("#local-grid"),
    detailOverlay: $("#detail-overlay"),
    detailSheet: $("#detail-overlay .sheet"),
    detailTitle: $("#detail-title"),
    detailCategory: $("#detail-category"),
    detailBody: $("#detail-body"),
    uploadOverlay: $("#upload-overlay"),
    uploadModal: $("#upload-overlay .modal"),
    fileInput: $("#file-input"),
    dropzone: $("#dropzone"),
    uploadPreview: $("#upload-preview"),
    uploadPreviewList: $("#upload-preview-list"),
    uploadPreviewCount: $("#upload-preview-count"),
    uploadSave: $("#upload-save"),
    uploadClear: $("#upload-clear"),
    pasteName: $("#paste-name"),
    pasteContent: $("#paste-content"),
    toastRegion: $("#toast-region"),
    themeToggle: $("#theme-toggle"),
    heroVisual: $("#hero-visual"),
    canvas: $("#constellation"),
  };

  const icons = {
    arrow: '<svg class="icon" aria-hidden="true"><use href="#i-arrow"></use></svg>',
    external: '<svg class="icon" aria-hidden="true"><use href="#i-external"></use></svg>',
    close: '<svg class="icon" aria-hidden="true"><use href="#i-close"></use></svg>',
    copy: '<svg class="icon" aria-hidden="true"><use href="#i-copy"></use></svg>',
    download: '<svg class="icon" aria-hidden="true"><use href="#i-download"></use></svg>',
    github: '<svg class="icon" aria-hidden="true"><use href="#i-github"></use></svg>',
    check: '<svg class="icon" aria-hidden="true"><use href="#i-check"></use></svg>',
    trash: '<svg class="icon" aria-hidden="true"><use href="#i-trash"></use></svg>',
    lock: '<svg class="icon" aria-hidden="true"><use href="#i-lock"></use></svg>',
    spark: '<svg class="icon" aria-hidden="true"><use href="#i-spark"></use></svg>',
    link: '<svg class="icon" aria-hidden="true"><use href="#i-link"></use></svg>',
    file: '<svg class="icon" aria-hidden="true"><use href="#i-file"></use></svg>',
  };

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[char]));

  const escapeRegExp = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const formatNumber = (value) => new Intl.NumberFormat("en-US").format(Number(value) || 0);

  function highlight(text, query) {
    const source = String(text ?? "");
    if (!query) return escapeHtml(source);
    const tokens = [...new Set(query.toLowerCase().split(/\s+/).filter(Boolean))];
    if (!tokens.length) return escapeHtml(source);
    const pattern = tokens
      .sort((a, b) => b.length - a.length)
      .map(escapeRegExp)
      .join("|");
    try {
      const parts = source.split(new RegExp(`(${pattern})`, "gi"));
      return parts
        .map((part, index) => (index % 2 === 1 ? `<mark>${escapeHtml(part)}</mark>` : escapeHtml(part)))
        .join("");
    } catch {
      return escapeHtml(source);
    }
  }

  function padIndex(value) {
    return String(value).padStart(2, "0");
  }

  function preferReduced() {
    return reducedMotion.matches;
  }

  function categoryFor(skill) {
    return state.categoryMap.get(skill.category) || {
      id: skill.category,
      label: skill.category_label,
      label_en: skill.category_label_en,
      index: skill.category_index || 0,
    };
  }

  function scoreSkill(skill, tokens) {
    const id = (skill.id || "").toLowerCase();
    const headline = (skill.headline || "").toLowerCase();
    const description = (skill.description || "").toLowerCase();
    const tags = (skill.tags || []).join(" ").toLowerCase();
    const category = `${skill.category_label || ""} ${skill.category_label_en || ""}`.toLowerCase();
    const path = (skill.path || "").toLowerCase();
    const haystack = `${id} ${headline} ${description} ${tags} ${category} ${path}`;
    if (!tokens.every((token) => haystack.includes(token))) return 0;
    let score = 0;
    for (const token of tokens) {
      if (id === token) score += 40;
      if (id.includes(token)) score += 16;
      if (headline.includes(token)) score += 10;
      if (tags.includes(token)) score += 7;
      if (description.includes(token)) score += 4;
      if (category.includes(token)) score += 3;
      if (path.includes(token)) score += 2;
    }
    if (skill.featured) score += 2;
    return score;
  }

  function curatedCompare(a, b) {
    return (
      Number(b.featured) - Number(a.featured) ||
      (a.featured_rank ?? 999) - (b.featured_rank ?? 999) ||
      Number(b.original) - Number(a.original) ||
      (a.category_index || 99) - (b.category_index || 99) ||
      a.id.localeCompare(b.id)
    );
  }

  function sortSkills(list) {
    const sorted = [...list];
    if (state.sort === "name-asc") sorted.sort((a, b) => a.id.localeCompare(b.id));
    else if (state.sort === "name-desc") sorted.sort((a, b) => b.id.localeCompare(a.id));
    else sorted.sort(curatedCompare);
    return sorted;
  }

  function getFilteredSkills() {
    let list = state.skills;
    if (state.category !== "all") list = list.filter((skill) => skill.category === state.category);
    if (state.originalsOnly) list = list.filter((skill) => skill.original);
    const query = state.query.trim();
    if (!query) return sortSkills(list);
    const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
    return list
      .map((skill) => ({ skill, score: scoreSkill(skill, tokens) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || curatedCompare(a.skill, b.skill))
      .map((item) => item.skill);
  }

  function skillTitle(skill) {
    return skill.headline && skill.headline.toLowerCase() !== skill.id.toLowerCase()
      ? skill.headline
      : skill.id;
  }

  function originBadge(skill) {
    if (skill.local) return '<span class="origin-badge">本地</span>';
    if (skill.original) return '<span class="origin-badge">原创</span>';
    return "";
  }

  function tagsHtml(skill, max = 3) {
    const tags = (skill.tags || []).filter(Boolean);
    if (!tags.length) return "";
    const shown = tags.slice(0, max);
    const more = tags.length - shown.length;
    return shown.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("") +
      (more > 0 ? `<span class="tag tag--more">+${more}</span>` : "");
  }

  function skillCard(skill, index, options = {}) {
    const category = categoryFor(skill);
    const domain = skill.category || "general-utilities";
    const title = skillTitle(skill);
    const isMonoTitle = title === skill.id;
    const wide = options.wide ? " skill-card--wide" : "";
    const localAttr = skill.local ? ' data-local="true"' : "";
    const href = `#/skill/${encodeURIComponent(skill.id)}`;
    return `
      <a class="skill-card${wide} reveal" href="${href}" data-skill="${escapeHtml(skill.id)}"${localAttr}
         data-domain="${escapeHtml(domain)}" style="--i:${Math.min(index, 12)}"
         aria-label="打开技能 ${escapeHtml(skill.id)}">
        <span class="skill-card__top">
          <span class="pill">${escapeHtml(category.label || "技能")}</span>
          ${originBadge(skill)}
        </span>
        <h3 class="skill-card__title${isMonoTitle ? " skill-card__title--mono" : ""}">${highlight(title, state.query)}</h3>
        ${isMonoTitle ? "" : `<p class="skill-card__id">${escapeHtml(skill.id)}</p>`}
        <p class="skill-card__desc">${highlight(skill.summary || skill.description || "", state.query)}</p>
        ${skill.tags?.length ? `<div class="skill-card__tags">${tagsHtml(skill)}</div>` : ""}
        <span class="skill-card__foot">
          <span class="skill-card__path">${escapeHtml(skill.path || "local draft")}</span>
          <span class="skill-card__arrow">${icons.arrow}</span>
        </span>
      </a>`;
  }

  function renderCategoryGrid() {
    el.categoryGrid.innerHTML = state.categories.map((category, index) => {
      const active = state.category === category.id;
      return `
        <button type="button" class="category-card reveal${active ? " is-active" : ""}"
                data-category="${escapeHtml(category.id)}" data-domain="${escapeHtml(category.id)}"
                style="--i:${index}" aria-pressed="${active}">
          <span class="category-card__top">
            <span class="category-card__index">${padIndex(category.index)}</span>
            <span class="category-card__dot" aria-hidden="true"></span>
            <span class="category-card__arrow">${icons.arrow}</span>
          </span>
          <h3>${escapeHtml(category.label)}</h3>
          <p class="category-card__en">${escapeHtml(category.label_en)}</p>
          <p class="category-card__desc">${escapeHtml(category.description)}</p>
          <span class="category-card__count"><b>${formatNumber(category.count)}</b> skills</span>
        </button>`;
    }).join("");
    observeReveal(el.categoryGrid);
  }

  function renderFeatured() {
    const featured = state.skills
      .filter((skill) => skill.featured)
      .sort((a, b) => (a.featured_rank ?? 999) - (b.featured_rank ?? 999))
      .slice(0, 6);
    if (!featured.length) {
      const section = $("#featured");
      if (section) section.hidden = true;
      return;
    }
    el.featuredGrid.innerHTML = featured.map((skill, index) => {
      const title = skillTitle(skill);
      return `
        <a class="featured-card reveal" href="#/skill/${encodeURIComponent(skill.id)}"
           data-skill="${escapeHtml(skill.id)}" data-domain="${escapeHtml(skill.category)}" style="--i:${index}">
          <div>
            <span class="featured-card__label">${icons.spark} Featured</span>
            <h3 class="featured-card__title">${escapeHtml(title)}</h3>
            <p class="featured-card__id">${escapeHtml(skill.id)}</p>
            <p class="featured-card__desc">${escapeHtml(skill.summary || skill.description || "")}</p>
          </div>
          <div class="featured-card__foot">
            <div class="featured-card__tags">${tagsHtml(skill, 3) || `<span class="tag">${escapeHtml(skill.category_label || "Skill")}</span>`}</div>
            <span class="featured-card__arrow">${icons.arrow}</span>
          </div>
        </a>`;
    }).join("");
    observeReveal(el.featuredGrid);
  }

  function renderFilters() {
    const total = state.skills.length;
    const chips = [
      `<button type="button" class="chip${state.category === "all" && !state.originalsOnly ? " is-active" : ""}"
               data-category="all" aria-pressed="${state.category === "all" && !state.originalsOnly}">
         全部 <span class="chip__count">${formatNumber(total)}</span>
       </button>`,
      ...state.categories.map((category) => {
        const active = state.category === category.id;
        return `<button type="button" class="chip${active ? " is-active" : ""}"
                        data-category="${escapeHtml(category.id)}" data-domain="${escapeHtml(category.id)}"
                        aria-pressed="${active}">
                  ${escapeHtml(category.label)} <span class="chip__count">${formatNumber(category.count)}</span>
                </button>`;
      }),
      `<button type="button" class="chip${state.originalsOnly ? " is-active" : ""}"
               data-originals="true" aria-pressed="${state.originalsOnly}">
         原创 <span class="chip__count">${formatNumber(state.data?.stats?.originals || 0)}</span>
       </button>`,
    ];
    el.filterRow.innerHTML = chips.join("");
    renderActiveFilters();
  }

  function renderActiveFilters() {
    const bar = $("#active-filters");
    if (!bar) return;
    const parts = [];
    if (state.query) parts.push(`搜索 “${state.query}”`);
    if (state.category !== "all") {
      const category = state.categoryMap.get(state.category);
      parts.push(category ? category.label : state.category);
    }
    if (state.originalsOnly) parts.push("原创");
    if (state.sort !== "curated") {
      parts.push(state.sort === "name-asc" ? "名称 A → Z" : "名称 Z → A");
    }
    if (!parts.length) {
      bar.hidden = true;
      bar.innerHTML = "";
      return;
    }
    bar.hidden = false;
    bar.innerHTML = `<span>当前筛选：${parts.map(escapeHtml).join(" · ")}</span>
      <button class="ghost-btn" type="button" id="clear-active">清除</button>`;
    $("#clear-active")?.addEventListener("click", clearFilters);
  }

  function renderCatalog() {
    const filtered = getFilteredSkills();
    const total = state.skills.length;
    const visibleCount = state.page * PAGE_SIZE;
    const visible = filtered.slice(0, visibleCount);

    el.skillGrid.innerHTML = visible.map((skill, index) => skillCard(skill, index, {
      wide: index === 0 && skill.featured && !state.query && state.page === 1,
    })).join("");

    el.skillGrid.setAttribute("aria-busy", "false");
    el.emptyState.hidden = filtered.length !== 0;

    if (state.query) {
      el.catalogCount.textContent = `搜索 “${state.query}” · 找到 ${formatNumber(filtered.length)} 个技能`;
    } else if (state.category !== "all") {
      const category = state.categoryMap.get(state.category);
      el.catalogCount.textContent = `${category ? category.label : state.category} · ${formatNumber(filtered.length)} 个技能`;
    } else if (state.originalsOnly) {
      el.catalogCount.textContent = `原创技能 · ${formatNumber(filtered.length)} 个`;
    } else {
      el.catalogCount.textContent = `${formatNumber(total)} 个技能 · ${state.categories.length} 个领域 · 当前显示 ${formatNumber(visible.length)} 个`;
    }

    const remaining = filtered.length - visible.length;
    el.loadMore.hidden = remaining <= 0;
    el.loadMore.textContent = remaining > 0 ? `加载更多（剩余 ${formatNumber(remaining)}）` : "加载更多";

    renderActiveFilters();
    observeReveal(el.skillGrid);
  }

  function renderLocal() {
    if (!state.local.length) {
      el.localSection.hidden = true;
      el.localGrid.innerHTML = "";
      return;
    }
    el.localSection.hidden = false;
    el.localGrid.innerHTML = state.local.map((skill, index) => skillCard(skill, index)).join("");
    observeReveal(el.localGrid);
  }

  function syncSearchInputs() {
    if (el.heroSearch.value !== state.query) el.heroSearch.value = state.query;
    if (el.catalogSearch.value !== state.query) el.catalogSearch.value = state.query;
  }

  function syncUrl() {
    const params = new URLSearchParams(window.location.search);
    if (state.query) params.set("q", state.query);
    else params.delete("q");
    if (state.category !== "all") params.set("cat", state.category);
    else params.delete("cat");
    if (state.originalsOnly) params.set("orig", "1");
    else params.delete("orig");
    if (state.sort !== "curated") params.set("sort", state.sort);
    else params.delete("sort");
    const queryString = params.toString();
    const nextState = { ...(window.history.state || {}) };
    if (!nextState.skill) nextState.list = true;
    window.history.replaceState(
      nextState,
      "",
      `${window.location.pathname}${queryString ? `?${queryString}` : ""}${window.location.hash}`,
    );
  }

  function setQuery(value, source) {
    state.query = String(value || "").slice(0, 120).trim();
    state.page = 1;
    if (source !== "hero") el.heroSearch.value = state.query;
    if (source !== "catalog") el.catalogSearch.value = state.query;
    syncUrl();
    renderCatalog();
  }

  function scrollActiveChip() {
    requestAnimationFrame(() => {
      const active = el.filterRow?.querySelector(".chip.is-active");
      if (!active) return;
      el.filterRow.scrollTo({
        left: Math.max(0, active.offsetLeft - 16),
        behavior: preferReduced() ? "auto" : "smooth",
      });
    });
  }

  function setCategory(categoryId) {
    state.category = categoryId || "all";
    state.page = 1;
    syncUrl();
    renderFilters();
    scrollActiveChip();
    renderCategoryGrid();
    renderCatalog();
  }

  function setOriginalsOnly(value) {
    state.originalsOnly = Boolean(value);
    state.page = 1;
    syncUrl();
    renderFilters();
    scrollActiveChip();
    renderCatalog();
  }

  function clearFilters() {
    state.query = "";
    state.category = "all";
    state.originalsOnly = false;
    state.sort = "curated";
    state.page = 1;
    el.sortSelect.value = "curated";
    syncSearchInputs();
    syncUrl();
    renderFilters();
    renderCategoryGrid();
    renderCatalog();
    requestAnimationFrame(() => {
      if (el.filterRow) el.filterRow.scrollLeft = 0;
    });
  }

  async function loadIndex() {
    const response = await fetch("data/index.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`索引加载失败（HTTP ${response.status}）`);
    const data = await response.json();
    if (!data || !Array.isArray(data.skills)) throw new Error("索引格式不正确");
    state.data = data;
    state.skills = data.skills.map((skill) => ({ ...skill, local: false }));
    state.categories = data.categories || [];
    state.categoryMap = new Map(state.categories.map((category) => [category.id, category]));
    state.skillMap = new Map(state.skills.map((skill) => [skill.id, skill]));
    document.title = `${data.site.title} · ${data.site.subtitle}`;
    if (el.catalogSearch) {
      el.catalogSearch.placeholder = `搜索 ${formatNumber(data.stats.total)} 个技能…`;
    }
  }

  function showLoadError(error) {
    const message = escapeHtml(error?.message || "未知错误");
    const retry = `<button class="primary-btn" type="button" id="retry-load">重新加载</button>`;
    el.categoryGrid.innerHTML = "";
    el.featuredGrid.innerHTML = "";
    el.filterRow.innerHTML = "";
    el.skillGrid.setAttribute("aria-busy", "false");
    el.skillGrid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <span class="empty-state__mark">${icons.file}</span>
        <h3>技能索引暂时无法加载</h3>
        <p>${message}。你仍然可以直接读取 <a href="data/index.json">data/index.json</a> 或 <a href="llms.txt">llms.txt</a>。</p>
        ${retry}
      </div>`;
    el.catalogCount.textContent = "索引加载失败";
    $("#retry-load")?.addEventListener("click", () => window.location.reload());
  }

  function readUrlState() {
    const params = new URLSearchParams(window.location.search);
    const query = params.get("q");
    if (query) state.query = query.slice(0, 120);
    const category = params.get("cat");
    if (category && state.categoryMap.has(category)) state.category = category;
    state.originalsOnly = params.get("orig") === "1";
    const sort = params.get("sort");
    if (["curated", "name-asc", "name-desc"].includes(sort)) state.sort = sort;
    el.sortSelect.value = state.sort;
    syncSearchInputs();
  }

  function renderAll() {
    renderCategoryGrid();
    renderFeatured();
    renderFilters();
    renderCatalog();
    renderLocal();
  }

  /* ------------------------------------------------------------------ */
  /* detail sheet                                                        */
  /* ------------------------------------------------------------------ */

  function hashSkillId() {
    const match = window.location.hash.match(/^#\/skill\/([^/?]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function openDetail(id, options = {}) {
    const local = state.local.find((skill) => skill.id === id);
    const skill = local || state.skillMap.get(id);
    if (!skill) {
      toast("没有找到这个技能");
      return;
    }
    if (state.activeSkill?.id === id && !el.detailOverlay.hidden) return;

    state.activeSkill = skill;
    state.detailTrigger = options.trigger || document.activeElement;
    if (options.push !== false) {
      const url = `${window.location.pathname}${window.location.search}#/skill/${encodeURIComponent(id)}`;
      window.history.pushState({ skill: id }, "", url);
    }

    el.detailOverlay.hidden = false;
    document.body.classList.add("is-locked");
    el.detailCategory.textContent = local ? "本地草稿" : (skill.category_label || "Skill");
    el.detailTitle.textContent = skillTitle(skill);
    el.detailBody.innerHTML = `
      <div class="detail-loading">
        <div class="skeleton skeleton--line"></div>
        <div class="skeleton skeleton--line"></div>
        <div class="skeleton skeleton--line skeleton--short"></div>
      </div>`;
    el.detailSheet.querySelector("[data-close-detail]")?.focus();
    state.detailFocusCleanup?.();
    state.detailFocusCleanup = trapFocus(el.detailSheet);

    const requestId = skill.id;
    if (local) {
      renderDetail(skill, { content: skill.content, content_available: true });
      return;
    }
    if (state.detailCache.has(skill.id)) {
      renderDetail(skill, state.detailCache.get(skill.id));
      return;
    }
    fetch(skill.json_url, { cache: "force-cache" })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        state.detailCache.set(skill.id, payload);
        if (state.activeSkill?.id === requestId) renderDetail(skill, payload);
      })
      .catch((error) => {
        if (state.activeSkill?.id !== requestId) return;
        el.detailBody.innerHTML = `
          <div class="empty-state" style="padding:32px 0">
            <h3>详情加载失败</h3>
            <p>${escapeHtml(error.message)}。可以直接打开 <a href="${escapeHtml(skill.repo_url)}" target="_blank" rel="noopener">GitHub 原文</a>。</p>
          </div>`;
      });
  }

  function metaCard(label, value) {
    if (!value) return "";
    return `<dl class="meta-card"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></dl>`;
  }

  function renderDetail(skill, payload) {
    const title = skillTitle(skill);
    const description = skill.description || "";
    const category = categoryFor(skill);
    const contentAvailable = payload.content_available !== false && Boolean(payload.content);
    const tags = (skill.tags || []).filter(Boolean);
    const actions = [
      `<button class="primary-btn" type="button" id="detail-copy">${icons.copy}复制给 AI</button>`,
      `<button class="glass-btn" type="button" id="detail-copy-md">${icons.copy}复制 Markdown</button>`,
      `<button class="glass-btn" type="button" id="detail-download">${icons.download}下载 .md</button>`,
    ];
    if (skill.repo_url) {
      actions.push(`<a class="glass-btn" href="${escapeHtml(skill.repo_url)}" target="_blank" rel="noopener">${icons.github}GitHub 原文</a>`);
    }
    if (skill.local) {
      actions.push(`<button class="ghost-btn" type="button" id="detail-delete-local">${icons.trash}删除本地技能</button>`);
    }

    el.detailBody.innerHTML = `
      <div class="detail-hero">
        <div class="detail-hero__badges">
          <span class="pill" data-domain="${escapeHtml(skill.category)}">${escapeHtml(category.label || "技能")}</span>
          ${skill.original ? `<span class="origin-badge" data-domain="${escapeHtml(skill.category)}">原创</span>` : ""}
          ${skill.featured ? `<span class="origin-badge" data-domain="${escapeHtml(skill.category)}">精选</span>` : ""}
          ${skill.local ? '<span class="origin-badge" data-domain="general-utilities">本地</span>' : ""}
        </div>
        <h1 id="detail-heading">${escapeHtml(title)}</h1>
        ${title.toLowerCase() !== skill.id.toLowerCase() ? `<p class="detail-hero__id">${escapeHtml(skill.id)}</p>` : ""}
        <p class="detail-hero__desc">${escapeHtml(description)}</p>
        ${tags.length ? `<div class="detail-tags">${tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
      </div>
      <div class="detail-layout">
        <aside class="detail-aside">
          ${metaCard("Category", category.label || "")}
          ${metaCard("Origin", skill.original ? "原创 (project-original)" : (skill.origin_kind && skill.origin_kind !== "unknown" ? skill.origin_kind : "未标注"))}
          ${metaCard("License", skill.license || "")}
          ${metaCard("Used by", (skill.used_by || []).join(", "))}
          ${metaCard("Support", skill.support_level || "")}
          ${metaCard("Path", skill.path || "local draft")}
          ${metaCard("Size", skill.char_count ? `${formatNumber(skill.char_count)} chars` : "")}
          <div class="detail-actions">${actions.join("")}</div>
        </aside>
        <div class="detail-main">
          ${contentAvailable
            ? `<article class="markdown" id="markdown-body">${markdownToHtml(stripDuplicateH1(payload.content, title, skill.id))}</article>`
            : `<div class="locked-panel">${icons.lock}<b>内容未公开</b><p>${escapeHtml(skill.private_reason || "这个技能在公开镜像中只保留索引信息。")}</p></div>`}
        </div>
      </div>`;

    decorateMarkdown($("#markdown-body"));
    bindDetailActions(skill, payload);
  }

  function stripDuplicateH1(markdown, title, id) {
    const match = markdown.match(/^\s*#\s+(.+?)\s*\n/);
    if (!match) return markdown;
    const heading = match[1].trim().toLowerCase();
    const candidates = [String(title || "").toLowerCase(), String(id || "").toLowerCase()];
    const duplicate = candidates.some((candidate) =>
      candidate &&
      (heading === candidate || heading.startsWith(`${candidate} -`) || heading.startsWith(`${candidate} —`))
    );
    return duplicate ? markdown.replace(match[0], "") : markdown;
  }

  function markdownToHtml(markdown) {
    if (!window.marked || !window.DOMPurify) {
      return `<pre>${escapeHtml(markdown)}</pre>`;
    }
    const raw = window.marked.parse(markdown, { gfm: true, breaks: false });
    return window.DOMPurify.sanitize(raw, {
      USE_PROFILES: { html: true },
      FORBID_TAGS: ["style", "form", "input", "button", "textarea", "select", "option", "iframe", "object", "embed", "link", "meta", "base", "video", "audio", "source"],
      FORBID_ATTR: ["style", "onerror", "onload", "onclick"],
      ALLOW_DATA_ATTR: false,
    });
  }

  function slugifyHeading(text) {
    return text.trim().toLowerCase().replace(/[^\w一-鿿]+/g, "-").replace(/^-+|-+$/g, "") || "section";
  }

  function decorateMarkdown(container) {
    if (!container) return;
    $$("a", container).forEach((anchor) => {
      const href = anchor.getAttribute("href") || "";
      if (/^https?:/i.test(href)) {
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
      }
    });
    $$("img", container).forEach((image) => {
      if (!image.hasAttribute("alt")) image.alt = "";
      image.loading = "lazy";
      image.decoding = "async";
      image.referrerPolicy = "no-referrer";
      image.addEventListener("error", () => {
        image.style.display = "none";
      }, { once: true });
    });
    $$("table", container).forEach((table) => {
      if (table.parentElement?.classList.contains("table-wrap")) return;
      const wrap = document.createElement("div");
      wrap.className = "table-wrap";
      wrap.tabIndex = 0;
      wrap.setAttribute("role", "region");
      wrap.setAttribute("aria-label", "表格，可横向滚动");
      table.parentNode.insertBefore(wrap, table);
      wrap.appendChild(table);
    });
    const usedIds = new Set();
    $$("h1,h2,h3,h4", container).forEach((heading) => {
      let id = slugifyHeading(heading.textContent || "");
      let suffix = 2;
      while (usedIds.has(id)) id = `${slugifyHeading(heading.textContent || "")}-${suffix++}`;
      usedIds.add(id);
      heading.id = id;
    });
    $$("pre", container).forEach((pre) => {
      pre.tabIndex = 0;
      const code = pre.querySelector("code");
      if (!code) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "code-copy";
      button.textContent = "复制";
      button.addEventListener("click", async () => {
        await copyText(code.textContent || "");
        button.textContent = "已复制";
        setTimeout(() => { button.textContent = "复制"; }, 1600);
      });
      pre.appendChild(button);
    });
  }

  function detailPrompt(skill, content) {
    return [
      `You are loading a skill from the AGI Skills Atlas.`,
      `Skill: ${skill.id}`,
      `Category: ${skill.category_label || skill.category}`,
      `Path: ${skill.path || "local draft"}`,
      `Description: ${skill.description || ""}`,
      `Source: ${skill.repo_url || "local"}`,
      "",
      "---",
      "",
      content,
    ].join("\n");
  }

  function skillFile(skill, content) {
    const tags = JSON.stringify(skill.tags || []);
    return [
      "---",
      `name: ${JSON.stringify(skill.id)}`,
      `description: ${JSON.stringify(skill.description || "")}`,
      `category: ${JSON.stringify(skill.category_label || skill.category || "local")}`,
      `tags: ${tags}`,
      `source: ${JSON.stringify(skill.repo_url || "local")}`,
      "---",
      "",
      content,
    ].join("\n");
  }

  function bindDetailActions(skill, payload) {
    const content = payload.content || "";
    $("#detail-copy")?.addEventListener("click", async () => {
      await copyText(detailPrompt(skill, content));
      toast("已复制给 AI 的完整提示");
    });
    $("#detail-copy-md")?.addEventListener("click", async () => {
      await copyText(content);
      toast("已复制 Markdown 原文");
    });
    $("#detail-download")?.addEventListener("click", () => {
      downloadText(`${skill.id}.md`, skillFile(skill, content));
      toast("已下载 SKILL.md");
    });
    $("#detail-copy-link")?.addEventListener("click", async () => {
      const url = new URL(window.location.href);
      url.hash = `#/skill/${encodeURIComponent(skill.id)}`;
      await copyText(url.toString());
      toast("已复制分享链接");
    });
    $("#detail-delete-local")?.addEventListener("click", () => {
      state.local = state.local.filter((item) => item.id !== skill.id);
      saveLocal();
      renderLocal();
      closeDetail();
      toast("已删除本地技能");
    });
  }

  function closeDetail(options = {}) {
    if (el.detailOverlay.hidden) return;
    if (options.updateHistory !== false) {
      if (window.history.state && window.history.state.skill) {
        window.history.back();
        return;
      }
      const url = `${window.location.pathname}${window.location.search}`;
      window.history.replaceState({ list: true }, "", url);
    }
    el.detailOverlay.hidden = true;
    state.activeSkill = null;
    state.detailFocusCleanup?.();
    state.detailFocusCleanup = null;
    if (options.restoreFocus !== false) {
      const trigger = state.detailTrigger;
      if (trigger && document.contains(trigger)) trigger.focus();
    }
    state.detailTrigger = null;
    syncBodyLock();
  }

  /* ------------------------------------------------------------------ */
  /* upload                                                              */
  /* ------------------------------------------------------------------ */

  function readLocal() {
    try {
      const raw = localStorage.getItem(STORAGE_LOCAL);
      const parsed = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter((item) => item && item.id && typeof item.content === "string")
        .map((item) => ({ ...item, local: true }));
    } catch {
      return [];
    }
  }

  function saveLocal() {
    try {
      localStorage.setItem(STORAGE_LOCAL, JSON.stringify(state.local));
    } catch {
      toast("本地存储不可用，技能只在当前页面有效");
    }
  }

  function openUpload(trigger) {
    state.uploadTrigger = trigger || document.activeElement;
    el.uploadOverlay.hidden = false;
    document.body.classList.add("is-locked");
    renderPending();
    el.uploadModal.querySelector("[data-close-upload]")?.focus();
    state.uploadFocusCleanup?.();
    state.uploadFocusCleanup = trapFocus(el.uploadModal);
  }

  function closeUpload() {
    if (el.uploadOverlay.hidden) return;
    el.uploadOverlay.hidden = true;
    state.uploadFocusCleanup?.();
    state.uploadFocusCleanup = null;
    const trigger = state.uploadTrigger;
    if (trigger && document.contains(trigger)) trigger.focus();
    state.uploadTrigger = null;
    syncBodyLock();
  }

  function syncBodyLock() {
    const locked = !el.detailOverlay.hidden || !el.uploadOverlay.hidden;
    document.body.classList.toggle("is-locked", locked);
  }

  function parseFrontmatter(text) {
    if (!text.startsWith("---")) return { data: {}, body: text };
    const end = text.indexOf("\n---", 3);
    if (end === -1) return { data: {}, body: text };
    const raw = text.slice(3, end).trim();
    const body = text.slice(end + 4).replace(/^\s*\n/, "");
    const data = {};
    const lines = raw.split(/\r?\n/);
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
      if (!match) { i += 1; continue; }
      const key = match[1];
      const rest = match[2].trim();
      if (rest === "" && i + 1 < lines.length && /^\s+- /.test(lines[i + 1])) {
        const items = [];
        i += 1;
        while (i < lines.length && /^\s+- /.test(lines[i])) {
          items.push(lines[i].replace(/^\s+- /, "").replace(/^["']|["']$/g, "").trim());
          i += 1;
        }
        data[key] = items;
        continue;
      }
      if (rest === ">" || rest === "|" || rest === ">-" || rest === "|-") {
        const block = [];
        i += 1;
        while (i < lines.length && (/^\s+/.test(lines[i]) || !lines[i].trim())) {
          block.push(lines[i].replace(/^\s{2}/, ""));
          i += 1;
        }
        data[key] = block.join(rest.startsWith(">") ? " " : "\n").trim();
        continue;
      }
      if (rest.startsWith("[") && rest.endsWith("]")) {
        data[key] = rest.slice(1, -1).split(",").map((item) => item.trim().replace(/^["']|["']$/g, "")).filter(Boolean);
      } else {
        data[key] = rest.replace(/^["']|["']$/g, "");
      }
      i += 1;
    }
    return { data, body };
  }

  function guessCategory(text) {
    const value = text.toLowerCase();
    const rules = [
      ["chinese-platform-workflows", ["小红书", "抖音", "公众号", "视频号", "b站", "哔哩", "微信"]],
      ["finance-trading-markets", ["交易", "股票", "a股", "基金", "crypto", "binance", "量化", "回测", "btc"]],
      ["content-media-publishing", ["视频", "剪辑", "封面", "写作", "内容", "发布", "图像"]],
      ["product-design-ux", ["设计", "ui", "ux", "frontend", "界面", "视觉"]],
      ["software-engineering", ["code", "代码", "工程", "测试", "debug", "api"]],
      ["ai-agents-orchestration", ["agent", "智能体", "orchestrat", "编排", "记忆"]],
      ["apps-workflow-automation", ["automation", "自动化", "workflow", "浏览器", "browser"]],
    ];
    for (const [category, keywords] of rules) {
      if (keywords.some((keyword) => value.includes(keyword))) return category;
    }
    return "general-utilities";
  }

  function parseSkillMarkdown(text, filename, folderHint) {
    const { data, body } = parseFrontmatter(text);
    const h1 = body.match(/^#\s+(.+)$/m)?.[1]?.trim() || "";
    const fallbackName = filename && filename.toLowerCase() !== "skill.md"
      ? filename.replace(/\.(md|markdown|txt)$/i, "")
      : (folderHint || "未命名技能");
    const name = String(data.name || "").trim() || h1.replace(/^#+\s*/, "").trim() || fallbackName;
    let description = String(data.description || "").trim();
    if (!description) {
      const paragraph = body
        .split(/\n{2,}/)
        .map((block) => block.replace(/^#.*$/gm, "").trim())
        .find((block) => block && !block.startsWith(">") && !block.startsWith("|"));
      description = paragraph ? paragraph.replace(/[*_`#>]/g, "").slice(0, 240) : "本地技能";
    }
    const tags = Array.isArray(data.tags) ? data.tags : [];
    const category = guessCategory(`${name} ${description} ${body.slice(0, 1200)}`);
    return {
      id: slugifyLocal(name),
      name,
      headline: h1 && h1.toLowerCase() !== name.toLowerCase() ? h1 : name,
      description,
      summary: description.length > 200 ? `${description.slice(0, 200)}…` : description,
      content: body,
      tags: tags.slice(0, 6),
      category,
      category_label: "本地草稿",
      category_label_en: "Local draft",
      category_index: 0,
      path: filename || "local draft",
      repo_url: "",
      original: false,
      featured: false,
      local: true,
      created_at: new Date().toISOString(),
    };
  }

  function slugifyLocal(value) {
    const slug = String(value || "")
      .toLowerCase()
      .replace(/[^\w一-鿿-]+/g, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^-+|-+$/g, "");
    return `local-${slug || "skill"}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
  }

  function addPending(skill) {
    const exists = state.pending.some((item) => item.name === skill.name && item.content === skill.content);
    if (exists) {
      toast("这个技能已经在待加入列表里");
      return;
    }
    state.pending.push(skill);
    renderPending();
  }

  function renderPending() {
    el.uploadSave.disabled = state.pending.length === 0;
    el.uploadPreview.hidden = state.pending.length === 0;
    el.uploadPreviewCount.textContent = `${state.pending.length} 个`;
    el.uploadPreviewList.innerHTML = state.pending.map((skill, index) => `
      <div class="upload-item">
        <span>${icons.file}</span>
        <div><b>${escapeHtml(skill.name)}</b><small>${escapeHtml(skill.description.slice(0, 90))}</small></div>
        <button class="icon-btn" type="button" data-remove-pending="${index}" aria-label="移除 ${escapeHtml(skill.name)}">${icons.close}</button>
      </div>`).join("");
  }

  async function handleFiles(files) {
    const list = Array.from(files || []);
    if (!list.length) return;
    const accepted = [];
    for (const file of list) {
      if (!/\.(md|markdown|txt)$/i.test(file.name) && file.type !== "text/markdown" && file.type !== "text/plain") {
        toast(`${file.name} 不是 Markdown 文件`);
        continue;
      }
      if (file.size > 2 * 1024 * 1024) {
        toast(`${file.name} 超过 2MB`);
        continue;
      }
      const text = await file.text();
      const folderHint = file.webkitRelativePath ? file.webkitRelativePath.split("/").slice(-2, -1)[0] : "";
      accepted.push(parseSkillMarkdown(text, file.name, folderHint));
    }
    accepted.forEach(addPending);
    if (accepted.length) toast(`已解析 ${accepted.length} 个技能，等待加入`);
  }

  function savePending() {
    if (!state.pending.length) return;
    state.local = [...state.local, ...state.pending];
    saveLocal();
    state.pending = [];
    renderPending();
    renderLocal();
    closeUpload();
    toast(`已加入 ${state.local.length} 个本地技能`);
  }

  function exportLocal() {
    const blob = new Blob([JSON.stringify(state.local, null, 2)], { type: "application/json" });
    downloadBlob(blob, "agi-skills-atlas-local.json");
    toast("已导出本地技能 JSON");
  }

  /* ------------------------------------------------------------------ */
  /* utilities                                                           */
  /* ------------------------------------------------------------------ */

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch { ok = false; }
      area.remove();
      return ok;
    }
  }

  function downloadText(filename, text) {
    downloadBlob(new Blob([text], { type: "text/markdown;charset=utf-8" }), filename);
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  function toast(message) {
    const node = document.createElement("div");
    node.className = "toast";
    node.innerHTML = `${icons.check}<span>${escapeHtml(message)}</span>`;
    el.toastRegion.appendChild(node);
    setTimeout(() => {
      node.style.opacity = "0";
      node.style.transform = "translateY(8px)";
      setTimeout(() => node.remove(), 240);
    }, 2600);
  }

  function trapFocus(container) {
    const selector = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
    const handler = (event) => {
      if (event.key !== "Tab") return;
      const items = $$(selector, container).filter((item) => item.offsetParent !== null);
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    container.addEventListener("keydown", handler);
    return () => container.removeEventListener("keydown", handler);
  }

  /* ------------------------------------------------------------------ */
  /* theme                                                               */
  /* ------------------------------------------------------------------ */

  function systemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function effectiveTheme() {
    const current = document.documentElement.dataset.theme;
    return current === "light" || current === "dark" ? current : systemTheme();
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    try { localStorage.setItem(STORAGE_THEME, theme); } catch { /* ignore */ }
    updateThemeButton();
    constellation?.refreshColor();
  }

  function toggleTheme() {
    const next = effectiveTheme() === "dark" ? "light" : "dark";
    if (document.startViewTransition && !preferReduced()) {
      document.startViewTransition(() => applyTheme(next));
    } else {
      applyTheme(next);
    }
  }

  function updateThemeButton() {
    if (!el.themeToggle) return;
    const dark = effectiveTheme() === "dark";
    el.themeToggle.setAttribute("aria-label", dark ? "切换到浅色模式" : "切换到深色模式");
    el.themeToggle.setAttribute("title", dark ? "切换到浅色模式" : "切换到深色模式");
  }

  /* ------------------------------------------------------------------ */
  /* motion                                                              */
  /* ------------------------------------------------------------------ */

  let revealObserver = null;

  function observeReveal(root = document) {
    const items = $$(".reveal:not(.is-visible)", root);
    if (preferReduced()) {
      items.forEach((item) => item.classList.add("is-visible"));
      return;
    }
    if (!revealObserver) {
      revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      }, { rootMargin: "0px 0px -8% 0px", threshold: 0.04 });
    }
    items.forEach((item) => revealObserver.observe(item));
  }

  function setupSpotlight() {
    if (!finePointer.matches || preferReduced()) return;
    let frame = 0;
    let lastEvent = null;
    document.addEventListener("pointermove", (event) => {
      lastEvent = event;
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const target = lastEvent?.target?.closest?.(".category-card, .featured-card, .skill-card");
        if (!target) return;
        const rect = target.getBoundingClientRect();
        target.style.setProperty("--mx", `${lastEvent.clientX - rect.left}px`);
        target.style.setProperty("--my", `${lastEvent.clientY - rect.top}px`);
      });
    }, { passive: true });
  }

  function setupHeroParallax() {
    if (!el.heroVisual || !finePointer.matches || preferReduced()) return;
    el.heroVisual.addEventListener("pointermove", (event) => {
      const rect = el.heroVisual.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      el.heroVisual.style.transform = `translate3d(${x * 10}px, ${y * 10}px, 0)`;
    });
    el.heroVisual.addEventListener("pointerleave", () => {
      el.heroVisual.style.transform = "";
    });
  }

  /* ------------------------------------------------------------------ */
  /* constellation canvas                                                */
  /* ------------------------------------------------------------------ */

  let constellation = null;

  function readConstellationColor() {
    if (!el.heroVisual) return "#6D28D9";
    const value = getComputedStyle(el.heroVisual).getPropertyValue("--domain").trim();
    return value || "#6D28D9";
  }

  function setupConstellation() {
    if (!el.canvas || !el.heroVisual) return;
    const context = el.canvas.getContext("2d");
    if (!context) return;
    let width = 0;
    let height = 0;
    let nodes = [];
    let frame = 0;
    let visible = true;
    let color = readConstellationColor();
    let dpr = 1;

    const resize = () => {
      const rect = el.heroVisual.getBoundingClientRect();
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      el.canvas.width = Math.round(width * dpr);
      el.canvas.height = Math.round(height * dpr);
      el.canvas.style.width = `${width}px`;
      el.canvas.style.height = `${height}px`;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.max(34, Math.min(110, Math.floor((width * height) / 6200)));
      nodes = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.16,
        vy: (Math.random() - 0.5) * 0.16,
        r: Math.random() * 1.4 + 0.7,
      }));
      draw();
    };

    const draw = () => {
      context.clearRect(0, 0, width, height);
      context.strokeStyle = color;
      context.fillStyle = color;
      for (let i = 0; i < nodes.length; i += 1) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j += 1) {
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const distance = Math.hypot(dx, dy);
          if (distance < 108) {
            context.globalAlpha = (1 - distance / 108) * 0.16;
            context.beginPath();
            context.moveTo(a.x, a.y);
            context.lineTo(b.x, b.y);
            context.stroke();
          }
        }
      }
      context.globalAlpha = 0.5;
      nodes.forEach((node) => {
        context.beginPath();
        context.arc(node.x, node.y, node.r, 0, Math.PI * 2);
        context.fill();
      });
      context.globalAlpha = 1;
    };

    const tick = () => {
      if (!visible || document.hidden) {
        frame = 0;
        return;
      }
      nodes.forEach((node) => {
        node.x += node.vx;
        node.y += node.vy;
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;
      });
      draw();
      frame = requestAnimationFrame(tick);
    };

    const start = () => {
      if (preferReduced() || frame) return;
      frame = requestAnimationFrame(tick);
    };
    const stop = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
    };

    resize();
    if (!preferReduced()) {
      start();
      const observer = new IntersectionObserver((entries) => {
        visible = entries[0]?.isIntersecting ?? true;
        if (visible) start();
        else stop();
      }, { threshold: 0.02 });
      observer.observe(el.heroVisual);
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) stop();
        else start();
      });
    }
    new ResizeObserver(() => {
      resize();
      if (preferReduced()) draw();
    }).observe(el.heroVisual);
    constellation = {
      refreshColor() {
        color = readConstellationColor();
        if (preferReduced()) draw();
      },
    };
    if (constellation) constellation.refreshColor();
  }

  /* ------------------------------------------------------------------ */
  /* events                                                              */
  /* ------------------------------------------------------------------ */

  function setupEvents() {
    el.heroSearchForm?.addEventListener("submit", (event) => {
      event.preventDefault();
      setQuery(el.heroSearch.value, "hero");
      $("#catalog")?.scrollIntoView({ behavior: preferReduced() ? "auto" : "smooth", block: "start" });
    });
    el.heroSearch?.addEventListener("input", () => {
      clearTimeout(state.searchTimer);
      state.searchTimer = setTimeout(() => setQuery(el.heroSearch.value, "hero"), 120);
    });
    el.catalogSearch?.addEventListener("input", () => {
      clearTimeout(state.searchTimer);
      state.searchTimer = setTimeout(() => setQuery(el.catalogSearch.value, "catalog"), 120);
    });
    $("#search-jump")?.addEventListener("click", () => {
      el.catalogSearch?.scrollIntoView({ behavior: preferReduced() ? "auto" : "smooth", block: "center" });
      el.catalogSearch?.focus();
    });
    el.sortSelect?.addEventListener("change", () => {
      state.sort = el.sortSelect.value;
      state.page = 1;
      syncUrl();
      renderCatalog();
    });
    el.loadMore?.addEventListener("click", () => {
      state.page += 1;
      renderCatalog();
    });
    $("#clear-filters")?.addEventListener("click", clearFilters);

    el.filterRow?.addEventListener("click", (event) => {
      const chip = event.target.closest(".chip");
      if (!chip) return;
      if (chip.dataset.originals) {
        setOriginalsOnly(!state.originalsOnly);
        return;
      }
      setCategory(chip.dataset.category || "all");
    });
    el.categoryGrid?.addEventListener("click", (event) => {
      const card = event.target.closest("[data-category]");
      if (!card) return;
      setCategory(card.dataset.category);
      $("#catalog")?.scrollIntoView({ behavior: preferReduced() ? "auto" : "smooth", block: "start" });
    });

    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[data-skill]");
      if (!link) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      openDetail(link.dataset.skill, { push: true, trigger: link });
    });

    $$("[data-close-detail]").forEach((button) => button.addEventListener("click", () => closeDetail()));
    $$("[data-close-upload]").forEach((button) => button.addEventListener("click", closeUpload));
    $("#detail-copy-link")?.addEventListener("click", () => {
      if (!state.activeSkill) return;
      const url = new URL(window.location.href);
      url.hash = `#/skill/${encodeURIComponent(state.activeSkill.id)}`;
      copyText(url.toString()).then(() => toast("已复制分享链接"));
    });

    $$("[data-upload-open]").forEach((button) => button.addEventListener("click", () => openUpload(button)));
    $("#upload-clear")?.addEventListener("click", () => {
      state.pending = [];
      renderPending();
    });
    el.uploadSave?.addEventListener("click", savePending);
    el.uploadPreviewList?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-remove-pending]");
      if (!button) return;
      state.pending.splice(Number(button.dataset.removePending), 1);
      renderPending();
    });
    el.fileInput?.addEventListener("change", () => {
      handleFiles(el.fileInput.files);
      el.fileInput.value = "";
    });
    ["dragenter", "dragover"].forEach((type) => {
      el.dropzone?.addEventListener(type, (event) => {
        event.preventDefault();
        el.dropzone.classList.add("is-over");
      });
    });
    ["dragleave", "drop"].forEach((type) => {
      el.dropzone?.addEventListener(type, (event) => {
        event.preventDefault();
        el.dropzone.classList.remove("is-over");
      });
    });
    el.dropzone?.addEventListener("drop", (event) => handleFiles(event.dataTransfer.files));

    $$(".upload-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        $$(".upload-tab").forEach((item) => {
          const active = item === tab;
          item.classList.toggle("is-active", active);
          item.setAttribute("aria-selected", String(active));
        });
        $("#upload-panel-file").hidden = tab.dataset.tab !== "file";
        $("#upload-panel-paste").hidden = tab.dataset.tab !== "paste";
      });
    });
    $("#paste-add")?.addEventListener("click", () => {
      const content = el.pasteContent.value.trim();
      if (!content) {
        toast("先粘贴 SKILL.md 内容");
        return;
      }
      const skill = parseSkillMarkdown(content, `${el.pasteName.value.trim() || "pasted-skill"}.md`, "");
      if (el.pasteName.value.trim()) skill.name = el.pasteName.value.trim();
      addPending(skill);
      el.pasteContent.value = "";
      el.pasteName.value = "";
    });

    $("#export-local")?.addEventListener("click", exportLocal);
    $("#clear-local")?.addEventListener("click", () => {
      if (!state.clearLocalArmed) {
        state.clearLocalArmed = true;
        $("#clear-local").textContent = "再点一次确认清空";
        setTimeout(() => {
          state.clearLocalArmed = false;
          $("#clear-local").textContent = "清空本地";
        }, 3200);
        return;
      }
      state.local = [];
      saveLocal();
      renderLocal();
      state.clearLocalArmed = false;
      $("#clear-local").textContent = "清空本地";
      toast("已清空本地技能");
    });

    el.themeToggle?.addEventListener("click", toggleTheme);
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (document.documentElement.dataset.theme === "auto") {
        updateThemeButton();
        constellation?.refreshColor();
      }
    });

    window.addEventListener("popstate", () => {
      const id = hashSkillId();
      if (id) openDetail(id, { push: false });
      else closeDetail({ updateHistory: false });
    });
    window.addEventListener("hashchange", () => {
      const id = hashSkillId();
      if (id) openDetail(id, { push: false });
      else if (state.activeSkill) closeDetail({ updateHistory: false });
    });

    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const typing = target instanceof HTMLElement && (
        target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable
      );
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        el.heroSearch.focus();
        el.heroSearch.select();
        return;
      }
      if (event.key === "/" && !typing) {
        event.preventDefault();
        el.catalogSearch.focus();
        return;
      }
      if (event.key === "Escape") {
        if (!el.detailOverlay.hidden) closeDetail();
        else if (!el.uploadOverlay.hidden) closeUpload();
        else if (state.query) {
          setQuery("", "escape");
          syncSearchInputs();
        }
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* bootstrap                                                           */
  /* ------------------------------------------------------------------ */

  async function init() {
    state.local = readLocal();
    setupEvents();
    setupSpotlight();
    setupHeroParallax();
    try {
      await loadIndex();
      readUrlState();
      renderAll();
    } catch (error) {
      showLoadError(error);
      return;
    }
    setupConstellation();
    updateThemeButton();
    const initialSkill = hashSkillId();
    if (initialSkill) {
      openDetail(initialSkill, { push: false });
    } else {
      window.history.replaceState({ list: true }, "", window.location.href);
    }
  }

  init();
})();
