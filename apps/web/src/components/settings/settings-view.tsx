"use client";

import type { ReactNode } from "react";
// Route folder owns the switch for now; chat surface will rehome it later.
import { RegistrationSwitch } from "@/app/(private)/settings/registration-switch";

// Full system settings body; the server page adds the owner gate around it.
export function SettingsView(): ReactNode {
  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
        System settings
      </p>
      <RegistrationSwitch />
    </div>
  );
}
