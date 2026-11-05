import { Head, Link, useForm } from "@inertiajs/react";
import type { FormEvent } from "react";

import type { VideoJob } from "../../types";

const input =
  "mt-1 block w-full rounded-md border border-zinc-300 bg-transparent px-3 py-2 focus:border-indigo-500 focus:outline-none dark:border-zinc-700";

interface Props {
  job: VideoJob;
  download: boolean;
  platforms: string[];
}

export default function Show({ job, download, platforms }: Props) {
  const pack = useForm({
    platform: job.pack_platform || "reels",
    title: job.pack_title || "",
    description: job.pack_description || "",
    hashtags: job.pack_hashtags || "",
  });

  const savePack = (e: FormEvent) => {
    e.preventDefault();
    pack.post(`/jobs/${job.id}/pack`);
  };

  const ready = download && job.status === "ready";

  return (
    <>
      <Head title={job.subject} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{job.subject}</h1>
        <Link href="/jobs" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
          All videos
        </Link>
      </div>
      <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-zinc-500">Status</dt>
          <dd>{job.status}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Duration</dt>
          <dd>{job.duration}s</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Style</dt>
          <dd>{job.style_skill}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Model</dt>
          <dd>{job.model_id}</dd>
        </div>
      </dl>
      {job.failure ? <p className="mt-4 whitespace-pre-wrap text-red-700 dark:text-red-300">{job.failure}</p> : null}
      <div className="mt-4 flex flex-wrap gap-4">
        {ready ? (
          <a href={`/jobs/${job.id}/download`} className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500">
            Download MP4
          </a>
        ) : null}
        {ready ? (
          <a href={`/jobs/${job.id}/captions.srt`} className="text-indigo-600 hover:underline dark:text-indigo-400">
            Caption file
          </a>
        ) : null}
        <Link href={`/jobs/${job.id}/retry`} method="post" as="button" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
          Re-run
        </Link>
      </div>
      <section className="mt-8">
        <h2 className="text-lg font-semibold">Prompt</h2>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-md bg-zinc-100 p-4 text-sm dark:bg-zinc-900">{job.prompt}</pre>
      </section>
      {job.script ? (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Script</h2>
          <p className="mt-2 whitespace-pre-wrap">{job.script}</p>
        </section>
      ) : null}
      <section className="mt-8 max-w-2xl">
        <h2 className="text-lg font-semibold">Publish pack</h2>
        <p className="mt-1 text-sm text-zinc-500">Saved for you to copy. Studio does not post it.</p>
        <form onSubmit={savePack} className="mt-4 space-y-4">
          <label className="block">
            <span className="font-medium">Platform</span>
            <select className={input} value={pack.data.platform} onChange={(e) => pack.setData("platform", e.target.value)}>
              {platforms.map((platform) => (
                <option key={platform} value={platform}>
                  {platform}
                </option>
              ))}
            </select>
            {pack.errors.platform && <p className="mt-1 text-sm text-red-600">{pack.errors.platform}</p>}
          </label>
          <label className="block">
            <span className="font-medium">Title</span>
            <input className={input} value={pack.data.title} onChange={(e) => pack.setData("title", e.target.value)} />
            {pack.errors.title && <p className="mt-1 text-sm text-red-600">{pack.errors.title}</p>}
          </label>
          <label className="block">
            <span className="font-medium">Description</span>
            <textarea className={input} rows={4} value={pack.data.description} onChange={(e) => pack.setData("description", e.target.value)} />
            {pack.errors.description && <p className="mt-1 text-sm text-red-600">{pack.errors.description}</p>}
          </label>
          <label className="block">
            <span className="font-medium">Hashtags</span>
            <input className={input} value={pack.data.hashtags} onChange={(e) => pack.setData("hashtags", e.target.value)} />
            {pack.errors.hashtags && <p className="mt-1 text-sm text-red-600">{pack.errors.hashtags}</p>}
          </label>
          <button
            type="submit"
            disabled={pack.processing}
            className="rounded-md bg-zinc-950 px-4 py-2 font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-50 dark:text-zinc-950"
          >
            Save pack
          </button>
        </form>
      </section>
    </>
  );
}
