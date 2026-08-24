import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

/** Renders the agent's reply as real markdown -- prompt.py's Formatting
 * section commits the model to a fixed shape (bold labels, one fact per
 * line, never a number buried inside a sentence), and this is the other
 * half of that contract: trust the markdown instead of guessing structure
 * out of loose prose after the fact.
 *
 * remarkBreaks matters here specifically: the option template puts the
 * train name and the route on adjacent lines with no blank line between
 * them (a "soft break" in CommonMark), which renders as a plain space by
 * default -- exactly the wall-of-text problem this exists to fix. With it,
 * a single newline is a real line break. */
export default function FormattedText({ text }: { text: string }) {
  return (
    <div className="text-ink flex flex-col gap-2 text-sm leading-relaxed [&_p]:whitespace-normal">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          p: ({ children }) => <p>{children}</p>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          ul: ({ children }) => (
            <ul className="marker:text-ink-dim ml-4 flex list-disc flex-col gap-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="marker:text-accent marker:font-mono ml-4 flex list-decimal flex-col gap-1">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="pl-1">{children}</li>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-accent underline">
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="bg-raised-2 rounded px-1 py-0.5 font-mono text-xs">{children}</code>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-rail text-ink-dim border-b px-2 py-1 text-left font-medium">
              {children}
            </th>
          ),
          td: ({ children }) => <td className="border-rail border-b px-2 py-1">{children}</td>,
          hr: () => <hr className="border-rail my-1" />,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
