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
    /// Descobre a pasta do programa (onde ficam api/, venv/, dados/, app.ico).
    ///
    /// Instalado, o executável fica na própria raiz. Em desenvolvimento ele fica
    /// em casca\bin\Debug\..., então subimos os níveis até achar "api\main.py".
    /// O argumento --raiz permite apontar manualmente durante os testes.
    /// </summary>
    private static string DescobrirRaiz(string[] args)
    {
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (args[i] == "--raiz")
                return Path.GetFullPath(args[i + 1]);
        }

        var pasta = AppContext.BaseDirectory;
        for (int nivel = 0; nivel < 8 && !string.IsNullOrEmpty(pasta); nivel++)
        {
            if (File.Exists(Path.Combine(pasta, "api", "main.py")))
                return pasta;
            pasta = Path.GetDirectoryName(pasta.TrimEnd(Path.DirectorySeparatorChar));
        }

        return AppContext.BaseDirectory;
    }
}
