import { Head, Link, router } from "@inertiajs/react";
import { useEffect, useState } from "react";

import type { Video } from "../../types";

interface Live {
  status: string;
  stage: string;
  progress: number;
  error: string;
}

const active = ["queued", "planning", "rendering"];
const preBox = "mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-zinc-300 p-3 text-xs dark:border-zinc-700";

export default function Show({ video }: { video: Video }) {
  const [live, setLive] = useState<Live>(video);

  useEffect(() => {
    setLive(video);
  }, [video]);

  useEffect(() => {
    if (!active.includes(live.status)) return;

    const timer = window.setInterval(async () => {
      const res = await fetch(`/videos/${video.id}/status`, { headers: { Accept: "application/json" } });
      if (!res.ok) return;
      const next: Live = await res.json();
      setLive(next);
      if (!active.includes(next.status)) router.reload();
    }, 2000);

    return () => window.clearInterval(timer);
  }, [live.status, video.id]);

  const cost = (video.cost_micros / 1_000_000).toFixed(4);
  const name = video.title || `Video ${video.id}`;

  return (
    <>
      <Head title={name} />
      <p className="mb-2">
        <Link href="/videos" className="text-indigo-600 hover:underline dark:text-indigo-400">
          All videos
        </Link>
      </p>
      <h1 className="text-2xl font-semibold">{name}</h1>
      <p className="mt-2" data-testid="status">
        {live.status}: {live.stage} ({live.progress}%)
      </p>
      {active.includes(live.status) && <progress className="mt-2 w-full" max={100} value={live.progress} aria-label="Progress" />}
      {live.status === "failed" && (
        <div role="alert" className="mt-4 rounded-md bg-red-50 p-4 text-red-900 dark:bg-red-950 dark:text-red-100">
          <p>{live.error}</p>
          {video.attempts < 3 && (
            <Link href={`/videos/${video.id}/retry`} method="post" as="button" className="mt-2 underline">
              Try again
            </Link>
          )}
        </div>
      )}
      {live.status === "ready" && (
        <p className="mt-4">
          <a href={`/videos/${video.id}/download`} className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500">
            Download MP4
          </a>
        </p>
      )}
      <dl className="mt-6 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
        <dt>Style</dt>
        <dd>{video.skill_id}</dd>
        <dt>Model</dt>
        <dd>{video.model_id}</dd>
        <dt>Tokens</dt>
        <dd>
          {video.input_tokens} in, {video.output_tokens} out
        </dd>
        <dt>Estimated cost</dt>
        <dd>${cost}</dd>
      </dl>
      <h2 className="mt-6 text-lg font-semibold">Compiled prompt</h2>
      <pre className={preBox}>{video.prompt}</pre>
      {video.plan && (
        <>
          <h2 className="mt-6 text-lg font-semibold">Scene plan</h2>
          <pre className={preBox}>{JSON.stringify(JSON.parse(video.plan), null, 2)}</pre>
        </>
      )}
    </>
  );
}
