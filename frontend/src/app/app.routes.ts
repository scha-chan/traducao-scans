import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/folders/folder-list.page').then(m => m.FolderListPage),
  },
  {
    path: 'nova-traducao',
    loadComponent: () =>
      import('./features/new-translation/new-translation.page').then(m => m.NewTranslationPage),
  },
  {
    path: 'pastas/:folderId',
    loadComponent: () =>
      import('./features/folder-detail/folder-detail.page').then(m => m.FolderDetailPage),
  },
  { path: '**', redirectTo: '' },
];
