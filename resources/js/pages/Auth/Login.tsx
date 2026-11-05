import { Head } from "@inertiajs/react";

export default function Login() {
  return (
    <>
      <Head title="Log in" />
      <h1 className="mb-6 text-2xl font-semibold">Log in</h1>
      <a
        href="/auth/google/redirect"
        className="inline-flex w-full items-center justify-center rounded-md bg-zinc-950 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200"
      >
        Continue with Google
      </a>
    </>
  );
}
