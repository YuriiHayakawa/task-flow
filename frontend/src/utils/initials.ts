/** Iniciais de um nome para avatares — primeira+última palavra, ou as duas
 * primeiras letras quando só há uma palavra. Reaproveitado em qualquer tela
 * que exiba avatares de usuário (workspace members, participantes de
 * tarefa). */
export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0] + parts[parts.length - 1]![0]).toUpperCase();
}
