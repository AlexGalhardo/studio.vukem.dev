import { Head } from "@inertiajs/react";

import BriefForm from "../../components/BriefForm";

interface Props {
  styles: string[];
  ratios: string[];
}

export default function Create({ styles, ratios }: Props) {
  return (
    <>
      <Head title="New video" />
      <h1 className="mb-4 text-2xl font-semibold">New video</h1>
      <p className="mb-6 max-w-2xl text-zinc-600 dark:text-zinc-400">
        The form is the brief. The server compiles the prompt, plans the cut, and renders a file. A silent cut needs no API key.
      </p>
      <BriefForm styles={styles} ratios={ratios} />
    </>
  );
}
