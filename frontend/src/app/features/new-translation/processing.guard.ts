import { CanDeactivateFn } from '@angular/router';
import { NewTranslationPage } from './new-translation.page';

export const processingGuard: CanDeactivateFn<NewTranslationPage> = (component) => {
  if (component.appState() !== 'processando') return true;
  return window.confirm('O processamento será interrompido. Sair mesmo assim?');
};
