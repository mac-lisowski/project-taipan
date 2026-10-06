import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { LoginForm } from "@/components/auth/login-form";
import { SetupForm } from "@/components/auth/setup-form";
import { resolveLanding } from "@/app/api/upstream";
import { hasSession } from "@/lib/session";

// Server component: a session cookie means the account page owns this
// visitor. Otherwise the probe picks the form server-side, so the
// browser gets the final render with no loading state.
export default async function Home(): Promise<ReactNode> {
  if (await hasSession()) redirect("/account");
  const decision = await resolveLanding();
  if (decision.view === "error") {
    return (
      <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
        err: {decision.error}
      </p>
    );
  }
  return decision.view === "setup" ? <SetupForm /> : <LoginForm />;
}
