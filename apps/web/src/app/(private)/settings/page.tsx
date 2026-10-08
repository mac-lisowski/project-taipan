import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { SettingsView } from "@/components/settings/settings-view";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";
import { requireAccount } from "@/lib/session";

// Owner-only gate stays server-side; the body is the reusable client view.
export default async function SettingsPage(): Promise<ReactNode> {
  const me = await requireAccount();
  if (!me.system_roles.includes(SYSTEM_OWNER_ROLE)) {
    redirect("/dashboard");
  }

  return <SettingsView />;
}
