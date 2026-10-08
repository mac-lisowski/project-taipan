import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { resolveRegistrationSwitch } from "@/app/api/upstream";
import { chooseRegisterGate } from "@/lib/register";
import { ActivateForm } from "@/components/auth/activate-form";
import { RegisterForm } from "@/components/auth/register-form";

// Server gate: the switch is read per render with no cache, so a flip
// to off closes the tokenless door at once. Closed answers 404 like
// the API; unknown shows a neutral note with nothing sign-up specific.
// The mailed link's token bypasses the off check and picks this form.
export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}): Promise<ReactNode> {
  const { token } = await searchParams;
  const gate = chooseRegisterGate(await resolveRegistrationSwitch(), token);
  if (gate.view === "not-found") notFound();
  if (gate.view === "error") {
    return (
      <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
        err: {gate.message}
      </p>
    );
  }
  return gate.view === "set-password" ? (
    <ActivateForm token={gate.token} />
  ) : (
    <RegisterForm />
  );
}
