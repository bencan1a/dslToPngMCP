export function renderDSLtoHTML({ width, height, elements, css }) {
  const renderElement = (el) => {
    const style = `
      position:absolute;
      left:${el.x || 0}px;
      top:${el.y || 0}px;
      width:${el.width || 100}px;
      height:${el.height || 40}px;
      ${el.style?.background ? `background:${el.style.background};` : ""}
      ${el.style?.color ? `color:${el.style.color};` : ""}
      ${el.style?.fontSize ? `font-size:${el.style.fontSize}px;` : ""}
      ${el.style?.fontWeight ? `font-weight:${el.style.fontWeight};` : ""}
    `.trim();

    const cls = el.class ? `class="${el.class}"` : "";

    if (el.type === "button") {
      return `<button ${cls} style="${style}">${el.label || "Button"}</button>`;
    }

    if (el.type === "text") {
      return `<div ${cls} style="${style}">${el.text || "Text"}</div>`;
    }

    if (el.type === "input") {
      return `<input ${cls} style="${style}" placeholder="${el.placeholder || ""}" />`;
    }

    return ""; // Unrecognized types are skipped
  };

  const body = elements.map(renderElement).join("\n");

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body {
          margin: 0;
          position: relative;
          width: ${width}px;
          height: ${height}px;
        }
        ${css}
      </style>
    </head>
    <body>
      ${body}
    </body>
    </html>
  `;
}
