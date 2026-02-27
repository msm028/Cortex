document$.subscribe(function () {
  if (!window.mermaid) return;

  window.mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
  });

  const blocks = document.querySelectorAll("pre.mermaid");
  blocks.forEach(function (block, idx) {
    if (block.dataset.processed === "true") return;

    const source = block.textContent || "";
    const graphId = "mermaid-" + Date.now() + "-" + idx;

    window.mermaid
      .render(graphId, source)
      .then(function (result) {
        const container = document.createElement("div");
        container.className = "mermaid-rendered";
        container.innerHTML = result.svg;
        block.replaceWith(container);
        if (result.bindFunctions) result.bindFunctions(container);
      })
      .catch(function () {
        block.dataset.processed = "true";
      });
  });
});
