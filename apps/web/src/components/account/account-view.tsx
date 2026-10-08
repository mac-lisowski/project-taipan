"use client";

import type { ReactNode } from "react";
import { ChangePasswordForm } from "@/components/auth/change-password-form";
import { useShellAccount } from "@/components/shell/shell-context";

// Account identity plus password change; identity comes from the shell
// context the server layout resolved.
export function AccountView(): ReactNode {
  const me = useShellAccount();
  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">account</p>
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
          <dd className="break-all">{me.tenant}</dd>
        </div>
        <div className="flex justify-between border-b border-border py-2">
          <dt className="text-muted-foreground">roles</dt>
          <dd>{me.roles.join(", ")}</dd>
        </div>
        <div className="flex justify-between py-2">
          <dt className="text-muted-foreground">system roles</dt>
          <dd>{me.systemRoles.join(", ") || "-"}</dd>
        </div>
      </dl>
      <div className="mt-4 border-t border-border pt-4">
        <ChangePasswordForm />
      </div>
    </div>
  );
}
