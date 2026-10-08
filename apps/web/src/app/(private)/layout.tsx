import type { ReactNode } from "react";
import { PrivateShell } from "@/components/shell/private-shell";
import { requireAccount } from "@/lib/session";

// Guard plus shell: auth is checked server-side, then the toggleable
// sidebar wraps every private page.
export default async function PrivateLayout({
  children,
}: {
  children: ReactNode;
}): Promise<ReactNode> {
  const me = await requireAccount();
  return (
    <PrivateShell
      id={me.id}
      email={me.email}
      tenant={me.tenant_id}
      roles={me.roles}
      systemRoles={me.system_roles}
    >
      {children}
    </PrivateShell>
  );
}
