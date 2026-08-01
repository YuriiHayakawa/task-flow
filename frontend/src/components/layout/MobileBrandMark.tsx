import { Workflow } from "lucide-react";

/** Marca visível apenas em telas pequenas, onde o `BrandPanel` (lg+) fica oculto. */
export function MobileBrandMark() {
  return (
    <div className="flex flex-col items-center gap-3 text-center lg:hidden">
      <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/20">
        <Workflow className="size-5 text-white" strokeWidth={2.25} />
      </div>
      <span className="text-base font-semibold tracking-tight">TaskFlow</span>
    </div>
  );
}
