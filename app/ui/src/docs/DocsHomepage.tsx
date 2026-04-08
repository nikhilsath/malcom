import React, { useEffect } from "react";

const DocsHomepage = () => {
  useEffect(() => {
    const createButton = document.getElementById("docs-create-button");
    const handleCreate = () => {
      window.location.href = "library.html?create=1";
    };
    createButton?.addEventListener("click", handleCreate);
    return () => createButton?.removeEventListener("click", handleCreate);
  }, []);

  return (
    <div id="docs-homepage">
      <div className="card">
        <div className="settings-section__header">
          <div className="title-row">
            <h3 className="settings-card__title">How Documentation Works</h3>
          </div>
        </div>
        <div className="docs-homepage-body">
          <p className="docs-homepage-intro">
            Documentation articles are written in <strong>Markdown</strong> and stored as{" "}
            <code className="docs-homepage-code">.md</code> files inside the{" "}
            <code className="docs-homepage-code">docs/</code> directory at the project root.
            The system automatically syncs files from that directory into the database so they
            can be searched, browsed, and edited from the UI.
          </p>

          <div className="docs-homepage-features">
            <div className="docs-homepage-feature">
              <span className="docs-homepage-feature__icon">📄</span>
              <div>
                <strong>Markdown format</strong>
                <p>Articles use standard Markdown syntax — headings, lists, code blocks, links, and images all work out of the box.</p>
              </div>
            </div>
            <div className="docs-homepage-feature">
              <span className="docs-homepage-feature__icon">✅</span>
              <div>
                <strong>GitHub Flavored Markdown (GFM)</strong>
                <p>Tables, strikethrough text, task lists, and fenced code blocks with syntax highlighting are fully supported.</p>
              </div>
            </div>
            <div className="docs-homepage-feature">
              <span className="docs-homepage-feature__icon">🗂️</span>
              <div>
                <strong>File-backed storage</strong>
                <p>Each article maps to a <code className="docs-homepage-code">.md</code> file in <code className="docs-homepage-code">docs/</code>. Editing in the UI writes back to the file automatically.</p>
              </div>
            </div>
            <div className="docs-homepage-feature">
              <span className="docs-homepage-feature__icon">✏️</span>
              <div>
                <strong>Built-in editor</strong>
                <p>The Library includes a split-pane editor with live preview so you can write and see the rendered output side by side.</p>
              </div>
            </div>
          </div>

          <div className="docs-homepage-actions">
            <a href="library.html" className="btn btn--primary">Browse Library →</a>
            <a href="library.html?create=1" className="btn btn--secondary">Create Article</a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocsHomepage;
