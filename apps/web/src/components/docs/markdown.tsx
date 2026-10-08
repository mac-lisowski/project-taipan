import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { isValidElement, type ReactNode } from "react";
import { MermaidBlock } from "@/components/docs/mermaid-block";
import { assetHref, docHref, slugify } from "@/lib/docs";

function textOf(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) {
    return textOf(node.props.children);
  }
  return "";
}

// Props are picked by name, not spread - spreading leaks node= into the DOM.
export function Markdown({ source, slug }: { source: string; slug: string }): ReactNode {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="font-display mt-8 text-2xl text-foreground first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2
            id={slugify(textOf(children))}
            className="mt-8 scroll-mt-8 border-b border-border pb-2 font-display text-lg text-foreground"
          >
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3
            id={slugify(textOf(children))}
            className="mt-6 scroll-mt-8 font-display text-base text-foreground"
          >
            {children}
          </h3>
        ),
        h4: ({ children }) => (
          <h4 className="mt-4 font-mono text-sm text-foreground">{children}</h4>
        ),
        p: ({ children }) => (
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{children}</p>
        ),
        a: ({ href, children }) => (
          <a
            href={href === undefined ? undefined : docHref(slug, href)}
            className="text-foreground underline underline-offset-4 hover:text-signal"
            {...(href?.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {})}
          >
            {children}
          </a>
        ),
        ul: ({ children }) => (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">{children}</ol>
        ),
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="mt-3 border-l-2 border-signal/50 pl-4 text-muted-foreground">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[11px]">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-border bg-secondary px-3 py-1.5 text-left uppercase tracking-[0.1em] text-foreground">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-border px-3 py-1.5 text-muted-foreground">{children}</td>
        ),
        pre: ({ children }) => <>{children}</>,
        code: ({ className, children }) => {
          const code = String(children).replace(/\n$/, "");
          if (className?.includes("language-mermaid")) {
            return <MermaidBlock code={code} />;
          }
          if (className?.includes("language-")) {
            return (
              <pre className="mt-4 overflow-x-auto border border-border bg-background/80 p-3">
                <code className="font-mono text-[10px] leading-relaxed text-muted-foreground">
                  {code}
                </code>
              </pre>
            );
          }
          return (
            <code className="border border-border bg-secondary px-1 py-0.5 font-mono text-[11px] text-foreground">
              {code}
            </code>
          );
        },
        img: ({ src, alt }) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={typeof src === "string" ? assetHref(slug, src) : undefined}
            alt={alt ?? ""}
            className="mt-4 max-w-full border border-border"
          />
        ),
        hr: () => <hr className="my-6 border-border" />,
        strong: ({ children }) => <strong className="text-foreground">{children}</strong>,
      }}
    >
      {source}
    </ReactMarkdown>
  );
}
