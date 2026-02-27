document$.subscribe(function () {
  if (window.mermaid) {
    window.mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });
    window.mermaid.run();
  }
});
