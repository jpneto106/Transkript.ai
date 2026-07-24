namespace Transkript;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();

        var raiz = DescobrirRaiz(args);
        var modoDesenvolvedor = args.Contains("--dev");

        Application.Run(new JanelaPrincipal(raiz, modoDesenvolvedor));
    }

    /// <summary>
    /// Descobre a pasta do programa (onde ficam servidor/, modelos/, dados/, app.ico).
    ///
    /// A ordem importa. Instalado, o executável já está na raiz e o servidor
    /// empacotado fica ao lado dele — esse caso precisa ser reconhecido ANTES da
    /// busca por "api\main.py", senão um código-fonte existente em alguma pasta
    /// acima seria escolhido por engano.
    /// </summary>
    private static string DescobrirRaiz(string[] args)
    {
        // 1. Apontado à mão (testes).
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (args[i] == "--raiz")
                return Path.GetFullPath(args[i + 1]);
        }

        // 2. Instalado: o servidor empacotado está ao lado do executável.
        var aoLado = AppContext.BaseDirectory;
        if (File.Exists(Path.Combine(aoLado, "servidor", "servidor.exe")))
            return aoLado;

        // 3. Desenvolvimento: o executável está em casca\bin\Debug\...,
        //    então subimos até encontrar o código-fonte.
        var pasta = aoLado;
        for (int nivel = 0; nivel < 8 && !string.IsNullOrEmpty(pasta); nivel++)
        {
            if (File.Exists(Path.Combine(pasta, "api", "main.py")))
                return pasta;
            pasta = Path.GetDirectoryName(pasta.TrimEnd(Path.DirectorySeparatorChar));
        }

        return aoLado;
    }
}
