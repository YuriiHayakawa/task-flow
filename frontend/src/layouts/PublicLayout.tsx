import { Outlet } from "react-router-dom";

import { BrandPanel } from "@/components/layout/BrandPanel";

export function PublicLayout() {
  return (
    <div className="flex min-h-svh">
      <BrandPanel />
      <div className="flex flex-1 items-center justify-center bg-background p-6">
        <div className="w-full max-w-lg">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
