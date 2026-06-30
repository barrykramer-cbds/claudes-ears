import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-button text-sm font-medium tracking-[-0.01em] whitespace-nowrap transition-[transform,background-color,border-color,opacity] duration-150 ease-out outline-none focus-visible:ring-2 focus-visible:ring-accent active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-accent-fg shadow-[inset_0_1px_0_0_rgba(255,255,255,0.17)] hover:bg-accent-hover",
        secondary: "bg-surface-hover text-fg border border-border-strong hover:border-faint",
        ghost: "text-muted hover:bg-surface-raised hover:text-fg",
      },
      size: {
        md: "h-9 px-4",
        sm: "h-7 px-3 text-xs",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type ButtonProps = React.ComponentProps<"button"> & VariantProps<typeof buttonVariants>;

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
