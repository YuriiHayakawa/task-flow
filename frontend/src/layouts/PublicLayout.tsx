import { Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="flex min-h-svh items-center justify-center bg-muted/30 p-6">
      <div className="w-full max-w-sm">
        <Outlet />
      </div>
    </div>
  );
}
