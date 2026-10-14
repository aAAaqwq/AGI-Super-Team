# Common browser publishing workflow

## 1. Preflight

1. Confirm the active platform and account identity.
2. Validate that every local asset exists and opens correctly.
3. Check orientation, duration, resolution, cover aspect ratio, and file size against the live uploader.
4. Prepare the exact title, body, tags, cover, visibility, schedule, and declarations.
5. Confirm the schedule timezone and whether the platform treats the time as local browser time.
6. Keep only one task active for an account.

## 2. Login and session check

1. Open the official creator site in the user's normal browser profile.
2. Check the displayed avatar/account/channel before uploading.
3. Let the user complete password, QR, MFA, CAPTCHA, or device confirmation.
4. Stop if the site reports unusual login, account restriction, or identity mismatch.

Do not export or print cookies. Do not copy authentication state into the skill directory.

## 3. Upload and edit

1. Enter the platform's create/upload page.
2. Select video or image-post mode before choosing files.
3. Upload assets once.
4. Wait for a visible editor and a clear upload/processing-complete state.
5. Fill the title and body; re-read the rendered values.
6. Add topics/tags through the platform's suggestion UI when required.
7. Set cover, playlist/collection, audience, visibility, location, product link, or other optional metadata only when present in the brief.
8. Set originality, commercial, AI/synthetic-content, copyright, or source declarations only from user-supplied facts.

## 4. Review gate

Before submitting, compare the live page with the brief:

- correct account;
- correct media and order;
- title/body/tags not truncated unexpectedly;
- correct cover;
- correct visibility or exact schedule/timezone;
- correct audience and declarations;
- no error, policy warning, security challenge, or unfinished upload.

Prefer saving a draft. Present discrepancies to the user instead of silently correcting consequential fields.

## 5. Submit once

1. Obtain the required final authorization.
2. Click the final publish/schedule/save-draft control once.
3. Wait for success, management-page navigation, or a processing state.
4. Never repeat the click solely because navigation is slow.

## 6. Verify

1. Open the platform's content-management page.
2. Match account, title, timestamp, status, and content type.
3. Capture the content URL/ID when available.
4. Treat `processing`, `under review`, `scheduled`, and `draft` as distinct from `published`.
5. If absent, return `unknown` or `not-found`; do not resubmit automatically.

## 7. Recover safely

- Upload failure: keep the page open, record the error, and ask before re-uploading.
- Session expiration: stop and let the user re-authenticate.
- CAPTCHA/security challenge: hand off to the user.
- Page redesign: inspect fresh UI; do not guess old coordinates.
- Duplicate possibility: check the management page before any new submission.
