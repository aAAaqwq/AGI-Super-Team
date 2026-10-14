# Douyin creator workflow

Source model: `creator.douyin.com`, video and image-post flows in social-auto-upload commit `008e4ff`.

## Login

1. Open Douyin Creator Center.
2. Confirm the account avatar/name.
3. Let the user scan the QR code or complete any phone/device verification.
4. Navigate to content upload.

## Video

1. Select video publishing and choose one video file.
2. Wait until the editor appears and upload status is complete.
3. Fill title and description; verify both separately in the live UI.
4. Add topics/tags through visible suggestions.
5. Add a product link and product title only when explicitly supplied and permitted for the account.
6. Set the requested portrait/landscape cover; verify the selected crop.
7. Set a self/content declaration only from the user's exact choice.
8. Review any third-party-content or authorization switch instead of accepting it automatically.
9. Choose immediate or scheduled publishing and verify exact date, time, and timezone.
10. Stop at the final review. Confirm account, media, cover, title, description, tags, product, declaration, and schedule.
11. Click Publish once.
12. If SMS verification appears, let the user request and enter the code.
13. Verify the item on content management and distinguish published, processing, reviewing, and scheduled states.

## Image post

1. Choose `发布图文` before uploading.
2. Upload images in the intended order. The audited code validates at most 35 images, title at most 20 characters, and body at most 1000 characters; the live UI is authoritative.
3. Wait for the image editor.
4. Fill and re-read title and body.
5. Add tags and optional BGM.
6. Set the requested schedule.
7. Review, publish once, and verify on content management.

## Risk stops

- SMS/security challenge;
- unexplained content-declaration prompt;
- product-link authorization mismatch;
- upload page loops or returns to login;
- management page does not show an unambiguous result.
