import { Injectable, signal, computed } from '@angular/core';

export type NotificationType = 'success' | 'error' | 'info';

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string; // ISO
  read: boolean;
}

const STORAGE_KEY = 'app_notifications';
const MAX_NOTIFICATIONS = 50;

@Injectable({ providedIn: 'root' })
export class NotificationService {
  readonly notifications = signal<AppNotification[]>(this._load());

  readonly unreadCount = computed(() => this.notifications().filter((n) => !n.read).length);

  add(title: string, message: string, type: NotificationType = 'info'): void {
    const n: AppNotification = {
      id: Math.random().toString(36).slice(2),
      type,
      title,
      message,
      timestamp: new Date().toISOString(),
      read: false,
    };
    this.notifications.update((list) => {
      const updated = [n, ...list].slice(0, MAX_NOTIFICATIONS);
      this._save(updated);
      return updated;
    });
  }

  markAllRead(): void {
    this.notifications.update((list) => {
      const updated = list.map((n) => ({ ...n, read: true }));
      this._save(updated);
      return updated;
    });
  }

  remove(id: string): void {
    this.notifications.update((list) => {
      const updated = list.filter((n) => n.id !== id);
      this._save(updated);
      return updated;
    });
  }

  clearAll(): void {
    this.notifications.set([]);
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  }

  private _load(): AppNotification[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as AppNotification[]) : [];
    } catch {
      return [];
    }
  }

  private _save(list: AppNotification[]): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch { /* ignore */ }
  }
}
