import { Toaster as SonnerToaster } from "sonner"

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast: "bg-background border-border",
          title: "text-foreground",
          description: "text-muted-foreground",
        },
      }}
    />
  )
}

