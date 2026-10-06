import Link from "next/link";
import type { ReactNode } from "react";
import { Panel, PanelHeader, Sparkline, Stat } from "@/ui";

const THROUGHPUT: readonly number[] = [12, 18, 15, 24, 31, 27, 34];

const JOBS = [
  { name: "invoice-1042.pdf", status: "done", ms: "388" },
  { name: "contract-q3.docx", status: "done", ms: "512" },
  { name: "scan-9917.png", status: "retry", ms: "901" },
] as const;

// Mock overview: static numbers proving the shell, not live data.
export default function DashboardPage(): ReactNode {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline gap-3">
        <h1 className="font-display text-2xl uppercase tracking-tight">dashboard</h1>
        <Link
          href="/account"
          className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
        >
          profile →
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat label="extractions" value="1,284" delta="+12% vs yesterday" />
        <Stat label="success" value="98.2%" delta="+0.4pt" />
        <Stat label="avg ms" value="412" delta="p95 890" />
        <Stat label="tokens" value="2.1M" delta="quota 78%" />
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <Sparkline label="throughput" values={THROUGHPUT} unit="jobs/h" />
        <Panel className="px-5 py-4">
          <PanelHeader label="recent jobs" />
          <table className="mt-2 w-full font-mono text-[11px]">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="py-1 pr-2 font-normal">job</th>
                <th className="py-1 pr-2 font-normal">status</th>
                <th className="py-1 font-normal">ms</th>
              </tr>
            </thead>
            <tbody>
              {JOBS.map((job) => (
                <tr key={job.name} className="border-t border-border">
                  <td className="py-1 pr-2">{job.name}</td>
                  <td className="py-1 pr-2">{job.status}</td>
                  <td className="py-1">{job.ms}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}
