import type { ReactNode } from "react";
import { listDocs } from "@/lib/docs";
import { Markdown } from "@/components/docs/markdown";

export default async function DocsIndex(): Promise<ReactNode> {
  const docs = await listDocs();
  const body = [
    "# documentation",
    "",
    "Everything in `docs/` renders here. Pick a page from the left.",
    "",
    ...docs.map((d) => `- [${d.title}](/docs/${d.slug.join("/")})`),
  ].join("\n");
  return <Markdown source={body} slug="README" />;
}
