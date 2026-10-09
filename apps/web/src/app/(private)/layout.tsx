import type { ReactNode } from "react";
import { PrivateShell } from "@/components/shell/private-shell";
import { getSessionToken, requireAccount } from "@/lib/session";
import { resolveThreadsSeed } from "@/app/api/upstream";

// Auth is checked server-side; the first thread page rides along for the sidebar.
export default async function PrivateLayout({
  children,
}: {
  children: ReactNode;
}): Promise<ReactNode> {
  const token = await getSessionToken();
  const [me, threads] = await Promise.all([requireAccount(), resolveThreadsSeed(token)]);
  return (
    <PrivateShell
      id={me.id}
      email={me.email}
      tenant={me.tenant_id}
      roles={me.roles}
      systemRoles={me.system_roles}
      threads={threads}
    >
      {children}
    </PrivateShell>
  );
}
