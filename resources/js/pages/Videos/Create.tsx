import { Head, useForm } from "@inertiajs/react";
import type { FormEvent } from "react";

import type { Skill } from "../../types";

interface Props {
  skills: Skill[];
  models: string[];
  ratios: string[];
  defaults: { skill: string; model: string; ratio: string; duration: number; language: string };
  limits: { min: number; max: number };
}

const input =
  "mt-1 block w-full rounded-md border border-zinc-300 bg-transparent px-3 py-2 focus:border-indigo-500 focus:outline-none dark:border-zinc-700";

type TextName = "goal" | "audience" | "subject" | "language" | "cta";
type AreaName = "facts" | "links";
type SelectName = "ratio" | "skill" | "model";

export default function Create({ skills, models, ratios, defaults, limits }: Props) {
  const form = useForm({
    goal: "",
    audience: "",
    subject: "",
    duration: defaults.duration,
    ratio: defaults.ratio,
    skill: defaults.skill,
    language: defaults.language,
    model: defaults.model,
    facts: "",
    links: "",
    cta: "",
  });
  const errors = form.errors as Record<string, string | undefined>;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    form.post("/videos");
  };

  const text = (name: TextName, label: string, hint?: string) => (
    <label className="block">
      <span className="font-medium">{label}</span>
      {hint ? <span className="ml-2 text-sm text-zinc-500">{hint}</span> : null}
      <input className={input} name={name} value={form.data[name]} onChange={(e) => form.setData(name, e.target.value)} />
      {errors[name] && <p className="mt-1 text-sm text-red-600">{errors[name]}</p>}
    </label>
  );

  const area = (name: AreaName, label: string, hint: string) => (
    <label className="block">
      <span className="font-medium">{label}</span>
      <span className="ml-2 text-sm text-zinc-500">{hint}</span>
      <textarea className={input} name={name} rows={3} value={form.data[name]} onChange={(e) => form.setData(name, e.target.value)} />
      {errors[name] && <p className="mt-1 text-sm text-red-600">{errors[name]}</p>}
    </label>
  );

  const select = (name: SelectName, label: string, options: string[]) => (
    <label className="block">
      <span className="font-medium">{label}</span>
      <select className={input} name={name} value={form.data[name]} onChange={(e) => form.setData(name, e.target.value)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
      {errors[name] && <p className="mt-1 text-sm text-red-600">{errors[name]}</p>}
    </label>
  );

  return (
    <>
      <Head title="New video" />
      <h1 className="mb-4 text-2xl font-semibold">New video</h1>
      <form onSubmit={submit} className="max-w-2xl space-y-4">
        {errors.form && (
          <p role="alert" className="text-red-600">
            {errors.form}
          </p>
        )}
        {text("goal", "Goal", "What should the viewer do or understand?")}
        {text("audience", "Audience")}
        {text("subject", "Offer or subject")}
        <label className="block">
          <span className="font-medium">Duration (seconds)</span>
          <input
            className={input}
            type="number"
            name="duration"
            min={limits.min}
            max={limits.max}
            value={form.data.duration}
            onChange={(e) => form.setData("duration", Number(e.target.value))}
          />
          {errors.duration && <p className="mt-1 text-sm text-red-600">{errors.duration}</p>}
        </label>
        {select("ratio", "Aspect ratio", ratios)}
        {select("skill", "Style skill", skills.map((s) => s.id))}
        {text("language", "Spoken language")}
        {select("model", "Model", models)}
        {area("facts", "Must-keep facts", "One per line. The script may not contradict them.")}
        {area("links", "Reference links", "One URL per line.")}
        {text("cta", "Call to action", "Optional")}
        <button
          type="submit"
          disabled={form.processing}
          className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          Create video
        </button>
      </form>
    </>
  );
}
