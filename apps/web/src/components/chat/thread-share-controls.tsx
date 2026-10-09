"use client";

import { useThreadList } from "@openuidev/react-headless";
import { IconButton, ShareThread } from "@openuidev/react-ui";
import { Link2Off } from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { generateShareLink, getShareStatus, revokeShareLink } from "@/lib/share-link";
import {
  recordRevoked,
  recordShared,
  shareStatusBlocked,
  useSharedThreadIds,
} from "@/lib/share-state";

// One module store behind both mounted copies so mobile and desktop agree.
export function ThreadShareControls(): ReactNode {
  const selectedThreadId = useThreadList((s) => s.selectedThreadId);
  const sharedThreadIds = useSharedThreadIds();

  // Shares made in earlier sessions: ask the API once per selected
  // thread and drop confirmed ids into the shared store.
  useEffect(() => {
    if (selectedThreadId === null || shareStatusBlocked(selectedThreadId)) return;
    let cancelled = false;
    void getShareStatus(selectedThreadId).then((shared) => {
      if (!cancelled && shared && !shareStatusBlocked(selectedThreadId)) {
        recordShared(selectedThreadId);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [selectedThreadId]);

  async function handleGenerate(threadId: string): Promise<string> {
    const url = await generateShareLink(threadId);
    // Only record after the POST resolves; a rejected create must not
    // light up the revoke button.
    recordShared(threadId);
    return url;
  }

  async function handleRevoke(threadId: string): Promise<void> {
    // Destructive and irreversible: confirm before the DELETE.
    if (!window.confirm("Revoke the public share link for this thread?")) {
      return;
    }
    if (await revokeShareLink(threadId)) {
      recordRevoked(threadId);
    }
  }

  const sharedId =
    selectedThreadId !== null && sharedThreadIds.has(selectedThreadId)
      ? selectedThreadId
      : null;

  return (
    <>
      <ShareThread generateShareLink={handleGenerate} />
      {sharedId !== null ? (
        <IconButton
          icon={<Link2Off />}
          appearance="destructive"
          variant="tertiary"
          size="small"
          aria-label="Revoke share link"
          title="Revoke share link"
          onClick={() => void handleRevoke(sharedId)}
        />
      ) : null}
    </>
  );
}
