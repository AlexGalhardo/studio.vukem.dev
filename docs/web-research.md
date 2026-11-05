# Web research — short-form video with LLMs and open source tools

Research date: 2026-11-04.

This note is the evidence behind Studio's pipeline. It records what is worth copying, what to leave out of the first milestone, and the license constraint that changes the renderer choice.

## Decision this research supports

Render motion graphics as code. Use a language model to write the script and the composition. Use FFmpeg to encode. Do not call a pixel-video model on the default path.

That choice is reversible. A photographed look can be a later adapter. It is a bad default: it needs a GPU or a per-second vendor bill, and the frames are harder to correct than a React or HTML composition.

## Pipelines worth copying

### OpenReels

[OpenReels](https://github.com/tsensei/OpenReels) is one command from a topic to a vertical MP4. The stages it names are the ones Studio's job record should keep, even when a stage is skipped:

| Stage | What it contributes |
| --- | --- |
| Research | The script is grounded in fetched facts, not only in the model |
| Script | Scene breaks, visual direction, emotional arc |
| Voice | Speech audio plus word times for captions |
| Visuals | Generated images, generated clips, or stock, with a retry when a match is bad |
| Music | A bed that follows the arc, ducked under the voice |
| Captions | Word-level karaoke, more than one style |
| Assembly | Remotion composites the vertical file and the transitions |
| Critique | A model scores the result |

Studio should store each of those artifacts on the job. Studio should not require all of them. A silent style skill has no voice stage.

### OpenMontage

[OpenMontage](https://metavert.io/openmontage) (reported 2026-10-24) treats the coding agent as the orchestrator. There is no second workflow engine. The repository gives the agent three things: pipeline manifests, skills, and a render backend.

The part worth copying is the manifest, not the "agent is the only orchestrator" deployment. A manifest names the stages, the skill each stage needs, what the review checks, where a person must approve, and a time or money budget. OpenMontage ships several manifests (explainer, avatar, documentary montage, screen demo, talking head, localization). Studio can start with two: `silent-motion` and `spoken-explainer`.

The same report lists three render backends chosen at proposal time: Remotion for data-driven explainers, HyperFrames for motion graphics and HTML, FFmpeg for assembly and for a pan-and-zoom fallback. That is the same split as [Renderers](../site/content/docs/tools/renderers.mdx).

It also names a post-render review: `ffprobe`, frame extraction, audio level, subtitle checks, and a refusal to deliver a file that fails. Studio's [QA](../site/content/docs/pipeline/qa.mdx) page is that idea, with numbers.

Provider adapters in that report cover hosted video models (Kling, Veo, Runway, Sora, and others) and local weights (Wan, HunyuanVideo, CogVideoX, LTX-Video, sometimes through ComfyUI). Those adapters are research, not milestone one.

### Video Wizard

[video-wizard](https://github.com/el-frontend/video-wizard) is a self-hosted clipper: Whisper captions, a model scores 30–90 second spans, Remotion renders. The useful product facts:

- A job queue with retry, so the page stays responsive while a render runs
- Caption templates as data (the repo names viral, minimal, hormozi, mrbeast, and others), not as one-off code
- More than one delivery shape: 9:16, 1:1, 4:5, 16:9

Studio's first milestone renders the brief's primary ratio only. Extra ratios are a later export of the same plan.

### Local short-form generators

A local pipeline described in November 2026 ([Shorts Generator](https://github.com/CosmoJelly/short-form-video-generator)) chains a local model for the script, a local voice (XTTS), Whisper for cue times, and FFmpeg for a 1080x1920 file. No GPU is required for that stack if the pictures are stock or generated stills rather than diffusion video.

[MoneyPrinterTurbo](https://www.opensourcealternatives.to/blog/open-source-ai-video-generators) is the other end of the same idea: topic in, stock footage, subtitles, music, MP4 out, MIT license, no GPU. The comparison article (2026-10-17) also says ComfyUI plus Wan weights when the goal is model control, and OpenMontage when the goal is an agent production with a provenance record.

Studio's first pictures come from a style skill (code), which is closer to Remotion and HyperFrames than to stock montage. Stock is an optional b-roll stage with a stored license, matching the media skills already in this repository.

## Remotion and HyperFrames

Both tools open a browser, capture a frame, and encode with FFmpeg. The authoring model differs.

| | HyperFrames | Remotion |
| --- | --- | --- |
| You write | HTML, CSS, JavaScript | React |
| Timing | The renderer seeks CSS, GSAP, Lottie, Three.js, or WAAPI to the frame | Code reads the frame number |
| License | Apache-2.0 | Remotion license. Free for individuals, non-profits, and for-profit companies up to three people. A company license above that |
| Agent skills | About twenty, including a workflow router | About a dozen, focused on correct Remotion code |
| Maturity | Released 2026 by HeyGen | Started 2020, large template and docs base |

Sources: [HyperFrames vs Remotion](https://hyperframes.heygen.com/guides/hyperframes-vs-remotion), [Open Skills guide](https://openskills.app/guides/hyperframes-vs-remotion) (2026-10-07), [Motionflare comparison](https://motionflare.ai/compare/hyperframes-vs-remotion) (2026-10-10), [Socialvik license note](https://www.socialvik.com/blog/hyperframes-vs-remotion-render-time) (2026-10-16).

HeyGen's own comparison measured a similar time-to-MP4 and a smaller dependency install for HyperFrames on one sample. That sample is one prompt, not a benchmark Studio should quote as a general speed claim.

Remotion publishes skills with `npx skills add remotion-dev/skills`. HyperFrames publishes a router skill that picks a workflow. Studio should vendor the skill it actually runs and pin the version, the same way this repository vendors the kits under `.agents/skills/`. Do not fetch skills from the network during a render.

### License consequence

Automated rendering is the product. If a for-profit company of four or more people runs Remotion, the company license applies. Published figures in October 2026 were about $25 per seat per month, or $0.01 per render with a $100 per month minimum. HyperFrames does not have that seat threshold.

The dashboard may offer both. The default for a new project that has not answered the license question is HyperFrames when the skill is HTML, and Remotion when the skill is React and the operator has confirmed the license. The sidecar records which one ran.

## Techniques that change the product

These are production rules, not model tricks.

- **Native frame size.** Compose at 1080x1920 for a vertical short. Cropping a landscape master afterwards throws away the layout.
- **Muted playback.** Burn captions in. Many viewers never turn sound on. Word times come from Whisper, not from evenly split lines.
- **Opening.** The first one to two seconds carry the reason to stay. The retention skill already cuts that opening last, from the strongest pictures in the finished piece. The pipeline should keep that order: picture first, opening last.
- **One claim.** A 15-second cut survives one idea. The brief's goal field is that idea. The compiler rejects a plan that adds a second call to action.
- **Safe areas.** Platform buttons cover the bottom and the right edge. Style skills must keep type inside a safe rect. The QA page does not measure this yet. It is a later check, not a guess in the encoder.
- **Loudness.** Studio targets -14 LUFS integrated and -1.5 dBTP when a voice exists. Platforms are not identical. The number is a project rule so two jobs match, not a claim that every network normalizes the same way.
- **License on every external asset.** B-roll and music store the license in the sidecar. No record, no asset in the file. The media skills already refuse a download without an explicit yes.
- **Deterministic rerun.** The same plan, skill version, and model output should render the same frames. Diffusion video does not give that. Code does.
- **Show the prompt.** The operator does not write it, but the job keeps it. A bad video is debuggable only if the instruction is still there.

## What not to take from the catalogs

`docs/recommend-tools.md` lists hosted editors (Opus Clip, Descript, Submagic, Pictory, Fliki, HeyGen, ElevenLabs). They are competitive references:

- Opus Clip and Video Wizard: long video to scored shorts
- Submagic: captions, punch-in, sound effects
- HeyGen: avatar. Out of scope until a brief asks for a person who is not in the room, and even then a consent record comes first
- ElevenLabs: a voice adapter, not the mixer

Do not wrap those products as the core. The core has to render with FFmpeg and one of the two code renderers when no API key is set.

## Sources

- OpenReels — <https://github.com/tsensei/OpenReels>
- OpenMontage overview — <https://metavert.io/openmontage> — 2026-10-24
- Remotion overview — <https://metavert.io/remotion> — 2026-10-24
- HyperFrames repository — <https://github.com/heygen-com/hyperframes>
- HyperFrames vs Remotion — <https://hyperframes.heygen.com/guides/hyperframes-vs-remotion> — 2026-10-26
- Open Skills, HyperFrames vs Remotion — <https://openskills.app/guides/hyperframes-vs-remotion> — 2026-10-07
- Motionflare comparison — <https://motionflare.ai/compare/hyperframes-vs-remotion> — 2026-10-10
- Socialvik, license and a timed render — <https://www.socialvik.com/blog/hyperframes-vs-remotion-render-time> — 2026-10-16
- Open source AI video generators, eight compared — <https://www.opensourcealternatives.to/blog/open-source-ai-video-generators> — 2026-10-17
- video-wizard — <https://github.com/el-frontend/video-wizard>
- short-form-video-generator — <https://github.com/CosmoJelly/short-form-video-generator>
- OpenSSF Scorecard badge — <https://github.com/ossf/scorecard#scorecard-badges>
