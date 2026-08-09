import { cn } from "@/lib/utils";

// Reusable Dograh wordmark. Theme-aware by default: the dark logo shows on light
// surfaces and the light/cream logo shows on dark. Pass `inverse` to force the
// light logo on an always-dark surface (e.g. the auth brand panel). Pass `mark`
// to render the square logo mark instead of the full wordmark (e.g. the app
// sidebar header). Height is controlled by the caller via className (e.g.
// "h-7"); width stays auto so each lockup keeps its aspect ratio.
export function BrandLogo({
  className,
  inverse = false,
  mark = false,
}: {
  className?: string;
  inverse?: boolean;
  mark?: boolean;
}) {
  if (mark) {
    return (
      <div className={cn("flex items-center gap-2 font-bold tracking-tight text-primary text-xl select-none", className)}>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-black text-sm">
          K
        </span>
      </div>
    );
  }
  return (
    <div className={cn("flex items-center gap-2 font-bold tracking-tight text-xl select-none", inverse ? "text-white" : "text-foreground", className)}>
      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-white font-black text-xs">
        KW
      </span>
      <span className="font-extrabold text-lg tracking-wide">
        Kode<span className="text-blue-500">waves</span>
      </span>
    </div>
  );
}
