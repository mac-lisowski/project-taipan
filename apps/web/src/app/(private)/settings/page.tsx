import { redirect } from "next/navigation";

// The settings surface moved under /system; keep old deep links alive.
export default function SettingsRedirect(): never {
  redirect("/system/settings");
}
