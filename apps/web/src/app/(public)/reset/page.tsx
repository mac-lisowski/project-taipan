import Link from "next/link";
import type { ReactNode } from "react";
import { ResetForm } from "@/components/auth/reset-form";

// Awaited searchParams keep the static shell free of a Suspense boundary.
export default async function ResetPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}): Promise<ReactNode> {
  const { token } = await searchParams;
  if (!token) {
    return (
      <div className="flex w-full flex-1 flex-col gap-3">
        <p role="alert" className="font-mono text-[11px] leading-relaxed text-muted-foreground">
          this reset link is invalid or expired.
        </p>
        <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground/60">
          <Link href="/forgot" className="underline-offset-4 hover:text-foreground hover:underline">
            ask for a new link
          </Link>
        </p>
      </div>
    );
  }
  return <ResetForm token={token} />;
}
