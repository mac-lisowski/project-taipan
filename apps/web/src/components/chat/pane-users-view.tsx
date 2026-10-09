"use client";

// Users adapter for the pane. The server page owns the SSR boot payload,
// so inside the pane this component owns list state instead: it fetches
// each filter page through the BFF and hands the table a boot prop.
// Table filter writes arrive as replace-target shell nav calls; this
// adapter converts them into local filter state so the main URL and the
// browser history never see in-pane list churn.

import { useEffect, useState, type ReactNode } from "react";

import { UserDetailPanel } from "@/components/users/user-detail-panel";
import { UsersView } from "@/components/users/users-view";
import { fetchUsersPage } from "@/lib/pane-users";
import { splitTargetPath, type ShellNavTarget } from "@/lib/shell-nav";
import { ShellNavProvider, useShellNavigate } from "@/lib/shell-nav-context";
import { Button } from "@/ui";
import {
  parseUsersFilters,
  USERS_COPY,
  type UsersFilters,
  type UsersRead,
} from "@/lib/users-list";

const DEFAULT_FILTERS = parseUsersFilters({});

function filtersFromPath(path: string): UsersFilters {
  const q = path.indexOf("?");
  const record =
    q === -1 ? {} : Object.fromEntries(new URLSearchParams(path.slice(q + 1)));
  return parseUsersFilters(record);
}

export function PaneUsersView({
  detailId,
}: {
  detailId: number | null;
}): ReactNode {
  // Captured before the nested provider below overrides the context.
  const paneNav = useShellNavigate();
  const [filters, setFilters] = useState<UsersFilters>(DEFAULT_FILTERS);
  // null means the first fetch has not landed; after that the previous
  // page stays visible while its replacement loads (same as the SSR path).
  const [result, setResult] = useState<UsersRead | null>(null);

  useEffect(() => {
    let alive = true;
    void fetchUsersPage(filters).then((read) => {
      if (alive) setResult(read);
    });
    return () => {
      alive = false;
    };
  }, [filters]);

  if (detailId !== null) {
    return (
      <UserDetailPanel
        id={detailId}
        onBack={() => paneNav({ path: "/users", detailId: null })}
      />
    );
  }

  // A retry that works in-pane: the table's own retry calls
  // router.refresh(), which cannot reach this adapter's state.
  function retry(): void {
    setResult(null);
    setFilters((prev) => ({ ...prev }));
  }

  // Only replace-writes that retarget the list become filter state;
  // anything else (detail picks, exits) is real pane navigation.
  function adapterNav(target: ShellNavTarget): void {
    const { pathname, user } = splitTargetPath(target.path);
    if (target.replace === true && pathname === "/users" && user === null) {
      const next = filtersFromPath(target.path);
      setFilters((prev) =>
        JSON.stringify(prev) === JSON.stringify(next) ? prev : next,
      );
      return;
    }
    paneNav(target);
  }

  return (
    <ShellNavProvider navigate={adapterNav}>
      {result === null ? (
        <p className="font-mono text-xs">loading…</p>
      ) : !result.ok ? (
        <div className="flex items-center gap-3">
          <p role="alert" className="font-mono text-xs text-red-400">
            {USERS_COPY.error}: {result.error}
          </p>
          <Button
            variant="outline"
            size="xs"
            onClick={retry}
            className="font-mono text-[11px] uppercase tracking-[0.25em]"
          >
            {USERS_COPY.retry}
          </Button>
        </div>
      ) : (
        <UsersView
          boot={{ filters, result }}
          onSelectUser={(id) => paneNav({ path: "/users", detailId: id })}
        />
      )}
    </ShellNavProvider>
  );
}
