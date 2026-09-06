import { ReflectionView } from "@/lib/api";

export function Reflection({
  reflection,
  runNumber,
  onReplay,
  onCompare,
  canCompare,
}: {
  reflection: ReflectionView;
  runNumber: number;
  onReplay: () => void;
  onCompare: () => void;
  canCompare: boolean;
}) {
  return (
    <div className="flex flex-col gap-10">
      <div>
        <p className="mb-3 text-xs text-muted">Run {runNumber}, finished</p>
        <p className="font-serif text-xl leading-relaxed text-parchment">{reflection.summary_text}</p>
      </div>

      {reflection.interpretations.length > 0 && (
        <div className="flex flex-col gap-4 border-t border-hairline pt-8">
          <p className="text-sm text-muted">Where this came from</p>
          <ul className="flex flex-col gap-4">
            {reflection.interpretations.map((interp) => (
              <li key={interp.id} className="flex items-baseline gap-3">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brass" />
                <span className="text-sm leading-relaxed text-parchment/90">
                  You chose <em className="font-serif not-italic text-brass">“{interp.choice_text}”</em>
                  {interp.reader_facing_description
                    ? ` — ${interp.reader_facing_description}`
                    : ` (${interp.tag_name})`}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-6 border-t border-hairline pt-8">
        <button
          onClick={onReplay}
          className="border border-brass px-5 py-2 text-sm text-brass transition-colors hover:bg-brass hover:text-ink"
        >
          Replay this story
        </button>
        {canCompare && (
          <button onClick={onCompare} className="text-sm text-slate transition-colors hover:text-parchment">
            Compare with run {runNumber - 1}
          </button>
        )}
      </div>
    </div>
  );
}
