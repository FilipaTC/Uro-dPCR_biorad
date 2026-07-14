# Uro-dPCR_biorad
Shiny (Python) app for analyzing QX200 digital PCR exports (TERT-124, TERT-146, FGFR3-248, FGFR3-249, FGFR3-372, FGFR3-375 — 7 single-plex reactions, 6 mutations).

# Files
run_app.py — entry point (run with python run_app.py, or shiny run app/app.py for local dev with autoreload).
app/analysis_pipeline.py — Step 1: the business logic. NTC/NC normalization, validation thresholds, own Fractional Abundance calculation, and Positive/Negative/Inconclusive classification. Writes the detailed intermediate Excel file.
app/final_results.py / app/summary_pipeline.py — Step 2: aggregates one or more detailed analysis files into a simplified, color-coded, wide-format summary (one row per sample) plus a full-detail export.
app/app.py — the Shiny UI/server tying the three steps together.

# Business rules implemented
NTC/NC normalization: per assay/target, within the same run (source file), Positives are normalized against the well named NTC; if no NTC well exists, the NC well is used as a fallback instead. The subtraction is floored at 0 and applied to both the mutant and the IC target. All downstream thresholds and the Fractional Abundance use these normalized values.
Validation: a sample/assay is only "valid" if Accepted Events (Total) ≥ 10,000 and normalized IC Positives ≥ 10.
If the IC itself is missing (e.g. no matching FGFR3-IC well was provided) → Inconclusive.
If IC Positives < 10 → Inconclusive.
If only the 10,000-event threshold fails (IC otherwise valid) → Positive (<10k droplets) / Negative (<10k droplets).
Fractional Abundance: FA = mut_positives_norm / (mut_positives_norm + ic_positives_norm) * 100, only computed when the denominator > 0.
Positive call: normalized mutant Positives ≥ 5 and FA ≥ 0.5%; otherwise Negative (within the validated population).
Control wells (PC, NC, NTC) are excluded from every output report.
Intermediate (Step 1) output columns
Source_File, Sample description 1, Assay, Target, Conc (copies/µL), Accepted Droplets, Positives, Fractional Abundance (Original), Accepted_Droplets_10000, Positive_Droplets_OK, Merged Fractional Abundance (calculated by the system), Fractional_Abundance_OK, Result
