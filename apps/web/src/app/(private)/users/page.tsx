import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { ChatApp } from "@/components/chat/chat-app";
import { resolveUsersPage } from "@/app/api/upstream";
import { canSeeNavPath } from "@/lib/nav";
import { getSessionToken, requireAccount } from "@/lib/session";
import { parseUsersFilters } from "@/lib/users-list";

// Owner-only; the URL owns list state and the server fetches its one page.
export default async function UsersPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<ReactNode> {
  const me = await requireAccount();
  if (!canSeeNavPath(me.system_roles, "/users")) {
    redirect("/chat");
  }
  const filters = parseUsersFilters(await searchParams);
  const result = await resolveUsersPage(await getSessionToken(), filters);

  return <ChatApp initialPath="/users" usersBoot={{ filters, result }} />;
}
