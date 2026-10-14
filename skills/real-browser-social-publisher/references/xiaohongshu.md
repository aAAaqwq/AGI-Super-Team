# Xiaohongshu creator workflow

Source model: `creator.xiaohongshu.com`, current browser uploader in social-auto-upload commit `008e4ff`.

## Login

1. Open Xiaohongshu Creator Center.
2. Confirm the creator account.
3. Let the user scan the creator-login QR code with the Xiaohongshu app.
4. Stop on CAPTCHA, unusual-login warnings, or a creator/account mismatch.

## Video note

1. Open Publish and choose video mode.
2. Upload one video.
3. Wait for both the editable title field and a clear completed/processed preview; do not rely on the title field alone.
4. Fill the title. The audited implementation truncates to 20 characters; confirm the live limit.
5. Fill the body/description.
6. Add topics one at a time and select the visible suggestion. Do not leave an unmatched raw tag accidentally in the body.
7. Upload and confirm the video cover when supplied.
8. Set originality only if the user owns the rights and explicitly authorizes the declaration.
9. Set immediate or scheduled publishing; verify local date/time.
10. Review account, title, body, topics, cover, declarations, and schedule.
11. Click Publish or Scheduled Publish once.
12. Wait for a success/processing result, then verify on the creator content-management page.

## Image note

1. Choose image mode before selecting files.
2. Upload images in the intended order.
3. Wait until the title/body editor is visible and thumbnails have finished processing.
4. Fill title and body.
5. Add up to the live platform limit of topics; the audited code caps at 10.
6. Confirm any originality or commercial disclosure.
7. Set immediate or scheduled publishing.
8. Review, submit once, and verify in content management.

## Xiaohongshu-specific safety

- Treat unofficial creator automation as carrying significant platform-agreement risk until the user confirms current authorization.
- Prefer the official sharing/open-platform route when it satisfies the use case.
- Keep the normal account/browser/network stable and operate at low, intentional volume.
- Never retry the publish button blindly. The audited code used an unbounded loop; this skill intentionally replaces it with one submit plus management-page verification.
- Stop immediately on verification, throttling, account restriction, or unexplained redirect.
