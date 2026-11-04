function asString(v) {
  if (v === null || v === undefined) return '';
  return String(v);
}

function pick(obj, keys) {
  for (const k of keys) {
    if (obj && Object.prototype.hasOwnProperty.call(obj, k) && obj[k] !== undefined) return obj[k];
  }
  return undefined;
}

function normalizeSameSite(v) {
  const s = asString(v).toLowerCase();
  if (!s) return undefined;
  if (s === 'lax') return 'Lax';
  if (s === 'strict') return 'Strict';
  if (s === 'none') return 'None';
  return undefined;
}

function normalizeExpires(v) {
  if (v === null || v === undefined || v === '') return undefined;

  // Common formats:
  // - Playwright uses seconds since epoch (number)
  // - Chrome exports can use milliseconds or ISO strings
  if (typeof v === 'number') {
    if (v <= 0) return undefined;
    // Heuristic: treat > 10^12 as ms
    const ms = v > 1e12 ? v : v * 1000;
    return new Date(ms).toISOString();
  }

  const s = asString(v).trim();
  if (!s) return undefined;

  const n = Number(s);
  if (!Number.isNaN(n)) {
    const ms = n > 1e12 ? n : n * 1000;
    return new Date(ms).toISOString();
  }

  const d = new Date(s);
  if (!Number.isNaN(d.getTime())) return d.toISOString();
  return undefined;
}

export function normalizeCookieObject(c) {
  if (!c || typeof c !== 'object') return null;

  const name = asString(pick(c, ['name', 'Name'])).trim();
  const value = asString(pick(c, ['value', 'Value'])).trim();
  if (!name) return null;

  const domain = asString(pick(c, ['domain', 'Domain'])).trim() || '.xiaohongshu.com';
  const path = asString(pick(c, ['path', 'Path'])).trim() || '/';

  const httpOnly = Boolean(pick(c, ['httpOnly', 'http_only', 'HttpOnly']));
  const secure = Boolean(pick(c, ['secure', 'Secure']));

  const sameSite = normalizeSameSite(pick(c, ['sameSite', 'same_site', 'SameSite']));
  const expires = normalizeExpires(pick(c, ['expires', 'expirationDate', 'expiry', 'Expires', 'Expiration']));

  return {
    name,
    value,
    domain,
    path,
    httpOnly,
    secure,
    sameSite,
    expires,
  };
}

export function normalizeCookiesPayload(input) {
  let cookiesRaw = input;
  if (input && typeof input === 'object' && !Array.isArray(input)) {
    // Supported shapes:
    // - [...]
    // - { cookies: [...] }
    // - { data: { cookies: [...] } } (agent-browser-stealth --json)
    // - { success: true, data: { cookies: [...] }, error: null } (agent-browser-stealth --json)
    if (Array.isArray(input.cookies)) {
      cookiesRaw = input.cookies;
    } else if (input.data && typeof input.data === 'object' && Array.isArray(input.data.cookies)) {
      cookiesRaw = input.data.cookies;
    }
  }

  if (!Array.isArray(cookiesRaw)) {
    throw new Error('Unsupported cookies JSON: expected array or {cookies:[...]}');
  }

  const cookies = [];
  for (const c of cookiesRaw) {
    const n = normalizeCookieObject(c);
    if (n) cookies.push(n);
  }

  if (cookies.length === 0) {
    throw new Error('No cookies parsed after normalization');
  }

  return {
    generated_at: new Date().toISOString(),
    format: 'cookie_list_v1',
    cookies,
  };
}

export function cookiesToHeaderString(cookies) {
  const parts = [];
  for (const c of cookies) {
    if (!c || typeof c !== 'object') continue;
    const name = asString(c.name).trim();
    const value = asString(c.value);
    if (!name) continue;
    parts.push(`${name}=${value}`);
  }
  return parts.join('; ');
}

export function summarizeCookies(cookies) {
  const domains = new Set();
  let sessionCount = 0;
  let persistentCount = 0;
  let earliest = null;
  let latest = null;

  for (const c of cookies) {
    if (!c || typeof c !== 'object') continue;
    if (c.domain) domains.add(String(c.domain));

    if (c.expires) {
      persistentCount += 1;
      const t = new Date(c.expires).getTime();
      if (!Number.isNaN(t)) {
        if (earliest === null || t < earliest) earliest = t;
        if (latest === null || t > latest) latest = t;
      }
    } else {
      sessionCount += 1;
    }
  }

  return {
    count: cookies.length,
    domains: Array.from(domains).sort(),
    sessionCount,
    persistentCount,
    earliestExpiry: earliest ? new Date(earliest).toISOString() : null,
    latestExpiry: latest ? new Date(latest).toISOString() : null,
  };
}
