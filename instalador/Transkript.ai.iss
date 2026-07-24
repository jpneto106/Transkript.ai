; ============================================================================
;  Instalador do Transkript.ai  ·  Inno Setup 6
;
;  Compilar (depois de rodar empacotar.py):
;      "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" instalador\Transkript.ai.iss
;
;  Duas exigências guiaram este arquivo:
;
;  1. PLUG AND PLAY — o mínimo de cliques e nenhuma senha de administrador.
;     Por isso a instalação vai para a pasta do usuário (%LOCALAPPDATA%), onde
;     não é preciso elevar privilégios, e as telas de boas-vindas e de grupo do
;     menu Iniciar foram desligadas.
;
;  2. DESINSTALAR SEM DEIXAR RASTRO — o desinstalador remove também o que o
;     programa criou DEPOIS de instalado (modelos, banco, logs, perfil da
;     janela). Instaladores comuns esquecem disso, e é justamente daí que vêm
;     as pastas órfãs em AppData. Ver as seções [UninstallDelete] e [Code].
; ============================================================================

#define MeuNome        "Transkript.ai"
#define MinhaVersao    "2.0.0"
#define MeuAutor       "JP.Neto"
#define MeuSite        "https://github.com/jpneto106/Transkript.ai"
#define MeuExecutavel  "Transkript.ai.exe"

[Setup]
; Identificador fixo do programa. NÃO mudar entre versões: é por ele que o
; Windows reconhece uma atualização em vez de instalar uma segunda cópia.
AppId={{8F3A2C7E-5B41-4D96-9A2F-1C7E4D8B6A31}
AppName={#MeuNome}
AppVersion={#MinhaVersao}
AppVerName={#MeuNome} {#MinhaVersao}
AppPublisher={#MeuAutor}
AppPublisherURL={#MeuSite}
AppSupportURL={#MeuSite}/issues
AppUpdatesURL={#MeuSite}/releases
UninstallDisplayName={#MeuNome}
UninstallDisplayIcon={app}\{#MeuExecutavel}

; Instala na pasta do usuário: sem pedido de senha de administrador.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#MeuNome}
DefaultGroupName={#MeuNome}

; Menos cliques. A escolha da pasta CONTINUA disponível de propósito: são quase
; 3 GB, e quem tem o disco C: cheio precisa poder mandar para outra unidade.
DisableWelcomePage=yes
DisableProgramGroupPage=yes
AllowNoIcons=yes

OutputDir=..\dist
OutputBaseFilename={#MeuNome}-{#MinhaVersao}-instalador
SetupIconFile=..\app.ico
WizardStyle=modern

Compression=lzma2/max
SolidCompression=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; Fecha o programa sozinho se ele estiver aberto durante uma atualização.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Área de Trabalho"; \
    GroupDescription: "Atalhos:"

[Files]
; As pastas excluídas nascem do USO do programa, não fazem parte dele. Se a
; máquina de compilação tiver sido usada para testar, elas estarão cheias —
; e sem esta exclusão o instalador sairia carregando modelos de 500 MB e o
; histórico de transcrições de quem compilou.
Source: "..\dist\{#MeuNome}\*"; DestDir: "{app}"; \
    Excludes: "\modelos,\dados,\entrada,\saida"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MeuNome}"; Filename: "{app}\{#MeuExecutavel}"
Name: "{autodesktop}\{#MeuNome}"; Filename: "{app}\{#MeuExecutavel}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MeuExecutavel}"; Description: "Abrir o {#MeuNome} agora"; \
    Flags: nowait postinstall skipifsilent

; ----------------------------------------------------------------------------
;  A parte que quase todo instalador erra.
;
;  O Inno remove sozinho apenas os arquivos que ELE instalou. Tudo o que o
;  programa cria depois — perfil da janela, logs, arquivos de entrada e saída —
;  ficaria para trás. É preciso listar explicitamente.
;
;  Os modelos e o histórico não estão aqui porque são tratados na seção [Code],
;  que pergunta ao usuário antes de apagá-los.
; ----------------------------------------------------------------------------
[UninstallDelete]
Type: filesandordirs; Name: "{app}\servidor"
Type: filesandordirs; Name: "{app}\frontend"
Type: filesandordirs; Name: "{app}\ferramentas"
Type: filesandordirs; Name: "{app}\entrada"
Type: filesandordirs; Name: "{app}\saida"
Type: dirifempty;     Name: "{app}"

[Code]

{ Pergunta uma única vez, no início da desinstalação, se os dados do usuário
  também devem sair. Marcado como "Sim" por padrão: o objetivo declarado é não
  deixar resíduo. Quem pretende reinstalar pode responder "Não" e poupar o
  download dos modelos. }
procedure CurUninstallStepChanged(CurStep: TUninstallStep);
var
  Resposta: Integer;
begin
  if CurStep = usUninstall then
  begin
    { Numa desinstalação automatizada (/SILENT) não há ninguém para clicar.
      Perguntar ali deixaria o desinstalador parado para sempre, esperando uma
      resposta que nunca vem. Nesse caso seguimos o objetivo declarado do
      projeto: remover tudo. }
    if UninstallSilent() then
      Resposta := IDYES
    else
      Resposta := MsgBox(
        'Remover também os modelos de transcrição baixados e o histórico?' + #13#10 + #13#10 +
        'Sim — apaga tudo, sem deixar nenhum arquivo no computador.' + #13#10 +
        'Não — mantém os modelos e o histórico, caso você pretenda reinstalar' + #13#10 +
        '        (assim não precisará baixar os modelos de novo).',
        mbConfirmation, MB_YESNO);

    if Resposta = IDYES then
    begin
      DelTree(ExpandConstant('{app}\modelos'), True, True, True);
      DelTree(ExpandConstant('{app}\dados'), True, True, True);
    end
    else
    begin
      { Mesmo mantendo os dados, o perfil da janela e os logs podem ir: são
        cache, recriados sozinhos, e só ocupam espaço. }
      DelTree(ExpandConstant('{app}\dados\janela'), True, True, True);
      DeleteFile(ExpandConstant('{app}\dados\launcher.log'));
      DeleteFile(ExpandConstant('{app}\dados\servidor.log'));
    end;
  end;
end;
