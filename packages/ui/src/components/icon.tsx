import { icons, type LucideProps } from "lucide-react"
import { cn } from "cn"

export type IconName = keyof typeof icons

export interface IconProps extends Omit<LucideProps, "ref" | "color"> {
  name: IconName
  /** Defaults to 16. Accepts number (px) or CSS string. */
  size?: number | string
  /** Defaults to "currentColor" — inherits text color via CSS. */
  color?: string
}

/**
 * Renders a Lucide icon by name. Color defaults to `currentColor` so the icon
 * inherits the surrounding text color automatically.
 *
 * Interactive usage: wrap in a `<button>` or `<a>` with `aria-label` and
 * ensure the touch target is at least 44 × 44 CSS px (e.g. `size-11 p-3`).
 */
function Icon({
  name,
  size = 16,
  color = "currentColor",
  className,
  strokeWidth = 2,
  ...props
}: IconProps) {
  const LucideIcon = icons[name]
  if (!LucideIcon) return null

  return (
    <LucideIcon
      size={size}
      color={color}
      strokeWidth={strokeWidth}
      className={cn("shrink-0", className)}
      {...props}
    />
  )
}

export { Icon }
