import { useThreadList } from "@openuidev/react-headless";
import { useEffect, useState } from "react";

import { resolveArtifactId } from "@/lib/artifact-storage";
import {
  DOCUMENT_TYPE,
  TABLE_TYPE,
  type ArtifactDraft,
} from "@/lib/artifact-renderers";

// The canonical artifacts path carries the stored id; in-thread detailed
// views have none, so the id resolves asynchronously from seen summaries.
export function useStoredArtifactId(
  draft: ArtifactDraft,
  pathId: string | null,
): string | null {
  const selectedThreadId = useThreadList((state) => state.selectedThreadId);
  const [resolved, setResolved] = useState<{ key: string; id: string | null } | null>(
    null,
  );
  const { kind, title, rows, markdown } = draft;
  const key = `${selectedThreadId}${title}${kind}`;

  useEffect(() => {
    if (pathId !== null || selectedThreadId === null) return;
    let live = true;
    void resolveArtifactId({
      threadId: selectedThreadId,
      title,
      type: kind === "table" ? TABLE_TYPE : DOCUMENT_TYPE,
      content: kind === "table" ? { rows } : { markdown },
    }).then((id) => {
      if (live) setResolved({ key, id: id ?? null });
    });
    return () => {
      live = false;
    };
  }, [pathId, selectedThreadId, title, kind, rows, markdown, key]);

  // A draft swap before the effect lands must not expose the prior id.
  return pathId ?? (resolved?.key === key ? resolved.id : null);
}
