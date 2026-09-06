import { RunComparison } from "@/lib/api";

export function CompareRuns({ comparison, onClose }: { comparison: RunComparison; onClose: () => void }) {
  const allTags = Array.from(
    new Set([...Object.keys(comparison.profile_a), ...Object.keys(comparison.profile_b)])
  );

  return (
    <div className="flex flex-col gap-10">
      <p className="font-serif text-xl leading-relaxed text-parchment">
        The story didn&rsquo;t change. You did.
      </p>

      {comparison.diverging_choices.length > 0 && (
        <div className="flex flex-col gap-5">
          {comparison.diverging_choices.map((d, i) => (
            <div key={i} className="grid grid-cols-2 gap-4 border-t border-hairline pt-5">
              <div>
                <p className="mb-1 text-xs text-brass">Run {comparison.run_a}</p>
                <p className="text-sm text-parchment/90">{d.run_a_choice}</p>
              </div>
              <div>
                <p className="mb-1 text-xs text-slate">Run {comparison.run_b}</p>
                <p className="text-sm text-parchment/90">{d.run_b_choice}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {allTags.length > 0 && (
        <div className="flex flex-col gap-3 border-t border-hairline pt-8">
          <p className="text-sm text-muted">Profile shift</p>
          {allTags.map((tag) => (
            <div key={tag} className="flex items-center justify-between text-sm">
              <span className="text-parchment/80">{tag.replace(/_/g, " ")}</span>
              <span className="flex gap-4">
                <span className="text-brass">{comparison.profile_a[tag] ?? 0}</span>
                <span className="text-slate">{comparison.profile_b[tag] ?? 0}</span>
              </span>
            </div>
          ))}
        </div>
      )}

      <button onClick={onClose} className="self-start text-sm text-muted transition-colors hover:text-parchment">
        Back
      </button>
    </div>
  );
}
