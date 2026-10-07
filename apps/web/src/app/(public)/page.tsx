import Link from "next/link";
import type { ReactNode } from "react";
import { LoginForm } from "@/components/auth/login-form";
import { SetupForm } from "@/components/auth/setup-form";
import { resolveLanding, resolveRegistrationSwitch } from "@/app/api/upstream";
import { redirectIfAuthenticated } from "@/lib/session";
import { showSignUpLink } from "@/lib/register";

// Server component: a session cookie means the account page owns this
// visitor. Otherwise the probe picks the form server-side, so the
// browser gets the final render with no loading state. The sign up
// link renders only on an open switch; off and unknown hide it.
export default async function Home(): Promise<ReactNode> {
  await redirectIfAuthenticated();
  const decision = await resolveLanding();
  if (decision.view === "error") {
    return (
      <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
        err: {decision.error}
      </p>
    );
  }
  if (decision.view === "setup") {
    return <SetupForm />;
  }
  const read = await resolveRegistrationSwitch();
  return (
    <div className="flex w-full flex-1 flex-col gap-3">
      <LoginForm />
      {showSignUpLink(read) && (
        <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground/60">
          <Link
            href="/register"
            className="underline-offset-4 hover:text-foreground hover:underline"
          >
            need an account? sign up
          </Link>
        </p>
      )}
    </div>
  );
}
