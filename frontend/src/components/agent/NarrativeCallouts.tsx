"use client";

import { createNarrativeCallouts } from "@/lib/narrativeCallouts";
import type { Dashboard } from "@/lib/types";

const TONE_CLASSES = {
  neutral: "border-white/10 bg-white/[0.05] text-white",
  risk: "border-red-300/20 bg-red-400/10 text-red-100",
  positive: "border-emerald-300/20 bg-emerald-400/10 text-emerald-100",
  action: "border-amber-300/20 bg-amber-300/10 text-amber-100",
};

export function NarrativeCallouts({ dashboard }: { dashboard: Dashboard }) {
  const callouts = createNarrativeCallouts(dashboard);
  if (callouts.length === 0) return null;

  return (
    <div
      data-testid="narrative-callouts"
      className="animate-rise-in mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4"
    >
      {callouts.map((callout) => (
        <article
          key={callout.id}
          data-testid="narrative-callout"
          data-callout-id={callout.id}
          className={`min-w-0 rounded-lg border px-3 py-2.5 ${TONE_CLASSES[callout.tone]}`}
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider opacity-55">
            {callout.label}
          </p>
          <p className="mt-1 line-clamp-2 text-xs font-medium leading-relaxed">{callout.text}</p>
        </article>
      ))}
    </div>
  );
}
