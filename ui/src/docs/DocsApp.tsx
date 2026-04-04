import React, { useCallback, useEffect, useState } from "react";
import { requestJson } from "../lib/request";
import type { DocArticle, DocArticleSummary } from "./types";
import { DocViewer } from "./DocViewer";
import { DocEditor } from "./DocEditor";

type AppView = "list" | "detail" | "edit";

const DocsApp = () => {
  const [view, setView] = useState<AppView>("list");
  const [articles, setArticles] = useState<DocArticleSummary[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<DocArticle | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadArticles = useCallback(() => {
    setLoading(true);
    setError(null);
    requestJson<DocArticleSummary[]>("/api/v1/docs")
      .then((data) => {
        setArticles(data);
      })
      .catch((err: Error) => {
        setError(err.message || "Failed to load articles.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadArticles();
  }, [loadArticles]);

  const openArticle = useCallback((slug: string) => {
    setLoading(true);
    setError(null);
    requestJson<DocArticle>(`/api/v1/docs/${slug}`)
      .then((data) => {
        setSelectedArticle(data);
        setView("detail");
      })
      .catch((err: Error) => {
        setError(err.message || "Failed to load article.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleSave = useCallback(
    (content: string) => {
      if (!selectedArticle) {
        return;
      }
      setLoading(true);
      setError(null);
      const nextIsAiCreated = selectedArticle.is_ai_created ? false : selectedArticle.is_ai_created;
      requestJson<DocArticle>(`/api/v1/docs/${selectedArticle.slug}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content,
          is_ai_created: nextIsAiCreated
        })
      })
        .then((updated) => {
          setSelectedArticle(updated);
          setView("detail");
          loadArticles();
        })
        .catch((err: Error) => {
          setError(err.message || "Failed to save article.");
        })
        .finally(() => {
          setLoading(false);
        });
    },
    [selectedArticle, loadArticles]
  );

  const filteredArticles = articles.filter((a) => {
    const q = searchQuery.toLowerCase();
    return (
      !q ||
      a.title.toLowerCase().includes(q) ||
      a.tags.some((t) => t.toLowerCase().includes(q)) ||
      a.summary.toLowerCase().includes(q)
    );
  });

  if (view === "edit" && selectedArticle) {
    return (
      <DocEditor
        initialContent={selectedArticle.content}
        onSave={handleSave}
        onCancel={() => setView("detail")}
      />
    );
  }

  if (view === "detail" && selectedArticle) {
    return (
      <div id="docs-detail-view" className="card">
        <div className="docs-detail-header">
          <div className="docs-detail-header__left">
            <button
              id="docs-back-button"
              type="button"
              className="btn btn--secondary"
              onClick={() => {
                setView("list");
                setSelectedArticle(null);
              }}
            >
              ← Back
            </button>
            <h3 id="docs-detail-title" className="docs-detail-title">
              {selectedArticle.title}
            </h3>
          </div>
          <div className="docs-detail-header__right">
            {selectedArticle.is_ai_created && (
              <span id="docs-ai-badge" className="docs-ai-badge">
                AI Generated
              </span>
            )}
            {selectedArticle.tags.length > 0 && (
              <div id="docs-detail-tags" className="docs-detail-tags">
                {selectedArticle.tags.map((tag) => (
                  <span key={tag} className="status-badge status-badge--muted">
                    {tag}
                  </span>
                ))}
              </div>
            )}
            <button
              id="docs-edit-button"
              type="button"
              className="btn btn--primary"
              onClick={() => setView("edit")}
            >
              Edit
            </button>
          </div>
        </div>
        {error && (
          <p id="docs-detail-error" className="docs-error">
            {error}
          </p>
        )}
        <DocViewer content={selectedArticle.content} />
      </div>
    );
  }

  return (
    <div id="docs-list-view">
      <div className="card">
        <div className="settings-section__header">
          <div className="title-row">
            <h3 className="settings-card__title">Articles</h3>
          </div>
        </div>
        <div className="docs-search-row">
          <input
            id="docs-search-input"
            type="search"
            className="input"
            placeholder="Search by title, tag, or summary…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <p id="docs-list-error" className="docs-error">
          {error}
        </p>
      )}

      {loading && !articles.length && (
        <p id="docs-list-loading" className="docs-loading">
          Loading…
        </p>
      )}

      {!loading && !error && filteredArticles.length === 0 && (
        <p id="docs-list-empty" className="docs-empty">
          {searchQuery ? "No articles match your search." : "No articles yet."}
        </p>
      )}

      <div id="docs-article-list" className="docs-article-list">
        {filteredArticles.map((article) => (
          <button
            key={article.id}
            id={`docs-article-item-${article.slug}`}
            type="button"
            className="docs-article-card"
            onClick={() => openArticle(article.slug)}
          >
            <div className="docs-article-card__header">
              <span className="docs-article-card__title">{article.title}</span>
              {article.is_ai_created && (
                <span className="docs-ai-badge">AI Generated</span>
              )}
            </div>
            {article.summary && (
              <p className="docs-article-card__summary">{article.summary}</p>
            )}
            {article.tags.length > 0 && (
              <div className="docs-article-card__tags">
                {article.tags.map((tag) => (
                  <span key={tag} className="status-badge status-badge--muted">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};

export default DocsApp;
