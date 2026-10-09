"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { ChatStorage } from "@openuidev/react-headless";
import { chatStorage, type ThreadSeed } from "@/lib/chat-config";

export type ShellAccount = {
  id: number;
  email: string;
  tenant: string;
  roles: string[];
  systemRoles: string[];
};

const ShellAccountContext = createContext<ShellAccount | null>(null);

export function ShellAccountProvider({
  account,
  children,
}: {
  account: ShellAccount;
  children: ReactNode;
}): ReactNode {
  return (
    <ShellAccountContext.Provider value={account}>{children}</ShellAccountContext.Provider>
  );
}

// Chat surface reads the session identity the server layout resolved.
export function useShellAccount(): ShellAccount {
  const account = useContext(ShellAccountContext);
  if (!account) throw new Error("useShellAccount used outside the private shell");
  return account;
}

const ShellThreadsContext = createContext<ChatStorage | null>(null);

// One storage per page load: the seed must be consumed once, or remounts replay it stale.
export function ShellThreadsProvider({
  threads,
  children,
}: {
  threads: ThreadSeed | null;
  children: ReactNode;
}): ReactNode {
  const [seed] = useState(threads);
  const storage = useMemo(() => chatStorage(seed), [seed]);
  return (
    <ShellThreadsContext.Provider value={storage}>{children}</ShellThreadsContext.Provider>
  );
}

// SDK thread storage owned by the shell; null outside the provider.
export function useShellThreads(): ChatStorage | null {
  return useContext(ShellThreadsContext);
}
