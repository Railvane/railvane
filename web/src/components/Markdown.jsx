import { useMemo } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";

// Wikilinks become clickable spans; the reader resolves them by name
const WIKILINK = /\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]/g;

export default function Markdown({ text, onWikilink }) {
  const html = useMemo(() => {
    const withLinks = text.replace(WIKILINK, (_, name) =>
      `<span class="wikilink" data-link="${encodeURIComponent(name.trim())}">${name.trim()}</span>`);
    return DOMPurify.sanitize(marked.parse(withLinks, { gfm: true }), { ADD_ATTR: ["data-link"] });
  }, [text]);

  const onClick = e => {
    const link = e.target.closest?.(".wikilink");
    if (link && onWikilink) onWikilink(decodeURIComponent(link.dataset.link));
  };

  return <div className="markdown" onClick={onClick} dangerouslySetInnerHTML={{ __html: html }} />;
}
