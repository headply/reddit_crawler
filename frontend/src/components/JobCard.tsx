import {
  ArrowUpRight,
  AlertTriangle,
  Clock,
  DollarSign,
  Flame,
  MessageCircle,
  ThumbsUp,
  Users,
  Sparkles,
} from "lucide-react";
import type { Job } from "@/api/types";
import { formatCompensation, timeAgo } from "@/lib/format";
import { Badge, seniorityTone, workModeTone } from "./Badge";

export function JobCard({ job }: { job: Job }) {
  const salary = formatCompensation(
    job.compensation_min,
    job.compensation_max,
    job.compensation_currency,
    job.compensation_period,
  );
  const urgent = (job.urgency_score ?? 0) >= 0.6;
  const ruleClassified = job.llm_classified === false;
  return (
    <article className="bg-white border border-line rounded-xl shadow-card hover:shadow-cardHover hover:border-[#93C5FD] transition-all p-4 sm:p-5">
      <header className="flex items-start justify-between gap-3 mb-2">
        <a
          href={job.post_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[15px] sm:text-base font-semibold text-ink hover:text-accent leading-snug break-words"
        >
          {job.title}
        </a>
        <ArrowUpRight
          size={14}
          className="text-soft opacity-50 shrink-0 mt-1"
        />
      </header>

      <div className="flex flex-wrap gap-1.5 mb-2">
        {job.domain && <Badge tone="blue">{job.domain}</Badge>}
        {job.work_mode && (
          <Badge tone={workModeTone(job.work_mode)}>{job.work_mode}</Badge>
        )}
        {job.seniority && (
          <Badge tone={seniorityTone(job.seniority)}>{job.seniority}</Badge>
        )}
        {job.job_type && <Badge tone="outline">{job.job_type}</Badge>}
        {salary && (
          <Badge tone="green" className="inline-flex items-center gap-1">
            <DollarSign size={11} /> {salary}
          </Badge>
        )}
        {urgent && (
          <Badge tone="amber" className="inline-flex items-center gap-1">
            <Flame size={11} /> Urgent
          </Badge>
        )}
        {ruleClassified && (
          <Badge tone="outline" className="inline-flex items-center gap-1">
            <Sparkles size={11} /> rule-classified
          </Badge>
        )}
        {job.is_scam && (
          <Badge tone="rose" className="inline-flex items-center gap-1">
            <AlertTriangle size={11} /> scam
          </Badge>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-soft mb-2">
        <span className="inline-flex items-center gap-1">
          <Users size={11} /> r/{job.subreddit}
        </span>
        <span className="inline-flex items-center gap-1">
          <ThumbsUp size={11} /> {job.score}
        </span>
        <span className="inline-flex items-center gap-1">
          <MessageCircle size={11} /> {job.num_comments}
        </span>
        <span className="inline-flex items-center gap-1">
          <Clock size={11} /> {timeAgo(job.created_utc)}
        </span>
      </div>

      {job.excerpt && (
        <p className="text-[13px] text-muted leading-relaxed mb-2 line-clamp-3">
          {job.excerpt}
        </p>
      )}

      {job.tech_stack.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {job.tech_stack.slice(0, 12).map((t) => (
            <span
              key={t}
              className="bg-slate-50 text-slate-600 border border-line px-1.5 py-0.5 rounded text-[10.5px] font-mono"
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
