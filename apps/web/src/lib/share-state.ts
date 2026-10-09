"use client";

// Live-share state lives in a module store, not component state:
// ThreadShareControls mounts twice (MobileHeader actions and the desktop
// ThreadHeader), and two private copies could disagree after a revoke.

import { useSyncExternalStore } from "react";

let sharedIds = new Set<string>();
const justRevoked = new Set<string>();
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

// Thread ids with a known-live share this session.
export function useSharedThreadIds(): ReadonlySet<string> {
  return useSyncExternalStore(subscribe, () => sharedIds);
}

export function recordShared(threadId: string): void {
  justRevoked.delete(threadId);
  if (sharedIds.has(threadId)) return;
  sharedIds = new Set(sharedIds).add(threadId);
  emit();
}

export function recordRevoked(threadId: string): void {
  // Blocks any in-flight status fetch from re-adding the id.
  justRevoked.add(threadId);
  if (!sharedIds.has(threadId)) return;
  const next = new Set(sharedIds);
  next.delete(threadId);
  sharedIds = next;
  emit();
}

// False when a status answer for this id must be ignored (just revoked)
// or the question never needs asking.
export function shareStatusBlocked(threadId: string): boolean {
  return justRevoked.has(threadId);
}
