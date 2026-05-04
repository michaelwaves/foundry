import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from 'radix-ui'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:brightness-110',
        outline:
          'border-border bg-background hover:bg-accent hover:text-accent-foreground aria-expanded:bg-accent aria-expanded:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:brightness-110',
        ghost:
          'hover:bg-accent hover:text-accent-foreground aria-expanded:bg-accent aria-expanded:text-accent-foreground',
        destructive:
          'bg-destructive/10 text-destructive hover:bg-destructive/20 focus-visible:border-destructive/40 focus-visible:ring-destructive/20',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 gap-1.5 px-3',
        xs: 'h-7 gap-1 rounded-md px-2 text-xs [&_svg:not([class*=size-])]:size-3',
        sm: 'h-8 gap-1.5 rounded-md px-2.5 text-[0.8rem] [&_svg:not([class*=size-])]:size-3.5',
        lg: 'h-10 gap-2 px-4',
        icon: 'size-9',
        'icon-sm': 'size-8 rounded-md',
        'icon-lg': 'size-10',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

function Button({
  className,
  variant = 'default',
  size = 'default',
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : 'button'
  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
