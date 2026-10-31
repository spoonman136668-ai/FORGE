# G90 recovered environment manifest discrepancy — 2026-10-31

The archived `cpu_g90_environment.txt` reports `transformers==4.48.4`, while the benchmark result JSON's runtime metadata reports `transformers==4.48.3`. The workflow source had requested `transformers==4.48.3`. These values are inconsistent across the artifact and are deliberately preserved as an evidence discrepancy rather than normalized or guessed.

The exact archived artifact is authoritative for the original run bytes. Recovered environment text is reproduced in `CPU-G90-GPT2-BATCHED-THROUGHPUT-ENVIRONMENT-20261031.txt`; machine-readable runtime metadata in the result receipt retains 4.48.3; the archive itself remains linked by artifact ID and SHA-256. This discrepancy does not alter the measured output or threshold disposition, but it limits exact environment reproducibility until independently reconciled.
