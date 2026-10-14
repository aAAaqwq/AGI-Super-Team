# Kuaishou creator workflow

Source model: `cp.kuaishou.com`, video and image-post flows in social-auto-upload commit `008e4ff`.

## Login

1. Open the Kuaishou Creator Platform.
2. Confirm the account and let the user scan the login QR code.
3. Open the publish page and dismiss onboarding overlays only after reading them.

## Video

1. Choose video upload and select the file once.
2. Wait until `上传中` disappears and no upload error is visible.
3. Fill description/title according to the live form.
4. Add topics. The audited implementation only adds the first three; do not assume this is the platform limit.
5. Set and verify the cover/crop.
6. Choose immediate or scheduled publishing and verify the exact time.
7. Stop at review and compare every field with the brief.
8. Click Publish once; if a separate Confirm Publish dialog appears, treat it as the same authorized submission.
9. Verify on the content-management page.

## Image post

1. Switch to the image-post tab.
2. Upload images in the intended order.
3. Dismiss any guide overlay after inspecting it.
4. Fill the image-post body and the title if the live form exposes a separate field.
5. Add topics and wait for asset processing to finish.
6. Set schedule if requested.
7. Review, publish once, confirm once if prompted, and verify on content management.

## Risk stops

- upload status remains ambiguous after the expected processing window;
- the UI lacks a title field expected by the brief;
- the confirm dialog changes visibility, declarations, or destination;
- account/session verification appears.
