import { cn } from "cn";
import { LogOut, Plus } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

interface SidebarProps {
  userEmail: string;
  conversationTitle: string | null;
  onNewChat: () => void;
  onLogout: () => void;
}

export function Sidebar({ userEmail, conversationTitle, onNewChat, onLogout }: SidebarProps) {
  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="flex flex-col gap-1 px-4 py-4">
        <img
          src="/brand/logo-uvg-altiplano-horizontal-blanco.png"
          alt="Universidad del Valle de Guatemala"
          className="h-7 w-auto"
        />
        <p className="text-xs font-medium text-sidebar-foreground/60">
          Asistente Virtual · Campus Altiplano
        </p>
      </div>

      <Separator className="bg-sidebar-border" />

      <div className="px-3 pt-3">
        <Button
          onClick={onNewChat}
          variant="outline"
          className="w-full justify-start gap-2 border-white/15 bg-white/5 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          <Plus className="size-4" />
          Nueva conversación
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4">
        <p className="px-2 pb-2 text-xs font-medium tracking-wide text-sidebar-foreground/50 uppercase">
          Conversaciones
        </p>
        {conversationTitle ? (
          <div
            className={cn(
              "w-full truncate rounded-lg bg-sidebar-accent px-3 py-2 text-left text-sm",
              "text-sidebar-accent-foreground",
            )}
          >
            {conversationTitle}
          </div>
        ) : (
          <p className="px-2 text-xs text-sidebar-foreground/50">
            Aún no hay conversaciones. Escribe tu primera pregunta.
          </p>
        )}
      </div>

      <Separator className="bg-sidebar-border" />

      <div className="flex items-center justify-between gap-2 px-3 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <Avatar size="sm">
            <AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground">
              {userEmail.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <span className="truncate text-sm text-sidebar-foreground/80">{userEmail}</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onLogout}
          className="shrink-0 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          aria-label="Cerrar sesión"
        >
          <LogOut className="size-4" />
        </Button>
      </div>
    </aside>
  );
}
