# Bilibili creator workflow

The audited project delegates Bilibili to the external `biliup` binary. The visible-browser flow below maps the same metadata into Bilibili Creator Center; exact live UI remains authoritative.

## Login

1. Open Bilibili Creator Center in the user's normal browser.
2. Let the user complete QR/password/MFA login.
3. Confirm the channel identity and open video submission.

## Video

1. Upload the video file once and wait for processing.
2. Fill the title and description.
3. Select the correct category/partition. The source CLI requires a numeric `tid`; in the browser verify the human-readable category.
4. Add tags.
5. Upload and confirm the cover.
6. Review type/source/copyright/originality fields and set them only from user-supplied facts.
7. Choose immediate or scheduled publication and confirm timezone.
8. Review the complete submission.
9. Submit once.
10. Verify the item in submission management and report whether it is processing, under review, scheduled, rejected, or published.

## Safety notes

- Do not download or execute `biliup` when the requested mode is real-browser Computer Use.
- Do not infer category, copyright source, or originality.
- Bilibili review acceptance is not the same as upload completion.
