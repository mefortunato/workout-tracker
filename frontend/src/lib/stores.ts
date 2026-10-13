import { writable } from 'svelte/store';
import type { User, ToastMessage } from './types';
import { api } from './api';

export const userStore = writable<User | null>(null);
export const loadingUser = writable<boolean>(true);
export const toasts = writable<ToastMessage[]>([]);

export function addToast(title: string, message: string, type: 'success' | 'info' | 'error' = 'success') {
  const id = Math.random().toString(36).substring(2, 9);
  const toast: ToastMessage = { id, title, message, type };
  toasts.update((all) => [...all, toast]);
  setTimeout(() => {
    removeToast(id);
  }, 4000);
}

export function removeToast(id: string) {
  toasts.update((all) => all.filter((t) => t.id !== id));
}

export async function checkAuth(): Promise<User | null> {
  loadingUser.set(true);
  try {
    const user = await api.getCurrentUser();
    userStore.set(user);
    return user;
  } catch (err) {
    userStore.set(null);
    return null;
  } finally {
    loadingUser.set(false);
  }
}
