import { useMemo, useState } from "react";
import type { DataFlowToken } from "./data-flow";

type Props = {
  idPrefix: string;
  tokens: DataFlowToken[];
  onInsert: (token: string) => void;
  description?: string;
};

export const TokenPicker = ({ idPrefix, tokens, onInsert, description }: Props) => {
  const [selectedToken, setSelectedToken] = useState(tokens[0]?.token || "");

  const groupedTokens = useMemo(() => {
    const map = new Map<string, DataFlowToken[]>();
    tokens.forEach((token) => {
      const current = map.get(token.source) || [];
      current.push(token);
      map.set(token.source, current);
    });
    return Array.from(map.entries());
  }, [tokens]);

  return (
    <div id={`${idPrefix}-token-picker`} className="automation-field automation-field--full automation-field__info">
      <div id={`${idPrefix}-token-picker-label`} className="automation-field__label">Insert variable token</div>
      {description ? (
        <div id={`${idPrefix}-token-picker-description`} className="automation-switch-field__description">{description}</div>
      ) : null}

      <div id={`${idPrefix}-token-picker-controls`} className="automation-field-group">
        <select
          id={`${idPrefix}-token-picker-input`}
          className="automation-native-select"
          value={selectedToken}
          onChange={(event) => setSelectedToken(event.target.value)}
        >
          {groupedTokens.map(([source, sourceTokens]) => (
            <optgroup key={source} label={source}>
              {sourceTokens.map((token) => (
                <option key={token.id} value={token.token}>{`${token.label} (${token.token})`}</option>
              ))}
            </optgroup>
          ))}
        </select>
        <button
          id={`${idPrefix}-token-picker-insert`}
          type="button"
          className="button button--secondary"
          onClick={() => {
            if (!selectedToken) {
              return;
            }
            onInsert(selectedToken);
          }}
        >
          Insert token
        </button>
      </div>
    </div>
  );
};
