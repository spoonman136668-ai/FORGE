# F139 G30 — signed V2 development seam, no live activation

Protected FORGE V1 baseline b2079282fed03df2203807de09b4f3e82bdfe05a
retains the only live workflow CLI: f139.nci04_worker_entry execute.

G30 adds execute_v2_development() as a separately callable Python
development API, not a CLI verb, scheduler, runner or controller. It accepts
an original authenticated NativeAdmission object (caller is responsible for
independent actual signer verification); checks exact pinned G13 Yggdrasil
original source and tree, supported OS, credential isolation and a fresh
output path; executes existing frozen run_v2() and validates receipt_v2().

V2 writes only f139-v2-development-receipt.json and
f139-v2-development-report.json. The V1 f139-receipt.json, provider receipt
parser and original owner ledger are unchanged; V2 cannot silently replace
or relabel a historical negative. Existing V2 original source integrity,
clean full ancestry, exhaustive per-OS behavioral inventory, explicit
Windows POSIX-only exclusion and frozen test counts remain mandatory.

G30 tests exercise positive and negative receipt semantics, source/signature
binding failure, no output after invalid evidence, no overwrite, no signing
secret inheritance, and absence of any live execute-v2 CLI.

This is a nondeployable integration boundary. The existing signed V1
candidate intent does NOT authorize choosing V2 semantics at production
runtime. Next gate requires separately version-bound original-owner
signature, durable provider V2 receipt admission/terminal custody, full
Linux/Windows regression, guarded owner source migration, and new original
nonconsumed ITD-02 candidate. Do not replay #907, reset the G3 attempt,
enable science, add a scheduler/controller/queue, or use paid API.
