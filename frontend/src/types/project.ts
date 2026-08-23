export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  /** 003-membros-projeto: `true` se o usuário autenticado tem acesso ao
   * conteúdo (quadro/tarefas) deste projeto — Owner do workspace sempre,
   * ou membro explícito. Admin pode ver o projeto na listagem com
   * `is_member: false` (visível, mas sem poder abrir). */
  is_member: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  description?: string | null;
}
