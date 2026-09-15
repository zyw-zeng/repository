"use client";

/** 在聊天消息内部展示 JD Agent 进度与可展开的证据化报告。 */

import {
  BriefcaseBusiness,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Download,
  LoaderCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import type {
  JdAnalysisArtifact,
  JdAnalysisReport,
  JdRequirementMatch,
  MatchLevel,
} from "@/features/jd-matching/types";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const levelPresentation: Record<MatchLevel, { label: string; className: string }> = {
  strong_match: {
    label: "强匹配",
    className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-500",
  },
  partial_match: {
    label: "部分匹配",
    className: "border-amber-500/30 bg-amber-500/10 text-amber-500",
  },
  missing: {
    label: "明确未满足",
    className: "border-rose-500/30 bg-rose-500/10 text-rose-500",
  },
  unverified: {
    label: "暂无依据",
    className: "border-border bg-muted text-muted-foreground",
  },
  conflict: {
    label: "存在冲突",
    className: "border-destructive/30 bg-destructive/10 text-destructive",
  },
};

const careerFollowups = [
  "这个岗位我的优势是什么？",
  "这个岗位有哪些应聘风险？",
  "我还存在哪些能力缺口？",
  "我应该采用什么投递策略？",
  "为这个岗位生成30秒、1分钟和文字版自我介绍",
  "从可信证据中提炼适合这个岗位的项目亮点",
  "生成这个岗位的面试问题和回答思路",
  "为这个岗位制定能力补足计划",
];

export function JdAnalysisCard({
  artifact,
  onAsk,
  reportDownloadUrl,
}: {
  artifact: JdAnalysisArtifact;
  onAsk?: (question: string) => void;
  reportDownloadUrl?: string;
}) {
  const [restoredReport, setRestoredReport] = useState<JdAnalysisReport>();
  const [restoreFailed, setRestoreFailed] = useState(false);
  const report = artifact.report ?? restoredReport;

  useEffect(() => {
    if (artifact.report || !artifact.analysisId || artifact.status !== "completed") return;
    let active = true;
    void apiClient
      .get<JdAnalysisReport>(`/jd-analyses/${artifact.analysisId}`)
      .then((response) => {
        if (active) setRestoredReport(response.data);
      })
      .catch(() => {
        if (active) setRestoreFailed(true);
      });
    return () => {
      active = false;
    };
  }, [artifact.analysisId, artifact.report, artifact.status]);

  if (!report) {
    const failed = artifact.status === "failed" || restoreFailed;
    return (
      <div className="border-border/70 bg-background/55 rounded-2xl border p-4">
        <div className="flex items-start gap-3">
          <span className="bg-primary/10 text-primary grid size-9 shrink-0 place-items-center rounded-xl">
            {failed ? <CircleAlert className="size-4" /> : <LoaderCircle className="size-4 animate-spin" />}
          </span>
          <div className="min-w-0">
            <p className="font-medium">JD 岗位匹配 Agent</p>
            <p className="text-muted-foreground mt-1 text-xs leading-5">
              {failed ? "岗位匹配失败，可以切换到岗位模式后重新提交。" : artifact.progress}
            </p>
            {!!artifact.requirementCount && (
              <p className="text-muted-foreground mt-2 text-xs tabular-nums">
                已核验 {artifact.evaluatedCount ?? 0}/{artifact.requirementCount} 项要求
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  const strongCount = report.matches.filter((item) => item.level === "strong_match").length;
  const partialCount = report.matches.filter((item) => item.level === "partial_match").length;
  const missingCount = report.matches.filter((item) => item.level === "missing").length;
  const unverifiedCount = report.matches.filter((item) => item.level === "unverified").length;

  return (
    <div className="border-primary/20 bg-background/55 overflow-hidden rounded-2xl border">
      <div className="from-primary/14 via-card to-brand-violet/10 bg-gradient-to-br p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <span className="from-brand-cyan via-brand-indigo to-brand-violet grid size-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br text-white">
            <BriefcaseBusiness className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-muted-foreground text-xs">证据化岗位匹配报告</p>
            <h3 className="mt-1 truncate text-base font-semibold sm:text-lg">
              {report.job_title || "未识别岗位"}
            </h3>
            {report.company_name && <p className="text-muted-foreground mt-0.5 text-xs">{report.company_name}</p>}
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3">
          <Score
            label="岗位匹配度"
            value={report.score ?? 0}
            featured
          />
          <Score label="证据完整度" value={report.completeness ?? 0} />
          <Score label="求职可行度" value={report.feasibility ?? report.score ?? 0} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <Badge variant="outline">强匹配 {strongCount}</Badge>
          <Badge variant="outline">部分匹配 {partialCount}</Badge>
          {!!missingCount && <Badge variant="outline">明确未满足 {missingCount}</Badge>}
          <Badge variant="outline">证据不足 {unverifiedCount}</Badge>
        </div>
      </div>

      <details className="group/report border-t">
        <summary className="hover:bg-muted/40 flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium">
          查看逐项要求与知识库证据
          <ChevronDown className="size-4 transition-transform group-open/report:rotate-180" />
        </summary>
        <div className="border-t p-3 sm:p-4">
          <div className="space-y-3">
            {report.matches.map((match) => <RequirementItem key={match.requirement_id} match={match} />)}
          </div>
          <p className="text-muted-foreground mt-4 text-[11px]">
            证据不足表示公开知识库中没有足够记录，不代表本人不具备该能力；只有资料明确证明未达到要求时才会标记为“明确未满足”。
          </p>
        </div>
      </details>
      {onAsk && (
        <div className="border-t px-4 py-3">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-muted-foreground text-[11px]">继续咨询求职顾问</p>
            {reportDownloadUrl && (
              <a
                href={reportDownloadUrl}
                download
                className="text-primary hover:bg-primary/10 inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] transition-colors"
              >
                <Download className="size-3" />
                导出完整报告
              </a>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {careerFollowups.map((question) => (
              <button
                key={question}
                type="button"
                className="border-border/70 bg-background/60 hover:border-primary/40 hover:text-primary rounded-full border px-3 py-1.5 text-xs transition-colors"
                onClick={() => onAsk(question)}
              >
                {followupLabel(question)}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function followupLabel(question: string): string {
  const labels: Record<string, string> = {
    "这个岗位我的优势是什么？": "岗位优势",
    "这个岗位有哪些应聘风险？": "应聘风险",
    "我还存在哪些能力缺口？": "能力缺口",
    "我应该采用什么投递策略？": "投递策略",
    "为这个岗位生成30秒、1分钟和文字版自我介绍": "生成自我介绍",
    "从可信证据中提炼适合这个岗位的项目亮点": "提炼项目亮点",
    "生成这个岗位的面试问题和回答思路": "准备面试问答",
    "为这个岗位制定能力补足计划": "制定补足计划",
  };
  return labels[question] ?? question;
}

function Score({
  label,
  value,
  featured = false,
}: {
  label: string;
  value: number;
  featured?: boolean;
}) {
  return (
    <div
      className={cn(
        "bg-background/70 rounded-xl border p-3",
        featured && "border-primary/30 col-span-2 sm:col-span-1",
      )}
    >
      <p className="text-muted-foreground text-[11px]">{label}</p>
      <p className={cn("mt-1 font-semibold tabular-nums", featured ? "text-2xl text-primary" : "text-xl")}>
        {value.toFixed(1)}%
      </p>
    </div>
  );
}

function RequirementItem({ match }: { match: JdRequirementMatch }) {
  const presentation = levelPresentation[match.level];
  return (
    <article className="bg-card rounded-xl border p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium leading-5">{match.requirement}</p>
          <p className="text-muted-foreground mt-1 text-[10px]">
            {requirementTypeLabel(match.requirement_type)}
          </p>
          <p className="text-muted-foreground mt-1 text-xs leading-5">{match.reason}</p>
        </div>
        <span className={cn("shrink-0 rounded-full border px-2 py-0.5 text-[11px]", presentation.className)}>
          {match.level === "strong_match" && <CheckCircle2 className="mr-1 inline size-3" />}
          {presentation.label}
        </span>
      </div>
      {!!match.evidence.length && (
        <details className="mt-2">
          <summary className="text-primary cursor-pointer text-xs">查看 {match.evidence.length} 条证据</summary>
          <div className="mt-2 space-y-2">
            {match.evidence.map((evidence) => (
              <blockquote key={evidence.chunk_id} className="bg-muted/55 rounded-lg p-2.5 text-xs leading-5">
                <p className="line-clamp-4">{evidence.quote}</p>
                <footer className="text-muted-foreground mt-1.5">
                  {evidence.filename}{evidence.page_number ? ` · 第 ${evidence.page_number} 页` : ""}
                  {` · 可信度 ${Math.round(evidence.source_quality * 100)}%`}
                </footer>
              </blockquote>
            ))}
          </div>
        </details>
      )}
    </article>
  );
}

function requirementTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    profile_fact: "结构化个人事实",
    technical_skill: "明确技术能力",
    engineering_capability: "工程综合能力",
    project_experience: "项目场景经验",
    bonus_experience: "加分经历",
  };
  return labels[type] ?? "岗位要求";
}
