import { Highlight, themes } from "prism-react-renderer";

const LANGUAGES = { py: "python", js: "javascript", jsx: "jsx", ts: "typescript", tsx: "tsx", json: "json", md: "markdown", yml: "yaml", yaml: "yaml", css: "css", html: "markup", toml: "toml" };

export function languageFor(path = "") {
  const extension = path.split(".").pop().toLowerCase();
  return LANGUAGES[extension] || "text";
}

/** Syntax-highlighted, line-numbered code viewer. */
export function CodeBlock({ code, path }) {
  return (
    <Highlight theme={themes.oneLight} code={code || ""} language={languageFor(path)}>
      {({ className, style, tokens, getLineProps, getTokenProps }) => (
        <pre className={`${className} overflow-auto text-[12.5px] leading-relaxed font-mono py-4`} style={{ ...style, background: "transparent" }}>
          {tokens.map((line, index) => {
            const lineProps = getLineProps({ line });
            return (
              <div key={index} {...lineProps} className={`${lineProps.className} table-row`}>
                <span className="table-cell select-none pr-4 pl-4 text-right text-slate-300 w-10">{index + 1}</span>
                <span className="table-cell pr-4">
                  {line.map((token, key) => (
                    <span key={key} {...getTokenProps({ token })} />
                  ))}
                </span>
              </div>
            );
          })}
        </pre>
      )}
    </Highlight>
  );
}
