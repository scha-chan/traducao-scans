import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiBase } from '../http/api-base';
import { Character, CharacterCreate, CharacterUpdate } from './models';

@Injectable({ providedIn: 'root' })
export class CharactersApi extends ApiBase {
  listByWork(workId: string): Observable<Character[]> {
    return this.http.get<Character[]>(this.url(`/api/works/${workId}/characters`));
  }

  create(workId: string, body: CharacterCreate): Observable<Character> {
    return this.http.post<Character>(this.url(`/api/works/${workId}/characters`), body);
  }

  update(characterId: string, body: CharacterUpdate): Observable<Character> {
    return this.http.patch<Character>(this.url(`/api/characters/${characterId}`), body);
  }

  remove(characterId: string): Observable<void> {
    return this.http.delete<void>(this.url(`/api/characters/${characterId}`));
  }
}
