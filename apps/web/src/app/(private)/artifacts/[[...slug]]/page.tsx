import type { ReactNode } from "react";
import { ChatApp } from "@/components/chat/chat-app";

// Artifact browser paths are SDK-internal ("artifacts/{category}/{id?}");
// a real page keeps reloads and shared links from 404ing.
export default async function ArtifactsPage({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}): Promise<ReactNode> {
  const { slug } = await params;
  const suffix = slug === undefined ? "" : `/${slug.join("/")}`;
  return <ChatApp initialPath={`artifacts${suffix}`} />;
}
