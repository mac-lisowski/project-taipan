import type { ReactNode } from "react";
import { OverviewView } from "@/components/dashboard/overview-view";

// Thin server page; the body is the reusable client view.
export default function DashboardPage(): ReactNode {
  return <OverviewView />;
}
