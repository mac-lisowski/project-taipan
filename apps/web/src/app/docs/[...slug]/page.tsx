import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { extractHeadings, listDocs, readDoc } from "@/lib/docs";
import { Markdown } from "@/components/markdown";

export async function generateStaticParams(): Promise<{ slug: string[] }[]> {
  const docs = await listDocs();
  return docs.map((d) => ({ slug: d.slug }));
}

export default async function DocPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}): Promise<ReactNode> {
  const { slug } = await params;
  const source = await readDoc(slug);
  if (source === null) notFound();

  const toc = extractHeadings(source);
  const crumb = slug.length > 1 ? `${slug[0]} / ${slug[slug.length - 1]}` : slug[0];

  return (
    <div className="flex gap-10">
      <div className="min-w-0 flex-1">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground/60">
          docs / {crumb}
        </p>
        <Markdown source={source} />
      </div>
      {toc.length > 1 && (
        <nav className="sticky top-10 hidden h-fit w-44 shrink-0 lg:block">
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground/60">
            on this page
          </p>
          <ul className="mt-3 flex flex-col gap-1.5">
            {toc.map((h) => (
              <li key={h.id} style={h.depth === 3 ? { paddingLeft: 12 } : undefined}>
                <a
                  href={`#${h.id}`}
                  className="font-mono text-[11px] leading-snug text-muted-foreground transition-colors hover:text-foreground"
                >
                  {h.text}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </div>
  );
}
