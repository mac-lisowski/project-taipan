"use client";

import { useEffect, useReducer, useState } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Badge, Button } from "@/ui";
import { formatDate } from "@/lib/users-list";
import {
  deleteUser,
  loadUserDetail,
  reduceDetailView,
  setUserActive,
  USERS_ADMIN_COPY,
} from "@/lib/users-admin";

// The endpoint result is the only source of detail state.
export function UserDetailPanel({
  id,
  onBack,
}: {
  id: number;
  /** In-chat navigation back to the list; falls back to a route change. */
  onBack?: () => void;
}): ReactNode {
  const [view, dispatch] = useReducer(reduceDetailView, { state: "loading" });
  // Retry and target changes bump the attempt so the load effect runs again.
  const [attempt, setAttempt] = useState(0);
  const router = useRouter();

  function back(): void {
    if (onBack) onBack();
    else router.push("/users");
  }

  useEffect(() => {
    let alive = true;
    dispatch({ type: "reload" });
    void loadUserDetail(id).then((result) => {
      if (alive) dispatch({ type: "loaded", result });
    });
    return () => {
      alive = false;
    };
  }, [id, attempt]);

  if (view.state === "loading") {
    return <p className="font-mono text-xs">{USERS_ADMIN_COPY.loading}</p>;
  }
  if (view.state === "error") {
    return (
      <div className="flex items-center gap-3">
        <p role="alert" className="font-mono text-xs text-red-400">
          err: {view.message}
        </p>
        <Button
          variant="outline"
          size="xs"
          onClick={() => setAttempt((a) => a + 1)}
          className="font-mono text-[11px] uppercase tracking-[0.25em]"
        >
          retry
        </Button>
      </div>
    );
  }

  const user = view.user;
  const busy = view.pending !== null;

  async function onToggleActive() {
    if (view.state !== "ready" || view.pending !== null) return;
    dispatch({ type: "activate_started" });
    const result = await setUserActive(id, !view.user.is_active);
    dispatch({ type: "activate_finished", result });
  }

  async function onDelete() {
    if (view.state !== "ready" || view.pending !== null) return;
    dispatch({ type: "delete_started" });
    const result = await deleteUser(id);
    dispatch({ type: "delete_finished", result });
    if (result.ok) back();
  }

  return (
    <div className="flex w-full max-w-2xl flex-col gap-5">
      <div className="flex items-center justify-between gap-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          account
        </p>
        <Button
          variant="ghost"
          size="xs"
          onClick={back}
          className="font-mono text-[11px] uppercase tracking-[0.25em]"
        >
          {USERS_ADMIN_COPY.back}
        </Button>
      </div>

      <dl className="flex flex-col gap-2 font-mono text-xs">
        <Row label="email">{user.email}</Row>
        <Row label="status">
          <Badge variant={user.is_active ? "default" : "secondary"}>
            {user.is_active ? "active" : "inactive"}
          </Badge>
        </Row>
        <Row label="registered">{formatDate(user.created_at)}</Row>
        <Row label="updated">{formatDate(user.updated_at)}</Row>
        <Row label="system roles">
          {user.system_roles.length === 0 ? "none" : user.system_roles.join(", ")}
        </Row>
        <Row label="tenants">
          {user.tenants
            .map((membership) => `${membership.tenant_id}: ${membership.roles.join(", ")}`)
            .join(" | ") || "none"}
        </Row>
      </dl>

      <section className="flex flex-col gap-2 border-t border-border pt-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          profile
        </p>
        {user.profile === null ? (
          <p className="font-mono text-xs text-muted-foreground">{USERS_ADMIN_COPY.noProfile}</p>
        ) : (
          <dl className="flex flex-col gap-2 font-mono text-xs">
            <Row label="name">{user.profile.display_name ?? "none"}</Row>
            <Row label="avatar">{user.profile.avatar_url ?? "none"}</Row>
            <Row label="bio">{user.profile.bio ?? "none"}</Row>
          </dl>
        )}
      </section>

      <section className="flex flex-col gap-2 border-t border-border pt-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          actions
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            size="xs"
            disabled={busy}
            onClick={onToggleActive}
            className="font-mono text-[11px] uppercase tracking-[0.25em]"
          >
            {user.is_active ? USERS_ADMIN_COPY.deactivate : USERS_ADMIN_COPY.activate}
          </Button>
          {view.confirmingDelete ? (
            <Button
              variant="destructive"
              size="xs"
              disabled={busy}
              onClick={onDelete}
              className="font-mono text-[11px] uppercase tracking-[0.25em]"
            >
              {USERS_ADMIN_COPY.confirmDelete}
            </Button>
          ) : (
            <Button
              variant="destructive"
              size="xs"
              disabled={busy}
              onClick={() => dispatch({ type: "delete_confirm_changed", confirming: true })}
              className="font-mono text-[11px] uppercase tracking-[0.25em]"
            >
              {USERS_ADMIN_COPY.delete}
            </Button>
          )}
        </div>
        {view.activationError !== null && (
          <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
            err: {view.activationError}
          </p>
        )}
        {view.deleteError !== null && (
          <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
            err: {view.deleteError}
          </p>
        )}
      </section>
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }): ReactNode {
  return (
    <div className="flex items-center gap-3">
      <dt className="w-28 shrink-0 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
        {label}
      </dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}
