import type { ReactNode } from "react";
import { requireAccount } from "@/lib/session";

// Group-level guard enforcing authentication across all private routes.
export default async function PrivateLayout({
  children,
}: {
  children: ReactNode;
}): Promise<ReactNode> {
  await requireAccount();
  return children;
}
