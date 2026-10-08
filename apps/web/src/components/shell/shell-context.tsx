"use client";

import { createContext, useContext, type ReactNode } from "react";

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
