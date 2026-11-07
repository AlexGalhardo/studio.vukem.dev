import { Head, Link, usePage } from "@inertiajs/react";

import type { SharedProps } from "../types";

export default function Dashboard() {
  const user = usePage<SharedProps>().props.auth?.user;

  return (
    <>
      <Head title="Dashboard" />
      <h1 className="text-2xl font-semibold">Hello, {user?.name}</h1>
      <p className="mt-2">Fill a brief, let a model write the scene plan, and download the MP4.</p>
      <p className="mt-4 flex gap-4">
        <Link href="/videos/create" className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500">
          New video
        </Link>
        <Link href="/videos" className="px-4 py-2 text-indigo-600 hover:underline dark:text-indigo-400">
          My videos
        </Link>
      </p>
    </>
  );
}
