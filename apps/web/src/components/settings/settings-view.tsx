"use client";

import type { ReactNode } from "react";
// Route folder owns the switch for now; chat surface will rehome it later.
import { RegistrationSwitch } from "@/app/(private)/system/settings/registration-switch";
import type { SwitchRead } from "@/lib/system-settings";

// Full system settings body; the server page adds the owner gate and
// hands down its own switch read for the first paint.
export function SettingsView({ initial }: { initial?: SwitchRead }): ReactNode {
  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
        System settings
      </p>
      <RegistrationSwitch initial={initial} />
    </div>
  );
}
