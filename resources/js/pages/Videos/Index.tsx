import { Head, Link } from "@inertiajs/react";

import type { Video } from "../../types";

export default function Index({ videos }: { videos: Video[] }) {
  return (
    <>
      <Head title="Videos" />
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Videos</h1>
        <Link href="/videos/create" className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500">
          New video
        </Link>
      </div>
      {videos.length === 0 ? (
        <p>No videos yet. Create the first one from a brief.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr>
              <th className="py-2">Title</th>
              <th>Status</th>
              <th>Style</th>
              <th>Model</th>
            </tr>
          </thead>
          <tbody>
            {videos.map((v) => (
              <tr key={v.id} className="border-t border-zinc-200 dark:border-zinc-800">
                <td className="py-2">
                  <Link href={`/videos/${v.id}`} className="text-indigo-600 hover:underline dark:text-indigo-400">
                    {v.title || `Video ${v.id}`}
                  </Link>
                </td>
                <td>{v.status}</td>
                <td>{v.skill_id}</td>
                <td>{v.model_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
