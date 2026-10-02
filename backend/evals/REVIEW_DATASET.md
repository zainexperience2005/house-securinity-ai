# Review Evaluation Dataset

Use `review_case_template.json` as the contract for every manually labeled submission package. Keep the source PDFs outside Git if they contain client material; record their secure storage reference in your evaluation runner.

For each case, label the final outcome, document presence, the important checklist checks, and every numeric value used in a bylaw decision. Each label must include the source page and a short evidence excerpt in the case notes or companion annotation file.

Build a balanced regression set before treating an accuracy number as a release gate: approved packages, missing documents, correction-required drawings, ambiguous scans, conflicting revisions, and adversarial or irrelevant text. Keep a held-out set for release checks and never update expected labels from the model output.

Run the dataset against a pinned model/configuration and compare the result with these rules:

- Outcome and document-type labels must match exactly.
- A PASS or CORRECTION_REQUIRED result must cite the correct source page.
- Numeric values must match within a documented tolerance and use the expected unit.
- Any unexpected PASS is a release-blocking false approval and requires engineer review.

The included template is intentionally not a scored benchmark. Add real, engineer-reviewed cases before publishing accuracy, latency, or cost claims.
