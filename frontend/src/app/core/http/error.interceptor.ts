import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { ToastService } from '../../shared/ui';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);

  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse) {
        // 4xx: deixa o componente tratar (validação, 409, etc.)
        if (err.status >= 400 && err.status < 500) {
          return throwError(() => err);
        }
        // 5xx e erros de rede: toast genérico
        const msg =
          err.status === 0
            ? 'Sem conexão com o servidor.'
            : `Erro do servidor (${err.status}). Tente novamente.`;
        toast.error(msg);
      }
      return throwError(() => err);
    })
  );
};
