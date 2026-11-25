# Lettrust — Agent Instructions

## 1. Project Baseline

Lettrust is an academic prototype (II3120 LaSTI, ITB, Kelompok 04, Deliverable 3): an independent offer-letter verification and recruitment-fraud risk analysis service integrated into a simulated job portal through a REST API. It is not a job portal.

Fixed baseline — do not redesign:

- `apps/issuer-console` (Next.js, TS): Lettrust Console for HR and Admin.
- `apps/partner-portal` (Next.js, TS): simulated job portal for applicants (no login); its server route is the only API-07 client and holds the partner token.
- `services/backend` (Python 3.12, FastAPI, SQLite/SQLAlchemy): modular monolith exposing `/api/v1/*`; the only writer to the blockchain registry and the only caller of the AI service.
- `services/ai-service` (FastAPI): PDF text extraction, Tesseract OCR (`ind+eng`, CPU), and risk analysis with a pre-trained LLM via an OpenAI-compatible free-tier API. No training, no fine-tuning, no GPU.
- `blockchain/` (Solidity, Foundry) and `chain` (Anvil, persistent state): `OfferProofRegistry`, single registrar signer, off-chain issuer authorization.
- Local deployment only, through Docker Compose and `python scripts/dev.py`. All data is synthetic.

Demo and test scenarios must use the real Anvil registry and the real LLM. Mocks are for tests only (`docs/MOCKS.md`).

## 2. Documentation and Context Efficiency

| Reference | Purpose |
|---|---|
| `docs/prd/` | Product requirements. Ch. 1 = conventions and ID scheme; Ch. 6 = detailed FR and acceptance criteria; Ch. 8 = business rules and result semantics; Ch. 9 = UI labels, states, guidance rules; Ch. 12 = scenarios (SCN) and evidence rules. |
| `docs/SYSTEM_ARCHITECTURE.md` | Technical baseline: components, ownership (§4.1, §13.1), API contracts (§10), orchestration (§5), blockchain (§6), AI (§7), auth (§8), data (§9), config (§14), deployment (§15), testing (§18), decisions AD/TOI (§19). |
| `docs/PLAN.md` | Tasks: shared `TB-xx` and individual `T<PIC>-xx` (e.g. `T3-02` = second task of PIC 3), with files, references, dependencies, deadlines, done criteria, and verification commands. |
| `docs/MOCKS.md` | Shared mocks, fakes, contract examples, conformance suites, and how to inject them in tests. |
| `docs/SCAFFOLD_REPORT.md` | Scaffold state, versions, and recorded deviations from SYSTEM_ARCHITECTURE (§6). |
| `contracts/openapi.json`, `contracts/examples/` | Frozen API contract and example responses (`examples/index.json` maps examples to schemas). Source of truth for frontend types and fixtures. |
| `docs/testing/` | Test cases (`TC-xxx`) and evidence. |
| `docs/evaluation/` | AI evaluation protocol and report. |
| `README.md` | Actual setup and commands. |

- On first onboarding, read PRD Ch. 1–3, the PRD sections for your task, and the SYSTEM_ARCHITECTURE sections for the module you touch. Inspect the repository before implementing. Do not start from assumptions.
- After that, read only what the task needs: locate headings (e.g. `### FR-03.11`, `## 10.7`) instead of loading whole files again.
- There is no shared progress file. Determine current state from the task given by the human, the code, tests, and read-only git output (`git status`, `git diff`, `git log`). Do not assume a new session remembers earlier decisions.
- If code, contract, and documents disagree materially, do not silently pick one. State the conflict and ask; continue with unaffected work when safe.
- Where `docs/SCAFFOLD_REPORT.md` §6 records a deviation from `docs/SYSTEM_ARCHITECTURE.md`, the recorded deviation is authoritative. Do not revert code to the SA text in those places.

## 3. Ownership and Scope

Each team member works on their own module. Ownership is defined in SYSTEM_ARCHITECTURE §4.1 and PLAN.md.

- Modify only files inside the module of the member you are working for, unless the human explicitly instructs otherwise.
- Shared files — `contracts/`, `compose.yaml`, `compose.dev.yaml`, `.env.example`, `scripts/dev.py`, `services/backend/app/core/`, `services/backend/app/main.py` — change only when explicitly instructed. Contract changes belong to the Technical Lead (Dws).
- Mocks, fakes, and conformance suites belong to Dws: `services/backend/app/modules/registry/mock.py`, `services/ai-service/app/analysis/mock_provider.py`, `services/backend/tests/fakes/`, `services/backend/tests/conformance/`. Do not edit them for another member; if a mock looks wrong, report it under "Perlu koordinasi".
- Never hand-edit generated files: `contracts/openapi.json`, `apps/*/src/lib/api/schema.d.ts`, `apps/*/src/fixtures/api/`, `services/backend/app/modules/registry/abi/`. `services/*/constraints.txt` is regenerated only with `python scripts/dev.py lock <svc>` when that service's requirements change, and only for its owner.
- If the task needs a change outside the owned module, do not make it. Describe the exact change needed and who owns it, so the human can coordinate.
- Do not expand scope, add features, or change product behavior beyond the PRD. Do not close Open Issues (OI) or Technical Open Issues (TOI) on assumption.

## 4. Git and External Actions

All git operations are done by humans.

- Never run `git add`, `commit`, `push`, `pull`, `merge`, `rebase`, `checkout`, `switch`, `branch`, `reset`, `stash`, `tag`, or `cherry-pick`, and never create pull requests. Read-only `git status`, `git diff`, and `git log` are allowed.
- Do not modify `.git/`, git hooks, or repository settings.
- Ask before destructive actions (deleting files outside your change, `dev.py reset`, removing Docker volumes), installing system packages, or anything that uses another person's account or key.

## 5. Development Workflow

1. Understand the task, the relevant FR/acceptance criteria, business rules, and the module's architecture section.
2. Identify the smallest complete change consistent with the architecture. Plan briefly only for complex or risky changes.
3. Reuse existing code. Avoid new abstractions, dependencies, refactors outside the task, and speculative features.
4. Implement including validation, error states, authorization, and tests.
5. Run the relevant checks with the project's real commands (§9). Run broader checks when shared contracts, auth, or orchestration are affected.
6. Fix failures within scope. Do not weaken or delete tests to make them pass.
7. Report as described in §11.

Do not ask for approval for routine steps. Ask before scope changes, contract changes, destructive actions, or anything listed in §4.

### Executing a PLAN task

When the human says "kerjakan <ID>" (e.g. "kerjakan T3-02"):

1. Find the row in `docs/PLAN.md`. If the ID does not exist or the task belongs to a different PIC than the member you work for, stop and ask.
2. Check each dependency. A dependency is available when its code is merged (read-only `git log`, file header `Status: COMPLETE`). If it is not available, implement against the real interface anyway and test with the shared mocks in `docs/MOCKS.md`; add one comment line at the call site, e.g. `# Bergantung pada T6-02; diuji dengan MockRegistryAdapter`. Never write placeholder success logic. If no mock covers the dependency and the task cannot proceed, stop and report.
3. Read the references in the row (FR/BR/SA sections) and the listed files before editing.
4. Edit only the files listed in the row, plus tests for them and small helpers in the same folders (name them in the report). If another file must change, do not change it; report it under "Perlu koordinasi".
5. Implement until every "Selesai bila" criterion is met. For each file that is fully implemented, change its header from `Status: STUB` to `Status: COMPLETE` and remove its `TODO` lines.
6. Run the row's verification commands and `python scripts/dev.py test <svc>` for affected services.
7. Report as in §11, starting with the task ID and each done criterion marked met or not met.
8. Do not start the next task. The human will say "kerjakan <next ID>".

## 6. API Contract Rules

- Request/response shapes, field names (camelCase), enums, and error codes follow SYSTEM_ARCHITECTURE §10 and `contracts/openapi.json`. Do not rename or remove D2 fields; D3 additions are additive only.
- If a backend schema change is instructed, regenerate the contract with `python scripts/dev.py openapi`, update `contracts/examples/` if affected, and state the change clearly in the report.
- Frontend types and fixtures are generated by `python scripts/dev.py openapi` (`src/lib/api/schema.d.ts`, `src/fixtures/api/`). Never hand-edit generated files.
- Never invent endpoints. Supporting endpoints are only those listed in SYSTEM_ARCHITECTURE §10.4.

## 7. Product Invariants (Never Break)

- Verification returns three separate components — `proofCheck`, `integrityCheck`, `riskAnalysis` — and no combined verdict. UI never shows "asli/palsu", "aman/penipuan", or similar.
- Registry failure is `UNAVAILABLE`, never `NOT_FOUND`. AI failure is `UNAVAILABLE` with a reason, never a category.
- A check that did not run is `NOT_REQUESTED` / `NOT_CHECKED` / `NOT_PERFORMED` with a reason; never show FOUND, NOT_FOUND, ACTIVE, REVOKED, MATCH, MISMATCH, or a category for it.
- AI-only mode (no reference code) never calls the registry and never does reverse hash lookup.
- `documentHash` = SHA-256 of the raw file bytes; never hash extracted or OCR text.
- ACTIVE/REVOKED and success responses only after the transaction receipt is confirmed. Status and hash shown to applicants are read from the registry, not from the database mirror.
- No document content, reference code, revocation reason, or personal data on-chain. No reactivation of REVOKED proofs.
- Issuance/revocation only by an AUTHORIZED HR of a VERIFIED issuer; issuer and role come from the server, never from client input.
- Partner token stays server-side in the portal; internal endpoints require the internal token; secrets never reach a browser.
- AI: closed taxonomy (PRD §8.4), every indicator needs an evidence quote found in the document, category from the scoring rules (PRD §8.5), recommendation from templates, document text treated as untrusted data. No silent fallback to another provider, mock, or baseline. Never hardcode results for specific fixtures.
- UI copy, labels, and guidance follow PRD §9.6–§9.8 in Indonesian.

## 8. Code Quality and Comments

- Every new or modified handwritten function, method, class, component, and contract function has a concise Indonesian comment or docstring stating its purpose, plus important constraints when useful for review or debugging. Identifiers stay in English.
- No decorative separators or banners (`=====`, `-----`), no line-by-line narration, no comments restating obvious code. Update comments when behavior changes. Do not add comments to generated files.
- Use clear names, types (TypeScript `strict`, Python type hints), input validation, and explicit error handling. No broad catches that hide failures; no silent fallbacks.
- Formatting: `ruff` (Python), project ESLint/Prettier (TS), `forge fmt` (Solidity).

```python
# Menghitung SHA-256 atas byte berkas asli untuk pemeriksaan integritas.
def compute_document_hash(file_bytes: bytes) -> str:
    ...
```

```typescript
// Menyusun panduan tindak lanjut dari kombinasi status hasil verifikasi.
export function buildGuidance(result: VerificationResponse): GuidanceItem[] {
  ...
}
```

```solidity
/// Mencatat bukti penerbitan baru; menolak proofId yang sudah ada.
function issueProof(bytes32 proofId, bytes32 documentHash, bytes32 issuerRef) external onlyRegistrar {
    ...
}
```

## 9. Verification and Testing

Use the real commands (see README):

| Area | Command |
|---|---|
| Whole stack | `python scripts/dev.py up`, `status`, `logs [svc]`, `stop/start <svc>` |
| Unit tests in containers | `python scripts/dev.py test [svc]` |
| Contract | `forge test` in `blockchain/` |
| Backend against real Anvil (stack up) | `docker compose exec backend python -m pytest -m real_registry tests/conformance tests/integration` |
| Contract regeneration (after an instructed schema change) | `python scripts/dev.py openapi` |
| Frontend logic | `npm test` (Vitest) in the app |
| API scenarios | scripts in `scripts/scn/` |
| AI evaluation | `python scripts/dev.py eval …` |

- State clearly what was verified and how: automated with mocks, automated against real Anvil/LLM, or manual. If a check could not run, say why. Never claim success without having run it.
- Mock results are never evidence for scenarios, evaluation, or demo.
- A registry provider is ready for integration only after the conformance suite passes against the real adapter (`real_registry`).
- In `docs/testing/`, fill `Actual result` and `Status` only after a real execution, with evidence saved under `docs/testing/evidence/<TC-ID>/`. Never pre-fill PASS. Evidence must not contain secrets.
- AI evaluation: tune prompts/thresholds on the dev set only; never use or modify the frozen test set for tuning; record model ID, prompt version, and raw outputs; report actual results including failures.
- Use only LLM API credits from the account of the member you work for. Keep calls small; do not loop on quota errors.

## 10. Security, Data, and Dependencies

- Never print, log, commit, or write secrets (`.env` values, partner/internal tokens, JWT secret, signer key, LLM API key) into code, docs, evidence, or reports. Do not edit `.env`; `.env.example` holds names and placeholders only.
- Use only synthetic data. Never send real documents or personal data to the LLM.
- Logs must not contain request bodies, file contents, extracted text, evidence quotes, raw model output, full reference codes, passwords, or tokens.
- Render API/document/model text as plain text in the UI; never use `dangerouslySetInnerHTML`.
- Add dependencies only when necessary, pin exact versions (`requirements.txt` with `==`, `package-lock.json`), and mention them in the report. Do not introduce frameworks or infrastructure excluded by SYSTEM_ARCHITECTURE §12.1 (e.g. LangChain, vector DB, Redis, queues, PostgreSQL, Alembic, local LLMs) without an approved architecture change.

## 11. Reporting

There is no shared progress file; the team coordinates directly. End every task with a concise report in Indonesian:

1. **Perubahan** — files changed and what changed.
2. **Verifikasi** — commands run and actual results (mock vs real).
3. **Belum selesai / risiko** — remaining issues, skipped checks, assumptions.
4. **Perlu koordinasi** — changes needed in other members' modules or shared files, and any contract change, written so the human can paste it to the team chat.

Do not report future or planned work as completed.

## 12. Communication

Respond in concise Indonesian unless asked otherwise. Use technical English terms where clearer. Keep important security and implementation details even when brief. Disclose assumptions, failed or skipped checks, and unresolved issues.

## 13. Evaluation Output Contract

- The offline `raw.jsonl` v1 contract is defined in `docs/evaluation/protocol.md` §6 and `ai-eval/scripts/_eval_schema.py` (`EvaluationRecord`). This contract was established in T6-05 at Sat's explicit instruction; it does not change the frozen public OpenAPI contract.
- B's `run_eval.py` (T5-07/T5-08), Sat's `baseline.py` (T6-05), and Pash's `metrics.py` (T4-07) must use the same record format: `schemaVersion`, `id`, `variant`, `status`, `result`, `extraction`, `error`, `latencyMs`. `result` is the existing API-08 response shape for both variants; failures have `status=UNAVAILABLE`, `result=null`, and a structured error.
- Join ground truth from the manifest by `id`. Group metrics by `variant` and read indicator codes from `result.indicatorDetails`, not the display strings in `result.indicators`. Never infer predictions from dataset IDs, filenames, reference labels, or indicator annotations.
- Producers write immutable run directories with `raw.jsonl` and `run_config.json`; consumers reject incomplete runs, unsupported schema versions, duplicate `(variant,id)`, and mismatched manifest checksums. Follow the exact fields and lifecycle in protocol §6 rather than inventing a different format.
- Do not serialize Settings objects, secrets, full extracted text, or raw provider exceptions. Evidence is saved only in synthetic evaluation artefacts, not stdout/application logs. Baseline remains evaluation-only and is never a runtime fallback.
- Format changes require coordinated updates to the schema, synthetic contract tests, protocol, and affected producers/consumers. Dataset review, English data, model selection, freeze, metric conventions, and final evaluation remain their respective owners' tasks; defining this format does not complete them.
