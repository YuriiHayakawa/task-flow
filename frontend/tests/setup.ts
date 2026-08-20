import "@testing-library/jest-dom/vitest";

// jsdom não implementa scrollIntoView nem a API de Pointer Capture —
// necessário para o Select do Radix (shadcn/ui) não quebrar ao abrir/
// selecionar um item em teste (primeiro uso real disso é TaskDetailPage,
// edição inline de status/prioridade).
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => {};
}

// jsdom não implementa matchMedia — necessário para o hook useIsMobile do
// componente de sidebar (shadcn/ui) não quebrar em ambiente de teste.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
