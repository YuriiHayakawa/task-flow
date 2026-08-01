import "@testing-library/jest-dom/vitest";

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
