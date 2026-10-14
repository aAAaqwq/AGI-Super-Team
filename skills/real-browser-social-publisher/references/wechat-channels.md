# WeChat Channels workflow

Source model: `channels.weixin.qq.com`, video flow in social-auto-upload commit `008e4ff`.

## Login

1. Open the Channels Assistant/creator site.
2. Let the user scan and confirm login in WeChat.
3. Confirm the exact Channels identity; a WeChat user may control multiple destinations.
4. Open `发表视频` or the create-post page.

## Video

1. Upload the video and wait until the Publish button is enabled and no upload error is shown.
2. Fill title, tags, and description; verify line breaks and tag conversion.
3. Fill the short title only when requested.
4. Add to a collection only when the user named the collection. Never select the first collection automatically.
5. Set portrait/landscape covers when the UI requests them and verify each crop.
6. Set originality only when factually correct. Let the user read and accept any originality terms.
7. Set the content declaration from user-supplied facts; do not default silently to `无需声明`.
8. For scheduling, select the date and enter both hour and minute in the live UI. The audited code only entered the hour, so manual verification is mandatory.
9. Choose Save Draft or Publish according to the brief.
10. Stop for final review, then click once.
11. Verify the draft, scheduled item, or published post on the post list.

## Image posts

The audited current CLI does not expose a completed Channels image-post workflow. If the live creator UI offers one, treat it as an unverified UI path: inspect each step, prefer draft, and require explicit review. Do not claim source-backed support.

## Risk stops

- destination Channels identity is unclear;
- originality terms or content declarations are not user-confirmed;
- collection was not specified;
- schedule minute/timezone is ambiguous;
- QR login or account permission changes unexpectedly.
