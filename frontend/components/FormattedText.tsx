import type { ReactNode } from "react";

/** Renders the agent's reply text with real structure -- numbered/bulleted
 * lists as actual lists, a short leading label ("Recommendation:", "What
 * it means —") bolded, and literal **bold** honored if the model happens
 * to emit it. The model isn't instructed to use markdown syntax and
 * mostly doesn't; this reads the plain-prose structure it already
 * produces (per prompt.py's four-part turn shape) rather than depending on
 * a stricter prompt contract. A single `<p className="whitespace-pre-wrap">`
 * previously rendered all of this as one undifferentiated block. */

const ORDERED_RE = /^\s*\d+[).]\s+/;
const BULLET_RE = /^\s*[-•]\s+/;
const LABEL_MAX_WORDS = 6;
const LABEL_MAX_CHARS = 44;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return part ? <span key={`${keyPrefix}-${i}`}>{part}</span> : null;
  });
}

function splitLeadingLabel(line: string): { label: string | null; rest: string } {
  const colon = line.match(/^([^:\n]{1,44}):\s*(.*)$/);
  if (colon) {
    const [, label, rest] = colon;
    if (label.trim().split(/\s+/).length <= LABEL_MAX_WORDS && label.length <= LABEL_MAX_CHARS) {
      return { label: `${label}:`, rest };
    }
  }
  const dash = line.match(/^([^—\n]{1,44})\s+—\s+(.*)$/);
  if (dash) {
    const [, label, rest] = dash;
    if (label.trim().split(/\s+/).length <= LABEL_MAX_WORDS && label.length <= LABEL_MAX_CHARS) {
      return { label: `${label} —`, rest };
    }
  }
  return { label: null, rest: line };
}

function Paragraph({ text, keyPrefix }: { text: string; keyPrefix: string }) {
  const [firstLine, ...restLines] = text.split("\n");
  const { label, rest } = splitLeadingLabel(firstLine);
  return (
    <p>
      {label && <strong>{label} </strong>}
      {renderInline(label ? rest : firstLine, `${keyPrefix}-0`)}
      {restLines.map((line, i) => (
        <span key={`${keyPrefix}-br${i}`}>
          <br />
          {renderInline(line, `${keyPrefix}-${i + 1}`)}
        </span>
      ))}
    </p>
  );
}

interface Block {
  type: "paragraph" | "ordered" | "bullet";
  header: string | null;
  lines: string[];
}

function classifyBlock(block: string): Block {
  const lines = block.split("\n").filter((l) => l.trim().length > 0);
  if (lines.length === 0) return { type: "paragraph", header: null, lines: [] };

  if (lines.every((l) => ORDERED_RE.test(l))) return { type: "ordered", header: null, lines };
  if (lines.every((l) => BULLET_RE.test(l))) return { type: "bullet", header: null, lines };

  const [first, ...rest] = lines;
  if (!ORDERED_RE.test(first) && !BULLET_RE.test(first) && rest.length > 0) {
    if (rest.every((l) => ORDERED_RE.test(l))) return { type: "ordered", header: first, lines: rest };
    if (rest.every((l) => BULLET_RE.test(l))) return { type: "bullet", header: first, lines: rest };
  }

  return { type: "paragraph", header: null, lines };
}

export default function FormattedText({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).filter((b) => b.trim().length > 0);

  return (
    <div className="text-ink flex flex-col gap-2.5 text-sm">
      {blocks.map((block, bi) => {
        const keyPrefix = `b${bi}`;
        const { type, header, lines } = classifyBlock(block);

        if (type === "ordered" || type === "bullet") {
          const List = type === "ordered" ? "ol" : "ul";
          return (
            <div key={keyPrefix} className="flex flex-col gap-1.5">
              {header && <p className="font-medium">{renderInline(header, `${keyPrefix}-h`)}</p>}
              <List className="flex flex-col gap-1.5">
                {lines.map((line, li) => {
                  const cleaned = line.replace(type === "ordered" ? ORDERED_RE : BULLET_RE, "");
                  return (
                    <li key={`${keyPrefix}-${li}`} className="flex gap-2">
                      <span className={type === "ordered" ? "text-accent font-mono text-xs mt-0.5" : "text-ink-dim mt-0.5"}>
                        {type === "ordered" ? `${li + 1}.` : "•"}
                      </span>
                      <span>{renderInline(cleaned, `${keyPrefix}-${li}`)}</span>
                    </li>
                  );
                })}
              </List>
            </div>
          );
        }

        return <Paragraph key={keyPrefix} text={lines.join("\n")} keyPrefix={keyPrefix} />;
      })}
    </div>
  );
}
