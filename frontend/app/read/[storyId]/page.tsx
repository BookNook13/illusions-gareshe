"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  fetchCurrentNode,
  fetchProfile,
  submitChoice,
  fetchReflection,
  startReplay,
  compareRuns,
  StoryNodeView,
  ProfileView,
  ReflectionView,
  RunComparison,
  ApiError,
} from "@/lib/api";
import { Wordmark } from "@/components/Wordmark";
import { Reflection } from "@/components/Reflection";
import { CompareRuns } from "@/components/CompareRuns";

type ViewState =
  | { kind: "loading" }
  | { kind: "reading"; node: StoryNodeView }
  | { kind: "reflecting"; reflection: ReflectionView; profile: ProfileView }
  | { kind: "comparing"; comparison: RunComparison }
  | { kind: "error"; message: string };

export default function ReaderPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const router = useRouter();
  const { token, isReady } = useAuth();
  const [state, setState] = useState<ViewState>({ kind: "loading" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadCurrent = useCallback(async () => {
    if (!token) return;
    try {
      const node = await fetchCurrentNode(token, storyId);
      if (node.is_ending) {
        const [reflection, profile] = await Promise.all([
          fetchReflection(token, storyId),
          fetchProfile(token, storyId),
        ]);
        setState({ kind: "reflecting", reflection, profile });
      } else {
        setState({ kind: "reading", node });
      }
    } catch (err) {
      setState({ kind: "error", message: err instanceof ApiError ? err.message : "Couldn't load the story." });
    }
  }, [token, storyId]);

  useEffect(() => {
    if (!isReady) return;
    if (!token) {
      router.push("/");
      return;
    }
    loadCurrent();
  }, [isReady, token, router, loadCurrent]);

  async function handleChoice(choiceId: string) {
    if (!token || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const { node, profile } = await submitChoice(token, storyId, choiceId);
      if (node.is_ending) {
        const reflection = await fetchReflection(token, storyId);
        setState({ kind: "reflecting", reflection, profile });
      } else {
        setState({ kind: "reading", node });
      }
    } catch (err) {
      setState({ kind: "error", message: err instanceof ApiError ? err.message : "Something went wrong." });
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReplay() {
    if (!token) return;
    setState({ kind: "loading" });
    try {
      const { node } = await startReplay(token, storyId);
      setState({ kind: "reading", node });
    } catch (err) {
      setState({ kind: "error", message: err instanceof ApiError ? err.message : "Couldn't start a replay." });
    }
  }

  async function handleCompare(currentRun: number) {
    if (!token) return;
    try {
      const comparison = await compareRuns(token, storyId, currentRun - 1, currentRun);
      setState({ kind: "comparing", comparison });
    } catch (err) {
      setState({ kind: "error", message: err instanceof ApiError ? err.message : "Couldn't compare runs." });
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-reading flex-col px-6 py-16">
      <header className="mb-16 flex items-center justify-between">
        <Link href="/library">
          <Wordmark />
        </Link>
        {state.kind === "reading" && (
          <span className="text-xs text-muted">{state.node.chapter_title}</span>
        )}
      </header>

      {state.kind === "loading" && <p className="text-sm text-muted">Loading…</p>}

      {state.kind === "error" && (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-slate">{state.message}</p>
          <Link href="/library" className="text-sm text-muted transition-colors hover:text-parchment">
            Back to library
          </Link>
        </div>
      )}

      {state.kind === "reading" && (
        <article className="flex flex-col gap-10">
          <p className="whitespace-pre-line font-serif text-[19px] leading-[1.85] text-parchment">
            {state.node.text_content}
          </p>

          {state.node.choices.length > 0 && (
            <div className="flex flex-col gap-4 border-t border-hairline pt-8">
              <ul className="flex flex-col gap-4">
                {state.node.choices.map((choice) => (
                  <li key={choice.id}>
                    <button
                      onClick={() => handleChoice(choice.id)}
                      disabled={isSubmitting}
                      className="group flex items-baseline gap-3 text-left disabled:opacity-50"
                    >
                      <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full border border-muted transition-colors group-hover:border-brass group-hover:bg-brass" />
                      <span className="font-serif text-[17px] leading-relaxed text-parchment/90 transition-colors group-hover:text-brass">
                        {choice.display_text}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </article>
      )}

      {state.kind === "reflecting" && (
        <Reflection
          reflection={state.reflection}
          runNumber={state.profile.run_number}
          onReplay={handleReplay}
          onCompare={() => handleCompare(state.profile.run_number)}
          canCompare={state.profile.run_number > 1}
        />
      )}

      {state.kind === "comparing" && (
        <CompareRuns comparison={state.comparison} onClose={() => loadCurrent()} />
      )}
    </main>
  );
}
