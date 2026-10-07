import Link from "next/link";
import type { ReactNode } from "react";
import { ChangePasswordForm } from "@/components/auth/change-password-form";
import { requireAccount } from "@/lib/session";

// Profile page: the shell owns nav and logout, this shows identity.
export default async function AccountPage(): Promise<ReactNode> {
  const me = await requireAccount();

  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <div className="flex items-baseline gap-3">
        <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
          account
        </p>
        <Link
          href="/dashboard"
          className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
        >
          ← dashboard
        </Link>
      </div>
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
      <div className="mt-4 border-t border-border pt-4">
        <ChangePasswordForm />
      </div>
    </div>
  );
}
