---
name: real-browser-social-publisher
description: Safely prepare, review, and publish video or image posts through real creator-site browser interfaces using Computer Use with human approval gates. Use for Douyin, Xiaohongshu, Kuaishou, WeChat Channels, Bilibili, YouTube, TikTok, or Baijiahao when the user requests browser-based login, upload, metadata entry, scheduling, draft saving, publishing, or post-publication verification and wants to reduce accidental account-risk without bypassing platform security.
---

# Real Browser Social Publisher

Operate the platform's visible creator interface with a stable real browser session. Optimize for correct, policy-compliant, low-volume publishing—not undetectability.

## Route the request

1. Identify the platform and content mode.
2. Read [common-workflow.md](references/common-workflow.md) and [detection-and-safety.md](references/detection-and-safety.md).
3. Read only the matching platform reference:

- Douyin: [douyin.md](references/douyin.md)
- Xiaohongshu: [xiaohongshu.md](references/xiaohongshu.md)
- Kuaishou: [kuaishou.md](references/kuaishou.md)
- WeChat Channels: [wechat-channels.md](references/wechat-channels.md)
- Bilibili: [bilibili.md](references/bilibili.md)
- YouTube: [youtube.md](references/youtube.md)
- TikTok or Baijiahao: [legacy-platforms.md](references/legacy-platforms.md)

Treat labels and page order as landmarks, not permanent selectors. Stop when the live UI conflicts materially with the reference.

## Require a publish brief

Resolve before opening the creator page:

- platform, account, and intended destination;
- video or image post;
- asset paths and cover;
- title, body/description, tags, and playlist/collection;
- immediate, scheduled, draft, private, unlisted, or public;
- audience/child-directed setting where applicable;
- commercial relationship, product link, originality, AI/synthetic-content, or other required disclosure;
- whether the user authorizes the final publish action.

Never infer originality, commercial claims, content declarations, audience classification, or legal acknowledgements. Ask the user when these affect the result.

## Choose the safest channel

Prefer, in order:

1. an official publishing API or officially authorized integration;
2. the platform's normal creator interface in a stable user-owned browser profile;
3. visible Computer Use for repetitive UI work with human review.

Do not introduce fingerprint spoofing, proxy rotation, CAPTCHA solvers, reverse-engineered request signing, hidden JavaScript injection, or automation intended to evade platform enforcement.

## Operate with Computer Use

When `computer-use` is available:

1. Inspect the browser with `get_app_state` before each decision.
2. Prefer accessibility element actions. Use coordinate clicks only when the accessibility tree is insufficient.
3. Fetch a fresh app state after every navigation, dialog, upload, or tab change. Never reuse stale element indexes.
4. Use visible text entry and verify the rendered value, character count, selected tags, cover, audience, schedule, and disclosure state.
5. Keep one account and one publishing task active at a time.
6. Stop for the user to complete passwords, MFA, QR confirmation, CAPTCHA, security warnings, or unexpected permission requests.
7. Save a draft when available. Otherwise stop on the final review screen.
8. Immediately before the final external publish/submit action, show the exact destination, title, visibility/schedule, disclosures, and assets. Obtain confirmation unless the current request already gives sufficiently specific authorization and the action is low-impact; still stop for any unexpected commitment or high-impact content.
9. Click the final publish control once. Do not retry blindly after a timeout.
10. Verify through the platform's content-management page or returned content URL.

## Handle uncertain submission state

If the final click does not produce a clear success result:

1. Record the current URL, visible status, and screenshot.
2. Do not click publish again.
3. Open the content-management page in the same account.
4. Search for the title, upload time, draft, scheduled item, or processing state.
5. Return `published`, `scheduled`, `draft`, `not-found`, or `unknown` with evidence.

## Stop conditions

Stop without publishing when:

- login or account identity is ambiguous;
- a security challenge or account warning appears;
- the UI requests a declaration the user did not authorize;
- content, cover, visibility, audience, or schedule differs from the brief;
- upload/processing status is unclear;
- the same account is already being operated elsewhere;
- the platform warns about posting frequency, policy, or account restrictions;
- the content-management page cannot distinguish a failed submission from a delayed one.

## Return a publication receipt

Report:

```yaml
platform:
account_label:
content_mode:
title:
visibility_or_schedule:
result: published|scheduled|draft|not-found|unknown|blocked
content_url_or_id:
verified_on_management_page: true|false
disclosures_confirmed:
security_challenges:
evidence:
remaining_risks:
```

Never describe Computer Use or a real browser as undetectable. State that it reduces some browser-automation markers while server-side and behavioral detection remain possible.
