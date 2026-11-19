#!/usr/bin/env python3
"""Build the AGI Skills Atlas static site.

The catalog (`catalog/skill-index.json`) is the curated inventory. Each
`skills/<id>/SKILL.md` supplies the readable body. The output is generated into
`docs/skills-atlas/` during the Pages workflow and is intentionally ignored by
git: the repository keeps one source of truth, and the site is rebuilt from it.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT_DEFAULT = PROJECT_DIR.parent
DEFAULT_OUT = REPO_ROOT_DEFAULT / "docs" / "skills-atlas"

GENERIC_TAGS = {
    "工作", "技能", "知识库", "笔记", "索引", "项目", "skill", "skills",
    "claude", "claude-code", "agent", "agent-skill", "workflow",
}

# A safety net, not a substitute for reviewing content before publishing.
SECRET_PATTERNS = [
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), "[REDACTED_TELEGRAM_TOKEN]"),
    (re.compile(r"https://discord(?:app)?\.com/api/webhooks/[A-Za-z0-9/_-]+"),
     "[REDACTED_DISCORD_WEBHOOK]"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----.*?"
                r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.S),
     "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
     "[REDACTED_JWT]"),
]

# Only redact a key/value pair when the key name itself is credential-shaped.
# This avoids turning ordinary configuration (MODEL_SONNET, STOCK_LIST,
# PROJECT, API_BASE) into [REDACTED] noise on a public skills site.
SECRET_KEY_NAME_RE = re.compile(
    r"(?i)^(?:.*_)?(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE[_-]?KEY|"
    r"ACCESS[_-]?KEY|CLIENT[_-]?SECRET|AUTH[_-]?TOKEN|ENCRYPT[_-]?KEY|KEY)(?:_|$)"
)
KV_LINE_RE = re.compile(
    r"(?m)^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z0-9_]*)\s*[:=]\s*([\"']?)([^\s\"'#]{16,})\2\s*$"
)
URL_CREDENTIAL_RE = re.compile(r"https?://([^/\s:@]+):([^/\s@]+)@([^/\s]+)")
HOME_PATH_RE = re.compile(r"/(?:Users|home|root)/[A-Za-z0-9._-]+")
PRIVACY_REPLACEMENTS = [
    (re.compile(r"~?/\.openclaw"), "[本地工作区]"),
    (re.compile(r"~?/\.zshrc"), "[本地密钥库]"),
    (re.compile(r"/opt/data"), "[DATA_ROOT]"),
]


def parse_scalar(value: str):
    v = value.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return v[1:-1]
    if len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        return v[1:-1].replace("''", "'")
    low = v.lower()
    if low in {"true", "false"}:
        return low == "true"
    if low in {"null", "~"}:
        return None
    return v


def split_inline_list(value: str) -> list[str]:
    inner = value.strip()[1:-1]
    items, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf).strip())
    return [str(parse_scalar(x)) for x in items if x.strip()]


def fold_block(text: str) -> str:
    out, paragraph = [], []
    for line in text.splitlines():
        if line.strip():
            paragraph.append(line.strip())
        else:
            if paragraph:
                out.append(" ".join(paragraph))
                paragraph = []
            out.append("")
    if paragraph:
        out.append(" ".join(paragraph))
    return "\n".join(out).strip()


def parse_yaml_subset(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, object]] = [(-1, root)]
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            if isinstance(parent, list):
                parent.append(parse_scalar(line[2:]))
            i += 1
            continue

        # Lists of mappings (permissions, platforms, ...) are not fields the
        # Atlas needs. Skip their continuation lines instead of guessing.
        if isinstance(parent, list):
            i += 1
            continue

        if ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key, rest = key.strip(), rest.strip()

        if rest in {"", "|", ">", "|-", ">-", "|+", ">+"}:
            if rest.startswith(("|", ">")):
                block_lines, j = [], i + 1
                while j < len(lines):
                    nxt = lines[j]
                    if not nxt.strip():
                        block_lines.append("")
                        j += 1
                        continue
                    nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                    if nxt_indent <= indent:
                        break
                    block_lines.append(nxt)
                    j += 1
                nonempty = [x for x in block_lines if x.strip()]
                min_indent = min((len(x) - len(x.lstrip(" ")) for x in nonempty), default=0)
                block = "\n".join(
                    x[min_indent:] if len(x) >= min_indent else "" for x in block_lines
                )
                parent[key] = fold_block(block) if rest.startswith(">") else block.strip()
                i = j
                continue

            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                nxt = lines[j]
                nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                if nxt_indent > indent and nxt.lstrip().startswith("- "):
                    container: object = []
                else:
                    container = {}
                parent[key] = container
                stack.append((indent, container))
            else:
                parent[key] = None
            i += 1
            continue

        if rest.startswith("[") and rest.endswith("]"):
            parent[key] = split_inline_list(rest)
        else:
            parent[key] = parse_scalar(rest)
        i += 1
    return root


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() in {"---", "..."}:
            end = idx
            break
    if end is None:
        return {}, text
    return parse_yaml_subset("\n".join(lines[1:end])), "\n".join(lines[end + 1:])


def normalize_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = " ".join(str(v) for v in value)
    elif isinstance(value, dict):
        value = " ".join(str(v) for v in value.values())
    value = str(value).replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip("\"'")


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", lambda m: m.group(1).split("/")[-1], text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.M)
    text = re.sub(r"[*_~>|]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def derive_description(body: str, name: str) -> str:
    lines = body.splitlines()
    in_fence = False
    paragraph: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("#"):
            if paragraph:
                break
            continue
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith((">", "|", "- ", "* ", "+ ")) and not paragraph:
            continue
        paragraph.append(stripped)
        if len(" ".join(paragraph)) > 90:
            break
    text = strip_markdown(" ".join(paragraph))
    return text[:600] if text else f"{name} skill"


def extract_headline(body: str, name: str) -> str:
    for line in body.splitlines():
        if line.strip().startswith("# "):
            title = strip_markdown(line.strip()[2:].strip())
            if title.lower().startswith(name.lower()):
                rest = title[len(name):].lstrip(" —–-:·|")
                if rest:
                    title = rest
            return title[:100]
    return ""


def collect_tags(frontmatter: dict) -> list[str]:
    candidates: list[str] = []

    def add(value):
        if isinstance(value, str):
            if "," in value:
                candidates.extend(part.strip() for part in value.split(","))
            else:
                candidates.append(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                add(item)

    add(frontmatter.get("tags"))
    metadata = frontmatter.get("metadata")
    if isinstance(metadata, dict):
        add(metadata.get("tags"))
        hermes = metadata.get("hermes")
        if isinstance(hermes, dict):
            add(hermes.get("tags"))

    out, seen = [], set()
    for tag in candidates:
        tag = normalize_text(tag).lstrip("#").strip()
        if not tag or tag.lower() in GENERIC_TAGS or tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return out[:6]


def looks_like_secret(value: str) -> bool:
    value = value.strip()
    if len(value) < 16:
        return False
    upper = value.upper()
    if any(marker in upper for marker in (
        "YOUR", "EXAMPLE", "PLACEHOLDER", "CHANGEME", "REDACTED", "...", "{{", "}}",
    )):
        return False
    if value.startswith(("http://", "https://", "/", "~/", "./", "file:")):
        return False
    if re.search(r"(?i)\b(process\.env|os\.environ|getenv|system\.getenv|env\.)", value):
        return False
    if any(ch in value for ch in " \t\r\n<>${}[]();,'\"`\\|&"):
        return False
    if len(set(value)) < 8:
        return False
    has_digit = bool(re.search(r"\d", value))
    has_upper = bool(re.search(r"[A-Z]", value))
    has_lower = bool(re.search(r"[a-z]", value))
    if not (has_digit or (has_upper and has_lower)):
        return False
    return value.lower() not in {
        "development", "production", "staging", "localhost", "default",
        "changeme", "example", "test", "demo", "none", "null", "secret",
    }


def redact_text(text: str) -> tuple[str, int, int]:
    count = 0
    for pattern, replacement in SECRET_PATTERNS:
        text, n = pattern.subn(replacement, text)
        count += n

    def kv_replace(match: re.Match) -> str:
        nonlocal count
        key, quote, value = match.groups()
        if not SECRET_KEY_NAME_RE.match(key):
            return match.group(0)
        if not looks_like_secret(value):
            return match.group(0)
        count += 1
        return match.group(0).replace(value, "[REDACTED]", 1)

    text = KV_LINE_RE.sub(kv_replace, text)

    def url_replace(match: re.Match) -> str:
        nonlocal count
        user, secret, host = match.groups()
        if len(secret) < 8 or any(ch in secret for ch in "{}$<>"):
            return match.group(0)
        count += 1
        return f"https://{user}:[REDACTED]@{host}"

    text = URL_CREDENTIAL_RE.sub(url_replace, text)
    text, privacy_count = HOME_PATH_RE.subn("~", text)
    for pattern, replacement in PRIVACY_REPLACEMENTS:
        text, n = pattern.subn(replacement, text)
        privacy_count += n
    return text, count, privacy_count


def convert_wikilinks(text: str) -> str:
    text = re.sub(r"!\[\[([^\]]+)\]\]", lambda m: f"[嵌入附件: {m.group(1)}]", text)
    text = re.sub(
        r"\[\[([^\]|]+)\|([^\]]+)\]\]",
        lambda m: m.group(2).strip(),
        text,
    )
    text = re.sub(
        r"\[\[([^\]]+)\]\]",
        lambda m: m.group(1).split("#")[0].split("/")[-1].strip(),
        text,
    )
    return text


def sanitize_content(body: str) -> tuple[str, int, int]:
    content = body.replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"<!--.*?-->", "", content, flags=re.S)
    content, redactions, privacy = redact_text(content)
    content = convert_wikilinks(content)
    content = re.sub(r"\n{4,}", "\n\n\n", content).strip()
    return content + "\n", redactions, privacy


def make_summary(description: str, limit: int = 200) -> str:
    description = normalize_text(description)
    if len(description) <= limit:
        return description
    cut = description[:limit]
    for sep in ("。", "；", ". ", "; ", "，", ", "):
        idx = cut.rfind(sep)
        if idx > int(limit * 0.55):
            return cut[:idx + len(sep)].rstrip() + "…"
    return cut.rstrip() + "…"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_categories(config: dict, catalog: dict, skills: list[dict]) -> list[dict]:
    counts = Counter(skill["category"] for skill in skills)
    config_categories = config.get("categories", {})
    categories = []
    seen = set()
    for index, category in enumerate(catalog.get("categories", []), start=1):
        cat_id = category["id"]
        seen.add(cat_id)
        cfg = config_categories.get(cat_id, {})
        categories.append({
            "id": cat_id,
            "index": index,
            "label": cfg.get("label_zh") or category.get("title", cat_id),
            "label_en": category.get("title", cat_id),
            "description": cfg.get("description_zh") or category.get("description", ""),
            "description_en": category.get("description", ""),
            "color_light": cfg.get("color_light", "#0066CC"),
            "color_dark": cfg.get("color_dark", "#6EA8FF"),
            "count": counts.get(cat_id, 0),
        })
    for cat_id, count in counts.items():
        if cat_id in seen:
            continue
        cfg = config_categories.get(cat_id, {})
        categories.append({
            "id": cat_id,
            "index": len(categories) + 1,
            "label": cfg.get("label_zh") or cat_id,
            "label_en": cat_id,
            "description": cfg.get("description_zh", ""),
            "description_en": "",
            "color_light": cfg.get("color_light", "#0066CC"),
            "color_dark": cfg.get("color_dark", "#6EA8FF"),
            "count": count,
        })
    return categories


def build_inventory(config: dict, repo_root: Path, catalog: dict) -> tuple[list[dict], list[str]]:
    categories = {c["id"]: c for c in catalog.get("categories", [])}
    category_index = {
        category["id"]: index
        for index, category in enumerate(catalog.get("categories", []), start=1)
    }
    config_categories = config.get("categories", {})
    featured = set(config.get("featured", []))
    featured_order = {
        skill_id: index for index, skill_id in enumerate(config.get("featured", []))
    }
    exclude_skills = set(config.get("exclude_skills", []))
    private_skills = set(config.get("private_skills", []))
    private_reason = config.get("private_reason", "")

    original_ids: set[str] = set()
    original_path = repo_root / config.get("original_index", "skills/original/index.json")
    if original_path.is_file():
        original_index = load_json(original_path)
        original_ids = {item["skill_id"] for item in original_index.get("skills", [])}

    skills: list[dict] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    for entry in catalog.get("skills", []):
        skill_id = entry.get("skill_id", "").strip()
        if not skill_id:
            warnings.append("catalog entry without skill_id")
            continue
        if skill_id in seen_ids:
            warnings.append(f"duplicate skill_id in catalog: {skill_id}")
            continue
        seen_ids.add(skill_id)
        if skill_id in exclude_skills:
            warnings.append(f"excluded by config: {skill_id}")
            continue

        relative_path = entry.get("path") or f"{config.get('skills_root', 'skills')}/{skill_id}/SKILL.md"
        path = repo_root / relative_path
        if not path.is_file():
            raise SystemExit(f"catalog path missing: {relative_path}")

        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = split_frontmatter(text)

        description = normalize_text(entry.get("description"))
        if not description:
            description = normalize_text(frontmatter.get("description"))
        if not description:
            description = derive_description(body, skill_id)
        description, _, _ = redact_text(description)

        is_private = skill_id in private_skills
        if is_private:
            description = description or f"{skill_id}（内容未公开）"
            headline = skill_id
            content, redactions, privacy = "", 0, 0
        else:
            headline = extract_headline(body, skill_id) or skill_id
            content, redactions, privacy = sanitize_content(body)
        headline, _, _ = redact_text(headline)

        category_id = entry.get("category_id") or "general-utilities"
        category = categories.get(category_id) or {
            "id": "general-utilities",
            "title": "Specialized Domains & Utilities",
            "description": "",
        }
        cfg = config_categories.get(category_id, {})
        category_label = cfg.get("label_zh") or category.get("title", category_id)
        category_label_en = category.get("title", category_id)

        used_by = entry.get("used_by")
        if not used_by:
            used_by = [
                assignment.get("agent")
                for assignment in entry.get("assignments", [])
                if assignment.get("agent")
            ]
        tags: list[str] = []
        for tag in list(used_by or []) + collect_tags(frontmatter):
            tag = normalize_text(tag)
            if tag and tag not in tags:
                tags.append(tag)
        tags = tags[:6]

        provenance = entry.get("provenance") or {}
        origin_kind = provenance.get("origin_kind") or "unknown"
        is_original = skill_id in original_ids or origin_kind == "project-original"
        license_info = provenance.get("license") or {}
        license_spdx = license_info.get("spdx") or normalize_text(frontmatter.get("license"))

        char_count = (
            len(re.findall(r"[一-鿿]", content))
            + len(re.findall(r"[A-Za-z0-9_]+", content))
        ) if content else 0

        skill = {
            "id": skill_id,
            "slug": skill_id,
            "name": skill_id,
            "headline": headline,
            "description": description,
            "summary": make_summary(description),
            "category": category_id,
            "category_label": category_label,
            "category_label_en": category_label_en,
            "category_index": category_index.get(category_id, 0),
            "tags": tags,
            "used_by": list(used_by or []),
            "origin_kind": origin_kind,
            "original": is_original,
            "license": license_spdx,
            "support_level": entry.get("support_level") or "",
            "curation_status": (entry.get("curation") or {}).get("status") or "",
            "path": relative_path,
            "repo_url": f"https://github.com/{config['site']['repo']}/blob/main/{relative_path}",
            "json_url": f"data/skills/{skill_id}.json",
            "url": f"#/skill/{skill_id}",
            "absolute_url": f"{config['site']['pages_url']}#/skill/{skill_id}",
            "featured": skill_id in featured,
            "featured_rank": featured_order.get(skill_id, 999),
            "private": is_private,
            "private_reason": private_reason if is_private else "",
            "content_available": not is_private,
            "char_count": char_count,
            "content": content,
            "_redactions": redactions,
            "_privacy": privacy,
        }
        skills.append(skill)

    catalog_count = catalog.get("inventoryCount")
    if isinstance(catalog_count, int) and catalog_count != len(skills):
        warnings.append(
            f"catalog inventoryCount={catalog_count}, built={len(skills)} "
            "(catalog drift; run the repository skill checks)"
        )

    category_order = {c["id"]: i for i, c in enumerate(catalog.get("categories", []))}
    skills.sort(key=lambda s: (
        category_order.get(s["category"], 99),
        0 if s["featured"] else 1,
        s.get("featured_rank", 999),
        0 if s["original"] else 1,
        s["name"].lower(),
    ))
    return skills, warnings


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_site(config: dict, catalog: dict, skills: list[dict], src: Path,
               out: Path, repo_root: Path, warnings: list[str]) -> dict:
    site = config["site"]
    generated = datetime.now(timezone.utc)
    date = generated.date().isoformat()
    total = len(skills)
    categories = build_categories(config, catalog, skills)
    originals = sum(1 for s in skills if s["original"])
    corpus_bytes = sum(len(s["content"].encode("utf-8")) for s in skills)
    corpus_mb = f"{corpus_bytes / 1024 / 1024:.1f}"

    public_skills = []
    for skill in skills:
        item = {k: v for k, v in skill.items() if not k.startswith("_") and k != "content"}
        public_skills.append(item)

    index = {
        "schema": "agi-skills-atlas/v1",
        "generated_at": generated.isoformat(timespec="seconds"),
        "build_date": date,
        "site": {
            "title": site["title"],
            "subtitle": site["subtitle"],
            "tagline": site["tagline"],
            "description": site["description"],
            "author": site.get("author", ""),
            "repo": site["repo"],
            "repo_url": site["repo_url"],
            "pages_url": site["pages_url"],
            "issue_url": site.get("issue_url", site["repo_url"] + "/issues/new"),
        },
        "stats": {
            "total": total,
            "categories": len(categories),
            "originals": originals,
            "characters": sum(s["char_count"] for s in skills),
            "corpus_bytes": corpus_bytes,
            "corpus_mb": corpus_mb,
            "private": sum(1 for s in skills if s["private"]),
        },
        "categories": categories,
        "skills": public_skills,
    }

    if out.exists():
        resolved = out.resolve()
        if resolved in {Path("/"), repo_root.resolve(), PROJECT_DIR.resolve()}:
            raise SystemExit(f"refusing to remove unsafe output path: {resolved}")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    assets_dir = out / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for name in ("app.js", "styles.css", "theme.js", "guide.js"):
        shutil.copy2(src / name, assets_dir / name)
    for item in (src / "assets").iterdir():
        if item.is_file():
            shutil.copy2(item, assets_dir / item.name)
    for item in (src / "vendor").iterdir():
        if item.is_file():
            shutil.copy2(item, assets_dir / item.name)

    domain_tokens = [":root{--domain-light:#0066CC;--domain-dark:#6EA8FF}"]
    for category in categories:
        domain_tokens.append(
            f'[data-domain="{category["id"]}"]'
            f'{{--domain-light:{category["color_light"]};--domain-dark:{category["color_dark"]}}}'
        )
    (assets_dir / "domain-tokens.css").write_text(
        "\n".join(domain_tokens) + "\n", encoding="utf-8"
    )

    template = (src / "index.html").read_text(encoding="utf-8")
    replacements = {
        "{{TITLE}}": html.escape(site["title"]),
        "{{SUBTITLE}}": html.escape(site["subtitle"]),
        "{{TAGLINE}}": html.escape(site["tagline"]),
        "{{DESCRIPTION}}": html.escape(site["description"]),
        "{{AUTHOR}}": html.escape(site.get("author", "")),
        "{{REPO_URL}}": html.escape(site["repo_url"], quote=True),
        "{{PAGES_URL}}": html.escape(site["pages_url"], quote=True),
        "{{ISSUE_URL}}": html.escape(index["site"]["issue_url"], quote=True),
        "{{GENERATED_DATE}}": date,
        "{{TOTAL}}": str(total),
        "{{CATEGORIES}}": str(len(categories)),
        "{{ORIGINALS}}": str(originals),
        "{{CORPUS_MB}}": corpus_mb,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    (out / "index.html").write_text(template, encoding="utf-8")

    guide_template = (src / "for-agents.html").read_text(encoding="utf-8")
    for token, value in replacements.items():
        guide_template = guide_template.replace(token, value)
    (out / "for-agents.html").write_text(guide_template, encoding="utf-8")

    write_json(out / "data" / "index.json", index)
    for skill in skills:
        payload = {
            "schema": "agi-skills-atlas/skill/v1",
            "generated_at": index["generated_at"],
            "category": skill["category"],
            "category_label": skill["category_label"],
            "content": skill["content"],
            "content_format": "markdown",
            **{
                k: v for k, v in skill.items()
                if k not in {"content", "category", "category_label"} and not k.startswith("_")
            },
        }
        write_json(out / "data" / "skills" / f"{skill['id']}.json", payload)

    write_json(out / "data" / "originals.json", {
        "count": originals,
        "skills": [s["id"] for s in skills if s["original"]],
    })

    lines = [
        f"# {site['title']} · {site['subtitle']}",
        "",
        f"> {site['description']}",
        f"> {total} skills · {len(categories)} categories · {originals} originals · generated {date}.",
        f"> Site: {site['pages_url']}",
        f"> Source: {site['repo_url']}",
        "",
        "## How to use (for agents)",
        "",
        "1. Fetch data/index.json for the metadata index.",
        "2. Shortlist 3-5 skills by id; do not invent ids.",
        "3. Fetch data/skills/<id>.json and read its content field.",
        "4. Use llms-full.txt only when the whole corpus is needed.",
        "",
        "Prompt:",
        f"Read {site['pages_url']}data/index.json, shortlist 3-5 skills for my task,",
        "then read data/skills/<id>.json for those ids. Use only ids that exist.",
        "",
        "## Categories",
        "",
    ]
    for category in categories:
        lines.append(
            f"- {category['label']} ({category['label_en']}): "
            f"{category['count']} skills: {category['description']}"
        )
    lines += ["", "## Skills", ""]
    for category in categories:
        lines.append(f"### {category['label']}")
        lines.append("")
        for skill in (s for s in skills if s["category"] == category["id"]):
            marker = " [original]" if skill["original"] else ""
            one_line = normalize_text(skill["description"])[:320]
            lines.append(
                f"- [{skill['id']}]({site['pages_url']}data/skills/{skill['id']}.json)"
                f"{marker}: {one_line}"
            )
        lines.append("")
    lines += [
        "## Machine-readable",
        "",
        f"- [AI guide]({site['pages_url']}for-agents.html)",
        f"- [Full index]({site['pages_url']}data/index.json)",
        f"- [Full corpus]({site['pages_url']}llms-full.txt)",
        f"- [Originals]({site['pages_url']}data/originals.json)",
        f"- Per-skill JSON: {site['pages_url']}data/skills/<id>.json",
        "",
    ]
    (out / "llms.txt").write_text("\n".join(lines), encoding="utf-8")

    full = [
        f"# {site['title']} · Full Corpus",
        "",
        f"> {site['description']}",
        f"> Generated {date}. {total} skills. Source: {site['repo_url']}",
        "",
    ]
    for skill in skills:
        if skill["private"]:
            continue
        full += [
            "---",
            "",
            f"## {skill['headline']}",
            "",
            f"- id: `{skill['id']}`",
            f"- category: {skill['category_label']} ({skill['category_label_en']})",
            f"- path: `{skill['path']}`",
            f"- original: {'yes' if skill['original'] else 'no'}",
            f"- tags: {', '.join(skill['tags']) if skill['tags'] else '—'}",
            f"- json: {site['pages_url']}data/skills/{skill['id']}.json",
            "",
            skill["content"].strip(),
            "",
        ]
    (out / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")

    sitemap = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in (site["pages_url"], f"{site['pages_url']}for-agents.html"):
        sitemap += [
            "  <url>",
            f"    <loc>{html.escape(page)}</loc>",
            f"    <lastmod>{date}</lastmod>",
            "  </url>",
        ]
    sitemap.append("</urlset>")
    (out / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    (out / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: {site['pages_url']}sitemap.xml\n",
        encoding="utf-8",
    )
    write_json(out / "manifest.webmanifest", {
        "name": f"{site['title']} · {site['subtitle']}",
        "short_name": site["title"],
        "description": site["description"],
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": "#f6f4ef",
        "theme_color": "#08080a",
        "icons": [{
            "src": "assets/favicon.svg",
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any maskable",
        }],
    })

    return {
        "total": total,
        "categories": len(categories),
        "originals": originals,
        "corpus_mb": corpus_mb,
        "date": date,
        "redactions": [(s["id"], s["_redactions"]) for s in skills if s["_redactions"]],
        "privacy": [(s["id"], s["_privacy"]) for s in skills if s["_privacy"]],
        "warnings": warnings,
        "out": str(out),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the AGI Skills Atlas")
    parser.add_argument("--config", type=Path, default=PROJECT_DIR / "atlas.config.json")
    parser.add_argument("--src", type=Path, default=PROJECT_DIR / "src")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    args = parser.parse_args()

    config = load_json(args.config)
    repo_root = args.repo_root.resolve()
    catalog_path = repo_root / config["catalog"]
    if not catalog_path.is_file():
        raise SystemExit(f"catalog not found: {catalog_path}")
    catalog = load_json(catalog_path)

    skills, warnings = build_inventory(config, repo_root, catalog)
    if not skills:
        raise SystemExit("no skills found in the catalog")

    report = build_site(
        config, catalog, skills, args.src.resolve(), args.out.resolve(), repo_root, warnings
    )

    print(f"AGI Skills Atlas built: {report['out']}")
    print(
        f"  skills: {report['total']} · categories: {report['categories']} "
        f"· originals: {report['originals']} · corpus: {report['corpus_mb']} MB"
    )
    print(f"  generated: {report['date']}")
    if report["redactions"]:
        print("  secret-like strings redacted:")
        for skill_id, count in report["redactions"]:
            print(f"    - {skill_id}: {count}")
    else:
        print("  secret scan: no secret-like strings found")
    if report["privacy"]:
        print(f"  local-path/privacy strings normalized in {len(report['privacy'])} skills")
    if report["warnings"]:
        print("  warnings:")
        for warning in report["warnings"]:
            print(f"    - {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
