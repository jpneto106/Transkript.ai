// Tipos compartilhados entre as telas.

export interface ModeloInfo {
  nome: string;
  rotulo: string;
  resumo: string;
  recomendado: boolean;
  tamanho_aprox_mb: number | null;
  baixado: boolean;
  tamanho_disco_mb: number | null;
  e_padrao: boolean;
  download_status?: "baixando" | "concluido" | "erro";
}

export interface Opcoes {
  modelos: string[];
  formatos: string[];
  pasta_saida: string;
}

export interface ParametrosTranscricao {
  entrada: string;
  modelo: string;
  idioma: string | null;
  tarefa: string;
  dispositivo: string;
  formatos: string[];
  max_caracteres: number;
  max_duracao: number;
  vad_filter: boolean;
}

export interface Transcricao {
  id: string;
  criado_em: string;
  atualizado_em: string;
  entrada_original: string;
  arquivo_local: string | null;
  nome_arquivo: string | null;
  modelo: string;
  idioma_solicitado: string | null;
  idioma_detectado: string | null;
  probabilidade_idioma: number | null;
  tarefa: string;
  dispositivo: string | null;
  formatos: string[];
  max_caracteres: number;
  max_duracao: number;
  pasta_saida: string;
  duracao_audio: number | null;
  tempo_processamento: number | null;
  status: string;
  progresso_segundos: number;
  mensagem_erro: string | null;
  arquivos_gerados: string[];
}

// Mensagens do WebSocket de progresso.
export interface EstadoAoVivo {
  tipo: "estado";
  id: string;
  status: string;
  rotulo_status: string;
  progresso_segundos: number;
  duracao_total: number | null;
  percentual: number | null;
  mensagem: string;
  erro: string | null;
  versao: number;
}

export interface MensagemConcluido {
  tipo: "concluido";
  transcricao: Transcricao;
}

export interface MensagemErro {
  tipo: "erro";
  mensagem: string;
  transcricao?: Transcricao;
}

export type MensagemWS = EstadoAoVivo | MensagemConcluido | MensagemErro;
