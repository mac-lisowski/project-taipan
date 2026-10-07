"use client";

import { useEffect, useReducer } from "react";
import type { ReactNode } from "react";
import {
  Badge,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/ui";
import { formatDate, loadUsers, reduceUsersView } from "@/lib/users-list";

// The endpoint result is the only source of list state.
export function UsersTable(): ReactNode {
  const [view, dispatch] = useReducer(reduceUsersView, { state: "loading" });

  useEffect(() => {
    let alive = true;
    void loadUsers().then((result) => {
      if (alive) dispatch({ type: "loaded", result });
    });
    return () => {
      alive = false;
    };
  }, []);

  if (view.state === "loading") {
    return <p className="font-mono text-xs">loading…</p>;
  }
  if (view.state === "error") {
    return (
      <p role="alert" className="font-mono text-xs text-red-400">
        err: {view.message}
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>email</TableHead>
          <TableHead>status</TableHead>
          <TableHead>registered</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {view.users.map((user) => (
          <TableRow key={user.id}>
            <TableCell className="font-mono text-xs">{user.email}</TableCell>
            <TableCell>
              <Badge variant={user.is_active ? "default" : "secondary"}>
                {user.is_active ? "active" : "inactive"}
              </Badge>
            </TableCell>
            <TableCell className="font-mono text-xs">
              {formatDate(user.created_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
