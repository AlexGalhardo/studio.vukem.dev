import { Head, Link } from "@inertiajs/react";

import type { JobListItem } from "../../types";

export default function Index({ jobs }: { jobs: JobListItem[] }) {
  return (
    <>
      <Head title="Videos" />
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Videos</h1>
        <Link href="/jobs/create" className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500">
          New video
        </Link>
      </div>
      {jobs.length === 0 ? (
        <p className="mt-6 text-zinc-500">No videos yet.</p>
      ) : (
        <table className="mt-6 w-full text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-200 dark:border-zinc-800">
              <th className="py-2 font-medium">Subject</th>
              <th className="py-2 font-medium">Status</th>
              <th className="py-2 font-medium">Duration</th>
              <th className="py-2 font-medium">Style</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id} className="border-b border-zinc-100 dark:border-zinc-900">
                <td className="py-2">
                  <Link href={`/jobs/${job.id}`} className="hover:underline">
                    {job.subject}
                  </Link>
                </td>
                <td className="py-2">{job.status}</td>
                <td className="py-2">{job.duration}s</td>
                <td className="py-2">{job.style_skill}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
