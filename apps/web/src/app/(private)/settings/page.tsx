import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";
import { requireAccount } from "@/lib/session";

// System settings placeholder: owners only. Real controls land later.
export default async function SettingsPage(): Promise<ReactNode> {
  const me = await requireAccount();
  if (!me.system_roles.includes(SYSTEM_OWNER_ROLE)) {
    redirect("/dashboard");
  }

  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
        system settings
      </p>
      <p className="font-mono text-xs text-muted-foreground">
        Nothing here yet. Instance-level controls will live on this page.
      </p>
    </div>
  );
}
