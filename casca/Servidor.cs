using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;

namespace Transkript;

/// <summary>
/// Cuida do servidor Python (FastAPI/uvicorn): acha onde ele está, escolhe uma
/// porta livre, sobe o processo e garante que ele morre junto com a janela.
///
/// A garantia de morte conjunta vem de um Job Object do Windows com a marca
/// KILL_ON_JOB_CLOSE — o mesmo truque que o launcher em Python já usava. É o que
/// evita servidor órfão e, principalmente, o que libera a memória da placa de
/// vídeo (o modelo vive no processo do servidor).
/// </summary>
internal sealed class Servidor : IDisposable
{
    private Process? _processo;
    private IntPtr _job = IntPtr.Zero;
    private readonly string _raiz;
    private readonly string _pastaDados;

    public int Porta { get; private set; }
    public string Url => $"http://127.0.0.1:{Porta}/";

    public Servidor(string raiz)
    {
        _raiz = raiz;
        _pastaDados = Path.Combine(raiz, "dados");
        Directory.CreateDirectory(_pastaDados);
    }

    /// <summary>Registra no mesmo log que o launcher antigo usava.</summary>
    public void Log(string mensagem)
    {
        try
        {
            File.AppendAllText(Path.Combine(_pastaDados, "launcher.log"),
                $"[{DateTime.Now:HH:mm:ss}] (casca) {mensagem}{Environment.NewLine}");
        }
        catch { /* log nunca pode derrubar o app */ }
    }

    /// <summary>Pede ao Windows uma porta livre qualquer.</summary>
    private static int PortaLivre()
    {
        var ouvinte = new TcpListener(IPAddress.Loopback, 0);
        ouvinte.Start();
        int porta = ((IPEndPoint)ouvinte.LocalEndpoint).Port;
        ouvinte.Stop();
        return porta;
    }

    /// <summary>
    /// Monta o comando do servidor. Aceita duas situações:
    ///   1. Instalado: existe "servidor\servidor.exe" (Python empacotado).
    ///   2. Desenvolvimento: usa o "venv\Scripts\python.exe" da pasta.
    /// </summary>
    private ProcessStartInfo? MontarComando()
    {
        var empacotado = Path.Combine(_raiz, "servidor", "servidor.exe");
        if (File.Exists(empacotado))
        {
            Log($"servidor empacotado: {empacotado}");
            return new ProcessStartInfo(empacotado)
            {
                Arguments = $"--host 127.0.0.1 --port {Porta}",
                WorkingDirectory = _raiz,
            };
        }

        // Em desenvolvimento pode haver mais de um ambiente Python. O da v3
        // (com a identificação de falantes) tem prioridade; o antigo continua
        // servindo para rodar a versão anterior sem as bibliotecas pesadas.
        var python = "";
        foreach (var pasta in new[] { "venv-v3", "venv" })
        {
            var candidato = Path.Combine(_raiz, pasta, "Scripts", "python.exe");
            if (File.Exists(candidato)) { python = candidato; break; }
        }

        if (python.Length > 0)
        {
            Log($"modo desenvolvimento, usando: {python}");
            var info = new ProcessStartInfo(python)
            {
                WorkingDirectory = _raiz,
            };
            foreach (var arg in new[]
            {
                "-m", "uvicorn", "api.main:app",
                "--host", "127.0.0.1",
                "--port", Porta.ToString(),
                "--log-level", "warning",
            })
            {
                info.ArgumentList.Add(arg);
            }
            return info;
        }

        Log("ERRO: nem servidor.exe nem venv encontrados");
        return null;
    }

    /// <summary>Sobe o servidor. Devolve false se não achou como executá-lo.</summary>
    public bool Iniciar()
    {
        Porta = PortaLivre();
        Log($"porta escolhida: {Porta}");

        var info = MontarComando();
        if (info is null) return false;

        info.UseShellExecute = false;
        info.CreateNoWindow = true;   // servidor roda invisível
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;

        // Diz ao Python onde fica a pasta do aplicativo. Sem isto, o servidor
        // empacotado guardaria modelos e banco dentro do próprio executável —
        // lugares que o desinstalador não varre.
        info.Environment["TRANSKRIPT_RAIZ"] = _raiz;

        _processo = new Process { StartInfo = info, EnableRaisingEvents = true };

        // A saída do servidor vai para dados\servidor.log (ajuda a diagnosticar).
        var logServidor = Path.Combine(_pastaDados, "servidor.log");
        try { File.WriteAllText(logServidor, ""); } catch { }
        void Registrar(object _, DataReceivedEventArgs e)
        {
            if (e.Data is null) return;
            try { File.AppendAllText(logServidor, e.Data + Environment.NewLine); } catch { }
        }
        _processo.OutputDataReceived += Registrar;
        _processo.ErrorDataReceived += Registrar;

        _processo.Start();
        _processo.BeginOutputReadLine();
        _processo.BeginErrorReadLine();
        Log($"servidor iniciado, pid {_processo.Id}");

        AmarrarAoJob(_processo);
        return true;
    }

    /// <summary>
    /// Espera o servidor responder em /api/saude. Devolve false se desistiu.
    /// </summary>
    public async Task<bool> EsperarFicarPronto(TimeSpan limite)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromMilliseconds(400) };
        var prazo = DateTime.UtcNow + limite;

        while (DateTime.UtcNow < prazo)
        {
            if (_processo is { HasExited: true })
            {
                Log($"servidor morreu antes de responder (código {_processo.ExitCode})");
                return false;
            }
            try
            {
                var resposta = await http.GetAsync(Url + "api/saude");
                if (resposta.IsSuccessStatusCode)
                {
                    Log("servidor pronto");
                    return true;
                }
            }
            catch { /* ainda subindo */ }

            await Task.Delay(120);
        }

        Log("ERRO: servidor não respondeu no prazo");
        return false;
    }

    // ---------- Job Object: mata o servidor junto com a janela ----------

    private const int ClasseLimiteEstendido = 9;          // JobObjectExtendedLimitInformation
    private const uint MatarAoFecharJob = 0x00002000;     // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

    [StructLayout(LayoutKind.Sequential)]
    private struct JobObjectBasicLimitInformation
    {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct IoCounters
    {
        public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
        public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct JobObjectExtendedLimitInformation
    {
        public JobObjectBasicLimitInformation BasicLimitInformation;
        public IoCounters IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr CreateJobObject(IntPtr atributos, string? nome);

    [DllImport("kernel32.dll")]
    private static extern bool SetInformationJobObject(
        IntPtr job, int classe, IntPtr info, uint tamanho);

    [DllImport("kernel32.dll")]
    private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr processo);

    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr objeto);

    private void AmarrarAoJob(Process processo)
    {
        try
        {
            _job = CreateJobObject(IntPtr.Zero, null);
            if (_job == IntPtr.Zero) { Log("aviso: CreateJobObject falhou"); return; }

            var info = new JobObjectExtendedLimitInformation();
            info.BasicLimitInformation.LimitFlags = MatarAoFecharJob;

            int tamanho = Marshal.SizeOf(info);
            IntPtr ponteiro = Marshal.AllocHGlobal(tamanho);
            try
            {
                Marshal.StructureToPtr(info, ponteiro, false);
                SetInformationJobObject(_job, ClasseLimiteEstendido,
                                        ponteiro, (uint)tamanho);
            }
            finally { Marshal.FreeHGlobal(ponteiro); }

            AssignProcessToJobObject(_job, processo.Handle);
            Log("servidor amarrado ao Job Object");
        }
        catch (Exception erro)
        {
            Log($"aviso: Job Object falhou: {erro.Message}");
        }
    }

    public void Dispose()
    {
        // Fechar o Job já mata o servidor; o resto é cinto e suspensório.
        try
        {
            if (_processo is { HasExited: false }) _processo.Kill(entireProcessTree: true);
        }
        catch { }

        try { if (_job != IntPtr.Zero) CloseHandle(_job); } catch { }
        _job = IntPtr.Zero;

        _processo?.Dispose();
        _processo = null;
        Log("servidor encerrado");
    }
}
