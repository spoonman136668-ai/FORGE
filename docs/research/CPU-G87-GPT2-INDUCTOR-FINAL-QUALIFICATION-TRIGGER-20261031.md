# G87 archived measurement receipt and final qualification — 2026-10-31

The original model run completed successfully on source SHA `5f368cc9775e49ca2f61ccc828bb7ba879f91a9b`, workflow #41214799091, artifact #13047314884. The ZIP artifact was recovered and independently inspected. Its ZIP SHA-256 is `f13ef344acffe59d0d784ac8062b50e7c6767c0c5dc2cdb68bf4b99bb0fb8523`; original result JSON SHA-256 is `40f29c9d6b11f72a09222fac7e3b74074a864315db546f93d26f3be3f70de06d`.

Durable compact result receipt: `CPU-G87-GPT2-INDUCTOR-ARTIFACT-RECEIPT-20261031.json`; pinned runtime and host manifest: `CPU-G87-GPT2-INDUCTOR-ENVIRONMENT-20261031.txt`.

Frozen result remains **engineering PASS, correctness PASS, INDUCTOR_NO_GO**. The original GPT-2 produced 96 exact responses/768 tokens. Three Inductor graphs compiled with zero graph breaks. Median warm speedup was 1.087657×; compile startup 90.910516 s; break-even 1,328 requests; 1,000-request amortized wall ratio 1.026416×. No thresholds or source changed.

This workflow performs receipt, source, isolation, F139 custody and full Go/Linux+Windows qualification only. It does not rerun or reinterpret the original benchmark, alter any model, or authorize acceptance/promotion.
