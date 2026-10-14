# Detectability and account-safety boundaries

## What real-browser Computer Use changes

Visible OS-level or accessibility-driven input can avoid some obvious WebDriver/CDP artifacts associated with Playwright, Selenium, injected scripts, and headless browsers. A normal browser profile also preserves ordinary cookies, extensions, fonts, history, and device continuity.

This is only one detection layer. It does not make automation invisible.

## What platforms can still observe

- account identity, account age, and prior enforcement history;
- IP/ASN, region, network changes, and concurrent sessions;
- browser/device fingerprint and changes across sessions;
- login, navigation, typing, upload, and publishing timing;
- posting frequency, bursts, repeated schedules, and multi-account correlation;
- duplicated media, perceptual hashes, templated text, and repeated metadata;
- content, copyright, commercial, originality, and AI disclosure compliance;
- failed challenges, repeated submissions, and unusual creator-site errors;
- server-side request sequence regardless of how the mouse was moved.

Some accessibility or direct-value operations may also produce an event sequence different from ordinary typing. Do not claim that `isTrusted` input or physical-looking clicks defeat server-side analysis.

## Safe interpretation

Use Computer Use to reduce brittle browser-driver fingerprints and to keep a human in the review loop. Do not use it to promise lower ban rates without measured account cohorts and platform authorization.

## Account-safety controls

1. Use the user's stable, ordinary browser profile and usual network.
2. Keep one active session and one task per account.
3. Publish at low, intentional volume consistent with the account's normal use.
4. Avoid duplicate or mass-produced content across accounts.
5. Stop on warnings, verification requests, throttling, or ambiguous submission state.
6. Let the user complete all security challenges.
7. Prefer drafts, previews, and explicit final review.
8. Use official APIs or authorized partner tools when available.
9. Maintain an audit receipt without storing credentials.
10. Use low-value test accounts for UI validation before important accounts, subject to platform rules.

## Prohibited tactics

Do not provide or execute:

- CAPTCHA or MFA bypass;
- device-fingerprint spoofing;
- proxy rotation intended to evade account linkage;
- fake-human mouse-path generation for detection evasion;
- reverse-engineered signing or private API abuse;
- automated account farming, warm-up, or ban evasion;
- silent repeated clicks after uncertain submission.
