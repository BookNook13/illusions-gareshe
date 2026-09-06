"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { fetchLibrary, StorySummary, ApiError } from "@/lib/api";
import { Wordmark } from "@/components/Wordmark";

export default function LibraryPage() {
  const router = useRouter();
  const { token, isReady, signOut } = useAuth();
  const [stories, setStories] = useState<StorySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isReady) return;
    if (!token) {
      router.push("/");
      return;
    }
    fetchLibrary(token)
      .then(setStories)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load the library."));
  }, [isReady, token, router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-reading flex-col px-6 py-16">
      <header className="mb-16 flex items-center justify-between">
        <Wordmark />
        <button onClick={signOut} className="text-sm text-muted transition-colors hover:text-parchment">
          Sign out
        </button>
      </header>

      <h1 className="mb-12 font-serif text-2xl leading-snug text-parchment">
        Every story here ends the same way it began.
        <br />
        What changes is you.
      </h1>

      {error && <p className="text-sm text-slate">{error}</p>}

      {stories === null && !error && <p className="text-sm text-muted">Loading…</p>}

      {stories?.length === 0 && (
        <p className="text-sm text-muted">
          No stories are published yet. Publish one from the admin dashboard to see it here.
        </p>
      )}

      <ul className="flex flex-col">
        {stories?.map((story) => (
          <li key={story.id} className="border-t border-hairline py-6 first:border-t-0">
            <Link href={`/read/${story.id}`} className="group flex flex-col gap-2">
              <span className="font-serif text-xl text-parchment transition-colors group-hover:text-brass">
                {story.title}
              </span>
              {story.description && (
                <span className="text-sm leading-relaxed text-muted">{story.description}</span>
              )}
              <span className="text-xs text-muted">
                {story.estimated_minutes} min
                {story.themes.length > 0 && ` · ${story.themes.map((t) => t.name).join(", ")}`}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
