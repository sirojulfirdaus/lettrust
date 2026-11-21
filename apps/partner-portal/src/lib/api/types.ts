// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §10.7.2, §11.1
import type { paths } from "./schema";

// Respons 200 API-07 yang diturunkan dari kontrak OpenAPI hasil generate.
export type VerificationResponse =
  paths["/api/v1/verifications"]["post"]["responses"][200]["content"]["application/json"];

export type ProofCheck = VerificationResponse["proofCheck"];
export type IntegrityCheck = VerificationResponse["integrityCheck"];
export type RiskAnalysis = VerificationResponse["riskAnalysis"];
