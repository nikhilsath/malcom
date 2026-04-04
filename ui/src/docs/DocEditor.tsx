import React, { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { indentWithTab } from "@codemirror/commands";
import { bracketMatching, indentOnInput, syntaxHighlighting, defaultHighlightStyle } from "@codemirror/language";
import { markdown } from "@codemirror/lang-markdown";

interface DocEditorProps {
  initialContent: string;
  onSave: (content: string) => void;
  onCancel: () => void;
}

export const DocEditor = ({ initialContent, onSave, onCancel }: DocEditorProps) => {
  const editorHostRef = useRef<HTMLDivElement>(null);
  const editorViewRef = useRef<EditorView | null>(null);
  const [preview, setPreview] = useState(initialContent);

  useEffect(() => {
    if (!editorHostRef.current) {
      return undefined;
    }

    const view = new EditorView({
      parent: editorHostRef.current,
      state: EditorState.create({
        doc: initialContent,
        extensions: [
          history(),
          indentOnInput(),
          bracketMatching(),
          syntaxHighlighting(defaultHighlightStyle),
          keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
          EditorView.lineWrapping,
          EditorView.theme({
            "&": {
              height: "100%",
              backgroundColor: "#fbfdff",
              color: "#0f172a",
              fontSize: "14px"
            },
            ".cm-content": {
              fontFamily: "SFMono-Regular, Consolas, Liberation Mono, monospace",
              padding: "16px"
            },
            ".cm-gutters": {
              backgroundColor: "#f8fafc",
              color: "#64748b",
              borderRight: "1px solid #dbe3ef"
            }
          }),
          markdown(),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              setPreview(update.state.doc.toString());
            }
          })
        ]
      })
    });

    editorViewRef.current = view;

    return () => {
      view.destroy();
      editorViewRef.current = null;
    };
  }, []);

  const handleSave = useCallback(() => {
    const content = editorViewRef.current?.state.doc.toString() ?? preview;
    onSave(content);
  }, [onSave, preview]);

  return (
    <div className="docs-editor-split">
      <div className="docs-editor-split__panes">
        <div className="docs-editor-split__pane docs-editor-split__pane--editor">
          <div ref={editorHostRef} className="docs-editor-host" />
        </div>
        <div className="docs-editor-split__pane docs-editor-split__pane--preview">
          <div className="docs-viewer">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{preview}</ReactMarkdown>
          </div>
        </div>
      </div>
      <div className="docs-editor-actions">
        <button type="button" className="btn btn--primary" onClick={handleSave}>
          Save
        </button>
        <button type="button" className="btn btn--secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
};
