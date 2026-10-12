# Methodology and evidence handling

## What a row represents
Each row is a candidate public review signal recorded from the supplied desk-research baseline. Some rows are faithful summaries rather than verbatim quotes. The dataset is not a complete review corpus.

## Coding
- Primary theme: the main product question the signal raises.
- Confidence: confidence in the theme classification, not confidence that the problem is widespread.
- Status: whether the source or issue needs further validation.

## Rules
1. Never turn these rows into a percentage of all users.
2. Do not claim a technical cause from a review alone.
3. Re-check the exact source before quoting a review verbatim.
4. Deduplicate reviews visible across different localized listings.
5. Keep source date, locale and URL.
6. Validate candidate issues against internal telemetry and operational records before prioritising implementation.

## What internal evidence would help
- Booking funnel and retries
- Last location update age and ETA error
- Notification delivery and latency
- No-show event timeline and dispute outcomes
- Support-ticket themes
- App version, device and network context where available and appropriate
