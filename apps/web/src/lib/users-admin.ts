// Owner account administration over the BFF: detail, activation, delete.
// The endpoint result is the only source of state on every path.

import { getJson, putJson, requestJson, type ApiResult } from "./api-result";

export const USERS_ADMIN_COPY = {
  loading: "loading…",
  delete: "delete",
  confirmDelete: "confirm delete",
  activate: "activate",
  deactivate: "deactivate",
  noProfile: "no profile",
  back: "back to users",
} as const;

export type UserProfileInfo = {
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  created_at: string;
  updated_at: string;
};

export type UserDetail = {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  profile: UserProfileInfo | null;
  system_roles: string[];
  tenants: { tenant_id: string; roles: string[] }[];
};

export type DetailLoadResult = ApiResult<UserDetail>;
export type ActivationResult = ApiResult<{ isActive: boolean }>;
export type DeleteResult = ApiResult<null>;

export async function loadUserDetail(id: number): Promise<DetailLoadResult> {
  const result = await getJson<UserDetail>(`/api/users/${id}`);
  if (result.ok && typeof result.data?.email !== "string") {
    return { ok: false, error: "unexpected user body" };
  }
  return result;
}

export async function setUserActive(
  id: number,
  active: boolean,
): Promise<ActivationResult> {
  const result = await putJson<{ is_active?: unknown }>(
    `/api/users/${id}/activation`,
    { active },
  );
  return result.ok
    ? { ok: true, data: { isActive: result.data?.is_active === true } }
    : result;
}

export async function deleteUser(id: number): Promise<DeleteResult> {
  return requestJson<null>(`/api/users/${id}`, { method: "DELETE" });
}

export type DetailView =
  | { state: "loading" }
  | { state: "error"; message: string }
  | {
      state: "ready";
      user: UserDetail;
      pending: null | "activation" | "delete";
      confirmingDelete: boolean;
      activationError: string | null;
      deleteError: string | null;
      deleted: boolean;
    };

export type DetailAction =
  | { type: "loaded"; result: DetailLoadResult }
  | { type: "reload" }
  | { type: "activate_started" }
  | { type: "activate_finished"; result: ActivationResult }
  | { type: "delete_started" }
  | { type: "delete_finished"; result: DeleteResult }
  | { type: "delete_confirm_changed"; confirming: boolean };

export function reduceDetailView(view: DetailView, action: DetailAction): DetailView {
  switch (action.type) {
    case "loaded":
      return action.result.ok
        ? {
            state: "ready",
            user: action.result.data,
            pending: null,
            confirmingDelete: false,
            activationError: null,
            deleteError: null,
            deleted: false,
          }
        : { state: "error", message: action.result.error };
    case "reload":
      // A fresh load is also the target-change reset for the confirm step.
      return { state: "loading" };
    case "activate_started":
      return view.state === "ready"
        ? { ...view, pending: "activation", activationError: null, confirmingDelete: false }
        : view;
    case "activate_finished":
      // Only an activation in flight can land; stale finishes keep the view.
      if (view.state !== "ready" || view.pending !== "activation") return view;
      return action.result.ok
        ? {
            ...view,
            pending: null,
            user: { ...view.user, is_active: action.result.data.isActive },
          }
        : { ...view, pending: null, activationError: action.result.error };
    case "delete_started":
      return view.state === "ready"
        ? { ...view, pending: "delete", deleteError: null, confirmingDelete: false }
        : view;
    case "delete_finished":
      if (view.state !== "ready" || view.pending !== "delete") return view;
      return action.result.ok
        ? { ...view, deleted: true }
        : { ...view, pending: null, deleteError: action.result.error };
    case "delete_confirm_changed":
      return view.state === "ready"
        ? { ...view, confirmingDelete: action.confirming, deleteError: null }
        : view;
  }
}
