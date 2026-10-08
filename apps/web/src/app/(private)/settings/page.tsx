import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";
import { requireAccount } from "@/lib/session";
import { RegistrationSwitch } from "./registration-switch";

// Owner-only system settings; non-owners never reach this page.
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
      <RegistrationSwitch />
    </div>
  );
}
