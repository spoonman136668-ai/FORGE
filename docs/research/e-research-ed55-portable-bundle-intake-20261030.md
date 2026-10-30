# E-D55 custody intake — local portable replay bundle

Bundle SHA-256: `bc41619ac869348d0895adb59f53a73445196556872ac179f72c2c54a5cd192a`

The local bundle was inspected and its SHA-256 matched the earlier recorded digest. Archive members include the original E-C2 source, original E-D52 source, original JSON results, a portable script, replay logs and manifest. The archive also contains a generated `__pycache__` file; this is incidental and not experimental source.

Original SHA-256 identities:
- E-C2 `run_ec2.py`: `1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154`
- E-D52 `run_ed52.py`: `d55a1041ca0a7e780b702d588da1387851e73110e3dece41345c21d06b73a13d`
- E-D52 `results.json`: `9c8546feb4e0e7998cf76321bdd5f5f771760d58682070e1d1f3c70c5ce93ca7`

Canonical replay-invariant digest, excluding elapsed runtime: `e6db25c13a0b50bfd4e33b5e996872501bf191ef8ced03f0438615915e0d8883`. Recorded 108 trajectories.

**Custody NOT complete:** this is a receipt for a *session-local archive* and does not attest that the archive bytes, source bytes, or result bytes have been pushed to this repository. A source-upload action attempted during E-D55 was blocked. Do not treat this manifest as authenticated original evidence, independent witness validation, or scientific first-use.

To close: upload the archive or exact original source/results through an authorized binary repository upload path, read back the bytes and independently verify the hashes. Keep PR #1194 draft pending normal review. No FORGE controller/autonomy changes.
