"use client";

import { useEffect, useReducer } from "react";
import type { ReactNode } from "react";
import {
  Badge,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/ui";
import {
  applyUsersQuery,
  formatDate,
  loadUsers,
  reduceUsersView,
  type StatusFilter,
} from "@/lib/users-list";

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

  const filtered = applyUsersQuery(view.users, view.query, view.status);

  return (
    <div className="flex w-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Input
          value={view.query}
          onChange={(e) =>
            dispatch({ type: "query_changed", query: e.target.value })
          }
          placeholder="search email"
          aria-label="search users by email"
          className="h-8 w-56 font-mono text-xs"
        />
        <Select
          value={view.status}
          onValueChange={(value) =>
            dispatch({ type: "status_changed", status: value as StatusFilter })
          }
        >
          <SelectTrigger
            aria-label="filter users by status"
            className="font-mono text-xs"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">all</SelectItem>
            <SelectItem value="active">active</SelectItem>
            <SelectItem value="inactive">inactive</SelectItem>
          </SelectContent>
        </Select>
        <p className="ml-auto font-mono text-[10px] tracking-[0.15em] text-muted-foreground">
          {filtered.length} of {view.users.length} users
        </p>
      </div>
      {filtered.length === 0 ? (
        <p className="font-mono text-xs text-muted-foreground">no users match</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>email</TableHead>
              <TableHead>status</TableHead>
              <TableHead>registered</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((user) => (
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
      )}
    </div>
  );
}
