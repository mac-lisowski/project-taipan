"use client";

import Link from "next/link";
import { useEffect, useReducer, useState } from "react";
import type { ReactNode } from "react";
import {
  Badge,
  Button,
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
  countLine,
  formatDate,
  loadUsers,
  pageCount,
  PAGE_SIZES,
  pageSlice,
  reduceUsersView,
  USERS_COPY,
  type PageSize,
  type StatusFilter,
} from "@/lib/users-list";

// The endpoint result is the only source of list state.
export function UsersTable(): ReactNode {
  const [view, dispatch] = useReducer(reduceUsersView, { state: "loading" });
  // Retry bumps the attempt so the load effect runs again.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    void loadUsers().then((result) => {
      if (alive) dispatch({ type: "loaded", result });
    });
    return () => {
      alive = false;
    };
  }, [attempt]);

  if (view.state === "loading") {
    return <p className="font-mono text-xs">{USERS_COPY.loading}</p>;
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
          onClick={() => {
            dispatch({ type: "retry" });
            setAttempt((a) => a + 1);
          }}
          className="font-mono text-[11px] uppercase tracking-[0.25em]"
        >
          {USERS_COPY.retry}
        </Button>
      </div>
    );
  }

  const filtered = applyUsersQuery(view.users, view.query, view.status);
  const pages = pageCount(filtered.length, view.pageSize);
  const rows = pageSlice(filtered, view.page, view.pageSize);

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
        <Select
          value={String(view.pageSize)}
          onValueChange={(value) =>
            dispatch({
              type: "page_size_changed",
              pageSize: Number(value) as PageSize,
            })
          }
        >
          <SelectTrigger
            aria-label="users per page"
            className="font-mono text-xs"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZES.map((size) => (
              <SelectItem key={size} value={String(size)}>
                {size} / page
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="ml-auto font-mono text-[10px] tracking-[0.15em] text-muted-foreground">
          {countLine(filtered.length, view.users.length)}
        </p>
      </div>
      {filtered.length === 0 ? (
        <p className="font-mono text-xs text-muted-foreground">{USERS_COPY.empty}</p>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>email</TableHead>
                <TableHead>status</TableHead>
                <TableHead>registered</TableHead>
                <TableHead>
                  <span className="sr-only">actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-mono text-xs">
                    {user.email}
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.is_active ? "default" : "secondary"}>
                      {user.is_active ? "active" : "inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {formatDate(user.created_at)}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/users/${user.id}`}
                      aria-label={`open details for ${user.email}`}
                      className="font-mono text-xs text-muted-foreground underline-offset-4 hover:underline"
                    >
                      view
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="xs"
              disabled={view.page === 1}
              onClick={() => dispatch({ type: "page_changed", page: 1 })}
              aria-label="first page"
              className="font-mono text-[11px]"
            >
              first
            </Button>
            <Button
              variant="outline"
              size="xs"
              disabled={view.page === 1}
              onClick={() =>
                dispatch({ type: "page_changed", page: view.page - 1 })
              }
              aria-label="previous page"
              className="font-mono text-[11px]"
            >
              prev
            </Button>
            <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground">
              page {view.page} of {pages}
            </p>
            <Button
              variant="outline"
              size="xs"
              disabled={view.page === pages}
              onClick={() =>
                dispatch({ type: "page_changed", page: view.page + 1 })
              }
              aria-label="next page"
              className="font-mono text-[11px]"
            >
              next
            </Button>
            <Button
              variant="outline"
              size="xs"
              disabled={view.page === pages}
              onClick={() => dispatch({ type: "page_changed", page: pages })}
              aria-label="last page"
              className="font-mono text-[11px]"
            >
              last
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
