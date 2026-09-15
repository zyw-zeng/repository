/** 定义 JD 岗位匹配报告和实时过程的数据结构。 */

export type MatchLevel =
  | "strong_match"
  | "partial_match"
  | "missing"
  | "unverified"
  | "conflict";

export interface JdEvidence {
  chunk_id: string;
  document_id: string;
  filename: string;
  quote: string;
  page_number: number | null;
  heading: string | null;
  index_version: number;
  score: number;
  source_type: string;
  source_quality: number;
}

export interface JdRequirementMatch {
  requirement_id: string;
  requirement: string;
  category: string;
  requirement_type: string;
  importance: "required" | "preferred";
  weight: number;
  level: MatchLevel;
  reason: string;
  awarded_score: number;
  max_score: number;
  evidence: JdEvidence[];
}

export interface JdAnalysisReport {
  id: string;
  request_id: string;
  status: string;
  company_name: string | null;
  job_title: string | null;
  score: number | null;
  completeness: number | null;
  verified_fit: number | null;
  feasibility: number | null;
  matches: JdRequirementMatch[];
  duration_ms: number | null;
}

export interface JdAnalysisArtifact {
  type: "jd_analysis";
  analysisId?: string;
  status: "running" | "completed" | "failed" | "cancelled";
  progress?: string;
  jobTitle?: string | null;
  companyName?: string | null;
  requirementCount?: number;
  evaluatedCount?: number;
  report?: JdAnalysisReport;
}
