# YouTube Studio workflow

Source model: YouTube Studio upload flow in social-auto-upload commit `008e4ff`.

## Login

1. Open YouTube Studio in the user's normal Chrome profile.
2. Let the user complete Google login, MFA, and channel selection.
3. Confirm the active channel before uploading.

## Video

1. Choose Create/Upload videos and select the file once.
2. Wait for the Details dialog.
3. Fill title and description.
4. Upload a custom thumbnail when supplied.
5. Add to an existing playlist or create one only when explicitly requested.
6. Select the audience setting. Never infer whether content is made for children.
7. Open additional details and add tags when requested.
8. Progress through checks and visibility steps while reading warnings.
9. Select Public, Unlisted, or Private exactly as requested.
10. The audited source does not implement scheduling. If Schedule is requested, use the live Studio option only after confirming date, time, and timezone with the user.
11. Wait until upload and processing have reached a state where Studio allows saving/publishing.
12. Stop at final review and confirm the channel, title, thumbnail, playlist, audience, checks, visibility, and schedule.
13. Click Save/Publish once.
14. Capture the video URL and verify its visibility/status in Studio Content.

## Risk stops

- channel identity is ambiguous;
- copyright/checks warning appears;
- audience classification is missing;
- upload is incomplete;
- visibility or schedule differs from the brief;
- repetitive or mass-produced content may conflict with YouTube spam policies.
