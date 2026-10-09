"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition, type ReactNode } from "react";
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
  countLine,
  formatDate,
  pageCount,
  PAGE_SIZES,
  usersPath,
  USERS_COPY,
  type PageSize,
  type StatusFilter,
  type UsersBoot,
  type UsersFilters,
} from "@/lib/users-list";

const SEARCH_DEBOUNCE_MS = 300;

// The URL is the only source of list state. Props carry the server
// render for the current URL; controls write params and let the next
// server render replace the rows, so old data stays visible meanwhile.
export function UsersTable({ boot, onSelectUser }: { boot: UsersBoot; onSelectUser?: (id: number) => void }): ReactNode {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const filters = boot.filters;
  // The search field keeps local state and debounces its navigation.
  const [query, setQuery] = useState(filters.q);
  const flushRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Controls read the latest filters and text, not the render they were born in.
  const filtersRef = useRef(filters);
  const queryRef = useRef(query);
  useEffect(() => {
    filtersRef.current = filters;
  }, [filters]);

  // A pasted link reseeds the field, but only while nothing is in flight.
  useEffect(() => {
    if (flushRef.current === null && filters.q !== queryRef.current) {
      setQuery(filters.q);
      queryRef.current = filters.q;
    }
  }, [filters.q]);

  useEffect(() => {
    return () => {
      if (flushRef.current !== null) clearTimeout(flushRef.current);
    };
  }, []);

  // Controls cancel a pending flush; the merge keeps the box and URL in agreement.
  function go(patch: Partial<UsersFilters>): void {
    if (flushRef.current !== null) {
      clearTimeout(flushRef.current);
      flushRef.current = null;
    }
    const next: UsersFilters = { ...filtersRef.current, q: queryRef.current.trim(), ...patch };
    startTransition(() => router.replace(usersPath(next), { scroll: false }));
  }

  function onSearch(value: string): void {
    setQuery(value);
    queryRef.current = value;
    if (flushRef.current !== null) clearTimeout(flushRef.current);
    flushRef.current = setTimeout(() => {
      flushRef.current = null;
      // The merge in go supplies the trimmed text; passing q here would
      // override it with a stale render's copy.
      go({ page: 1 });
    }, SEARCH_DEBOUNCE_MS);
  }

  // Row actions navigate away; a queued flush must not fire over them.
  function cancelFlush(): void {
    if (flushRef.current !== null) {
      clearTimeout(flushRef.current);
      flushRef.current = null;
    }
  }

  if (!boot.result.ok) {
    return (
      <div className="flex items-center gap-3">
        <p role="alert" className="font-mono text-xs text-red-400">
          {USERS_COPY.error}: {boot.result.error}
        </p>
        <Button
          variant="outline"
          size="xs"
          onClick={() => router.refresh()}
          className="font-mono text-[11px] uppercase tracking-[0.25em]"
        >
          {USERS_COPY.retry}
        </Button>
      </div>
    );
  }

  const payload = boot.result.data;
  const pages = pageCount(payload.total, payload.page_size);

  return (
    <div className="flex w-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Input
          value={query}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="search email"
          aria-label="search users by email"
          className="h-8 w-56 font-mono text-xs"
        />
        <Select
          value={filters.status}
          onValueChange={(value) => go({ status: value as StatusFilter, page: 1 })}
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
          value={String(filters.pageSize)}
          onValueChange={(value) => go({ pageSize: Number(value) as PageSize, page: 1 })}
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
          {pending ? "…" : countLine(payload.total, payload.total_all)}
        </p>
      </div>
      {payload.items.length === 0 ? (
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
              {payload.items.map((user) => (
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
                    <button
                      type="button"
                      onClick={() => {
                        cancelFlush();
                        onSelectUser?.(user.id);
                      }}
                      aria-label={`open details for ${user.email}`}
                      className="font-mono text-xs text-muted-foreground underline-offset-4 hover:underline"
                    >
                      view
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="xs"
              disabled={payload.page === 1}
              onClick={() => go({ page: 1 })}
              aria-label="first page"
              className="font-mono text-[11px]"
            >
              first
            </Button>
            <Button
              variant="outline"
              size="xs"
              disabled={payload.page === 1}
              onClick={() => go({ page: payload.page - 1 })}
              aria-label="previous page"
              className="font-mono text-[11px]"
            >
              prev
            </Button>
            <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground">
              page {payload.page} of {pages}
            </p>
            <Button
              variant="outline"
              size="xs"
              disabled={payload.page === pages}
              onClick={() => go({ page: payload.page + 1 })}
              aria-label="next page"
              className="font-mono text-[11px]"
            >
              next
            </Button>
            <Button
              variant="outline"
              size="xs"
              disabled={payload.page === pages}
              onClick={() => go({ page: pages })}
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
