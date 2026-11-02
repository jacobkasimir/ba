# Evaluation Status

The repository does not yet contain an evaluation runner, evaluation dataset,
frozen question set, or reference outputs. The existing synthetic data is a
20-row connectivity fixture and must not be described as the final synthetic
AKTIN/i2b2 evaluation data.

Decision D-012 accepts the System Usability Scale (SUS) as the usability
measure. Decisions D-013 through D-015 leave the suppression threshold, data
and concept source, and LLM provider/model unresolved. No evaluation results
or participant procedures are evidenced by the implementation.

The MCP development example is marked `development_only`; it contains a
question and the supported count SQL but no expected result. MCP tests check
that examples omit expected-result fields and match the constraints metadata.
These are context/unit tests, not an evaluation of query quality or usability.

Before an evaluation can be documented as implemented, the repository needs
evidence for the approved synthetic dataset and generation method, evaluation
questions and scoring/reference method, model/provider and settings if used,
the agreed suppression policy, and the actual evaluation procedure. Do not
include real patient data or secrets in evaluation documentation.
