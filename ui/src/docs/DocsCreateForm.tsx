import React, { useCallback, useState } from "react";
import { DocEditor } from "./DocEditor";

interface DocsCreateFormProps {
  onSave: (fields: {
    slug: string;
    title: string;
    summary: string;
    tags: string[];
    content: string;
  }) => void;
  onCancel: () => void;
  saving?: boolean;
}

const titleToSlug = (title: string): string =>
  title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

const DocsCreateForm = ({ onSave, onCancel, saving = false }: DocsCreateFormProps) => {
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [summary, setSummary] = useState("");
  const [tags, setTags] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleTitleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setTitle(value);
      if (!slugEdited) {
        setSlug(titleToSlug(value));
      }
    },
    [slugEdited]
  );

  const handleSlugChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSlug(e.target.value);
    setSlugEdited(true);
  }, []);

  const handleSubmit = useCallback(
    (editorContent: string) => {
      const errs: Record<string, string> = {};
      if (!title.trim()) {
        errs.title = "Title is required.";
      }
      if (!slug.trim()) {
        errs.slug = "Slug is required.";
      } else if (!/^[a-z0-9-]+$/.test(slug.trim())) {
        errs.slug = "Slug must contain only lowercase letters, numbers, and hyphens.";
      }
      if (Object.keys(errs).length > 0) {
        setErrors(errs);
        return;
      }
      setErrors({});
      onSave({
        title: title.trim(),
        slug: slug.trim(),
        summary: summary.trim(),
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        content: editorContent
      });
    },
    [title, slug, summary, tags, onSave]
  );

  return (
    <div id="docs-create-form">
      <div className="card">
        <div className="settings-section__header">
          <div className="title-row">
            <h3 className="settings-card__title">New Article</h3>
          </div>
        </div>
        <div className="docs-create-fields">
          <div className="docs-create-field">
            <label className="docs-create-label" htmlFor="docs-create-title">
              Title <span className="docs-create-required">*</span>
            </label>
            <input
              id="docs-create-title"
              type="text"
              className={`input${errors.title ? " input--error" : ""}`}
              placeholder="Article title"
              value={title}
              onChange={handleTitleChange}
              disabled={saving}
            />
            {errors.title && <p className="docs-error">{errors.title}</p>}
          </div>
          <div className="docs-create-field">
            <label className="docs-create-label" htmlFor="docs-create-slug">
              Slug <span className="docs-create-required">*</span>
            </label>
            <input
              id="docs-create-slug"
              type="text"
              className={`input${errors.slug ? " input--error" : ""}`}
              placeholder="article-slug"
              value={slug}
              onChange={handleSlugChange}
              disabled={saving}
            />
            {errors.slug && <p className="docs-error">{errors.slug}</p>}
          </div>
          <div className="docs-create-field">
            <label className="docs-create-label" htmlFor="docs-create-summary">
              Summary
            </label>
            <input
              id="docs-create-summary"
              type="text"
              className="input"
              placeholder="Brief description (optional)"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              disabled={saving}
            />
          </div>
          <div className="docs-create-field">
            <label className="docs-create-label" htmlFor="docs-create-tags">
              Tags
            </label>
            <input
              id="docs-create-tags"
              type="text"
              className="input"
              placeholder="Comma-separated tags (optional)"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              disabled={saving}
            />
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "12px" }}>
        <div className="settings-section__header">
          <div className="title-row">
            <h3 className="settings-card__title">Content</h3>
          </div>
        </div>
        <DocEditor
          initialContent=""
          onSave={(editorContent) => handleSubmit(editorContent)}
          onCancel={onCancel}
          saveLabel="Create Article"
        />
      </div>
    </div>
  );
};

export default DocsCreateForm;
