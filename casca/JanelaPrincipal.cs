using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace Transkript;

/// <summary>
/// A janela do programa. Mostra um aviso de "iniciando" enquanto o servidor
/// Python sobe e, assim que ele responde, troca pela interface web.
/// </summary>
internal sealed class JanelaPrincipal : Form
{
    private readonly Servidor _servidor;
    private readonly bool _modoDesenvolvedor;
    private readonly string _raiz;
    private WebView2? _navegador;
    private Label? _aviso;

    public JanelaPrincipal(string raiz, bool modoDesenvolvedor)
    {
        _raiz = raiz;
        _modoDesenvolvedor = modoDesenvolvedor;
        _servidor = new Servidor(raiz);

        Text = "Transkript.ai";
        ClientSize = new Size(1180, 840);
        MinimumSize = new Size(900, 640);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(24, 24, 27);

        // Ícone próprio na barra de tarefas — o motivo de existir esta casca.
        var ico = Path.Combine(raiz, "app.ico");
        if (File.Exists(ico))
        {
            try { Icon = new Icon(ico); } catch { }
        }

        _aviso = new Label
        {
            Text = "Iniciando o Transkript.ai…",
            Dock = DockStyle.Fill,
            TextAlign = ContentAlignment.MiddleCenter,
            ForeColor = Color.FromArgb(228, 228, 231),
            Font = new Font("Segoe UI", 12F, FontStyle.Regular),
        };
        Controls.Add(_aviso);

        Load += AoCarregar;
        FormClosed += (_, _) => _servidor.Dispose();
    }

    private async void AoCarregar(object? remetente, EventArgs e)
    {
        _servidor.Log("=== casca iniciando ===");

        if (!_servidor.Iniciar())
        {
            Falhar("Não foi possível iniciar o servidor do programa.\n\n" +
                   "Não encontrei nem o servidor empacotado nem o ambiente Python " +
                   $"na pasta:\n{_raiz}");
            return;
        }

        if (!await _servidor.EsperarFicarPronto(TimeSpan.FromSeconds(60)))
        {
            Falhar("O servidor do programa não respondeu a tempo.\n\n" +
                   $"Detalhes em:\n{Path.Combine(_raiz, "dados", "servidor.log")}");
            return;
        }

        await MostrarInterface();
    }

    private async Task MostrarInterface()
    {
        // O perfil do WebView2 fica DENTRO da pasta do programa. Sem isso o
        // Windows cria uma pasta solta em AppData que sobrevive à desinstalação.
        var perfil = Path.Combine(_raiz, "dados", "janela");
        Directory.CreateDirectory(perfil);

        var ambiente = await CoreWebView2Environment.CreateAsync(null, perfil);

        _navegador = new WebView2 { Dock = DockStyle.Fill };
        Controls.Add(_navegador);
        await _navegador.EnsureCoreWebView2Async(ambiente);

        var nucleo = _navegador.CoreWebView2;
        var opcoes = nucleo.Settings;

        // Deixar com cara de programa, não de navegador.
        opcoes.AreDefaultContextMenusEnabled = _modoDesenvolvedor;
        opcoes.AreDevToolsEnabled = _modoDesenvolvedor;
        opcoes.IsStatusBarEnabled = false;
        opcoes.IsSwipeNavigationEnabled = false;
        opcoes.IsZoomControlEnabled = true;

        // Link externo abre no navegador padrão, e não numa janela sem controles.
        nucleo.NewWindowRequested += (_, evento) =>
        {
            evento.Handled = true;
            AbrirNoNavegadorPadrao(evento.Uri);
        };

        nucleo.Navigate(_servidor.Url);

        if (_aviso is not null)
        {
            Controls.Remove(_aviso);
            _aviso.Dispose();
            _aviso = null;
        }

        _navegador.Focus();
        _servidor.Log("interface carregada");
    }

    private static void AbrirNoNavegadorPadrao(string url)
    {
        try
        {
            System.Diagnostics.Process.Start(
                new System.Diagnostics.ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch { }
    }

    private void Falhar(string mensagem)
    {
        _servidor.Log("FALHA: " + mensagem.Replace("\n", " "));
        MessageBox.Show(this, mensagem, "Transkript.ai",
                        MessageBoxButtons.OK, MessageBoxIcon.Error);
        Close();
    }
}
