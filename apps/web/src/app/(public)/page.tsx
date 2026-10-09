import Link from "next/link";
import type { ReactNode } from "react";
import { LoginForm } from "@/components/auth/login-form";
import { SetupForm } from "@/components/auth/setup-form";
import { resolveLanding, resolveRegistrationSwitch } from "@/app/api/upstream";
import { redirectIfAuthenticated } from "@/lib/session";
import { safeNextPath } from "@/lib/return-path";
import { showSignUpLink } from "@/lib/register";

// `next` returns a shared-link visitor after login; the probe picks the form otherwise.
export default async function Home({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<ReactNode> {
  const next = safeNextPath((await searchParams).next);
  await redirectIfAuthenticated(next ?? "/chat");
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
