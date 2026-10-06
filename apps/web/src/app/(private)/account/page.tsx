import type { ReactNode } from "react";
import { LogoutButton } from "@/components/auth/logout-button";
import { requireAccount } from "@/lib/session";

// Server component proving the session by rendering the me response.
export default async function AccountPage(): Promise<ReactNode> {
  const me = await requireAccount();

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6">
      <div className="flex w-full max-w-md flex-col gap-2">
        <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
          account
        </p>
        <dl className="font-mono text-xs">
          <div className="flex justify-between border-b border-border py-2">
            <dt className="text-muted-foreground">id</dt>
            <dd>{me.id}</dd>
          </div>
          <div className="flex justify-between border-b border-border py-2">
            <dt className="text-muted-foreground">email</dt>
            <dd>{me.email}</dd>
          </div>
          <div className="flex justify-between border-b border-border py-2">
            <dt className="text-muted-foreground">tenant</dt>
            <dd className="break-all">{me.tenant_id}</dd>
          </div>
          <div className="flex justify-between py-2">
            <dt className="text-muted-foreground">roles</dt>
            <dd>{me.roles.join(", ")}</dd>
          </div>
        </dl>
        <div className="flex justify-end pt-2">
          <LogoutButton />
        </div>
      </div>
    </main>
  );
}
