import { useForm } from "@inertiajs/react";
import type { FormEvent } from "react";

const input =
  "mt-1 block w-full rounded-md border border-zinc-300 bg-transparent px-3 py-2 focus:border-indigo-500 focus:outline-none dark:border-zinc-700";

interface Props {
  styles: string[];
  ratios: string[];
}

export default function BriefForm({ styles, ratios }: Props) {
  const form = useForm({
    goal: "",
    audience: "",
    subject: "",
    duration: "6",
    ratio: "9:16",
    style_skill: styles[0] ?? "traco-simples",
    language: "en",
    facts: "",
    links: "",
    call_to_action: "",
    voice: "none",
    music_license: "",
    voice_file: null as File | null,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    form.post("/jobs", { forceFormData: true });
  };

  const error = (name: keyof typeof form.data) => {
    const message = form.errors[name];
    return message ? <p className="mt-1 text-sm text-red-600">{message}</p> : null;
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="block">
        <span className="font-medium">Goal</span>
        <input className={input} value={form.data.goal} onChange={(e) => form.setData("goal", e.target.value)} />
        {error("goal")}
      </label>
      <label className="block">
        <span className="font-medium">Audience</span>
        <input className={input} value={form.data.audience} onChange={(e) => form.setData("audience", e.target.value)} />
        {error("audience")}
      </label>
      <label className="block">
        <span className="font-medium">Offer or subject</span>
        <input className={input} value={form.data.subject} onChange={(e) => form.setData("subject", e.target.value)} />
        {error("subject")}
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="font-medium">Duration (seconds)</span>
          <input
            className={input}
            type="number"
            min={5}
            max={300}
            value={form.data.duration}
            onChange={(e) => form.setData("duration", e.target.value)}
          />
          {error("duration")}
        </label>
        <label className="block">
          <span className="font-medium">Aspect ratio</span>
          <select className={input} value={form.data.ratio} onChange={(e) => form.setData("ratio", e.target.value)}>
            {ratios.map((ratio) => (
              <option key={ratio} value={ratio}>
                {ratio}
              </option>
            ))}
          </select>
          {error("ratio")}
        </label>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="font-medium">Style skill</span>
          <select className={input} value={form.data.style_skill} onChange={(e) => form.setData("style_skill", e.target.value)}>
            {styles.map((style) => (
              <option key={style} value={style}>
                {style}
              </option>
            ))}
          </select>
          {error("style_skill")}
        </label>
        <label className="block">
          <span className="font-medium">Spoken language</span>
          <input className={input} value={form.data.language} onChange={(e) => form.setData("language", e.target.value)} />
          {error("language")}
        </label>
      </div>
      <label className="block">
        <span className="font-medium">Must-keep facts</span>
        <textarea
          className={input}
          rows={4}
          value={form.data.facts}
          onChange={(e) => form.setData("facts", e.target.value)}
          placeholder="One fact per line"
        />
        {error("facts")}
      </label>
      <label className="block">
        <span className="font-medium">Reference links</span>
        <textarea className={input} rows={2} value={form.data.links} onChange={(e) => form.setData("links", e.target.value)} />
        {error("links")}
      </label>
      <label className="block">
        <span className="font-medium">Call to action</span>
        <input className={input} value={form.data.call_to_action} onChange={(e) => form.setData("call_to_action", e.target.value)} />
        {error("call_to_action")}
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="font-medium">Voice</span>
          <select className={input} value={form.data.voice} onChange={(e) => form.setData("voice", e.target.value)}>
            <option value="none">Silent</option>
            <option value="tts">Local text to speech</option>
            <option value="upload">Upload a WAV</option>
          </select>
          {error("voice")}
        </label>
        <label className="block">
          <span className="font-medium">Music license</span>
          <input
            className={input}
            value={form.data.music_license}
            onChange={(e) => form.setData("music_license", e.target.value)}
            placeholder="Leave empty to ship without a bed"
          />
          {error("music_license")}
        </label>
      </div>
      {form.data.voice === "upload" ? (
        <label className="block">
          <span className="font-medium">Voice recording (WAV)</span>
          <input
            className={input}
            type="file"
            accept="audio/wav,audio/wave,.wav"
            onChange={(e) => form.setData("voice_file", e.target.files?.[0] ?? null)}
          />
          {error("voice_file")}
        </label>
      ) : null}
      <button
        type="submit"
        disabled={form.processing}
        className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
      >
        Render
      </button>
    </form>
  );
}
