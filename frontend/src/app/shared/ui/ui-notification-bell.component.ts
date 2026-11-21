import {
  Component,
  HostListener,
  ElementRef,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService, AppNotification } from '../../core/notifications/notification.service';

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return 'agora';
  const m = Math.floor(s / 60);
  if (m < 60) return `há ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `há ${h}h`;
  const d = Math.floor(h / 24);
  return `há ${d}d`;
}

@Component({
  selector: 'ui-notification-bell',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative">
      <!-- Bell button -->
      <button
        type="button"
        (click)="toggle()"
        [attr.aria-label]="unreadCount() > 0 ? unreadCount() + ' notificações não lidas' : 'Notificações'"
        class="relative flex items-center justify-center size-9 rounded-lg text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors focus-visible:outline-none focus-visible:ring-2 ring-primary-500"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        @if (unreadCount() > 0) {
          <span class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-primary-600 text-white text-[10px] font-semibold leading-none select-none">
            {{ unreadCount() > 99 ? '99+' : unreadCount() }}
          </span>
        }
      </button>

      <!-- Dropdown -->
      @if (open()) {
        <div
          class="absolute right-0 top-11 w-80 max-h-[420px] flex flex-col rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-lg shadow-zinc-900/10 dark:shadow-black/30 z-50 overflow-hidden"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-4 py-3 border-b border-zinc-100 dark:border-zinc-800">
            <span class="text-sm font-semibold text-zinc-800 dark:text-zinc-100">Notificações</span>
            @if (notifications().length > 0) {
              <div class="flex items-center gap-2">
                @if (unreadCount() > 0) {
                  <button
                    type="button"
                    (click)="markAllRead()"
                    class="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 transition-colors"
                  >Marcar tudo como lido</button>
                  <span class="text-zinc-300 dark:text-zinc-700">·</span>
                }
                <button
                  type="button"
                  (click)="clearAll()"
                  class="text-xs text-zinc-400 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300 transition-colors"
                >Limpar</button>
              </div>
            }
          </div>

          <!-- List -->
          <div class="overflow-y-auto flex-1">
            @if (notifications().length === 0) {
              <div class="flex flex-col items-center justify-center py-10 gap-2 text-zinc-400 dark:text-zinc-600">
                <svg xmlns="http://www.w3.org/2000/svg" class="size-8 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                  <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                </svg>
                <span class="text-sm">Nenhuma notificação</span>
              </div>
            }
            @for (n of notifications(); track n.id) {
              <div
                class="flex items-start gap-3 px-4 py-3 border-b border-zinc-50 dark:border-zinc-800 last:border-0 transition-colors"
                [class.bg-primary-50]="!n.read"
                [class.dark:bg-primary-950]="!n.read"
              >
                <!-- Type icon -->
                <div class="shrink-0 mt-0.5" [class]="iconClass(n)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    @if (n.type === 'success') {
                      <polyline points="20 6 9 17 4 12"/>
                    } @else if (n.type === 'error') {
                      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    } @else {
                      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                    }
                  </svg>
                </div>

                <!-- Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-baseline justify-between gap-2">
                    <p class="text-sm font-medium text-zinc-800 dark:text-zinc-100 truncate">{{ n.title }}</p>
                    <span class="shrink-0 text-[11px] text-zinc-400 dark:text-zinc-500 tabular-nums">{{ relTime(n.timestamp) }}</span>
                  </div>
                  <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 line-clamp-2">{{ n.message }}</p>
                </div>

                <!-- Dismiss -->
                <button
                  type="button"
                  (click)="remove(n.id)"
                  class="shrink-0 mt-0.5 text-zinc-300 hover:text-zinc-500 dark:text-zinc-700 dark:hover:text-zinc-400 transition-colors"
                  aria-label="Remover notificação"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
})
export class UiNotificationBellComponent {
  private readonly svc = inject(NotificationService);
  private readonly el = inject(ElementRef);

  readonly open = signal(false);
  readonly notifications = this.svc.notifications;
  readonly unreadCount = this.svc.unreadCount;

  toggle(): void {
    const next = !this.open();
    this.open.set(next);
    if (next && this.unreadCount() > 0) {
      this.svc.markAllRead();
    }
  }

  markAllRead(): void {
    this.svc.markAllRead();
  }

  clearAll(): void {
    this.svc.clearAll();
  }

  remove(id: string): void {
    this.svc.remove(id);
  }

  relTime(iso: string): string {
    return relativeTime(iso);
  }

  iconClass(n: AppNotification): string {
    if (n.type === 'success') return 'text-emerald-500';
    if (n.type === 'error') return 'text-red-500';
    return 'text-blue-500';
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.el.nativeElement.contains(event.target)) {
      this.open.set(false);
    }
  }
}
